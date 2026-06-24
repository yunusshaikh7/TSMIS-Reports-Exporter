"""Fake-site selector-contract checks for the TSMIS export engine.

Pairs the pure-Python WS1 checks (build/check_export_engine.py) with a REAL
headless browser: it loads minimal synthetic HTML fixtures (build/fake_site/*)
that reconstruct only the contract-bearing structure of the live TSMIS report
page -- the shared action bar (renderActionBar), the per-report empty states,
the #rampResults error box, and the #customReport dropdown -- and evaluates the
engine's actual JS/selector predicates against them. This catches selector
drift that pure Python can't (e.g. EXPORT_READY_JS keying on a button's text,
not the bare .export-btn class shared by Print).

Run with the build venv:

    build\\.venv\\Scripts\\python.exe build\\check_fake_site.py

The fixtures are AUTHORED synthetic reconstructions, not copies of the
Caltrans-internal source; they carry only the class names / element types /
marker text the predicates depend on.

CI-safe: if no Chromium-based browser is drivable, it prints a clear SKIPPED
line and exits 0 (the predicates are still partly covered by
check_export_engine.py, which needs no browser).
"""
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

import common  # noqa: E402
import exporter  # noqa: E402  (imported for parity with the engine; documents the dep)
from common import select_report, ReportUnavailableError  # noqa: E402
import export_ramp_summary as ramp_summary  # noqa: E402
import export_ramp_detail as ramp_detail  # noqa: E402
import export_highway_sequence as highway_sequence  # noqa: E402
import export_highway_log as highway_log  # noqa: E402
import export_highway_log_pdf as highway_log_pdf  # noqa: E402
import export_intersection_detail as intersection_detail  # noqa: E402
import export_intersection_summary as intersection_summary  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

assert exporter is not None  # keep the import (engine-parity); see module docstring

FIXTURES = Path(__file__).resolve().parent / "fake_site"

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _fixture_url(name):
    p = FIXTURES / name
    if not p.exists():
        raise FileNotFoundError(f"fixture missing: {p}")
    return p.as_uri()


def _launch(p):
    """Launch the first drivable Chromium-based browser, or None if none work.

    Tries the same channel order the app would: Built-in Chromium, then the
    system Edge, then Chrome. A headless launch + a trivial page drive proves
    the channel is actually controllable (mirrors common._probe_channel)."""
    for channel in ("chromium", "msedge", "chrome"):
        try:
            browser = p.chromium.launch(headless=True, channel=channel)
        except Exception as e:  # noqa: BLE001
            print(f"  (channel {channel} unavailable: {type(e).__name__})")
            continue
        try:
            page = browser.new_context().new_page()
            page.goto("about:blank", timeout=15_000)
            if page.evaluate("1 + 1") != 2:
                raise RuntimeError("page not drivable")
            print(f"  using browser channel: {channel}")
            return browser
        except Exception as e:  # noqa: BLE001
            print(f"  (channel {channel} not drivable: {type(e).__name__})")
            try:
                browser.close()
            except Exception:
                pass
    return None


def _eval_export_ready(page):
    """EXPORT_READY_JS is a JS *expression*; wrap it in an arrow and evaluate,
    exactly as it is embedded inside each report's wait_js arrow."""
    return bool(page.evaluate("() => (" + common.EXPORT_READY_JS + ")"))


def _eval_wait(page, spec, route):
    """Evaluate a report SPEC's wait condition the way exporter._attempt_route
    wraps it: `() => ((<wait_js>))() || (<ERROR_JS>)`. wait_js(route) is itself
    a full `() => {...}` arrow, so it is invoked, then OR'd with ERROR_JS."""
    ready_js = spec.wait_js(route)
    wrapped = f"() => (({ready_js}))() || ({common.ERROR_JS})"
    return bool(page.evaluate(wrapped))


def _eval_error(page):
    return bool(page.evaluate("() => (" + common.ERROR_JS + ")"))


