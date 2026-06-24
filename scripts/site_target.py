"""TSMIS site/environment selection + report-page URL building (P8a leaf).

Extracted verbatim from `common.py`: the host constants, the data-source /
environment vocabulary, the process-global + per-thread site selection
(`set_site` / `set_thread_site` / `get_site`), and the URL builders (`get_url`,
`default_site_url`, `dev_site_url`, `expected_host`). One TSMIS page serves every
(data source × environment) combination via query parameters; this module owns
"which combination the next navigation targets" and the URL that encodes it.

`settings` is imported lazily inside `get_url` (the custom-URL override), so this
stays an import-time leaf. The module logger keeps the `"tsmis.auth"` name
`common.py` used, so `set_site` / `get_url` log byte-for-byte as before (it is the
SAME logger object as `common.log`). `common.py` re-exports every public name
here, so callers' `from common import get_url` (and friends) are unchanged.

NAMED `site_target` rather than `site`: a flat `site.py` on `scripts/` would be
shadowed by the Python standard-library `site` module (preloaded into
`sys.modules` at interpreter startup), so `from site import get_url` would resolve
to the stdlib module and fail. Console-free; stdlib only at import time.
"""
import logging
import os
import threading
from urllib.parse import urlsplit

log = logging.getLogger("tsmis.auth")

# The TSMIS report site. One page serves every combination of data source
# (SSOR / ARS) and environment (prod / test / dev) via query parameters; the
# user picks both in the GUI header (set_site) or via TSMIS_SRC / TSMIS_ENV in
# the console flow. Defaults: SSOR + prod.
TSMIS_HOST = "tsmis.dot.ca.gov"
# The development host (same path + ?env=/?src= scheme). The dev site offers
# report types still greyed in production (Intersection Summary/Detail), so the
# Settings "use development site" preset points all six combos here.
TSMIS_DEV_HOST = "tsmis-dev.dot.ca.gov"
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


# The env-access scan probes several src/env combos in PARALLEL worker
# threads; a process-wide set_site would race (and fight the user's header
# selection). A scanner thread pins its own target here instead — every
# site-aware helper (get_url, expected_host, _site_params_ok, the signed-in
# host check) flows through get_site(), so the pin retargets all of them for
# that thread only. Engine/export/login threads never set this and keep
# following the global selection.
_thread_site = threading.local()


def set_thread_site(source=None, environment=None):
    """Pin THIS thread's site target (both None = clear the pin). A partial pin
    (exactly one of source/environment given) is treated as "clear" rather than
    crashing on a None.lower() -- callers always pass both or neither."""
    if not source or not environment:
        _thread_site.pair = None
    else:
        _thread_site.pair = (source.lower(), environment.lower())


def get_site():
    """The active (data_source, environment) pair — this thread's pin when
    one is set (env-access scan workers), else the global selection."""
    pair = getattr(_thread_site, "pair", None)
    return pair if pair else (_data_source, _environment)


def default_site_url(source, environment):
    """The built-in report-page URL for one data source / environment."""
    return f"https://{TSMIS_HOST}/index.html?env={environment}&src={source}"


def dev_site_url(source, environment):
    """The DEVELOPMENT-host report-page URL for one data source / environment —
    the Settings 'use development site' preset (where Intersection reports live)."""
    return f"https://{TSMIS_DEV_HOST}/index.html?env={environment}&src={source}"


def get_url():
    """The full report-page URL for the active data source / environment
    (this thread's pin when set — see set_thread_site). A Settings-tab
    override (settings.get_site_url — the "site moved before an app update
    shipped" stopgap) wins over the built-in pattern and applies to the very
    next navigation."""
    src, env = get_site()
    try:
        import settings
        override = settings.get_site_url(src, env)
    except Exception:                    # settings must never stop a run
        override = None
    if override:
        log.info("site: using custom URL for %s-%s: %s", src, env, override)
        return override
    return default_site_url(src, env)


def expected_host():
    """Hostname the ACTIVE site URL points at. The signed-in detector and the
    navigation breadcrumbs compare page hosts against this (not the built-in
    TSMIS_HOST), so a custom URL override moves them along with it."""
    try:
        return urlsplit(get_url()).hostname or TSMIS_HOST
    except (ValueError, TypeError):
        return TSMIS_HOST
