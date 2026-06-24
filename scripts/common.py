"""Shared engine helpers for every TSMIS export script — and, since the v0.18.0
engine decomposition (P8a + P8b), the re-export SHIM over the extracted layers.

The whole engine now lives in flat, layered modules and is RE-EXPORTED here, so
`from common import X` is unchanged for every consumer (the import surface):
  * `errors`           — exception types
  * `site_target`      — site/env selection + report URL
  * `timeouts`         — timeout defaults + Settings accessors
  * `routes`           — the route list + parser
  * `browser_channels` — browser launch + channel resolution (L1)
  * `auth_nav`         — page sign-in/navigation + the auth-file lifecycle (L2)
  * `report_nav`       — report-form select/preflight/wait/error (L2', above auth_nav)
  * `edge_device`      — Edge device-SSO login + storage-state capture (L3)
  * `session`          — `new_authed_browser` session orchestration (L4)
The modules form a verified acyclic DAG (leaves -> channels/auth -> report ->
edge -> session); see check_import_direction. Report-specific logic (which report
to pick, how to save the result) lives in ReportSpec objects (see exporter.py).

This module is console-free: auth problems raise AuthError and progress is
reported through an Events sink, so the same helpers back both the console
shim (cli.py) and the GUI.
"""
import logging

from paths import AUTH
from errors import (AuthError, PreflightError, SiteUnreachableError,
                    ReportUnavailableError, BrowserNotFoundError, RunCancelled,
                    ReportError)
from site_target import (TSMIS_HOST, TSMIS_DEV_HOST, DATA_SOURCES, ENVIRONMENTS,
                         DATA_SOURCE_LABELS, ENVIRONMENT_LABELS, set_site,
                         set_thread_site, get_site, default_site_url, dev_site_url,
                         get_url, expected_host)
from timeouts import (REPORT_TIMEOUT_MS, SKIP_PROMPT_AFTER_MS,
                      COUNTY_ENABLE_TIMEOUT_MS, DOWNLOAD_START_TIMEOUT_MS,
                      FAST_REPORT_TIMEOUT_MS, RETRY_REPORT_TIMEOUT_MS, RETRY_COUNT,
                      report_timeout_ms, fast_report_timeout_ms,
                      retry_report_timeout_ms, county_enable_timeout_ms,
                      download_start_timeout_ms)
from routes import ROUTES, normalize_route, parse_routes
from browser_channels import (BROWSER_CHANNELS, CHANNEL_LABELS, LOGIN_BROWSER_ARGS,
                              check_browsers, get_preferred_channel,
                              init_preferred_channel_from_settings,
                              set_preferred_channel, launch_browser,
                              new_login_context, resolve_parallel_channel)
from auth_nav import (clear_auth, require_valid_auth, has_valid_auth,
                      save_auth_state, _auth_file_age_hours, auth_state,
                      navigate_with_auth, is_logged_in, require_signed_in,
                      require_site_params, dump_auth_failure, _CONFIG_JS,
                      page_url_for_display)
from report_nav import (ERROR_JS, EXPORT_READY_JS, maybe_screenshot, preflight,
                        report_error_text, select_report, wait_with_skip_option)
from edge_device import (capture_edge_login_state_from_profiles,
                         capture_edge_login_state_over_cdp,
                         capture_storage_state_if_logged_in,
                         launch_edge_login_context, open_edge_device_context,
                         storage_state_is_portable, try_device_sso_login)
from session import new_authed_browser

log = logging.getLogger("tsmis.auth")
