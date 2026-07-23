"""Page sign-in detection + navigation + the auth-file lifecycle (P8b — L2).

Extracted verbatim from common.py: navigating an already-launched page to the
selected TSMIS site with the saved session, detecting the signed-in state, the
fail-closed site/param backstops, the auth-diagnostic dump, and the at-rest
session-file lifecycle (save/validate/clear, owner-only ACL). Given a page; it
does not launch a browser. `page_url_for_display` lives here with its sole caller
`auth_state` (the plan's §E left it unplaced; homing it here keeps report_nav a
one-way dependent of auth_nav, so the layering stays acyclic). common.py
re-exports the public names.

Console-free; the `"tsmis.auth"` logger name is preserved.
"""
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from urllib.parse import quote, urlsplit

from paths import AUTH, FAILURES_DIR
from errors import AuthError, PreflightError, SiteUnreachableError
from site_target import expected_host, get_site, get_url

log = logging.getLogger("tsmis.auth")


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


def _restrict_to_owner(path):
    """Best-effort: tighten `path`'s NTFS ACL to the current user only — remove
    inherited ACEs and grant the owner full control — so the plaintext session file
    isn't readable by other accounts even where the parent folder's ACL is broad.
    Windows-only, via the built-in ``icacls`` (no admin needed for an owned file, no
    console window). ANY failure is logged and ignored: the file already lives in the
    user's own profile, and an ACL hiccup must never block sign-in; a total icacls
    failure leaves the prior inherited (still user-readable) ACL, so there is no
    lock-out risk. This is NOT DPAPI — it changes the file's permissions, not its
    bytes, so storage_state stays portable (copying it to another machine simply
    re-inherits that machine's default ACL)."""
    if os.name != "nt":
        return
    user = os.environ.get("USERNAME", "")
    # USERNAME is just an env var; accept only a structurally valid Windows account
    # name (the char class is exactly what Windows forbids in a name) so a tampered /
    # odd value can't mis-parse the icacls `account:perm` argument — a stray ':' or
    # '\\' would silently break the grant. On reject we skip + log, leaving the file's
    # inherited (still owner-readable) ACL rather than issuing a malformed grant.
    if not re.fullmatch(r'[^"/\\\[\]:;|=,+*?<>]{1,104}', user):
        log.info("auth: ACL tighten skipped (USERNAME missing or invalid: %r)", user)
        return
    try:
        cp = subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    except (OSError, subprocess.SubprocessError) as e:
        log.info("auth: ACL tighten skipped (%s: %s)", type(e).__name__, e)
        return
    # icacls ran: a NON-ZERO return is a real ACL failure (e.g. access denied), distinct
    # from an exception — log it (with rc + first output line) so the "one log upload
    # answers it" contract holds, but DON'T fail the save (the file keeps its prior
    # inherited, still owner-readable ACL — best-effort, no lock-out).
    if cp.returncode != 0:
        first = next((ln for ln in (cp.stdout or "").splitlines() if ln.strip()), "")
        log.info("auth: ACL tighten reported a non-zero icacls result (rc=%s)%s; "
                 "kept the prior inherited ACL", cp.returncode,
                 f": {first.strip()}" if first else "")