# (spec, label, data fixture, empty fixture). route "005" drives wait_js.
_REPORTS = [
    (ramp_summary.SPEC, "Ramp Summary",
     "ramp_summary_data.html", "ramp_summary_empty.html"),
    (ramp_detail.SPEC, "Ramp Detail",
     "ramp_detail_data.html", "ramp_detail_empty.html"),
    (highway_sequence.SPEC, "Highway Sequence",
     "highway_sequence_data.html", "highway_sequence_empty.html"),
    (highway_log.SPEC, "Highway Log",
     "highway_log_data.html", "highway_log_empty.html"),
    # The PDF variant renders the SAME way (same dropdown option), so its
    # wait_js/is_empty must resolve on the very same fixtures as the Excel one.
    (highway_log_pdf.SPEC, "Highway Log (PDF)",
     "highway_log_data.html", "highway_log_empty.html"),
    (intersection_detail.SPEC, "Intersection Detail",
     "intersection_detail_data.html", "intersection_detail_empty.html"),
    (intersection_summary.SPEC, "Intersection Summary",
     "intersection_summary_data.html", "intersection_summary_empty.html"),
]


def test_export_ready(page):
    print("EXPORT_READY_JS (Export button, not the shared Print .export-btn):")
    page.goto(_fixture_url("actionbar_export_and_print.html"))
    check("Export+Print bar -> ready True", _eval_export_ready(page))
    page.goto(_fixture_url("actionbar_print_only.html"))
    check("Print-only bar -> ready False (text, not bare .export-btn)",
          not _eval_export_ready(page))
    page.goto(_fixture_url("blank.html"))
    check("no action bar -> ready False", not _eval_export_ready(page))


def test_wait_conditions(page):
    print("per-report wait_js resolves on data / empty / error, not on blank:")
    for spec, label, data_fx, empty_fx in _REPORTS:
        page.goto(_fixture_url(data_fx))
        check(f"{label}: wait resolves on DATA", _eval_wait(page, spec, "005"))
        page.goto(_fixture_url(empty_fx))
        check(f"{label}: wait resolves on EMPTY", _eval_wait(page, spec, "005"))
        page.goto(_fixture_url("error.html"))
        check(f"{label}: wait resolves on ERROR", _eval_wait(page, spec, "005"))
        page.goto(_fixture_url("blank.html"))
        check(f"{label}: wait stays False on BLANK",
              not _eval_wait(page, spec, "005"))


def test_is_empty(page):
    print("per-report is_empty: True on empty fixture, False on data fixture:")
    for spec, label, data_fx, empty_fx in _REPORTS:
        page.goto(_fixture_url(empty_fx))
        check(f"{label}: is_empty True on EMPTY", spec.is_empty(page))
        page.goto(_fixture_url(data_fx))
        check(f"{label}: is_empty False on DATA", not spec.is_empty(page))


def test_error_js(page):
    print("ERROR_JS keys on #rampResults.error:")
    page.goto(_fixture_url("error.html"))
    check("ERROR_JS True on the error box", _eval_error(page))
    page.goto(_fixture_url("ramp_detail_data.html"))
    check("ERROR_JS False on a normal data page", not _eval_error(page))
    page.goto(_fixture_url("blank.html"))
    check("ERROR_JS False on a blank page", not _eval_error(page))


def _option_class(page, label):
    """Mirror select_report's read: the matching #customReport li.cs-option's
    class attribute."""
    loc = page.locator("#customReport li.cs-option", has_text=label).first
    return loc.get_attribute("class") or ""


