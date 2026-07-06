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
from urllib.parse import parse_qs, urlsplit

from paths import CONFIG_FILE, OUTPUT_ROOT

log = logging.getLogger("tsmis.settings")

# Built-in defaults. Timeout values mirror the documented constants in
# common.py (minutes/seconds here — the file stays human-editable).
DEFAULTS = {
    "report_timeout_min": 6,     # per-route ceiling, sequential flow
    "fast_timeout_min": 10,      # per-route ceiling, fast mode
    "retry_timeout_min": 15,     # per-route ceiling, end-of-run retry pass
    "county_timeout_s": 60,      # county dropdown enable wait
    "download_start_timeout_s": 60,  # max wait for the Export download to START
    "fast_workers": 3,           # default fast-mode browser count
    "debug_logging": False,      # verbose (DEBUG) file logging
    "ui_devtools": False,        # open WebView2 DevTools on the next launch
    "env_check_after_signin": True,   # auto-run the env-access scan after sign-in
    "env_check_after_start": False,    # ...and after app start (off by default)
    "notify_on_finish": True,    # flash the taskbar when a run/batch finishes
}

# Validation: (min, max) for the numeric knobs; values outside are clamped.
# 30 mirrors exporter_parallel.MAX_WORKERS (not imported — that would pull
# the whole engine, and through it Playwright, into every settings read).
_RANGES = {
    "report_timeout_min": (1, 120),
    "fast_timeout_min": (1, 120),
    "retry_timeout_min": (1, 180),
    "county_timeout_s": (10, 600),
    "download_start_timeout_s": (10, 600),
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
    except json.JSONDecodeError as e:
        # Corrupt CONTENT: don't silently fall back to defaults and then let the
        # next write overwrite (and lose) the user's site_urls / overrides. Move
        # the bad file aside first so it can be recovered, and log it loudly.
        log.warning("settings: %s is corrupt (%s); preserving it as a backup and "
                    "falling back to defaults", CONFIG_FILE, e)
        _backup_corrupt_config()
        _cache = {}
    except OSError as e:                 # transient read error: keep the file
        log.warning("settings: could not read %s (%s: %s); using defaults",
                    CONFIG_FILE, type(e).__name__, e)
        _cache = {}
    _cache_mtime = mtime
    return _cache


def _backup_corrupt_config():
    """Move a corrupt config.json aside to config.json.corrupt (recoverable),
    so a fresh write doesn't silently destroy the user's saved overrides."""
    bad = CONFIG_FILE.parent / (CONFIG_FILE.name + ".corrupt")
    try:
        os.replace(CONFIG_FILE, bad)
        log.warning("settings: corrupt config moved to %s for recovery", bad)
    except OSError as e:
        log.warning("settings: could not back up corrupt config (%s: %s)",
                    type(e).__name__, e)


def _atomic_write(data):
    """Persist the settings dict atomically (temp file + ``os.replace``) and bust
    the cache. The ONE writer every setter routes through (R1-N02 dedup): a crash
    or lock mid-write can't truncate the prior good config, and on a write error the
    temp is removed and the original error re-raised so the prior file is untouched."""
    global _cache, _cache_mtime
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


# Settings safe to put in a shareable diagnostic support bundle. An explicit
# ALLOWLIST (not all_settings()) so adding a future DEFAULTS key that holds
# something sensitive (a path with PII, a token, a username, ...) does NOT silently
# leak into a bundle the user emails out: a new key must be listed here, after a
# review, before it appears in the bundle (support-bundle-settings-future-leak,
# R1-N02). The asymmetry (allowlist ⊆ DEFAULTS, not ==) is the safeguard.
_SUPPORT_BUNDLE_KEYS = (
    "report_timeout_min", "fast_timeout_min", "retry_timeout_min",
    "county_timeout_s", "download_start_timeout_s", "fast_workers",
    "debug_logging", "ui_devtools", "env_check_after_signin",
    "env_check_after_start", "notify_on_finish",
)
assert set(_SUPPORT_BUNDLE_KEYS) <= set(DEFAULTS), \
    "settings: support-bundle allowlist names an unknown setting"


def support_bundle_settings():
    """The allowlisted subset of settings safe to include in a shareable support
    bundle (the reliability/debug knobs), each at its effective value. Excludes
    site_urls / batch_dest / matrix_* and anything not explicitly allowlisted, so a
    future sensitive setting is not auto-shared — the bundle calls THIS, never
    all_settings()."""
    return {k: get(k) for k in _SUPPORT_BUNDLE_KEYS}


def update(changes):
    """Validate + persist `changes` (a dict of known keys), returning the new
    effective settings. Unknown keys are ignored with a log line; numeric
    values are clamped into range. The write goes through `_atomic_write`
    (temp file + os.replace) so a crash can't truncate the config."""
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
    _atomic_write(data)
    log.info("settings: saved %s -> %s", dict(changes or {}), CONFIG_FILE)
    return all_settings()


# ---- per-site URL overrides -------------------------------------------------
# Stored under the "site_urls" key as {"<src>-<env>": "https://…", ...} —
# a stopgap for "the site moved before an app update shipped". common.get_url()
# consults these on every navigation, so a change applies immediately. NOT part
# of DEFAULTS/all_settings (those stay scalar); the Settings tab edits these
# through gui_api.set_site_url.
#
# An override is VALIDATED against the combo it overrides (not just "is it a
# URL"): it must be https, point at a California state host (*.ca.gov), and carry
# matching ?env=/?src= query params. Without the param check a custom address
# missing ?env=/?src= would default the site to prod/ars and could silently
# mislabel output as the wrong environment; the host + scheme limits keep a
# typo / misdirection from pointing the app (with its saved session) at an
# arbitrary off-network origin. An invalid stored value is ignored on read (the
# app falls back to the built-in URL) rather than trusted.


def _host_is_ca_gov(host):
    host = (host or "").lower()
    return host == "ca.gov" or host.endswith(".ca.gov")


def _override_problem(url, src, env):
    """A user-safe reason `url` is unusable as the override for (src, env), or
    None when it's valid. Enforces https + a *.ca.gov host + matching
    ?env=/?src= params."""
    try:
        parts = urlsplit(url)
    except (TypeError, ValueError):
        return "That doesn't look like a usable web address."
    if not parts.netloc:
        return "That doesn't look like a usable web address."
    if parts.scheme != "https":
        return "The address must start with https://."
    if not _host_is_ca_gov(parts.hostname):
        return ("The address must be a California state site "
                "(a .ca.gov web address).")
    q = parse_qs(parts.query)
    got_env = (q.get("env") or [""])[0].lower()
    got_src = (q.get("src") or [""])[0].lower()
    if got_env != env or got_src != src:
        return (f"The address must include ?env={env}&src={src} so it matches "
                f"this environment (found env={got_env or '—'}, "
                f"src={got_src or '—'}).")
    return None


def get_site_url(src, env):
    """The override URL for one (src, env), or None when unset/unusable."""
    urls = _read_file().get("site_urls")
    if not isinstance(urls, dict):
        return None
    url = urls.get(f"{src}-{env}")
    if not isinstance(url, str) or _override_problem(url, src, env) is not None:
        return None
    return url


def all_site_urls():
    """Every VALID saved override, {"src-env": url} (invalid ones omitted)."""
    urls = _read_file().get("site_urls")
    if not isinstance(urls, dict):
        return {}
    out = {}
    for key, v in urls.items():
        if not isinstance(v, str):
            continue
        try:
            src, env = key.split("-", 1)
        except ValueError:
            continue
        if _override_problem(v, src, env) is None:
            out[key] = v
    return out


def set_site_url(src, env, url):
    """Save (or, with an empty url, clear) one site's URL override.
    Raises ValueError with a user-safe message for an unusable URL."""
    key = f"{src}-{env}"
    url = (url or "").strip()
    if url:
        problem = _override_problem(url, src, env)
        if problem:
            raise ValueError(problem)
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
    _atomic_write(data)
    log.info("settings: site url %s %s", key, "set" if url else "reset to default")
    return all_site_urls()


# ---- Export Everything destination (B3) -------------------------------------
# The always-current folder Export Everything refreshes into (a single string
# path under the "batch_dest" key). Empty/unset -> the default below. A plain
# local folder path the user picks from a dialog, so it isn't URL-validated.

def default_batch_dest():
    return str(OUTPUT_ROOT / "All Reports (current)")


def get_batch_dest():
    """The configured Export-Everything destination, or the default folder."""
    raw = _read_file().get("batch_dest")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return default_batch_dest()


def set_batch_dest(path):
    """Save (or, with an empty path, reset to default) the Export-Everything
    destination. Returns the new effective destination."""
    path = (path or "").strip()
    data = dict(_read_file())
    if path:
        data["batch_dest"] = path
    else:
        data.pop("batch_dest", None)
    _atomic_write(data)
    log.info("settings: batch_dest %s", "set" if path else "reset to default")
    return get_batch_dest()


# ---- Comparison-matrix baseline --------------------------------------------
# The environment the matrix compares every other env against (a "src-env" key
# like "ssor-prod"). Empty/unset -> the default. The caller (gui_api) validates
# the key against the known combos before saving (like batch_dest, this stores a
# plain string and isn't validated here, so settings stays common-free).

_DEFAULT_MATRIX_BASELINE = "ssor-prod"


def get_matrix_baseline():
    """The configured matrix baseline env key, or the default."""
    raw = _read_file().get("matrix_baseline")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return _DEFAULT_MATRIX_BASELINE


def set_matrix_baseline(key):
    """Save (or, with an empty key, reset to default) the matrix baseline.
    Returns the new effective baseline."""
    key = (key or "").strip()
    data = dict(_read_file())
    if key:
        data["matrix_baseline"] = key
    else:
        data.pop("matrix_baseline", None)
    _atomic_write(data)
    log.info("settings: matrix_baseline -> %s", key or "(default)")
    return get_matrix_baseline()


# ---- Export browser (which Chromium-class browser does the work) ------------
# Edge stays the implicit one-click / device sign-in path and the ultimate
# fallback; this pins which CHROMIUM-CLASS browser normal exports, fast-mode
# workers and the login capture prefer. "" / absent = auto (Chrome when
# installed, else Built-in Chromium). NOT in DEFAULTS: the right auto depends on
# what's installed, so a hardcoded default would mislead all_settings()/resolver.

def get_export_browser():
    """The pinned export browser ('chrome' or 'chromium'), or '' for auto
    (Chrome-first). Any other stored value is treated as unset."""
    raw = _read_file().get("export_browser")
    return raw if raw in ("chrome", "chromium") else ""


def set_export_browser(channel):
    """Pin the export browser to 'chrome'/'chromium', or clear it (any other
    value, including 'msedge' or '', means auto). Returns the new effective
    value."""
    data = dict(_read_file())
    if channel in ("chrome", "chromium"):
        data["export_browser"] = channel
    else:
        data.pop("export_browser", None)
    _atomic_write(data)
    log.info("settings: export_browser -> %s", get_export_browser() or "(auto)")
    return get_export_browser()


# ---- Comparison-matrix report visibility -----------------------------------
# Which report ROWS the matrix shows (and refreshes). Stored as the set of HIDDEN
# row keys so any report type added later defaults to VISIBLE. Validation (key is
# a known matrix row) lives in gui_api; settings just stores the list.

def get_matrix_hidden_reports():
    """The list of matrix row keys the user has hidden (default: none hidden)."""
    raw = _read_file().get("matrix_hidden_reports")
    if isinstance(raw, list):
        return [k for k in raw if isinstance(k, str)]
    return []


def set_matrix_hidden_reports(keys):
    """Persist the hidden matrix row keys (a list of strings). Empty -> cleared.
    Returns the new effective list."""
    data = dict(_read_file())
    keys = [k for k in (keys or []) if isinstance(k, str)]
    if keys:
        data["matrix_hidden_reports"] = sorted(set(keys))
    else:
        data.pop("matrix_hidden_reports", None)
    _atomic_write(data)
    log.info("settings: matrix_hidden_reports -> %s", keys or "(none)")
    return get_matrix_hidden_reports()


# ---- Comparison-matrix modes / env visibility / TSN files ------------------
# Per-row comparison MODE (env / tsn / vs-format), the hidden ENV columns, and the
# TSN file the user explicitly picked per subdir (else the matrix auto-finds one in
# <dest>/_tsn_input/<subdir>/). Validation lives in gui_api.

def get_matrix_row_modes():
    """{row_key: mode_id} — the comparison mode chosen per row (default: 'env',
    omitted from the map)."""
    raw = _read_file().get("matrix_row_modes")
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items()
                if isinstance(k, str) and isinstance(v, str) and v}
    return {}


