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
import logging
import os
import re
import socket
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

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


class SiteUnreachableError(PreflightError):
    """Raised when the TSMIS page can't be opened at all (network/VPN/DNS), so
    the user sees "check your connection" instead of a raw Playwright error.
    Subclasses PreflightError because every driver already handles that as
    "the run can't start; show the message as-is"."""


class BrowserNotFoundError(Exception):
    """Raised when no usable Chromium-based browser (Edge or Chrome) is installed
    on the machine. The app drives the browser already present rather than
    bundling one, so this is the "please install Edge" case. Message is user-safe
    and UI-neutral."""


class RunCancelled(Exception):
    """Raised mid-route when the user cancels (events.is_cancelled() goes True
    while we're waiting on a report). Lets Cancel interrupt the *current* route's
    wait instead of only taking effect between routes. The engines catch it and
    stop the run cleanly -- it is NOT a route failure or a worker crash."""


class ReportError(Exception):
    """Raised when the TSMIS site itself renders a fatal error for a route -- its
    #rampResults box goes into an `error` state (e.g. "Cannot read properties of
    undefined (reading 'size')") instead of producing a report or a clean "no
    results". Detected during the post-Generate wait so the route fails FAST with
    the site's own message, instead of silently waiting out the whole per-route
    timeout (and then the long retry) on something the site simply can't build."""


# The TSMIS report site. One page serves every combination of data source
# (SSOR / ARS) and environment (prod / test / dev) via query parameters; the
# user picks both in the GUI header (set_site) or via TSMIS_SRC / TSMIS_ENV in
# the console flow. Defaults: SSOR + prod.
TSMIS_HOST = "tsmis-dev.dot.ca.gov"
DATA_SOURCES = ("ssor", "ars")
ENVIRONMENTS = ("prod", "test", "dev")
DATA_SOURCE_LABELS = {"ssor": "SSOR", "ars": "ARS"}
ENVIRONMENT_LABELS = {"prod": "Prod", "test": "Test", "dev": "Dev"}


def _env_choice(var, valid, default):
    v = os.environ.get(var, "").strip().lower()
    return v if v in valid else default


_data_source = _env_choice("TSMIS_SRC", DATA_SOURCES, "ssor")
_environment = _env_choice("TSMIS_ENV", ENVIRONMENTS, "prod")


def set_site(source=None, environment=None):
    """Record which data source / environment the next navigation should use.
    Invalid values are ignored (the current choice is kept)."""
    global _data_source, _environment
    if source and source.lower() in DATA_SOURCES:
        _data_source = source.lower()
    if environment and environment.lower() in ENVIRONMENTS:
        _environment = environment.lower()
    log.info("site: set to src=%s env=%s", _data_source, _environment)


def get_site():
    """The active (data_source, environment) pair."""
    return _data_source, _environment


def get_url():
    """The full report-page URL for the active data source / environment."""
    return f"https://{TSMIS_HOST}/index.html?env={_environment}&src={_data_source}"


# The shared auth file path is resolved by paths.py, which is frozen-aware: in
# the packaged build it lives next to the .exe (auto-falling back to
# %LOCALAPPDATA% if that folder is read-only); in the dev / .bat workflow it
# stays at scripts/tsmis_auth.json. Re-exported here for login.py and cli.py.
# (Output paths also come from paths.py, imported directly by the exporter and
# consolidators.)
from paths import AUTH, EDGE_LOGIN_PROFILE_DIR, FAILURES_DIR

log = logging.getLogger("tsmis.auth")

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


# The constants above are the DEFAULTS; the Settings tab can override the
# ceilings (persisted via settings.py). Engines call these accessors at RUN
# time, so a changed setting applies to the next run without a restart.
def _settings_ms(key, default_ms, unit_ms):
    try:
        import settings
        return settings.get(key) * unit_ms
    except Exception as e:                       # settings must never stop a run
        log.warning("settings read failed for %s (%s: %s); using default",
                    key, type(e).__name__, e)
        return default_ms