def test_cs_disabled(page):
    print("cs-disabled detection on the #customReport dropdown:")
    page.goto(_fixture_url("dropdown.html"))
    disabled_cls = _option_class(page, "TSAR: Ramp Detail")
    enabled_cls = _option_class(page, "Highway Log")
    check("disabled report option carries cs-disabled",
          "cs-disabled" in disabled_cls.split())
    check("enabled report option lacks cs-disabled",
          "cs-disabled" not in enabled_cls.split())

    # End-to-end: select_report on the loaded fixture must raise for the
    # greyed report and proceed past the class check for the enabled one. The
    # fixture has no District/County/Route controls, so an enabled selection
    # fails LATER (timeout) -- the contract under test is only that it does NOT
    # raise ReportUnavailableError, so we treat any other exception as "passed
    # the cs-disabled gate".
    raised = None
    try:
        select_report(page, "TSAR: Ramp Detail")
    except ReportUnavailableError as e:
        raised = e
    except Exception as e:  # noqa: BLE001
        raised = e
    check("select_report raises ReportUnavailableError on a cs-disabled report",
          isinstance(raised, ReportUnavailableError))

    page.goto(_fixture_url("dropdown.html"))
    # The enabled selection clears the cs-disabled gate, then fails fast on the
    # missing District/County/Route control. Cap the action timeout so that
    # failure is ~2s, not Playwright's default 30s (the assertion only cares
    # that ReportUnavailableError did NOT fire).
    page.set_default_timeout(2000)
    gate = "passed"
    try:
        select_report(page, "Highway Log")
    except ReportUnavailableError:
        gate = "blocked"
    except Exception:  # noqa: BLE001
        gate = "passed"   # failed later (no Route control) -- gate was cleared
    finally:
        page.set_default_timeout(30000)
    check("select_report does NOT block an enabled report", gate == "passed")


def test_exact_match(page):
    print("select_report EXACT-match guard (substring / duplicate / 0-match):")
    # "Highway Log" is a substring of "Highway Log (PDF)" and "Detailed Highway
    # Log", which appear FIRST in the list -- the old has_text + .first read
    # would click the wrong one. The fixture records the clicked option text in
    # window.__picked.
    page.goto(_fixture_url("dropdown_ambiguous.html"))
    page.set_default_timeout(2000)
    try:
        select_report(page, "Highway Log")
    except Exception:  # noqa: BLE001  -- fails later at the missing District control
        pass
    finally:
        picked = page.evaluate("() => window.__picked")
        page.set_default_timeout(30000)
    check("exact 'Highway Log' clicked the exact option, not a substring near-miss",
          picked == "Highway Log")

    # A cs-disabled option, matched EXACTLY, still raises ReportUnavailableError.
    page.goto(_fixture_url("dropdown_ambiguous.html"))
    raised = None
    try:
        select_report(page, "TSAR: Ramp Detail")
    except Exception as e:  # noqa: BLE001
        raised = e
    check("exact match of a cs-disabled report -> ReportUnavailableError",
          isinstance(raised, ReportUnavailableError))

    # Zero matches (report not offered / page changed) -> PreflightError.
    page.goto(_fixture_url("dropdown_ambiguous.html"))
    raised = None
    try:
        select_report(page, "No Such Report")
    except Exception as e:  # noqa: BLE001
        raised = e
    check("unknown report -> PreflightError",
          isinstance(raised, common.PreflightError))

    # Multiple exact matches (ambiguous list) -> PreflightError.
    page.goto(_fixture_url("dropdown_ambiguous.html"))
    raised = None
    try:
        select_report(page, "Duplicated Report")
    except Exception as e:  # noqa: BLE001
        raised = e
    check("duplicate report entries -> PreflightError",
          isinstance(raised, common.PreflightError))


def test_current_report_label(page):
    print("current_report_label reads the armed #customReport .cs-value:")
    page.goto(_fixture_url("dropdown_selected.html"))
    check("reads the selected report label",
          common.current_report_label(page) == "Highway Log")
    page.goto(_fixture_url("dropdown.html"))
    check("reads the unselected placeholder",
          common.current_report_label(page) == "-- Select report --")
    page.goto(_fixture_url("blank.html"))
    check("returns '' when there's no dropdown",
          common.current_report_label(page) == "")


