"""Persisted user settings (config.json under the app's private data dir).

The reliability / debugging knobs the GUI's Settings tab edits. Consumers
read through accessor functions at RUN time (not import time), so a change
applies to the next run without restarting:

  * common.py        -> the per-route / county timeout ceilings
  * exporter_parallel-> the default fast-mode worker count
  * logging_setup    -> verbose (DEBUG) file logging
  * gui_api          -> open DevTools on the next launch

The console flow gets the same overrides automatically because common.py
reads through here. Precedence stays: explicit function arguments and
TSMIS_* environment variables (where one exists) win over this file, which
wins over the built-in defaults.

Console-free and dependency-free (stdlib + paths only — common.py imports
this, so this module must never import common). Tolerant by design: a
missing or broken config.json silently means "defaults" (with a log line),
unknown keys survive round-trips, and writes go through a temp file so a
crash mid-write can't leave half a JSON file.
"""
import json
import logging
import os
import tempfile
from urllib.parse import urlsplit

from paths import CONFIG_FILE

log = logging.getLogger("tsmis.settings")

# Built-in defaults. Timeout values mirror the documented constants in
# common.py (minutes/seconds here — the file stays human-editable).
DEFAULTS = {
    "report_timeout_min": 6,     # per-route ceiling, sequential flow
    "fast_timeout_min": 10,      # per-route ceiling, fast mode
    "retry_timeout_min": 15,     # per-route ceiling, end-of-run retry pass
    "county_timeout_s": 60,      # county dropdown enable wait
    "fast_workers": 3,           # default fast-mode browser count
    "debug_logging": False,      # verbose (DEBUG) file logging
    "ui_devtools": False,        # open WebView2 DevTools on the next launch
    "env_check_on_start": True,  # auto-run the env-access scan after start/sign-in
}

# Validation: (min, max) for the numeric knobs; values outside are clamped.
# 30 mirrors exporter_parallel.MAX_WORKERS (not imported — that would pull
# the whole engine, and through it Playwright, into every settings read).
_RANGES = {
    "report_timeout_min": (1, 120),
    "fast_timeout_min": (1, 120),
    "retry_timeout_min": (1, 180),
    "county_timeout_s": (10, 600),
    "fast_workers": (1, 30),
}

_cache = None          # parsed file content
_cache_mtime = None    # CONFIG_FILE mtime the cache was read at


def _read_file():
    """The raw dict from config.json ({} when missing/broken), cached by
    mtime so repeated get() calls don't re-read an unchanged file but a
    change from another process (GUI vs console) is still picked up."""
    global _cache, _cache_mtime
    try:
        mtime = os.path.getmtime(CONFIG_FILE)
    except OSError:
        _cache, _cache_mtime = {}, None
        return _cache
    if _cache is not None and mtime == _cache_mtime:
        return _cache
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache = data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        log.warning("settings: could not read %s (%s: %s); using defaults",
                    CONFIG_FILE, type(e).__name__, e)
        _cache = {}
    _cache_mtime = mtime
    return _cache


def _clamp(key, value):
    """Coerce + clamp a numeric setting; None when the value is unusable."""
    lo, hi = _RANGES[key]
    try:
        v = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(lo, min(v, hi))


def get(key):
    """The effective value of one setting (file value validated, else its
    default). Unknown keys raise KeyError — a typo'd key is a bug, not a
    user state."""
    default = DEFAULTS[key]
    raw = _read_file().get(key, default)
    if key in _RANGES:
        v = _clamp(key, raw)
        return default if v is None else v
    return bool(raw) if isinstance(default, bool) else raw


def all_settings():
    """Every known setting at its effective value (for the Settings tab)."""
    return {k: get(k) for k in DEFAULTS}


def update(changes):
    """Validate + persist `changes` (a dict of known keys), returning the new
    effective settings. Unknown keys are ignored with a log line; numeric
    values are clamped into range. The write is temp-file + os.replace so a
    crash can't truncate the config."""
    global _cache, _cache_mtime
    data = dict(_read_file())
    for key, value in (changes or {}).items():
        if key not in DEFAULTS:
            log.info("settings: ignoring unknown key %r", key)
            continue
        if key in _RANGES:
            v = _clamp(key, value)
            if v is None:
                log.info("settings: ignoring unusable value %r for %s", value, key)
                continue
            data[key] = v
        elif isinstance(DEFAULTS[key], bool):
            data[key] = bool(value)
        else:
            data[key] = value
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(CONFIG_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, CONFIG_FILE)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _cache, _cache_mtime = None, None       # next get() re-reads
    log.info("settings: saved %s -> %s", dict(changes or {}), CONFIG_FILE)
    return all_settings()


# ---- per-site URL overrides -------------------------------------------------
# Stored under the "site_urls" key as {"<src>-<env>": "https://…", ...} —
# a stopgap for "the site moved before an app update shipped". common.get_url()
# consults these on every navigation, so a change applies immediately. NOT part
# of DEFAULTS/all_settings (those stay scalar); the Settings tab edits these
# through gui_api.set_site_url.

def _valid_url(url):
    try:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and bool(parts.netloc)
    except (TypeError, ValueError):
        return False


def get_site_url(src, env):
    """The override URL for one (src, env), or None when unset/unusable."""
    urls = _read_file().get("site_urls")
    if not isinstance(urls, dict):
        return None
    url = urls.get(f"{src}-{env}")
    return url if isinstance(url, str) and _valid_url(url) else None


def all_site_urls():
    """Every VALID saved override, {"src-env": url}."""
    urls = _read_file().get("site_urls")
    if not isinstance(urls, dict):
        return {}
    return {k: v for k, v in urls.items()
            if isinstance(v, str) and _valid_url(v)}


def set_site_url(src, env, url):
    """Save (or, with an empty url, clear) one site's URL override.
    Raises ValueError with a user-safe message for an unusable URL."""
    global _cache, _cache_mtime
    key = f"{src}-{env}"
    url = (url or "").strip()
    if url and not _valid_url(url):
        raise ValueError("That doesn't look like a usable web address — it "
                         "needs to start with https:// (or http://).")
    data = dict(_read_file())
    urls = dict(data.get("site_urls") or {})
    if url:
        urls[key] = url
    else:
        urls.pop(key, None)
    if urls:
        data["site_urls"] = urls
    else:
        data.pop("site_urls", None)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(CONFIG_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, CONFIG_FILE)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _cache, _cache_mtime = None, None
    log.info("settings: site url %s -> %s", key, url or "(default)")
    return all_site_urls()


def reset():
    """Delete the settings file (back to all defaults). Returns True if a
    file was removed."""
    global _cache, _cache_mtime
    _cache, _cache_mtime = None, None
    try:
        CONFIG_FILE.unlink()
        log.info("settings: reset (deleted %s)", CONFIG_FILE)
        return True
    except FileNotFoundError:
        return False