def report_timeout_ms():
    """Effective per-route ceiling for the sequential flow (Settings tab can
    raise it; default REPORT_TIMEOUT_MS)."""
    return _settings_ms("report_timeout_min", REPORT_TIMEOUT_MS, 60_000)


def fast_report_timeout_ms():
    """Effective per-route ceiling under fast mode's concurrent load."""
    return _settings_ms("fast_timeout_min", FAST_REPORT_TIMEOUT_MS, 60_000)


def retry_report_timeout_ms():
    """Effective per-route ceiling for the end-of-run serial retry pass."""
    return _settings_ms("retry_timeout_min", RETRY_REPORT_TIMEOUT_MS, 60_000)


def county_enable_timeout_ms():
    """Effective wait for the County dropdown to enable."""
    return _settings_ms("county_timeout_s", COUNTY_ENABLE_TIMEOUT_MS, 1_000)

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
            log.info("auth: stale session file deleted (%s)", AUTH)
            return True
        except OSError as e:
            log.warning("auth: could not delete stale session file %s: %s", AUTH, e)
            return False
    return False


def require_valid_auth():
    """Raise AuthError if the saved session is missing, corrupt, or not shaped
    like a Playwright storage_state.

    Validating the SHAPE here (not just "is it JSON") matters: a valid-JSON file
    that isn't a real storage_state would otherwise blow up later inside
    `browser.new_context(storage_state=...)` as a raw, un-handled error (a
    traceback in the console flow). Catching it here turns it into a clean
    AuthError the drivers already know how to surface + guide a re-login for.
    """
    if not AUTH.exists():
        raise AuthError("No saved session file found.")
    try:
        with open(AUTH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise AuthError(f"Session file is corrupted ({type(e).__name__}).")
    # Playwright's storage_state is always {"cookies": [...], "origins": [...]}.
    if (not isinstance(data, dict)
            or not isinstance(data.get("cookies"), list)
            or not isinstance(data.get("origins"), list)):
        raise AuthError("Session file isn't a valid saved login.")


def has_valid_auth():
    """True if a usable saved session file exists (require_valid_auth passes)."""
    try:
        require_valid_auth()
        return True
    except AuthError:
        return False


def save_auth_state(state):
    """Write a Playwright storage_state (dict) to the shared auth file."""
    AUTH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH, "w", encoding="utf-8") as f:
        json.dump(state, f)
    try:
        log.info("auth: session saved -> %s (%d cookies, %d origins)",
                 AUTH, len(state.get("cookies", [])), len(state.get("origins", [])))
    except Exception:
        log.info("auth: session saved -> %s", AUTH)


def _auth_file_age_hours():
    """Age of the saved session file in hours, or None when unavailable."""
    try:
        return (time.time() - AUTH.stat().st_mtime) / 3600
    except OSError:
        return None


def _page_host(page):
    """Hostname of the page's current URL ('' when unavailable). Substring
    checks against page.url are WRONG here: the portal's authorize URL carries
    the app host inside its redirect_uri parameter."""
    try:
        return urlsplit(page.url).hostname or ""
    except Exception:
        return ""


# CONFIG is a top-level `const` in the app's config.js -- a lexical global, NOT
# a window property -- so it must be read by bare identifier inside try/catch.
# (Reading window.CONFIG always yields undefined; acting on that once caused
# every successful sign-in to be reloaded away.)
_CONFIG_JS = "() => { try { return [CONFIG.env || null, CONFIG.src || null]; } catch (e) { return null; } }"


def _site_params_ok(page):
    """True when the app is running the selected data source / environment --
    or when that can't be determined. Callers must NEVER reload on 'unknown':
    the app's token lives only in page memory, so a reload destroys the session
    and forces a whole new sign-in round-trip."""
    try:
        got = page.evaluate(_CONFIG_JS)
    except Exception as e:
        log.info("auth: site-params check unavailable (%s); treating as OK",
                 type(e).__name__)
        return True
    if not got:
        return True
    want_src, want_env = get_site()
    if got != [want_env, want_src]:
        log.info("auth: app is running env=%s src=%s but env=%s src=%s was "
                 "selected", got[0], got[1], want_env, want_src)
        return False
    return True


