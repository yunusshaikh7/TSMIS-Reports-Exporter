# PyInstaller spec for TSMIS Reports Exporter (portable onefolder).
#
# Driven by build\build.ps1, which sets these environment variables:
#   TSMIS_ENTRY     path to the entry-point .py to package
#   TSMIS_APP_NAME  output folder / exe name (e.g. "TSMIS Exporter")
#   TSMIS_BROWSERS  path to the ms-playwright folder to bundle
#   TSMIS_CONSOLE   "1" to show a console window, "0" for a windowed GUI app
#
# Proven recipe (Phase 1 spike):
#   * collect_all('playwright') + Playwright's own bundled PyInstaller hooks
#     make the Node driver importable when frozen.
#   * The ms-playwright browser folder is bundled as data -> _internal/ms-playwright.
#   * At runtime the app sets PLAYWRIGHT_BROWSERS_PATH to that folder BEFORE
#     importing Playwright and launches headless via channel="chromium", so the
#     full Chromium is used and chrome-headless-shell need not be bundled.
#   * pdfminer ships CMap data files that must be collected or pdfplumber text
#     extraction breaks when frozen -> collect_data_files('pdfminer').
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

ENTRY    = os.environ.get("TSMIS_ENTRY", os.path.join(SPECPATH, "smoke_entry.py"))
APP_NAME = os.environ.get("TSMIS_APP_NAME", "TSMIS Exporter")
BROWSERS = os.environ.get("TSMIS_BROWSERS", os.path.join(SPECPATH, "ms-playwright"))
CONSOLE  = os.environ.get("TSMIS_CONSOLE", "1") == "1"

datas, binaries, hiddenimports = [], [], []

# Playwright: Node driver + package data + hidden imports.
_d, _b, _h = collect_all("playwright")
datas += _d; binaries += _b; hiddenimports += _h

# PDF + Excel consolidators. pdfminer's CMap data is the known frozen-build trap.
datas += collect_data_files("pdfminer")
for _pkg in ("pdfplumber", "openpyxl"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d; binaries += _b; hiddenimports += _h

# Bundle the Chromium browser folder -> _internal/ms-playwright at runtime.
datas += [(BROWSERS, "ms-playwright")]

a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