def set_matrix_row_mode(row_key, mode_id):
    """Set one row's comparison mode. 'env' (the default) clears the entry.
    Returns the new {row_key: mode_id} map."""
    data = dict(_read_file())
    modes = dict(get_matrix_row_modes())
    mode_id = (mode_id or "").strip()
    if mode_id and mode_id != "env":
        modes[row_key] = mode_id
    else:
        modes.pop(row_key, None)
    if modes:
        data["matrix_row_modes"] = modes
    else:
        data.pop("matrix_row_modes", None)
    _atomic_write(data)
    log.info("settings: matrix_row_mode[%s] -> %s", row_key, mode_id or "env")
    return get_matrix_row_modes()


def get_matrix_hidden_envs():
    """Env (column) keys the user has hidden on the matrix (default: none)."""
    raw = _read_file().get("matrix_hidden_envs")
    if isinstance(raw, list):
        return [k for k in raw if isinstance(k, str)]
    return []


def set_matrix_hidden_envs(keys):
    """Persist the hidden env-column keys. Empty -> cleared. Returns the new list."""
    data = dict(_read_file())
    keys = [k for k in (keys or []) if isinstance(k, str)]
    if keys:
        data["matrix_hidden_envs"] = sorted(set(keys))
    else:
        data.pop("matrix_hidden_envs", None)
    _atomic_write(data)
    log.info("settings: matrix_hidden_envs -> %s", keys or "(none)")
    return get_matrix_hidden_envs()


