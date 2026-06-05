"""Shared helpers used by every TSMIS export script.

Keeps one copy of: the report URL, the route list, auth file location,
auth validation, and the Playwright navigation helpers. Report-specific
logic (which report to pick, how to save the result) lives in ReportSpec
objects (see exporter.py) so a change to one report does not affect the
others.

This module is console-free: auth problems raise AuthError and progress is
reported through an Events sink, so the same helpers back both the console
shim (cli.py) and the future GUI.
"""
import json
import os
import re
import time

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    PlaywrightTimeoutError = Exception  # only hit if Playwright isn't installed yet


class AuthError(Exception):
    """Raised when the saved TSMIS session is missing, expired, or corrupt.

    The core raises this; the caller (the console shim in cli.py, or the GUI)
    decides how to tell the user and whether to clear the stale file.
    """


class PreflightError(Exception):
    """Raised when the TSMIS page doesn't look as expected before a run (likely
    a site change). Its message is user-safe and UI-neutral, so callers can show
    it as-is."""


class BrowserNotFoundError(Exception):
    """Raised when no usable Chromium-based browser (Edge or Chrome) is installed
    on the machine. The app drives the browser already present rather than
    bundling one, so this is the "please install Edge" case. Message is user-safe
    and UI-neutral."""


URL = "https://rhansonrizing.github.io/tsmis_reports/index.html"

# The shared auth file path is resolved by paths.py, which is frozen-aware: in
# the packaged build it lives next to the .exe (auto-falling back to
# %LOCALAPPDATA% if that folder is read-only); in the dev / .bat workflow it
# stays at scripts/tsmis_auth.json. Re-exported here for login.py and cli.py.
# (Output paths also come from paths.py, imported directly by the exporter and
# consolidators.)
from paths import AUTH

# Timeouts (milliseconds). Increase these if reports are timing out.
#
#   REPORT_TIMEOUT_MS      Hard ceiling for a single route to render or
#                          download. Some routes (e.g. Route 5 Ramp Detail)
#                          legitimately take minutes, so this is generous.
#   SKIP_PROMPT_AFTER_MS   How long to wait before the soft "still working"
#                          status fires and the skip escape-hatch opens. The
#                          hard timeout still applies independently.
#   COUNTY_ENABLE_TIMEOUT_MS  Wait for the County dropdown to enable after
#                          District is set.
REPORT_TIMEOUT_MS = 360_000
SKIP_PROMPT_AFTER_MS = 60_000
COUNTY_ENABLE_TIMEOUT_MS = 60_000

# Fast mode runs several browsers at once, so the shared TSMIS server is under a
# heavier load and big reports (e.g. Highway Sequence) take noticeably longer to
# render/download. Give each route a more generous ceiling there than in the
# one-browser flow, or they time out purely because of the concurrency.
FAST_REPORT_TIMEOUT_MS = 600_000          # 10 min per route under parallel load

# Routes that still failed after the main run get one slow, serial second chance
# (see the retry pass in exporter.py). It runs one route at a time -- so the
# server isn't loaded by other browsers -- with the most generous window.
RETRY_REPORT_TIMEOUT_MS = 900_000         # 15 min per route in the retry pass

# Extra attempts per route after a transient (non-timeout) failure. 1 = retry
# once before recording the route as failed. A hard timeout is NOT retried (the
# user already had a skip window during the wait).
RETRY_COUNT = 1

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

_ROUTES_SET = set(ROUTES)


def normalize_route(token):
    """Normalize one user-typed route token to its canonical ROUTES form.

    Accepts loose input -- any casing or zero-padding, with an optional letter
    suffix -- so '5', '05', '005', '5s', and '005S' all map to their canonical
    spelling ('005', '005S'). Returns the canonical route string if it matches a
    known route, else None.
    """
    t = token.strip().upper()
    m = re.fullmatch(r"(\d+)([A-Z]*)", t)
    if not m:
        return None
    digits, suffix = m.groups()
    candidate = f"{int(digits):03d}{suffix}"
    return candidate if candidate in _ROUTES_SET else None


