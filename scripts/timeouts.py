"""Engine timeout defaults + Settings-backed accessors (P8a leaf).

Extracted verbatim from `common.py`. The constants are the DEFAULTS; the Settings
tab can override the ceilings (persisted via settings.py), so engines call the
ACCESSORS (`report_timeout_ms()` etc.) at RUN time and a changed setting applies to
the next run without a restart (CLAUDE.md convention). `settings` is imported lazily
inside `_settings_ms` so this stays an import-time leaf (no module-load dependency).

`common.py` re-exports every constant and accessor here, so callers'
`from common import report_timeout_ms` (and the constants) are unchanged. The module
logger keeps the `"tsmis.auth"` name `common.py` used, so the one warning this module
can emit lands in the log byte-for-byte as before.

Console-free; stdlib only at import time.
"""
import logging

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

# How long to wait for the Export *download* to begin after the report has
# already rendered. The site builds every Excel export client-side (SheetJS
# serializes the already-fetched, already-rendered rows synchronously), so a
# non-empty report's download fires within a second of the click -- the per-route
# ceilings above size the report-GENERATION wait, not this. A rendered route
# whose Export produces no download is the site's "nothing to export" no-op
# (e.g. an empty Intersection Detail), so capping this window lets the engine
# record the route as empty in seconds instead of waiting out the full ceiling
# (and then the 15-min retry) on a download that will never start. Generous on
# purpose; settings-backed (download_start_timeout_s) but with no Settings-tab
# control yet -- raise it by hand-editing data/config.json only if a real report
# legitimately needs longer.
DOWNLOAD_START_TIMEOUT_MS = 60_000

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
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        log.warning("settings read failed for %s (%s: %s); using default",
                    key, type(e).__name__, reason)
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


def download_start_timeout_ms():
    """Effective wait for the Export download to start after a rendered report
    (settings-backed via download_start_timeout_s — config.json only, no Settings
    UI; default DOWNLOAD_START_TIMEOUT_MS). See the constant's note: this bounds
    the download, NOT report generation."""
    return _settings_ms("download_start_timeout_s", DOWNLOAD_START_TIMEOUT_MS, 1_000)