def navigate_with_auth(page):
    """Open the TSMIS page and see the sign-in through.

    The app NEVER shows a signed-out page: with no token it immediately
    redirects itself into the portal OAuth flow (same tab). The portal keeps
    NO session cookie, so each round-trip needs the IdP hop; we drive it
    directly off the sign-in page's own data (the SAML authorize URL on the
    IdP button + the page's oauth_state), with a plain click as fallback. With
    a live Azure session (saved cookies, Kerberos, or Windows device auth in
    the Edge profile) the rest completes silently and the app comes back
    signed in -- the token in the URL hash, kept only in page memory. Because
    a reload destroys that token, the wrong-site check runs INSIDE the loop
    (at most one corrective reload, then a fresh sign-in pass) and never after
    success. Every state change is breadcrumbed to the log.
    """
    url = get_url()
    log.info("auth: navigate start -> %s", url)
    try:
        page.goto(url)
    except Exception as e:
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        log.warning("auth: could not open %s: %s", url, reason)
        raise SiteUnreachableError(
            f"The TSMIS site could not be reached ({reason}). Check the "
            "network / VPN connection, then try again."
        ) from e
    start = time.monotonic()
    deadline = start + 60
    idp_drives = 0
    reloaded_for_params = False
    last_note = None

    def note(msg):
        nonlocal last_note
        if msg != last_note:               # breadcrumb state CHANGES only
            log.info("auth: +%ds %s", int(time.monotonic() - start), msg)
            last_note = msg

    while time.monotonic() < deadline:
        try:
            if is_logged_in(page):
                if _site_params_ok(page) or reloaded_for_params:
                    note("signed in")
                    break
                # Signed in, but on the wrong data source / environment:
                # reload with the right parameters ONCE. The reload destroys
                # the in-memory token, so keep looping to sign in again (the
                # app re-stores our env/src via its own sessionStorage handoff).
                reloaded_for_params = True
                note("signed in on wrong site params; reloading with target URL")
                page.goto(url)
                continue
        except Exception as e:
            note(f"signed-in check error: {type(e).__name__}")
        # The app's own (currently unused) signed-out screen.
        try:
            btn = page.get_by_role("button", name="Sign In with ArcGIS")
            if btn.count() > 0 and btn.first.is_visible():
                note("clicking 'Sign In with ArcGIS'")
                btn.first.click(timeout=2000)
        except Exception:
            pass
        # The portal sign-in page.
        try:
            idp = page.get_by_text("Caltrans Azure AD")
            if idp.count() > 0 and idp.first.is_visible():
                if idp_drives < 3:
                    idp_drives += 1
                    idp_url = idp.first.get_attribute("data-url")
                    state_loc = page.locator("#oauth_state")
                    state_val = (state_loc.input_value(timeout=1000)
                                 if state_loc.count() > 0 else None)
                    if idp_url and state_val:
                        note(f"portal sign-in page; driving SAML authorize "
                             f"(attempt {idp_drives})")
                        page.goto(f"{idp_url}?oauth_state={quote(state_val, safe='')}")
                    else:
                        note(f"portal sign-in page; clicking IdP button "
                             f"(attempt {idp_drives})")
                        idp.first.click(timeout=2000)
                else:
                    note("portal sign-in page keeps returning; waiting")
        except Exception as e:
            note(f"idp step error: {type(e).__name__}")
        # Off-site breadcrumb (e.g. parked at an Azure interactive page).
        try:
            host = _page_host(page)
            if host and host != TSMIS_HOST:
                note(f"waiting at {host} ({page.title()!r})")
        except Exception:
            pass
        try:
            page.wait_for_timeout(1000)
        except Exception as e:
            note(f"wait aborted: {type(e).__name__}")
            break
    page.wait_for_timeout(1000)
    signed = is_logged_in(page)
    log.info("auth: navigate done signed_in=%s idp_drives=%d reloaded_for_params=%s "
             "elapsed=%ds url=%s", signed, idp_drives, reloaded_for_params,
             int(time.monotonic() - start), auth_state(page).get("url"))
    if not signed:
        log.info("auth: signals after navigate: %s", auth_state(page).get("signals"))