# ---- Matrix ROW / COLUMN ORDER (drag-to-reorder) ---------------------------
# A user-chosen display order for the matrix rows (reports) and columns (envs on
# the Everything matrix, days on the by-day matrix). Unlike the hidden lists these
# PRESERVE order (no sort). The list is a PREFERENCE, not the source of truth:
# apply_order() (matrix.py) treats it as a sort key over the ACTUAL rows/columns,
# so a report/env/day added or removed later degrades gracefully (unknown keys fall
# to the end in their natural order; stale keys are ignored).

def _get_order(name):
    """A de-duplicated, order-preserving list of string keys for `name` (or [])."""
    raw = _read_file().get(name)
    if not isinstance(raw, list):
        return []
    seen, out = set(), []
    for k in raw:
        if isinstance(k, str) and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _set_order(name, keys):
    """Persist an order list (de-duplicated, order preserved). Empty -> cleared."""
    data = dict(_read_file())
    seen, clean = set(), []
    for k in (keys or []):
        if isinstance(k, str) and k not in seen:
            seen.add(k)
            clean.append(k)
    if clean:
        data[name] = clean
    else:
        data.pop(name, None)
    _atomic_write(data)
    log.info("settings: %s -> %s", name, clean or "(none)")
    return _get_order(name)


def get_matrix_row_order():
    """Preferred row (report) order for the Everything matrix."""
    return _get_order("matrix_row_order")


