"""Standalone regression checks for the WS1 export-engine hardening.

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
