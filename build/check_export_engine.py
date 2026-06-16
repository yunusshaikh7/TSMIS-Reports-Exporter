"""Standalone regression checks for the WS1/WS3 audit-fix hardening.

Pure Python, no login and no live browser -- run with the build venv:

    build\\.venv\\Scripts\\python.exe build\\check_export_engine.py

Covers the v0.11 audit fixes that don't need the live site:
  * saved-file integrity (_file_looks_complete / _verify_saved_file / _can_resume)
  * the general no-download fast-fail in save_via_export_button
    (download -> save+verify | no-download+no-error -> EmptyExport |
     no-download+error -> ReportError | truncated save -> failure + cleanup)
  * _attempt_route translating EmptyExport into the "empty" outcome
  * the per-report empty-marker predicates (Intersection Detail's td.hl-empty,
    Intersection Summary's "Total Intersections = 0", and the unchanged ramp/
    highway-log markers)
  * select_report raising ReportUnavailableError on a cs-disabled option
  * auth_state stripping the token fragment from logged URLs (WS3)
  * the custom site-URL override validation (https + *.ca.gov + matching
    ?env=/?src= params) (WS3)

The browser-coupled JS predicates (EXPORT_READY_JS, the wait_js arrow functions)
are exercised by the fake-site harness; this file covers everything provable in
pure Python.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import openpyxl  # noqa: E402

import common  # noqa: E402
import exporter  # noqa: E402
from common import ReportUnavailableError, select_report  # noqa: E402
from exporter import (  # noqa: E402
    EmptyExport,
    ReportSpec,
    _attempt_route,
    _can_resume,
    _file_looks_complete,
    _verify_saved_file,
    save_via_export_button,
)
from events import Events  # noqa: E402
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def expect_raises(name, exc, fn):
    try:
        fn()
    except exc:
        check(name, True)
    except Exception as e:  # noqa: BLE001
        check(f"{name} (got {type(e).__name__})", False)
    else:
        check(f"{name} (no exception)", False)


# --- integrity helpers -------------------------------------------------------

def _write_xlsx(path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "hi"
    wb.save(path)


def test_integrity(tmp):
    print("saved-file integrity:")
    good_xlsx = tmp / "good.xlsx"
    _write_xlsx(good_xlsx)
    good_pdf = tmp / "good.pdf"
    good_pdf.write_bytes(b"%PDF-1.4\nstuff\n%%EOF")
    check("valid xlsx looks complete", _file_looks_complete(good_xlsx))
    check("valid pdf looks complete", _file_looks_complete(good_pdf))

    zero = tmp / "zero.xlsx"
    zero.write_bytes(b"")
    html = tmp / "html.xlsx"
    html.write_bytes(b"<html>error page</html>")
    short_pdf = tmp / "short.pdf"
    short_pdf.write_bytes(b"%PD")
    check("0-byte xlsx rejected", not _file_looks_complete(zero))
    check("html-as-xlsx rejected", not _file_looks_complete(html))
    check("truncated pdf rejected", not _file_looks_complete(short_pdf))
    check("missing file rejected", not _file_looks_complete(tmp / "nope.xlsx"))

    # _verify_saved_file: passes silently on good, deletes+raises on bad.
    _verify_saved_file(good_xlsx)  # must not raise
    bad = tmp / "bad.xlsx"
    bad.write_bytes(b"not a zip")
    expect_raises("verify_saved_file raises on truncated", RuntimeError,
                  lambda: _verify_saved_file(bad))
    check("verify_saved_file deleted the bad file", not bad.exists())

    # _can_resume: True for complete, deletes+False for partial, False missing.
    check("can_resume trusts a complete file", _can_resume(good_xlsx))
    partial = tmp / "partial.xlsx"
    partial.write_bytes(b"")
    check("can_resume rejects a partial file", not _can_resume(partial))
    check("can_resume removed the partial", not partial.exists())
    check("can_resume False for missing", not _can_resume(tmp / "absent.xlsx"))

    # A complete file that can't be READ (e.g. open in Excel, sharing-deny) must
    # be TRUSTED and skipped -- never deleted + re-pulled (would spuriously fail).
    import builtins
    locked = tmp / "locked.xlsx"
    _write_xlsx(locked)
    real_open = builtins.open

    def _deny(path, *a, **k):
        if str(path) == str(locked):
            raise PermissionError("file is open in Excel")
        return real_open(path, *a, **k)

    builtins.open = _deny
    try:
        trusted = _can_resume(locked)
    finally:
        builtins.open = real_open
    check("can_resume trusts a locked (unreadable) existing file", trusted)
    check("can_resume did NOT delete the locked file", locked.exists())


# --- fake page for save_via_export_button ------------------------------------

class _Download:
    def __init__(self, saver):
        self._saver = saver

    def save_as(self, path):
        self._saver(Path(path))


class _ExpectDownloadCM:
    """Mimics Playwright's `with page.expect_download(timeout=...) as info:` --
    raises PlaywrightTimeoutError on exit when no download was produced."""

    def __init__(self, page):
        self.page = page

    def __enter__(self):
        return self

    @property
    def value(self):
        return self.page.download

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False
        if self.page.download is None:
            raise PlaywrightTimeoutError("no download started")
        return False


class _ClickTarget:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    def click(self, *a, **k):
        self.page.clicked = True


class FakeExportPage:
    def __init__(self, download=None):
        self.download = download
        self.clicked = False

    def expect_download(self, timeout=None):
        self.last_timeout = timeout
        return _ExpectDownloadCM(self)

    def locator(self, *a, **k):
        return _ClickTarget(self)


def test_save_via_export_button(tmp, monkeypatch_error):
    print("save_via_export_button fast-fail:")

    # 1. Download arrives -> file saved + verified.
    out1 = tmp / "ok.xlsx"
    page1 = FakeExportPage(download=_Download(_write_xlsx))
    monkeypatch_error(None)
    save_via_export_button(page1, out1, timeout_ms=600_000)
    check("download success saves a valid file", _file_looks_complete(out1))
    check("export button was clicked", page1.clicked)
    check("download wait capped at the short window (<= 60s)",
          page1.last_timeout <= 60_000)

    # 2. No download, no site error -> EmptyExport (the no-op empty route).
    page2 = FakeExportPage(download=None)
    monkeypatch_error(None)
    expect_raises("no-download + no-error -> EmptyExport", EmptyExport,
                  lambda: save_via_export_button(page2, tmp / "e.xlsx"))

    # 3. No download, site error rendered -> ReportError with the site message.
    page3 = FakeExportPage(download=None)
    monkeypatch_error("Cannot read properties of undefined")
    expect_raises("no-download + site error -> ReportError",
                  common.ReportError,
                  lambda: save_via_export_button(page3, tmp / "x.xlsx"))

    # 4. Download arrives but the bytes are junk -> failure + the partial is gone.
    out4 = tmp / "trunc.xlsx"
    page4 = FakeExportPage(download=_Download(lambda p: p.write_bytes(b"<html>")))
    monkeypatch_error(None)
    expect_raises("truncated download -> RuntimeError", RuntimeError,
                  lambda: save_via_export_button(page4, out4))
    check("truncated download cleaned up", not out4.exists())


# --- _attempt_route translates EmptyExport -> "empty" ------------------------

class _NoopChain:
    def __getattr__(self, name):
        return lambda *a, **k: self


class FakeRoutePage:
    def get_by_label(self, *a, **k):
        return _NoopChain()

    def get_by_role(self, *a, **k):
        return _NoopChain()

    def wait_for_timeout(self, *a, **k):
        return None


def test_attempt_route_empty(monkeypatch):
    print("_attempt_route EmptyExport -> empty:")
    monkeypatch(exporter, "wait_with_skip_option", lambda *a, **k: True)
    monkeypatch(exporter, "report_error_text", lambda page: None)
    monkeypatch(exporter, "maybe_screenshot", lambda *a, **k: None)

    def _raise_empty(page, out_path, timeout_ms):
        raise EmptyExport()

    spec = ReportSpec(
        label="X", subdir="x",
        filename=lambda r: f"x_{r}.xlsx",
        wait_js=lambda r: "() => true",
        is_empty=lambda page: False,        # marker missed it...
        save=_raise_empty,                   # ...but the no-download guard caught it
    )
    outcome = _attempt_route(FakeRoutePage(), spec, "005", "[t]",
                             Path("x_005.xlsx"), Events(), 600_000)
    check("EmptyExport from save becomes the 'empty' outcome", outcome == "empty")


# --- empty-marker predicates -------------------------------------------------

class _CountLoc:
    def __init__(self, n):
        self._n = n

    def count(self):
        return self._n


class FakeMarkerPage:
    def __init__(self, body="", hl_empty=0):
        self._body = body
        self._hl = hl_empty

    def locator(self, sel):
        return _CountLoc(self._hl if sel == "td.hl-empty" else 0)

    def inner_text(self, sel):
        return self._body


def test_markers():
    print("empty-marker predicates:")
    import export_intersection_detail as intd
    import export_intersection_summary as ints
    import export_ramp_detail as rd
    import export_highway_log as hl

    # Intersection Detail: structural td.hl-empty OR the text.
    check("INTD empty via td.hl-empty",
          intd.SPEC.is_empty(FakeMarkerPage(body="anything", hl_empty=1)))
    check("INTD empty via text fallback",
          intd.SPEC.is_empty(FakeMarkerPage(body="No results found.", hl_empty=0)))
    check("INTD non-empty when data present",
          not intd.SPEC.is_empty(FakeMarkerPage(body="P Post Mile Location ...", hl_empty=0)))

    # Intersection Summary: zero total only.
    check("INTS empty at Total Intersections = 0",
          ints.SPEC.is_empty(FakeMarkerPage(body="Total Intersections = 0")))
    check("INTS non-empty at Total Intersections = 12",
          not ints.SPEC.is_empty(FakeMarkerPage(body="Total Intersections = 12")))

    # Unchanged ramp / highway-log markers still hold.
    check("Ramp Detail empty marker",
          rd.SPEC.is_empty(FakeMarkerPage(body="No ramps found in this segment.")))
    check("Highway Log empty marker",
          hl.SPEC.is_empty(FakeMarkerPage(body="No results found in this segment.")))


# --- cs-disabled detection in select_report ----------------------------------

class _OptionLoc:
    def __init__(self, cls):
        self._cls = cls

    @property
    def first(self):
        return self

    def get_attribute(self, name):
        return self._cls if name == "class" else None

    def __getattr__(self, name):
        return lambda *a, **k: self


class FakeDropdownPage:
    def __init__(self, option_cls):
        self.option_cls = option_cls

    def locator(self, sel, **k):
        if "li.cs-option" in sel:
            return _OptionLoc(self.option_cls)
        return _NoopChain()

    def get_by_role(self, *a, **k):
        return _NoopChain()

    def get_by_label(self, *a, **k):
        return _NoopChain()

    def wait_for_function(self, *a, **k):
        return None


def test_cs_disabled():
    print("select_report cs-disabled handling:")
    expect_raises("cs-disabled report -> ReportUnavailableError",
                  ReportUnavailableError,
                  lambda: select_report(FakeDropdownPage("cs-option cs-disabled"),
                                        "TSAR: Ramp Detail"))
    # An enabled report must NOT raise (it runs through the rest of the no-op fakes).
    try:
        select_report(FakeDropdownPage("cs-option"), "Highway Log")
        check("enabled report proceeds without error", True)
    except Exception as e:  # noqa: BLE001
        check(f"enabled report proceeds (raised {type(e).__name__})", False)


def test_auth_url_redaction():
    print("auth_state URL token redaction:")

    class FakeAuthPage:
        url = ("https://tsmis.dot.ca.gov/index.html?env=prod&src=ssor"
               "#access_token=SECRET_TOKEN_VALUE&expires_in=7200")

        def evaluate(self, js):
            raise RuntimeError("signals unavailable")

    st = common.auth_state(FakeAuthPage())
    check("token fragment stripped from logged URL", "SECRET_TOKEN" not in st["url"])
    check("clean URL preserved (query kept)",
          st["url"] == "https://tsmis.dot.ca.gov/index.html?env=prod&src=ssor")


def test_site_url_override():
    print("custom site-URL override validation:")
    import settings
    ok = "https://tsmis.dot.ca.gov/index.html?env=dev&src=ssor"
    check("valid override accepted", settings._override_problem(ok, "ssor", "dev") is None)
    check("any *.ca.gov host accepted",
          settings._override_problem("https://new.ca.gov/?env=dev&src=ssor", "ssor", "dev") is None)
    check("http rejected",
          settings._override_problem("http://tsmis.dot.ca.gov/?env=dev&src=ssor", "ssor", "dev") is not None)
    check("non-ca.gov host rejected",
          settings._override_problem("https://evil.com/?env=dev&src=ssor", "ssor", "dev") is not None)
    check("suffix-spoof host rejected",
          settings._override_problem("https://fake-ca.gov.evil.com/?env=dev&src=ssor", "ssor", "dev") is not None)
    check("missing env/src params rejected",
          settings._override_problem("https://tsmis.dot.ca.gov/index.html", "ssor", "dev") is not None)
    check("mismatched env rejected",
          settings._override_problem("https://tsmis.dot.ca.gov/?env=prod&src=ssor", "ssor", "dev") is not None)
    check("mismatched src rejected",
          settings._override_problem("https://tsmis.dot.ca.gov/?env=dev&src=ars", "ssor", "dev") is not None)


def test_corrupt_config_backup():
    print("corrupt config.json backup (WS3):")
    import settings
    cfgdir = Path(tempfile.mkdtemp(prefix="tsmis_cfg_"))
    orig_file = settings.CONFIG_FILE
    settings.CONFIG_FILE = cfgdir / "config.json"
    settings._cache = settings._cache_mtime = None
    try:
        settings.CONFIG_FILE.write_text("{ not valid json", encoding="utf-8")
        data = settings._read_file()
        check("corrupt read falls back to defaults ({})", data == {})
        check("corrupt file moved aside to config.json.corrupt",
              (cfgdir / "config.json.corrupt").exists())
        check("original config.json removed", not settings.CONFIG_FILE.exists())
        # get() of any key still returns its default (no crash, no silent loss path)
        settings._cache = settings._cache_mtime = None
        check("get() returns the default after corruption",
              settings.get("report_timeout_min") == settings.DEFAULTS["report_timeout_min"])
        # A transient OSError (not JSONDecodeError) must NOT move the file aside.
        settings.CONFIG_FILE.write_text('{"report_timeout_min": 9}', encoding="utf-8")
        settings._cache = settings._cache_mtime = None
        check("valid config reads back", settings.get("report_timeout_min") == 9)
    finally:
        settings.CONFIG_FILE = orig_file
        settings._cache = settings._cache_mtime = None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_ws1_"))

    error_text = {"value": None}

    def monkeypatch_error(value):
        error_text["value"] = value
        exporter.report_error_text = lambda page: error_text["value"]

    _orig_error = exporter.report_error_text
    _patched = []

    def monkeypatch(obj, name, value):
        _patched.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    try:
        test_integrity(tmp)
        test_save_via_export_button(tmp, monkeypatch_error)
        exporter.report_error_text = _orig_error
        test_attempt_route_empty(monkeypatch)
        test_markers()
        test_cs_disabled()
        test_auth_url_redaction()
        test_site_url_override()
        test_corrupt_config_backup()
    finally:
        exporter.report_error_text = _orig_error
        for obj, name, old in reversed(_patched):
            setattr(obj, name, old)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL EXPORT-ENGINE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