def set_matrix_row_order(keys):
    return _set_order("matrix_row_order", keys)


def get_matrix_env_order():
    """Preferred env-column order for the Everything matrix."""
    return _get_order("matrix_env_order")


def set_matrix_env_order(keys):
    return _set_order("matrix_env_order", keys)


def get_day_matrix_row_order():
    """Preferred row (report) order for the by-day matrix."""
    return _get_order("day_matrix_row_order")


def set_day_matrix_row_order(keys):
    return _set_order("day_matrix_row_order", keys)


def get_matrix_tsn_files():
    """{subdir: tsn_file_path} the user explicitly selected (keyed by the report's
    store subdir, since the TSN dataset is per format — highway_log vs
    highway_log_pdf)."""
    raw = _read_file().get("matrix_tsn_files")
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items()
                if isinstance(k, str) and isinstance(v, str) and v.strip()}
    return {}


def set_matrix_tsn_file(subdir, path):
    """Set (or, with an empty path, clear) the TSN file for one report subdir.
    Returns the new {subdir: path} map."""
    data = dict(_read_file())
    files = dict(get_matrix_tsn_files())
    path = (path or "").strip()
    if path:
        files[subdir] = path
    else:
        files.pop(subdir, None)
    if files:
        data["matrix_tsn_files"] = files
    else:
        data.pop("matrix_tsn_files", None)
    _atomic_write(data)
    log.info("settings: matrix_tsn_file[%s] -> %s", subdir, path or "(default)")
    return get_matrix_tsn_files()