def test_highway_log_pdf_save(page):
    print("Highway Log PDF save: invokes the Print layout and writes a real PDF:")
    from exporter import save_highway_log_pdf
    from common import ReportError
    page.goto(_fixture_url("highway_log_print.html"))
    out = Path(tempfile.gettempdir()) / "_hl_pdf_check.pdf"
    if out.exists():
        out.unlink()
    save_highway_log_pdf(page, out)
    data = out.read_bytes() if out.exists() else b""
    check("a non-empty PDF was written", data[:4] == b"%PDF" and len(data) > 800)
    # The FULL multi-page print layout (not the single paginated page) is in the
    # DOM after save -- proof window.print() was neutralized so hl_printAll's
    # synchronous restore didn't run.
    n = page.evaluate("() => document.querySelectorAll('#rampResults .hl-print-section').length")
    check("the full multi-page print layout was built (restore skipped)", n >= 2)
    if out.exists():
        out.unlink()

    # Fails LOUDLY (ReportError) when the site's Print function is gone, rather
    # than silently saving the one paginated on-screen page.
    page.goto(_fixture_url("blank.html"))      # no hl_printAll
    raised = None
    try:
        save_highway_log_pdf(page, Path(tempfile.gettempdir()) / "_hl_pdf_none.pdf")
    except Exception as e:  # noqa: BLE001
        raised = e
    check("missing hl_printAll -> ReportError (no silent truncated PDF)",
          isinstance(raised, ReportError))

    # A built layout with ZERO data rows (only the spanning empty notice) is the
    # marker-independent empty case: EmptyExport, never a contentless PDF.
    from exporter import EmptyExport
    page.goto(_fixture_url("highway_log_print_empty.html"))
    out_e = Path(tempfile.gettempdir()) / "_hl_pdf_empty.pdf"
    if out_e.exists():
        out_e.unlink()
    raised = None
    try:
        save_highway_log_pdf(page, out_e)
    except Exception as e:  # noqa: BLE001
        raised = e
    check("empty HL print layout -> EmptyExport (no blank PDF)",
          isinstance(raised, EmptyExport))
    check("no PDF written for the empty HL layout", not out_e.exists())


def test_ramp_summary_pdf_empty(page):
    print("Ramp Summary PDF empty backstop (action bar present == has data):")
    from exporter import save_pdf_letter, EmptyExport
    # Data: the action bar is present -> a real PDF is written.
    page.goto(_fixture_url("ramp_summary_data.html"))
    out = Path(tempfile.gettempdir()) / "_rs_pdf_data.pdf"
    if out.exists():
        out.unlink()
    save_pdf_letter(page, out)
    check("data ramp summary writes a non-empty PDF",
          out.exists() and out.read_bytes()[:4] == b"%PDF")
    if out.exists():
        out.unlink()
    # Empty: no action bar -> EmptyExport, never a contentless PDF.
    page.goto(_fixture_url("ramp_summary_empty.html"))
    out_e = Path(tempfile.gettempdir()) / "_rs_pdf_empty.pdf"
    if out_e.exists():
        out_e.unlink()
    raised = None
    try:
        save_pdf_letter(page, out_e)
    except Exception as e:  # noqa: BLE001
        raised = e
    check("empty ramp summary -> EmptyExport (no blank PDF)",
          isinstance(raised, EmptyExport))
    check("no PDF written for the empty ramp summary", not out_e.exists())


def main():
    print("Fake-site selector-contract checks")
    print(f"fixtures: {FIXTURES}")
    with sync_playwright() as p:
        browser = _launch(p)
        if browser is None:
            print("\nSKIPPED: no browser available (no drivable Chromium / "
                  "Edge / Chrome). The pure-Python predicates are covered by "
                  "build/check_export_engine.py.")
            return 0
        try:
            page = browser.new_context().new_page()
            test_export_ready(page)
            test_wait_conditions(page)
            test_is_empty(page)
            test_error_js(page)
            test_cs_disabled(page)
            test_exact_match(page)
            test_current_report_label(page)
            test_highway_log_pdf_save(page)
            test_ramp_summary_pdf_empty(page)
        finally:
            try:
                browser.close()
            except Exception:
                pass

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL FAKE-SITE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