def parse_routes(text):
    """Parse free-text into a validated route list in canonical ROUTES order.

    Routes may be separated by commas, spaces, semicolons, or newlines, in any
    casing or zero-padding ('5', '005', '5s', '005S'). Returns the matched
    routes de-duplicated and ordered as in ROUTES (so export order stays stable
    regardless of how the user typed them).

    Raises ValueError -- with a user-safe, UI-neutral message -- if no routes
    were given or if any token doesn't match a known route. Callers decide
    whether "no input" should instead mean "all routes" before calling this.
    """
    tokens = [t for t in re.split(r"[\s,;]+", text.strip()) if t]
    if not tokens:
        raise ValueError("No routes entered.")
    chosen, unknown = set(), []
    for tok in tokens:
        norm = normalize_route(tok)
        if norm is None:
            unknown.append(tok)
        else:
            chosen.add(norm)
    if unknown:
        raise ValueError("Not valid route(s): " + ", ".join(unknown))
    return [r for r in ROUTES if r in chosen]


def clear_auth():
    """Delete the stale auth file. Returns True if a file was removed."""
    if AUTH.exists():
        try:
            AUTH.unlink()
            return True
        except OSError:
            return False
    return False


def require_valid_auth():
    """Raise AuthError if the saved session is missing or corrupt."""
    if not AUTH.exists():
        raise AuthError("No saved session file found.")
    try:
        with open(AUTH, "r", encoding="utf-8") as f:
            json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise AuthError(f"Session file is corrupted ({type(e).__name__}).")


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


def preflight(page, report_label):
    """Confirm the report form looks as expected before a long run.

    Selects the report, then verifies the Route control and Generate button are
    present. Raises PreflightError (UI-neutral message) if anything is missing,
    so a TSMIS change fails fast with one clear error instead of every route
    failing cryptically.
    """
    if page.locator("#customReport").count() == 0:
        raise PreflightError(
            "The TSMIS report list didn't load as expected — the page may have "
            "changed. Please contact the maintainer."
        )
    try:
        select_report(page, report_label)
        page.get_by_label("Route", exact=True).wait_for(state="attached", timeout=15000)
        page.get_by_role("button", name="Generate").wait_for(state="attached", timeout=15000)
    except Exception as e:
        raise PreflightError(
            "The TSMIS page looks different than expected — it may have changed. "
            "Please contact the maintainer."
        ) from e


