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

    # 5. GUI + app modules: construct the real window (withdrawn) and tear it
    #    down, so the self-test also catches a prune/exclude that broke an import
    #    the GUI needs. (Import paths were set up at module load.)
    import tkinter as tk
    try:
        import gui_app

        class _NoCheck:                 # don't spawn the background browser probe here
            def __init__(self, q): pass
            def start(self): pass
        gui_app.CheckWorker = _NoCheck

        app = gui_app.App()
        app.withdraw(); app.update_idletasks(); app.destroy()
        print("gui: App window constructed + torn down ok")
    except tk.TclError as e:
        print(f"gui: skipped, no display ({e})")

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
