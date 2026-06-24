"""Engine exception types (P8a leaf — the lowest layer, no dependencies).

Extracted verbatim from `common.py` so the exception vocabulary lives in one
small module the rest of the engine can depend on without pulling in Playwright,
auth, or navigation. `common.py` re-exports every name here, so
`from common import AuthError` (and friends) is unchanged for all callers.

Console-free, dependency-free (stdlib only — in fact no imports at all). The
catch hierarchy is preserved exactly: `SiteUnreachableError` and
`ReportUnavailableError` subclass `PreflightError`, so every driver's existing
"the run can't start; show the message as-is" handling is unaffected.
"""


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


class ReportUnavailableError(PreflightError):
    """Raised when the chosen report is greyed out on the live site (the site
    marks it `cs-disabled` -- TSMIS can temporarily disable a report from
    exporting by design). Subclasses PreflightError so every driver shows the
    message as-is, but says "this report is currently unavailable" rather than
    the generic "the page looks different" -- and it's caught BEFORE the inert
    dropdown click would stall ~30 s into a preflight failure."""


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