def save_auth_state(state):
    """Write a Playwright storage_state (dict) to the shared auth file ATOMICALLY,
    then tighten its ACL to the current user.

    The write is temp file + ``os.replace`` (F9) so an interrupted / failed / locked
    write never truncates a prior good session; the owner-only ACL is applied to the
    TEMP file BEFORE the rename, so the cookies never sit at the well-known AUTH path
    with a broad inherited ACL even briefly.

    AT REST: this is plaintext JSON (the session cookies), protected by NTFS
    permissions in the user's own app folder, and is git-ignored + never added to
    the support bundle. Windows DPAPI (CryptProtectData) at-rest ENCRYPTION is the
    candidate further hardening — deferred because it binds to user+machine and would
    break storage_state portability (gated on O2); see docs/it-and-security.md."""
    AUTH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(AUTH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
        _restrict_to_owner(tmp)     # tighten the ACL on the temp BEFORE it becomes
        os.replace(tmp, AUTH)       # AUTH, so AUTH is owner-only the instant it appears
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:  # silent-ok: cleanup inside a re-raising handler; the raise reports
            pass
        raise
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


def navigate_with_auth(page, *, budget_s=60, should_cancel=None):
    """Open the TSMIS page and see the sign-in through.

    `budget_s` caps the sign-in loop (default 60s). The quiet background
    active-env check passes a shorter budget so a managed PC's silent SSO still
    completes but an unreachable machine fails fast instead of hanging.

    `should_cancel` (optional) is polled once per ~1s pass; when it returns True
    the sign-in loop stops early so a user Stop/Cancel doesn't have to wait out
    the whole budget (the caller sees not-signed-in and handles the cancel). It
    defaults to None — existing callers are unchanged.

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
    deadline = start + budget_s
    idp_drives = 0
    reloaded_for_params = False
    last_note = None

    def note(msg):
        nonlocal last_note
        if msg != last_note:               # breadcrumb state CHANGES only
            log.info("auth: +%ds %s", int(time.monotonic() - start), msg)
            last_note = msg

    while time.monotonic() < deadline:
        if should_cancel is not None and should_cancel():
            note("cancel requested — stopping sign-in")
            break
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
        except Exception as e:
            note(f"arcgis-click step error: {type(e).__name__}")
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
            if host and host != expected_host():
                note(f"waiting at {host} ({page.title()!r})")
        except Exception:  # silent-ok: a best-effort breadcrumb; the sign-in loop itself reports
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
        log.info("auth: not signed in — %s", classify_signin_stall(page))


# Common Microsoft / Azure AD interactive sign-in hosts. When a headless silent
# navigate ends parked here, the saved device session has expired or Conditional
# Access / MFA is demanding interactive auth — NOT a site or network fault.
_IDP_HOSTS = ("login.microsoftonline.com", "login.microsoft.com",
              "login.windows.net", "adfs")


def classify_signin_stall(page):
    """A one-line, human diagnosis of WHY a not-signed-in navigate stalled, so one
    uploaded log distinguishes the common causes instead of leaving a raw signals
    dump to interpret (M1-E/G2). Also drives the Edge sign-in chip's message.
    Returns a short string; never raises."""
    try:
        host = (_page_host(page) or "").lower()
        title = (page.title() or "")
    except Exception:  # silent-ok: the classification is a best-effort diagnostic
        return "could not read the stalled page"
    if any(h in host for h in _IDP_HOSTS) or "sign in to your account" in title.lower():
        return ("stalled at the Microsoft sign-in page — the saved device session "
                "expired or Conditional Access/MFA is prompting for interactive "
                "sign-in; use “Retry Edge sign-in” to refresh it")
    if host and host != expected_host():
        return (f"stalled off-site at {host} — not the TSMIS host; "
                "check VPN / network reachability")
    return ("on the TSMIS host but not signed in — the signals snapshot above says "
            "which (accessDenied = not in the TSMIS group; all-absent = possible "
            "page change)")


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
        if _page_host(page) != expected_host():
            return False
        return bool(page.evaluate(_SIGNED_IN_JS))
    except Exception as e:
        # M1-E/G1: a DOM-eval error (e.g. the site renamed the signed-in markers)
        # used to read IDENTICALLY to a clean "not signed in". Record the class so a
        # log reader can tell them apart; the navigate-level snapshot has the detail.
        log.debug("auth: is_logged_in check errored (%s: %s)", type(e).__name__, e)
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
    """Best-effort snapshot of the page's sign-in signals for diagnostics.

    The URL is taken through page_url_for_display so the access token (which
    rides in the URL fragment for the sub-second between the OAuth redirect
    committing and the SPA's history.replaceState strip) can never reach a log
    line or a failure dump -- this snapshot feeds both."""
    info = {}
    try:
        info["url"] = page_url_for_display(page) or "<unavailable>"
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


def require_site_params(page):
    """Export-path backstop: after sign-in, confirm the app is actually running
    the SELECTED data source / environment, and raise PreflightError if not.

    navigate_with_auth issues at most ONE corrective reload and then accepts the
    next signed-in page unconditionally (the in-memory token can't survive a
    second reload), so a site that ignores the env/src query params after the
    OAuth handoff could leave the app on the WRONG env while still signed in.
    Without this check, run_export derives the output folder name from get_site()
    and would write wrong-env data into a folder LABELED with the selected env
    and report success — which the cross-environment comparison would then trust.
    This mirrors the env-scan's wrong_site verdict
    (gui_worker.EnvScanWorker._check_one).

    No-ops when the running env/src can't be determined (_site_params_ok returns
    True on 'unknown'), so it never blocks a run it cannot positively refute.
    """
    if _site_params_ok(page):
        return
    want_src, want_env = get_site()
    try:
        got = page.evaluate(_CONFIG_JS) or []
    except Exception:
        got = []
    got_env, got_src = (list(got) + [None, None])[:2]
    dump_auth_failure(page, "preflight: wrong site env/src after sign-in",
                      stem="preflight_wrong_env")
    raise PreflightError(
        f"The site loaded the {got_src}-{got_env} data source / environment, "
        f"but {want_src}-{want_env} was selected, and re-checking the sign-in "
        "didn't switch it. Stopping before export so reports aren't saved under "
        "the wrong label — verify the selected data source / environment, then "
        "try again."
    )


def page_url_for_display(page):
    """The page's current address, safe to show in the UI: the URL fragment is
    stripped (the app's sign-in returns the access token in the hash — it must
    never reach the screen). Best-effort: "" when the page can't say."""
    try:
        return urlsplit(page.url)._replace(fragment="").geturl()
    except Exception:
        return ""