def wait_with_skip_option(page, js_condition, prefix, events,
                          hard_timeout_ms=None,
                          skip_prompt_after_ms=None):
    """Wait for a JS condition with a hard ceiling and a user-skip escape.

    Polls page.wait_for_function in short chunks so we can:
      - honor a skip request (events.should_skip() -> 'S' in the console,
        a Skip button in the GUI),
      - emit a "still working" status (events.on_log) once the soft timer fires,
      - and enforce a hard timeout independent of the skip prompt.

    Returns True when the condition matched, False if the user asked to skip.
    Raises PlaywrightTimeoutError when the hard timeout elapses.
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
        if events.should_skip():
            events.on_log(f"  {prefix} skipped by user")
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
            pass  # not done yet -- fall through and re-check skip / deadline

        now = time.monotonic()
        if not prompted and now >= prompt_at:
            elapsed = int(now - start)
            remaining = int(hard_deadline - now)
            events.on_log(
                f"  {prefix} still working ({elapsed}s elapsed; "
                f"up to {remaining}s left) -- you can skip this route"
            )
            prompted = True
            next_status = now + 30
        elif prompted and now >= next_status:
            events.on_log(f"  {prefix} still working ({int(now - start)}s)...")
            next_status = now + 30


# The app drives a Chromium-based browser ALREADY on the machine instead of
# bundling one (smaller download, nothing for AV/DLP to flag, auto-updated by the
# OS). Microsoft Edge ships with Windows; Chrome is the common alternative. Both
# are Chromium, so page.pdf() and downloads work.
#
# Forward-compatibility: launching a *system channel* (not a pinned bundled
# Chromium) is intentionally version-tolerant -- Playwright talks CDP, which is
# stable, so ordinary Edge auto-updates keep working without a rebuild. To be
# safe anyway we (a) PROBE the browser before trusting it -- launch headless and
# actually drive a page -- so a too-new Edge that Playwright can't control is
# detected and we fall through to Chrome, and (b) fail with a clear, accurate
# message that tells the user to update the tool (vs. "install a browser") only
# when a browser is present but unusable. Only a very major Chromium-wide change
# that breaks BOTH Edge and Chrome would require bumping Playwright.
#
# An admin can pin a channel with the TSMIS_BROWSER_CHANNEL environment variable.
BROWSER_CHANNELS = ("msedge", "chrome")
CHANNEL_LABELS = {"msedge": "Microsoft Edge", "chrome": "Google Chrome"}

_resolved_channel = None        # validated channel, cached for the process
_preferred_channel = None       # user's pick (tried first; the other stays a fallback)


def set_preferred_channel(channel):
    """Record the user's preferred browser (tried first; the other channel stays
    a fallback). None resets to the default (Edge first). Clears the resolved
    cache so the next launch honors the new preference. A hard
    TSMIS_BROWSER_CHANNEL env override still wins over this."""
    global _preferred_channel, _resolved_channel
    _preferred_channel = channel if channel in BROWSER_CHANNELS else None
    _resolved_channel = None


def _candidate_channels():
    forced = os.environ.get("TSMIS_BROWSER_CHANNEL", "").strip()
    if forced:
        return (forced,)
    if _preferred_channel:
        return (_preferred_channel,) + tuple(c for c in BROWSER_CHANNELS if c != _preferred_channel)
    return BROWSER_CHANNELS


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
    "ok" | "missing" | "broken"; always closes the probe browser.
    """
    browser = None
    try:
        browser = p.chromium.launch(headless=True, channel=channel)
    except Exception as e:
        return "missing" if _looks_missing(e) else "broken"
    try:
        page = browser.new_context().new_page()
        page.goto("about:blank", timeout=15_000)
        return "ok" if page.evaluate("1 + 1") == 2 else "broken"
    except Exception:
        return "broken"            # launches but can't be driven -> try the next one
    finally:
        try:
            browser.close()
        except Exception:
            pass


def _resolve_channel(p):
    """Pick a browser Playwright can drive -- Edge, then Chrome -- validating each
    by probe. Cached for the process. Raises BrowserNotFoundError (UI-neutral)
    with a message that distinguishes "none installed" from "installed but too
    new for this tool"."""
    global _resolved_channel
    if _resolved_channel:
        return _resolved_channel
    statuses = {}
    for channel in _candidate_channels():
        status = _probe_channel(p, channel)
        statuses[channel] = status
        if status == "ok":
            _resolved_channel = channel
            return channel
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


def launch_browser(p, *, headless=True, **kwargs):
    """Launch the system browser Playwright can drive (Edge, then Chrome).

    Resolves + validates the channel once per process (a headless probe, so no
    window flashes during headed login), caches it, then launches for real. If a
    previously-good channel unexpectedly fails an actual launch, the cache is
    cleared and the chain is re-resolved so it can still fall back. All terminal
    failures surface as BrowserNotFoundError with a user-safe message.
    """
    global _resolved_channel
    channel = _resolve_channel(p)               # may raise BrowserNotFoundError
    try:
        return p.chromium.launch(headless=headless, channel=channel, **kwargs)
    except Exception as first_err:
        _resolved_channel = None                # forget it and try the whole chain again
        try:
            channel = _resolve_channel(p)
            return p.chromium.launch(headless=headless, channel=channel, **kwargs)
        except BrowserNotFoundError:
            raise
        except Exception:
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
    return results


def new_authed_browser(p):
    """Launch the headless system browser with the saved auth restored.

    Returns (browser, context, page). Caller is responsible for browser.close().
    Raises BrowserNotFoundError if neither Edge nor Chrome is installed.
    """
    browser = launch_browser(
        p,
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