# Signed-in detection for the report page. The page ships its whole form
# (#customReport included) in the static HTML even when signed out, and the
# unauthenticated state is "you get redirected away" rather than any visible
# prompt — so the trustworthy signals are the app's post-auth UI: setAuthUI(true)
# shows #modeSelector (immediately for ARS; for SSOR after the TSMIS_HI group
# check passes), and the later stages show #controlsGrid / #generateRow /
# #appForm / #versionCtrl. ANY of those visible counts as signed in, while
# #accessDenied (authenticated but not in the TSMIS group) and #loginPrompt are
# definitive "not usable". Visibility uses Element.checkVisibility() when the
# browser has it — the offsetParent trick is wrong for fixed-position ancestors.
_SIGNED_IN_JS = """(() => {
  const visible = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    if (el.checkVisibility) return el.checkVisibility();
    let n = el;
    while (n && n.nodeType === 1) {
      if (getComputedStyle(n).display === 'none') return false;
      n = n.parentElement;
    }
    return true;
  };
  if (visible('#accessDenied') || visible('#loginPrompt')) return false;
  return ['#modeSelector', '#controlsGrid', '#generateRow', '#appForm', '#versionCtrl']
      .some(visible);
})()"""


def is_logged_in(page):
    """Quick check: are we on the report page in a usable, signed-in state?"""
    try:
        if _page_host(page) != TSMIS_HOST:
            return False
        return bool(page.evaluate(_SIGNED_IN_JS))
    except Exception:
        return False


# Diagnostic snapshot of every sign-in signal, logged whenever a sign-in gate
# fails so the rotating log shows WHAT the page looked like — not just that it
# "didn't complete". Each entry is "visible/<computed display>" or "absent".
_AUTH_DIAG_JS = """(() => {
  const st = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return 'absent';
    const cs = getComputedStyle(el);
    const vis = el.checkVisibility ? el.checkVisibility() : cs.display !== 'none';
    return (vis ? 'visible' : 'hidden') + '/' + cs.display;
  };
  return {
    title: document.title,
    config: (() => { try { return [CONFIG.env, CONFIG.src]; } catch (e) { return null; } })(),
    modeSelector: st('#modeSelector'), accessDenied: st('#accessDenied'),
    loginPrompt: st('#loginPrompt'), controlsGrid: st('#controlsGrid'),
    generateRow: st('#generateRow'), appForm: st('#appForm'),
    versionCtrl: st('#versionCtrl'), customReport: st('#customReport'),
  };
})()"""


def auth_state(page):
    """Best-effort snapshot of the page's sign-in signals for diagnostics."""
    info = {}
    try:
        info["url"] = page.url
    except Exception:
        info["url"] = "<unavailable>"
    try:
        info["signals"] = page.evaluate(_AUTH_DIAG_JS)
    except Exception as e:
        info["signals"] = f"<unavailable: {type(e).__name__}>"
    return info


def dump_auth_failure(page, note, *, stem="auth_fail"):
    """Write a screenshot + page HTML to FAILURES_DIR and log the page's
    sign-in signals, so a failed gate can be diagnosed from one run (no
    back-and-forth for "what did the page look like?"). Best-effort."""
    log.warning("page gate failed (%s): %s", note, auth_state(page))
    try:
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        page.screenshot(path=str(FAILURES_DIR / f"{stem}_{stamp}.png"),
                        full_page=True)
        (FAILURES_DIR / f"{stem}_{stamp}.html").write_text(
            page.content(), encoding="utf-8")
        log.warning("failure page captured to %s (%s_%s.*)",
                    FAILURES_DIR, stem, stamp)
    except Exception as e:
        log.warning("could not capture failure page: %s", e)


