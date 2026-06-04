"""Build-pipeline self-test, packaged by build\\build.ps1 until the real GUI
entry point exists (Phase 4).

When frozen and run it proves the whole bundle is healthy:
  * Playwright launches the bundled Chromium -- headless via channel="chromium"
    so no separate chrome-headless-shell needs bundling, and
  * pdfplumber + openpyxl import correctly from the frozen build.
"""
import os
import sys
from pathlib import Path


def bundle_base() -> Path:
    """Folder containing the bundled 'ms-playwright' directory."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)          # onefolder: the _internal dir
    return Path(__file__).resolve().parent


# Point Playwright at the bundled browsers BEFORE importing it.
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundle_base() / "ms-playwright")

import openpyxl                                   # noqa: E402  (after env var)
import pdfplumber                                 # noqa: E402
from playwright.sync_api import sync_playwright   # noqa: E402


def main() -> int:
    print("=" * 56)
    print("TSMIS Exporter -- build self-test")
    print("=" * 56)
    print(f"frozen:     {getattr(sys, 'frozen', False)}")
    print(f"openpyxl:   {getattr(openpyxl, '__version__', '?')}")
    print(f"pdfplumber: {getattr(pdfplumber, '__version__', '?')}")

    with sync_playwright() as p:
        print(f"chromium:   {p.chromium.executable_path}")
        browser = p.chromium.launch(headless=True, channel="chromium")
        page = browser.new_context().new_page()
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        print(f"render:     {page.title()!r}")
        browser.close()

    print("\nSMOKE OK -- bundled Chromium + pdf/excel libs all working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
