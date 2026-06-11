"""Comprehensive runtime self-test for the bundled libraries.

Exercises EVERY real code path the app depends on -- Chromium launch + page.pdf()
+ download, pdfplumber text/word/table extraction (exactly what the Ramp Summary
consolidator uses), and an openpyxl write/read round-trip -- then reports which
*optional* libraries actually got imported. Used two ways:
  1. Against the build venv, to prove PIL/pypdfium2 are never loaded (so they can
     be excluded from the bundle).
  2. Frozen (built by build.ps1 -SelfTest style), as the gate that proves a
     pruned bundle still runs everything.

Exit 0 = all good. Nonzero/raise = something the app needs is broken.
"""
import sys
import tempfile
import threading
import time
from pathlib import Path

# Make the app modules importable before importing `common` (frozen builds bundle
# them; dev/venv runs need the repo on sys.path).
if not getattr(sys, "frozen", False):
    _repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_repo / "scripts"))      # common, gui_app, ...
    sys.path.insert(0, str(_repo))                  # version.py at repo root

import openpyxl                                   # noqa: E402
import pdfplumber                                 # noqa: E402
from playwright.sync_api import sync_playwright   # noqa: E402

from common import launch_browser                 # noqa: E402  (drives system Edge/Chrome)

HTML = """
<h1>Route 005 Ramp Summary</h1>
<table border=1>
  <tr><th>Ramp</th><th>Count</th></tr>
  <tr><td>NB On</td><td>1234</td></tr>
  <tr><td>SB Off</td><td>5678</td></tr>
</table>
"""


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    print("=" * 60)
    print("TSMIS Exporter -- full bundle self-test")
    print("=" * 60)
    print(f"frozen={getattr(sys, 'frozen', False)}  "
          f"openpyxl={openpyxl.__version__}  pdfplumber={pdfplumber.__version__}")

    # 1. Chromium: launch + render to PDF (Ramp Summary path) + a download.
    pdf_path = tmp / "page.pdf"
    with sync_playwright() as p:
        browser = launch_browser(p, headless=True)   # system Edge/Chrome
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        page.set_content(HTML)
        page.pdf(path=str(pdf_path), format="Letter", print_background=True)
        page.set_content('<a id="d" href="data:text/plain,hello" download="x.txt">d</a>')
        with page.expect_download() as dl:
            page.click("#d")
        dl.value.save_as(str(tmp / "x.txt"))
        browser.close()
    assert pdf_path.stat().st_size > 0, "page.pdf produced nothing"
    print(f"chromium: PDF {pdf_path.stat().st_size} bytes, download ok")

    # 2. pdfplumber: exactly the calls consolidate_ramp_summary makes.
    with pdfplumber.open(str(pdf_path)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        words = pdf.pages[0].extract_words()
        tables = pdf.pages[0].extract_tables()
    assert "Route 005" in text, f"extract_text failed: {text!r}"
    assert any(w.get("text") == "1234" for w in words), "extract_words failed"
    print(f"pdfplumber: text={len(text)} chars, words={len(words)}, tables={len(tables)}")

    # 3. openpyxl: write + read round-trip (consolidator output path).
    xlsx = tmp / "wb.xlsx"
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Route", "Ramp", "Count"]); ws.append(["005", "NB On", 1234])
    wb.save(str(xlsx))
    wb2 = openpyxl.load_workbook(str(xlsx))
    assert wb2.active["C2"].value == 1234, "openpyxl round-trip failed"
    print("openpyxl: write/read round-trip ok")

    # 4. Report optional libraries that should NOT be needed.
    opt = {m: (m in sys.modules) for m in ("PIL", "pypdfium2", "pypdfium2_raw")}
    print(f"optional libs loaded: {opt}")
    print(f"cryptography loaded (required by pdfminer): {'cryptography' in sys.modules}")

    # 5. GUI: the WebView shell. The import + bridge api MUST work (these catch
    #    a prune/exclude that broke pywebview/pythonnet or lost the ui/ assets);
    #    actually opening a window is attempted too, but tolerated as a skip in
    #    environments that can't show one.
    import webview
    import gui_api

    class _NoCheck:                 # don't spawn the background browser probe here
        def __init__(self, q): pass
        def start(self): pass
    gui_api.CheckWorker = _NoCheck

    api = gui_api.GuiApi()
    state = api.get_initial_state()
    assert state["reports"] and state["routes"], "GUI initial state incomplete"
    ui_index = gui_api._ui_index_path()
    assert ui_index.exists(), f"UI assets missing: {ui_index}"
    print(f"gui: bridge api ok ({len(state['reports'])} reports, "
          f"{len(state['routes'])} routes, ui={ui_index})")

    res = {}

    def _drive(w):
        try:
            deadline = time.time() + 30
            while time.time() < deadline:                # wait for app.js to boot
                if w.evaluate_js("typeof window.__tsmis !== 'undefined'"):
                    break
                time.sleep(0.25)
            res["state"] = w.evaluate_js("window.__tsmis.test_state()")
        except Exception as e:
            res["err"] = f"{type(e).__name__}: {e}"
        finally:
            w.destroy()

    window = webview.create_window("smoke", str(ui_index), js_api=api, hidden=True)
    window.events.loaded += lambda: threading.Thread(
        target=_drive, args=(window,), daemon=True).start()
    watchdog = threading.Timer(60, lambda: (res.setdefault("err", "watchdog timeout"),
                                            window.destroy()))
    watchdog.daemon = True
    watchdog.start()
    try:
        webview.start(gui="edgechromium")
    except Exception as e:
        print(f"gui: window skipped, environment can't start WebView2 "
              f"({type(e).__name__}: {e})")
    else:
        watchdog.cancel()
        if not res.get("state"):
            raise AssertionError(f"gui window cycle failed: {res.get('err', 'no JS state')}")
        print(f"gui: WebView window + JS bridge ok ({res['state']})")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nSMOKE OK -- every app-required code path works.")
    # Signal to the caller (venv run) whether the excludable libs stayed out.
    if any(opt.values()):
        print(f"NOTE: optional libs were imported: "
              f"{[k for k, v in opt.items() if v]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