def require_signed_in(page, message):
    """Raise AuthError(message) unless the page is signed in — capturing full
    diagnostics (signal snapshot + screenshot + HTML) first when it isn't."""
    if is_logged_in(page):
        return
    dump_auth_failure(page, message)
    raise AuthError(message)


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
        timeout=county_enable_timeout_ms(),
    )
    page.locator("#districtCountySelect").select_option(label="-- ALL --")


# Every report renders a fatal error into the shared #rampResults box by adding
# the `error` class (e.g. highway_log/hsl: `box.className = 'ramp-results error'`;
# ramp detail/summary via the shared showRampResults('error', ...)). clearResults()
# resets that class on each Generate, so this only ever reflects the CURRENT
# route -- no stale-error false positives. JS expression form for use inside the
# post-Generate wait condition.
ERROR_JS = "document.querySelector('#rampResults.error') !== null"


def report_error_text(page):
    """If the report rendered an error (the site's #rampResults is in its `error`
    state), return the site's message; otherwise None.

    The site shows fatal report errors here with NO Export button and NO "no
    results" text, so without detecting this the export loop would wait out the
    full per-route timeout (then the long retry) on a route the site can't build.
    Best-effort: any lookup problem returns None (treat as "no error seen")."""
    try:
        loc = page.locator("#rampResults.error")
        if loc.count() > 0:
            text = (loc.first.inner_text() or "").strip()
            return text or "The TSMIS site reported an error for this route."
    except Exception:
        return None
    return None


def preflight(page, report_label):
    """Confirm the report form looks as expected before a long run.

    Selects the report, then verifies the Route control and Generate button are
    present. Raises PreflightError (UI-neutral message) if anything is missing,
    so a TSMIS change fails fast with one clear error instead of every route
    failing cryptically.
    """
    if page.locator("#customReport").count() == 0:
        log.warning("preflight: #customReport (the report dropdown) is missing")
        dump_auth_failure(page, "preflight: report dropdown missing",
                          stem="preflight_fail")
        raise PreflightError(
            "The TSMIS report list didn't load as expected — the page may have "
            "changed. Please contact the maintainer."
        )
    step = "selecting the report"
    try:
        select_report(page, report_label)
        step = "finding the Route control"
        page.get_by_label("Route", exact=True).wait_for(state="attached", timeout=15000)
        step = "finding the Generate button"
        page.get_by_role("button", name="Generate").wait_for(state="attached", timeout=15000)
        log.info("preflight ok: %s", report_label)
    except Exception as e:
        log.warning("preflight failed while %s for %r: %s: %s",
                    step, report_label, type(e).__name__,
                    str(e).splitlines()[0] if str(e) else "")
        dump_auth_failure(page, f"preflight: {step} failed",
                          stem="preflight_fail")
        raise PreflightError(
            "The TSMIS page looks different than expected — it may have changed. "
            "Please contact the maintainer."
        ) from e


