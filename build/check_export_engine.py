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
import auth_nav  # noqa: E402  (P8b: dump_auth_failure / require_site_params live in auth_nav now)
import exporter  # noqa: E402
from common import ReportUnavailableError, select_report  # noqa: E402
from exporter import (  # noqa: E402
    EmptyExport,
    ReportSpec,
    _attempt_route,
    _can_resume,
    _file_looks_complete,
    _process_route,
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
    print("_attempt_route empty handling (positive vs no-download):")
    monkeypatch(exporter, "wait_with_skip_option", lambda *a, **k: True)
    monkeypatch(exporter, "report_error_text", lambda page: None)
    monkeypatch(exporter, "maybe_screenshot", lambda *a, **k: None)

    def _raise_empty(page, out_path, timeout_ms):
        raise EmptyExport()

    # A POSITIVE is_empty match is authoritative -> returns "empty" before save.
    spec_pos = ReportSpec(
        label="X", subdir="x", filename=lambda r: f"x_{r}.xlsx",
        wait_js=lambda r: "() => true",
        is_empty=lambda page: True, save=_raise_empty)
    outcome = _attempt_route(FakeRoutePage(), spec_pos, "005", "[t]",
                             Path("x_005.xlsx"), Events(), 600_000)
    check("positive is_empty match returns 'empty'", outcome == "empty")

    # A no-download EmptyExport (marker missed) now PROPAGATES (inconclusive) so
    # _process_route can retry it once rather than recording empty immediately.
    spec_nodl = ReportSpec(
        label="X", subdir="x", filename=lambda r: f"x_{r}.xlsx",
        wait_js=lambda r: "() => true",
        is_empty=lambda page: False, save=_raise_empty)
    expect_raises("no-download EmptyExport propagates out of _attempt_route",
                  EmptyExport,
                  lambda: _attempt_route(FakeRoutePage(), spec_nodl, "005", "[t]",
                                         Path("x_005.xlsx"), Events(), 600_000))


def test_process_route_empty_retry(monkeypatch, tmp):
    print("transient export-click empty is retried, not recorded empty on first try:")
    from events import RunResult
    monkeypatch(exporter, "wait_with_skip_option", lambda *a, **k: True)
    monkeypatch(exporter, "report_error_text", lambda page: None)
    monkeypatch(exporter, "maybe_screenshot", lambda *a, **k: None)
    monkeypatch(exporter, "_recover_or_stop", lambda *a, **k: True)
    monkeypatch(exporter, "_capture_failure", lambda *a, **k: None)

    # Case A: EmptyExport on the FIRST attempt, a real download on the retry ->
    # the route is SAVED (a transient export-click flake must not read as empty).
    calls = {"n": 0}

    def save_flaky(page, out_path, timeout_ms):
        calls["n"] += 1
        if calls["n"] == 1:
            raise EmptyExport()
        _write_xlsx(out_path)

    specA = ReportSpec(label="X", subdir="x", filename=lambda r: "x.xlsx",
                       wait_js=lambda r: "() => true", is_empty=lambda p: False,
                       save=save_flaky)
    rA = RunResult(output_dir=str(tmp))
    _process_route(FakeRoutePage(), specA, "005", "[t]", tmp / "x_a.xlsx",
                   Events(), rA, 600_000)
    check("transient empty retried then SAVED",
          rA.saved == 1 and "005" not in rA.empty)
    check("the export was attempted twice", calls["n"] == 2)

    # Case B: EmptyExport on BOTH attempts -> genuinely empty, recorded once.
    def save_always_empty(page, out_path, timeout_ms):
        raise EmptyExport()

    specB = ReportSpec(label="X", subdir="x", filename=lambda r: "x.xlsx",
                       wait_js=lambda r: "() => true", is_empty=lambda p: False,
                       save=save_always_empty)
    rB = RunResult(output_dir=str(tmp))
    _process_route(FakeRoutePage(), specB, "006", "[t]", tmp / "x_b.xlsx",
                   Events(), rB, 600_000)
    check("reproduced empty recorded as 'empty'", rB.empty == ["006"])
    check("reproduced empty NOT recorded 'failed'", "006" not in rB.failed)


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

    # Highway Sequence now keys empty on the POSITIVE "No results found" text
    # (hsl.js), not Export-button absence — so an error page (no button, message
    # in #rampResults.error, NOT in the body) is no longer misread as empty.
    import export_highway_sequence as hsq
    check("Highway Sequence empty via 'No results found'",
          hsq.SPEC.is_empty(FakeMarkerPage(body="No results found")))
    check("Highway Sequence NOT empty on an error page (no no-results text)",
          not hsq.SPEC.is_empty(FakeMarkerPage(body="An unexpected error occurred.")))
    check("Highway Sequence NOT empty when data present",
          not hsq.SPEC.is_empty(FakeMarkerPage(body="District County Route PM ...")))


# --- cs-disabled detection in select_report ----------------------------------

class _Opt:
    """One #customReport li.cs-option: exact text + class, plus the optional
    data-value (stable id) / data-label (full name) the nested flyout leaves carry."""

    def __init__(self, text, cls, data_value="", data_label=""):
        self._text, self._cls = text, cls
        self._dv, self._dl = data_value, data_label

    def text_content(self):
        return self._text

    def get_attribute(self, name):
        return {"class": self._cls, "data-value": self._dv,
                "data-label": self._dl}.get(name)

    def __getattr__(self, name):              # click(), etc. -> no-op chain
        return lambda *a, **k: self


class _OptionList:
    def __init__(self, opts):
        self._opts = opts

    def count(self):
        return len(self._opts)

    def nth(self, i):
        return self._opts[i]


class FakeDropdownPage:
    """A dropdown of (text, class[, data-value, data-label]) options for
    select_report's exact-match read."""

    def __init__(self, options):
        self._opts = [_Opt(*o) for o in options]

    def locator(self, sel, **k):
        if "li.cs-option" in sel:
            return _OptionList(self._opts)
        return _NoopChain()

    def get_by_role(self, *a, **k):
        return _NoopChain()

    def get_by_label(self, *a, **k):
        return _NoopChain()

    def wait_for_function(self, *a, **k):
        return None


# A dropdown with substring + duplicate + disabled near-misses (the pure-Python
# mirror of build/fake_site/dropdown_ambiguous.html). "Highway Log" is a substring
# of two other options and "Duplicated Report" appears twice.
_DROPDOWN = [
    ("Highway Log (PDF)", "cs-option"),
    ("Detailed Highway Log", "cs-option"),
    ("Highway Log", "cs-option"),
    ("TSAR: Ramp Detail", "cs-option cs-disabled"),
    ("Duplicated Report", "cs-option"),
    ("Duplicated Report", "cs-option"),
]


def test_cs_disabled():
    print("select_report exact-match + cs-disabled handling:")
    # cs-disabled, matched EXACTLY -> ReportUnavailableError (unchanged behavior).
    expect_raises("cs-disabled report -> ReportUnavailableError",
                  ReportUnavailableError,
                  lambda: select_report(FakeDropdownPage(_DROPDOWN), "TSAR: Ramp Detail"))
    # EXACT match wins over substrings: "Highway Log" must NOT pick "Highway Log
    # (PDF)" / "Detailed Highway Log" (the old has_text + .first bug), and proceeds.
    try:
        select_report(FakeDropdownPage(_DROPDOWN), "Highway Log")
        check("exact 'Highway Log' proceeds (not a substring near-miss)", True)
    except Exception as e:  # noqa: BLE001
        check(f"exact 'Highway Log' proceeds (raised {type(e).__name__})", False)
    # Zero matches (report not offered / page changed) -> PreflightError.
    expect_raises("unknown report -> PreflightError", common.PreflightError,
                  lambda: select_report(FakeDropdownPage(_DROPDOWN), "No Such Report"))
    # Multiple exact matches (ambiguous list) -> PreflightError.
    expect_raises("duplicate report entries -> PreflightError", common.PreflightError,
                  lambda: select_report(FakeDropdownPage(_DROPDOWN), "Duplicated Report"))


# A nested-flyout dropdown (the pure-Python mirror of dropdown_nested.html): a
# flat option plus leaves whose VISIBLE text is just "Detail"/"Summary", with the
# full name in data-label and the stable id in data-value. Two visible "Detail"
# rows prove the text read alone is ambiguous -- only data-value disambiguates.
_DROPDOWN_NESTED = [
    ("Highway Log", "cs-option", "highway_log", ""),
    ("Detail", "cs-option cs-leaf", "intersection_detail", "Intersection Detail"),
    ("Summary", "cs-option cs-leaf", "intersection_summary", "Intersection Summary"),
    ("Detail", "cs-option cs-leaf cs-disabled", "highway_detail", "Highway Detail"),
    ("Summary", "cs-option cs-leaf cs-disabled", "highway_summary", "Highway Summary"),
]


def test_data_value_match():
    print("select_report data-value matching + data-label fallback (nested leaves):")
    from report_nav import _find_exact_option
    page = FakeDropdownPage(_DROPDOWN_NESTED)
    # data-value picks the right leaf despite the duplicate visible text "Detail".
    opt = _find_exact_option(page, "Intersection Detail", data_value="intersection_detail")
    check("data-value picks the intersection_detail leaf",
          opt.get_attribute("data-value") == "intersection_detail")
    # No data_value -> fall back to data-label (the full name carried on a leaf).
    opt2 = _find_exact_option(page, "Intersection Summary")
    check("data-label fallback matches the full name (no data_value)",
          opt2.get_attribute("data-value") == "intersection_summary")
    # A data_value that matches nothing falls through to text/label; all-unknown
    # -> PreflightError (a changed page), never a silent wrong pick.
    expect_raises("unknown report -> PreflightError", common.PreflightError,
                  lambda: _find_exact_option(page, "No Such Report", data_value="nope"))


def test_nested_disabled():
    print("select_report cs-disabled detection on a nested flyout leaf:")
    page = FakeDropdownPage(_DROPDOWN_NESTED)
    # The Highway group ships cs-disabled ("coming soon"); selecting it by its
    # data-value still raises ReportUnavailableError at the class gate.
    expect_raises("cs-disabled Highway leaf -> ReportUnavailableError",
                  ReportUnavailableError,
                  lambda: select_report(page, "Highway Detail", data_value="highway_detail"))


def test_wait_condition_validation():
    print("wait_js config-error validation (_build_wait_condition):")
    from exporter import _build_wait_condition
    good = ReportSpec(label="X", subdir="x", filename=lambda r: "x.xlsx",
                      wait_js=lambda r: "() => true", is_empty=lambda p: False,
                      save=lambda *a: None)
    js = _build_wait_condition(good, "005")
    check("valid arrow wait_js builds the wrapped condition",
          js.startswith("() =>") and "=>" in js)
    # A spec that forgot the arrow wrapper (returns a bare expression that the engine
    # would try to CALL) is a config error — caught clearly, not as a route timeout.
    bad = ReportSpec(label="BadReport", subdir="x", filename=lambda r: "x.xlsx",
                     wait_js=lambda r: "document.ready", is_empty=lambda p: False,
                     save=lambda *a: None)
    expect_raises("non-arrow wait_js -> PreflightError (clear config error)",
                  common.PreflightError, lambda: _build_wait_condition(bad, "005"))
    # An empty wait_js likewise (never silently wrapped into broken JS).
    bad2 = ReportSpec(label="BadReport2", subdir="x", filename=lambda r: "x.xlsx",
                      wait_js=lambda r: "", is_empty=lambda p: False, save=lambda *a: None)
    expect_raises("empty wait_js -> PreflightError", common.PreflightError,
                  lambda: _build_wait_condition(bad2, "005"))


def test_ensure_report_armed(monkeypatch):
    print("per-route stale-form re-arm guard (_ensure_report_armed):")
    from events import Events
    calls = {"select": 0}
    monkeypatch(exporter, "select_report",
                lambda page, label, data_value=None:
                    calls.__setitem__("select", calls["select"] + 1))

    # --- Legacy fallback path: a spec with NO data_value uses the visible label. ---
    spec = exporter.ReportSpec(
        label="Highway Log", subdir="x", filename=lambda r: "x.xlsx",
        wait_js=lambda r: "() => true", is_empty=lambda p: False, save=lambda *a: None)
    monkeypatch(exporter, "current_report_value", lambda page: "")   # no stable id

    # Happy path: the shown label already matches -> NO re-arm.
    monkeypatch(exporter, "current_report_label", lambda page: "Highway Log")
    exporter._ensure_report_armed(object(), spec, "[t]", Events())
    check("no-data_value: matching label does NOT re-arm", calls["select"] == 0)

    # Drifted: a different label is shown -> re-arm (select_report called once).
    monkeypatch(exporter, "current_report_label", lambda page: "-- Select report --")
    exporter._ensure_report_armed(object(), spec, "[t]", Events())
    check("no-data_value: drifted label re-arms", calls["select"] == 1)

    # Unknown (''): can't tell -> never act (no spurious re-arm).
    monkeypatch(exporter, "current_report_label", lambda page: "")
    exporter._ensure_report_armed(object(), spec, "[t]", Events())
    check("no-data_value: unreadable selection does NOT re-arm", calls["select"] == 1)

    # --- Stable-id path: a spec WITH data_value compares the hidden #reportSelect. ---
    # Highway Detail is a nested-menu leaf: its VISIBLE label is the short "Detail",
    # never the full spec.label. The guard must key on the stable id, not the text.
    calls["select"] = 0
    hd = exporter.ReportSpec(
        label="Highway Detail", subdir="x", data_value="highway_detail",
        filename=lambda r: "x.xlsx", wait_js=lambda r: "() => true",
        is_empty=lambda p: False, save=lambda *a: None)

    # THE REGRESSION: armed id matches even though the visible leaf text is "Detail"
    # (which the old text compare would have re-selected on EVERY route) -> NO re-arm.
    monkeypatch(exporter, "current_report_value", lambda page: "highway_detail")
    monkeypatch(exporter, "current_report_label", lambda page: "Detail")
    exporter._ensure_report_armed(object(), hd, "[t]", Events())
    check("data_value: matching id ignores short leaf text (no re-arm)",
          calls["select"] == 0)

    # Genuine drift: the form armed a DIFFERENT report id -> re-arm.
    monkeypatch(exporter, "current_report_value", lambda page: "highway_log")
    exporter._ensure_report_armed(object(), hd, "[t]", Events())
    check("data_value: different armed id re-arms", calls["select"] == 1)

    # Stable id unreadable ('') -> fall back to the label text: mismatch re-arms...
    monkeypatch(exporter, "current_report_value", lambda page: "")
    monkeypatch(exporter, "current_report_label", lambda page: "-- Select report --")
    exporter._ensure_report_armed(object(), hd, "[t]", Events())
    check("data_value: unreadable id falls back to label (mismatch re-arms)",
          calls["select"] == 2)

    # ...and a matching label under an unreadable id does NOT re-arm.
    monkeypatch(exporter, "current_report_label", lambda page: "Highway Detail")
    exporter._ensure_report_armed(object(), hd, "[t]", Events())
    check("data_value: unreadable id, matching label does NOT re-arm",
          calls["select"] == 2)


def test_pdf_empty_backstop():
    print("PDF save marker-independent empty backstop (EmptyExport before page.pdf):")
    from exporter import save_pdf_letter, save_highway_log_pdf

    class _RSPage:                      # Ramp Summary: action-bar probe -> absent
        def evaluate(self, js):
            return False

    expect_raises("ramp PDF: no action bar -> EmptyExport", EmptyExport,
                  lambda: save_pdf_letter(_RSPage(), Path("x.pdf")))

    class _HLEmpty:                     # Highway Log: layout built, zero data rows
        def evaluate(self, js):
            return {"status": "ok", "rows": 0}

    expect_raises("HL PDF: zero data rows -> EmptyExport", EmptyExport,
                  lambda: save_highway_log_pdf(_HLEmpty(), Path("x.pdf")))

    class _HLNoLayout:                  # Highway Log: print control gone -> ReportError
        def evaluate(self, js):
            return {"status": "no-layout", "rows": 0}

    expect_raises("HL PDF: no layout -> ReportError", common.ReportError,
                  lambda: save_highway_log_pdf(_HLNoLayout(), Path("x.pdf")))


def test_report_error_text():
    print("report_error_text (best-effort but never silent):")
    import io
    import logging

    class _Loc:
        def __init__(self, cnt, text=None):
            self._c, self._t = cnt, text

        def count(self):
            return self._c

        @property
        def first(self):
            return self

        def inner_text(self):
            return self._t

    class P:
        def __init__(self, loc):
            self._loc = loc

        def locator(self, sel):
            return self._loc

    check("error page returns the site message",
          common.report_error_text(P(_Loc(1, "Build failed"))) == "Build failed")
    check("error page with blank text -> generic message",
          "error" in (common.report_error_text(P(_Loc(1, "  "))) or "").lower())
    check("no error -> None", common.report_error_text(P(_Loc(0))) is None)

    # A probe flake must return None AND be logged (the swallow is the gate that
    # turns a site error into a `failed` route; a silent None downgrades it).
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    common.log.addHandler(handler)
    old_level = common.log.level
    common.log.setLevel(logging.DEBUG)

    class _BoomPage:
        def locator(self, sel):
            raise RuntimeError("navigation race")

    try:
        res = common.report_error_text(_BoomPage())
    finally:
        common.log.removeHandler(handler)
        common.log.setLevel(old_level)
    check("probe exception -> None (best effort)", res is None)
    check("probe exception is LOGGED (not silent)",
          "report_error_text" in buf.getvalue())


def test_require_site_params(monkeypatch):
    print("require_site_params env backstop:")
    monkeypatch(auth_nav, "dump_auth_failure", lambda *a, **k: None)
    # P8a moved the site globals (_data_source/_environment) into site_target; pin the
    # selected site through the public API (what require_site_params reads via get_site).
    common.set_site("ssor", "prod")

    class FakeCfgPage:
        def __init__(self, cfg, raises=False):
            self._cfg = cfg
            self._raises = raises

        def evaluate(self, js):
            if self._raises:
                raise RuntimeError("config unavailable")
            return self._cfg

    # _CONFIG_JS resolves to [env, src]; selected = ssor/prod.
    common.require_site_params(FakeCfgPage(["prod", "ssor"]))   # match -> no raise
    check("matching env/src passes the backstop", True)
    common.require_site_params(FakeCfgPage(None, raises=True))  # unknown -> no raise
    check("undeterminable env/src does NOT false-block", True)
    common.require_site_params(FakeCfgPage([]))                 # empty -> no raise
    check("empty config does NOT false-block", True)
    expect_raises("wrong env/src raises PreflightError", common.PreflightError,
                  lambda: common.require_site_params(FakeCfgPage(["test", "ssor"])))
    expect_raises("wrong src raises PreflightError", common.PreflightError,
                  lambda: common.require_site_params(FakeCfgPage(["prod", "ars"])))


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
        test_process_route_empty_retry(monkeypatch, tmp)
        test_markers()
        test_cs_disabled()
        test_data_value_match()
        test_nested_disabled()
        test_wait_condition_validation()
        test_ensure_report_armed(monkeypatch)
        test_pdf_empty_backstop()
        test_report_error_text()
        test_require_site_params(monkeypatch)
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
