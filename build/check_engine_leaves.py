"""P8a: engine leaf-module unit checks (routes / timeouts / site_target / errors)
+ the re-export-shim parity contract.

P8a extracts the pure leaves out of common.py behind a re-export shim. This check
locks two things:

  1. Each leaf's behavior is unchanged -- route normalization/parsing, the
     Settings-backed timeout accessors (default + override + unit conversion), the
     site/env selection + URL building, and the exception catch hierarchy.
  2. The 14-module import surface is preserved: `from common import X` yields the
     SAME object the leaf defines (a re-export, not a copy), so every existing
     caller is byte-identical.

Pure Python: imports the real leaf modules + the common shim; no browser, no
network, no auth file. `settings.get` / `settings.get_site_url` are stubbed in
process to exercise the override + fallback paths offline. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_engine_leaves.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import common  # noqa: E402  (the re-export shim)
import errors  # noqa: E402
import routes  # noqa: E402
import site_target  # noqa: E402
import timeouts  # noqa: E402
import settings  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def test_routes():
    print("routes: normalize + parse (verbatim leaf behavior):")
    check("'5' -> '005'", routes.normalize_route("5") == "005")
    check("'05' -> '005'", routes.normalize_route("05") == "005")
    check("'005' -> '005'", routes.normalize_route("005") == "005")
    check("'5s' -> '005S' (suffix, casing)", routes.normalize_route("5s") == "005S")
    check("'005S' -> '005S'", routes.normalize_route("005S") == "005S")
    check("'880s' -> '880S'", routes.normalize_route("880s") == "880S")
    check("unknown '999' -> None", routes.normalize_route("999") is None)
    check("garbage 'abc' -> None", routes.normalize_route("abc") is None)
    check("empty '' -> None", routes.normalize_route("") is None)
    parsed = routes.parse_routes("5, 005S; 880\n101")
    check("mixed separators parse to canonical order + form",
          parsed == ["005", "005S", "101", "880"])
    check("duplicates de-dupe", routes.parse_routes("5 5 005") == ["005"])
    try:
        routes.parse_routes("")
        check("empty input raises ValueError", False)
    except ValueError:
        check("empty input raises ValueError", True)
    try:
        routes.parse_routes("5, 999")
        check("unknown token raises ValueError", False)
    except ValueError as e:
        check("unknown token raises ValueError naming it", "999" in str(e))
    check("ROUTES non-empty + unique", len(routes.ROUTES) == len(set(routes.ROUTES)) > 0)


def test_timeouts():
    print("timeouts: defaults, override, unit conversion, fail-safe:")
    orig = settings.get
    try:
        # Override path: settings.get(key) * unit_ms. min-based -> x60000; sec-based -> x1000.
        settings.get = lambda _key: 10
        check("report_timeout_ms = minutes*60000", timeouts.report_timeout_ms() == 600_000)
        check("fast_report_timeout_ms = minutes*60000", timeouts.fast_report_timeout_ms() == 600_000)
        check("retry_report_timeout_ms = minutes*60000", timeouts.retry_report_timeout_ms() == 600_000)
        check("county_enable_timeout_ms = seconds*1000", timeouts.county_enable_timeout_ms() == 10_000)
        check("download_start_timeout_ms = seconds*1000", timeouts.download_start_timeout_ms() == 10_000)

        # Fail-safe: a settings read error -> the default constant (never raises).
        def boom(_key):
            raise KeyError("missing")
        settings.get = boom
        check("report_timeout_ms falls back to the default", timeouts.report_timeout_ms() == timeouts.REPORT_TIMEOUT_MS)
        check("county_enable_timeout_ms falls back to the default",
              timeouts.county_enable_timeout_ms() == timeouts.COUNTY_ENABLE_TIMEOUT_MS)
    finally:
        settings.get = orig
    check("default constants unchanged (REPORT/COUNTY/RETRY_COUNT)",
          (timeouts.REPORT_TIMEOUT_MS, timeouts.COUNTY_ENABLE_TIMEOUT_MS, timeouts.RETRY_COUNT)
          == (360_000, 60_000, 1))


def test_site_target():
    print("site_target: selection, thread pin, URL building:")
    orig_src, orig_env = site_target.get_site()
    orig_url = settings.get_site_url
    try:
        settings.get_site_url = lambda _s, _e: None      # no custom-URL override
        site_target.set_site("ssor", "prod")
        check("set_site/get_site round-trip", site_target.get_site() == ("ssor", "prod"))
        site_target.set_site("ars", "test")
        check("set_site changes the selection", site_target.get_site() == ("ars", "test"))
        site_target.set_site("BOGUS", "prod")            # invalid src ignored, env kept
        check("invalid source ignored (selection kept)", site_target.get_site() == ("ars", "prod"))
        check("default_site_url prod host",
              site_target.default_site_url("ssor", "prod")
              == "https://tsmis.dot.ca.gov/index.html?env=prod&src=ssor")
        check("dev_site_url dev host",
              site_target.dev_site_url("ars", "dev")
              == "https://tsmis-dev.dot.ca.gov/index.html?env=dev&src=ars")
        check("get_url builds from the selection when no override",
              site_target.get_url() == "https://tsmis.dot.ca.gov/index.html?env=prod&src=ars")
        check("expected_host of the active URL", site_target.expected_host() == "tsmis.dot.ca.gov")
        # thread pin overrides the global selection for THIS thread only
        site_target.set_thread_site("ssor", "dev")
        check("thread pin wins over the global selection", site_target.get_site() == ("ssor", "dev"))
        site_target.set_thread_site(None, None)
        check("clearing the pin restores the global selection", site_target.get_site() == ("ars", "prod"))
        # custom-URL override wins
        settings.get_site_url = lambda _s, _e: "https://moved.example/r"
        check("settings custom-URL override wins over the built-in pattern",
              site_target.get_url() == "https://moved.example/r")
    finally:
        settings.get_site_url = orig_url
        site_target.set_thread_site(None, None)
        site_target.set_site(orig_src, orig_env)


def test_errors():
    print("errors: the preflight catch hierarchy is preserved:")
    check("SiteUnreachableError is a PreflightError", issubclass(errors.SiteUnreachableError, errors.PreflightError))
    check("ReportUnavailableError is a PreflightError", issubclass(errors.ReportUnavailableError, errors.PreflightError))
    check("AuthError is NOT a PreflightError", not issubclass(errors.AuthError, errors.PreflightError))
    check("each error is an Exception",
          all(issubclass(c, Exception) for c in (errors.AuthError, errors.PreflightError,
              errors.BrowserNotFoundError, errors.RunCancelled, errors.ReportError)))


def test_shim_parity():
    """The 14-module import surface: `from common import X` is the SAME object the
    leaf defines (a re-export, not a copy) for every extracted name."""
    print("shim parity: common re-exports the SAME leaf objects (import surface intact):")
    pairs = [
        (errors, ["AuthError", "PreflightError", "SiteUnreachableError", "ReportUnavailableError",
                  "BrowserNotFoundError", "RunCancelled", "ReportError"]),
        (routes, ["ROUTES", "normalize_route", "parse_routes"]),
        (timeouts, ["REPORT_TIMEOUT_MS", "SKIP_PROMPT_AFTER_MS", "COUNTY_ENABLE_TIMEOUT_MS",
                    "DOWNLOAD_START_TIMEOUT_MS", "FAST_REPORT_TIMEOUT_MS", "RETRY_REPORT_TIMEOUT_MS",
                    "RETRY_COUNT", "report_timeout_ms", "fast_report_timeout_ms",
                    "retry_report_timeout_ms", "county_enable_timeout_ms", "download_start_timeout_ms"]),
        (site_target, ["TSMIS_HOST", "TSMIS_DEV_HOST", "DATA_SOURCES", "ENVIRONMENTS",
                       "DATA_SOURCE_LABELS", "ENVIRONMENT_LABELS", "set_site", "set_thread_site",
                       "get_site", "default_site_url", "dev_site_url", "get_url", "expected_host"]),
    ]
    for mod, names in pairs:
        for n in names:
            check(f"common.{n} is {mod.__name__}.{n}",
                  getattr(common, n) is getattr(mod, n))
    # common's own auth/page logger is the SAME instance the leaves log through,
    # so log output (logger name) is byte-identical after the split.
    check("site_target.log is common.log (logger name preserved)", site_target.log is common.log)
    check("timeouts.log is common.log (logger name preserved)", timeouts.log is common.log)


def main():
    test_routes()
    test_timeouts()
    test_site_target()
    test_errors()
    test_shim_parity()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL ENGINE-LEAF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