def maybe_screenshot(page, events, note=""):
    """Answer a pending live-preview request for this worker's browser.

    The GUI's Preview button sets a flag (events.screenshot_wanted); engines
    call this at safe poll points ON THE WORKER'S OWN THREAD (Playwright is
    thread-affine, so the GUI can never screenshot a page directly). Captures
    the current viewport as JPEG bytes and hands them to events.on_screenshot.
    Best-effort: a capture problem reports a None image with the reason in
    `note` (so the GUI stops waiting) and never disturbs the run."""
    try:
        if not events.screenshot_wanted(events.worker_no):
            return
    except Exception:
        return
    try:
        data = page.screenshot(type="jpeg", quality=70)   # viewport, not full page
        log.info("preview screenshot captured for browser %d (%d bytes)",
                 events.worker_no, len(data))
        events.on_screenshot(events.worker_no, data, note)
    except Exception as e:
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        log.info("preview screenshot failed for browser %d (%s: %s)",
                 events.worker_no, type(e).__name__, reason)
        try:
            events.on_screenshot(events.worker_no, None,
                                 "The screenshot couldn't be taken right now "
                                 "(the browser was busy) — try again.")
        except Exception:
            pass


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
    Raises RunCancelled immediately if the user cancels the whole run while we're
    waiting (so Cancel interrupts the current route, not just between routes), and
    PlaywrightTimeoutError when the hard timeout elapses.
    """
    if hard_timeout_ms is None:
        hard_timeout_ms = report_timeout_ms()
    if skip_prompt_after_ms is None:
        skip_prompt_after_ms = SKIP_PROMPT_AFTER_MS

    start = time.monotonic()
    hard_deadline = start + hard_timeout_ms / 1000
    prompt_at = start + skip_prompt_after_ms / 1000
    poll_chunk_ms = 5000
    prompted = False
    next_status = 0.0

    while True:
        # Cancel wins over everything: stop waiting on this route right now rather
        # than only checking between routes (the "Cancel is just a suggestion" bug).
        if events.is_cancelled():
            raise RunCancelled()
        if events.should_skip():
            events.on_log(f"  {prefix} skipped by user")
            return False
        # Live view for the GUI: answer a pending Preview request (≤ one poll
        # chunk of latency) and keep the worker's status row current.
        maybe_screenshot(page, events, note=prefix.strip())
        events.on_status(events.worker_no,
                         f"{prefix} working… ({int(time.monotonic() - start)}s)")

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


# The app normally drives a Chromium-based browser ALREADY on the machine
# instead of bundling one (smaller download, nothing for AV/DLP to flag,
# auto-updated by the OS). Microsoft Edge ships with Windows; Chrome is the
# common alternative. Both are Chromium, so page.pdf() and downloads work.
#
# Some installs ALSO carry a private "Built-in Chromium" for Playwright: the
# with-browser release zip ships one inside _internal\ms-playwright (paths.py
# points PLAYWRIGHT_BROWSERS_PATH at it), and the .bat setup downloads one via
# `playwright install chromium`. When present it is listed first and becomes
# the default: it is unmanaged -- org policy can't relaunch it into a work
# profile mid-SSO, the failure that broke managed-Edge sign-in -- and its
# revision is pinned to the Playwright driver. Edge and Chrome stay in the
# picker as fallbacks. channel="chromium" runs the full browser in new-headless
# mode, so the one binary serves both headed sign-in and headless exports.
#
# Forward-compatibility: launching a *system channel* is intentionally
# version-tolerant -- Playwright talks CDP, which is stable, so ordinary Edge
# auto-updates keep working without a rebuild. To be safe anyway we (a) PROBE
# the browser before trusting it -- launch headless and actually drive a page --
# so a too-new Edge that Playwright can't control is detected and we fall
# through to the next channel, and (b) fail with a clear, accurate message that
# tells the user to update the tool (vs. "install a browser") only when a
# browser is present but unusable.
#
# An admin can pin a channel with the TSMIS_BROWSER_CHANNEL environment variable.


def _playwright_browsers_dir():
    """Folder where Playwright keeps its own browsers, or None when no private
    Chromium should be considered. PLAYWRIGHT_BROWSERS_PATH wins (paths.py
    points it at the bundle's ms-playwright when one ships next to the .exe).
    PACKAGED builds otherwise return None: the machine may carry an unrelated
    Playwright cache (e.g. from dev work) whose revision doesn't match this
    app's driver -- the system-browser build must default to Edge, not to that.
    Dev / .bat runs use Playwright's per-OS default cache, which is exactly
    where `1. setup…bat`'s `playwright install chromium` puts it."""
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env and env != "0":
        return Path(env)
    if getattr(sys, "frozen", False):
        return None
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / "ms-playwright"
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "ms-playwright"
    return home / ".cache" / "ms-playwright"


def _chromium_available():
    """True if a Playwright-managed Chromium appears to be installed (bundled
    next to the .exe, or downloaded by `playwright install chromium`). A cheap
    folder check -- the launch-time probe still validates it actually runs."""
    browsers_dir = _playwright_browsers_dir()
    if browsers_dir is None:
        return False
    try:
        return any(browsers_dir.glob("chromium-*"))
    except OSError:
        return False


BROWSER_CHANNELS = ((("chromium",) if _chromium_available() else ())
                    + ("msedge", "chrome"))
CHANNEL_LABELS = {"chromium": "Built-in Chromium", "msedge": "Microsoft Edge",
                  "chrome": "Google Chrome"}

_resolved_channel = None        # validated channel, cached for the process
_preferred_channel = None       # user's pick (tried first; the other stays a fallback)


def set_preferred_channel(channel):
    """Record the user's preferred browser (tried first; the other channels stay
    fallbacks). None resets to the default order (Built-in Chromium when present,
    then Edge, then Chrome). Clears the resolved cache so the next launch honors
    the new preference. A hard TSMIS_BROWSER_CHANNEL env override still wins
    over this."""
    global _preferred_channel, _resolved_channel
    _preferred_channel = channel if channel in BROWSER_CHANNELS else None
    _resolved_channel = None
    log.info("browser: preferred channel set to %s", _preferred_channel or "(default order)")


def get_preferred_channel():
    """The channel the user explicitly pinned -- the TSMIS_BROWSER_CHANNEL env
    override first, then the UI pick recorded by set_preferred_channel -- or
    None when no explicit choice was made. Lets the sign-in flow honor the same
    browser choice the exports use."""
    forced = os.environ.get("TSMIS_BROWSER_CHANNEL", "").strip()
    if forced:
        return forced
    return _preferred_channel


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
    "ok" | "missing" | "broken"; always closes the probe browser. The reason a
    probe fails is logged here -- it is deliberately not in the user-facing
    message, so the log is the place that says WHY a channel was passed over.
    """
    browser = None
    try:
        browser = p.chromium.launch(headless=True, channel=channel)
    except Exception as e:
        status = "missing" if _looks_missing(e) else "broken"
        log.info("browser: probe %s -> %s (%s: %s)", channel, status,
                 type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return status
    try:
        page = browser.new_context().new_page()
        page.goto("about:blank", timeout=15_000)
        return "ok" if page.evaluate("1 + 1") == 2 else "broken"
    except Exception as e:
        # Launches but can't be driven -> try the next one.
        log.info("browser: probe %s -> broken driving a page (%s: %s)", channel,
                 type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return "broken"
    finally:
        try:
            browser.close()
        except Exception:
            pass


def _resolve_channel(p, exclude=()):
    """Pick a browser Playwright can drive -- Built-in Chromium when present,
    then Edge, then Chrome -- validating each by probe. Cached for the process.
    `exclude` skips channels already known to fail a real launch (so the
    fallback doesn't re-pick the same broken one). Raises BrowserNotFoundError
    (UI-neutral) with a message that distinguishes "none installed" from
    "installed but too new for this tool"."""
    global _resolved_channel
    if _resolved_channel and _resolved_channel not in exclude:
        return _resolved_channel
    statuses = {}
    for channel in _candidate_channels():
        if channel in exclude:
            continue
        status = _probe_channel(p, channel)
        statuses[channel] = status
        if status == "ok":
            _resolved_channel = channel
            log.info("browser: resolved channel %s (candidates %s, excluded %s)",
                     channel, list(_candidate_channels()), list(exclude))
            return channel
    log.warning("browser: no usable channel (probes: %s, excluded %s)",
                statuses, list(exclude))
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
    """Launch the first browser Playwright can drive (Built-in Chromium when
    present, then the system Edge, then Chrome).

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
        # The probe passed but the real launch failed. Re-resolve EXCLUDING this
        # channel so we actually fall through to the OTHER browser instead of
        # re-picking the same broken one (a probe pass doesn't guarantee a real
        # launch succeeds).
        failed = channel
        log.warning("browser: launch of %s failed (%s: %s); re-resolving without it",
                    failed, type(first_err).__name__,
                    str(first_err).splitlines()[0] if str(first_err) else "")
        _resolved_channel = None
        try:
            channel = _resolve_channel(p, exclude={failed})
            return p.chromium.launch(headless=headless, channel=channel, **kwargs)
        except BrowserNotFoundError:
            raise
        except Exception:
            log.exception("browser: fallback launch failed too")
            raise BrowserNotFoundError(
                "The web browser could not be started. It may have updated to a "
                "version this tool doesn't support yet -- please update TSMIS "
                "Exporter, or contact the maintainer."
            ) from first_err


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


def check_browsers():
    """Probe each known browser channel for the readiness panel. Returns
    {channel: "ok" | "missing" | "broken"} (see _probe_channel). Opens its own
    Playwright, so call it from a worker thread -- never the Tk main thread."""
    from playwright.sync_api import sync_playwright
    results = {}
    with sync_playwright() as p:
        for channel in BROWSER_CHANNELS:
            results[channel] = _probe_channel(p, channel)
    log.info("browser: readiness check %s", results)
    return results


# The TSMIS page pulls report data from an intranet host, which Chromium's
# Local Network Access checks would block behind an "allow this site to access
# devices on your local network?" prompt no one can answer headless. Launch
# with the checks in their non-warning form and pre-grant the permission on
# every automated context (_new_app_context).
_LNA_ARGS = [
    "--disable-features=LocalNetworkAccessChecksWarnings",
    "--enable-features=LocalNetworkAccessChecks",
]


def _new_app_context(browser, storage_state=None):
    """New context with the local-network-access permission pre-granted (see
    _LNA_ARGS). The fallback drops only the optional permissions kwarg (older
    browsers may not know the permission name)."""
    kwargs = {}
    if storage_state is not None:
        kwargs["storage_state"] = storage_state
    try:
        return browser.new_context(permissions=["local-network-access"], **kwargs)
    except Exception:
        return browser.new_context(**kwargs)


# Public face of the LNA setup for the HEADED sign-in flows (login.py /
# gui_worker.LoginWorker). The headed windows need the exact same treatment as
# the automated contexts: without it, Chrome gates the TSMIS page's intranet
# data behind an "access devices on your local network?" prompt on EVERY
# sign-in -- and while the prompt sits unanswered the signed-in UI never
# appears, so a completed login is never detected and nothing is saved.
# (The persistent-profile Edge flow has carried this since v0.5.)
LOGIN_BROWSER_ARGS = _LNA_ARGS


def new_login_context(browser):
    """Context for a headed sign-in window, local-network-access pre-granted.
    Pair with a launch that passed LOGIN_BROWSER_ARGS."""
    return _new_app_context(browser)


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


def new_authed_browser(p):
    """Launch a headless browser ready to drive TSMIS.

    With a valid saved session, restores it into the user's preferred browser
    (the original flow). With NO usable saved session, runs in DEVICE SIGN-IN
    mode instead: it reopens the app-owned persistent Edge sign-in profile,
    where the one-click Windows sign-in lives, and the "Caltrans Azure AD"
    click signs the context in live with no typed credentials. Edge-only and
    profile-bound by design: on managed Caltrans PCs Chrome asks for
    credentials, and even a fresh Edge context without this profile doesn't
    get the one-click sign-in.

    Returns (browser, context, page). Caller is responsible for browser.close()
    -- in device mode the persistent context doubles as the browser handle, and
    its .close() shuts the persistent browser down.
    """
    state = None
    try:
        require_valid_auth()
        state = str(AUTH)
    except AuthError as e:
        log.info("auth: no usable saved session (%s)", e)
        state = None

    if state is None:
        log.info("auth: DEVICE SIGN-IN mode (persistent Edge profile, no auth file)")
        ctx, page = open_edge_device_context(p)   # raises AuthError if it can't sign in
        return ctx, ctx, page

    age = _auth_file_age_hours()
    log.info("auth: using saved session %s%s", AUTH,
             f" (saved {age:.1f} h ago)" if age is not None else "")
    browser = launch_browser(p, headless=True, args=_LNA_ARGS)
    ctx = _new_app_context(browser, storage_state=state)
    page = ctx.new_page()
    return browser, ctx, page


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