# ---- Comparison-matrix fast (parallel) mode --------------------------------
# Whether the matrix's live re-exports run in fast mode (N browsers per env). A
# matrix-local toggle, NOT a Settings-tab knob — it reuses the global
# "fast_workers" count for N, so it lives here (not in DEFAULTS/all_settings).

def get_matrix_fast():
    """Whether matrix re-exports run in fast (parallel) mode (default off)."""
    return bool(_read_file().get("matrix_fast", False))


def set_matrix_fast(on):
    """Persist the matrix fast-mode toggle (cleared when off). Returns the new
    effective value."""
    data = dict(_read_file())
    if on:
        data["matrix_fast"] = True
    else:
        data.pop("matrix_fast", None)
    _atomic_write(data)
    log.info("settings: matrix_fast -> %s", bool(on))
    return get_matrix_fast()


def get_matrix_formulas():
    """Whether matrix comparisons ALSO write a live-formulas workbook beside the
    values copy (default off; the values copy always wins for the offline counts)."""
    return bool(_read_file().get("matrix_formulas", False))


def set_matrix_formulas(on):
    """Persist the matrix formulas-workbook toggle (cleared when off). Returns the
    new effective value."""
    data = dict(_read_file())
    if on:
        data["matrix_formulas"] = True
    else:
        data.pop("matrix_formulas", None)
    _atomic_write(data)
    log.info("settings: matrix_formulas -> %s", bool(on))
    return get_matrix_formulas()


def get_day_matrix_formulas():
    """Whether the by-day matrix ALSO writes a live-formulas workbook (its own
    toggle, independent of the Everything matrix's; default off)."""
    return bool(_read_file().get("day_matrix_formulas", False))


def set_day_matrix_formulas(on):
    """Persist the by-day matrix formulas-workbook toggle (cleared when off).
    Returns the new effective value."""
    data = dict(_read_file())
    if on:
        data["day_matrix_formulas"] = True
    else:
        data.pop("day_matrix_formulas", None)
    _atomic_write(data)
    log.info("settings: day_matrix_formulas -> %s", bool(on))
    return get_day_matrix_formulas()


# ---- Compare-tab "TSN by day" matrix ---------------------------------------
# The data source (a "src-env" key), the picked day-columns (date strings), and
# the hidden report rows. The TSN file reuses matrix_tsn_files (one TSN dataset).
# Validation (known source / real run-folder dates) lives in gui_api.

_DEFAULT_DAY_MATRIX_SOURCE = "ssor-prod"


def get_day_matrix_source():
    raw = _read_file().get("day_matrix_source")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return _DEFAULT_DAY_MATRIX_SOURCE


def set_day_matrix_source(key):
    """Save (or, empty, reset) the by-day matrix source. Returns the new value."""
    data = dict(_read_file())
    key = (key or "").strip()
    if key:
        data["day_matrix_source"] = key
    else:
        data.pop("day_matrix_source", None)
    _atomic_write(data)
    log.info("settings: day_matrix_source -> %s", key or "(default)")
    return get_day_matrix_source()


def get_day_matrix_days():
    """The ordered day-column date strings the user added (default: none)."""
    raw = _read_file().get("day_matrix_days")
    if isinstance(raw, list):
        return [d for d in raw if isinstance(d, str) and d]
    return []


def set_day_matrix_days(days):
    """Persist the ordered day-column list. Empty -> cleared. Returns the new list."""
    data = dict(_read_file())
    days = [d for d in (days or []) if isinstance(d, str) and d]
    if days:
        data["day_matrix_days"] = days
    else:
        data.pop("day_matrix_days", None)
    _atomic_write(data)
    log.info("settings: day_matrix_days -> %s", days or "(none)")
    return get_day_matrix_days()


def get_day_matrix_hidden():
    """Hidden report-row keys on the by-day matrix (default: none)."""
    raw = _read_file().get("day_matrix_hidden")
    if isinstance(raw, list):
        return [k for k in raw if isinstance(k, str)]
    return []


def set_day_matrix_hidden(keys):
    """Persist the hidden by-day report rows. Empty -> cleared. Returns the list."""
    data = dict(_read_file())
    keys = [k for k in (keys or []) if isinstance(k, str)]
    if keys:
        data["day_matrix_hidden"] = sorted(set(keys))
    else:
        data.pop("day_matrix_hidden", None)
    _atomic_write(data)
    log.info("settings: day_matrix_hidden -> %s", keys or "(none)")
    return get_day_matrix_hidden()


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
