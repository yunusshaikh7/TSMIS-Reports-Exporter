# PyInstaller spec for TSMIS Reports Exporter (portable onefolder).
#
# Driven by build\build.ps1, which sets these environment variables:
#   TSMIS_ENTRY     path to the entry-point .py to package
#   TSMIS_APP_NAME  output folder / exe name (e.g. "TSMIS Exporter")
#   TSMIS_CONSOLE   "1" to show a console window, "0" for a windowed GUI app
#
# Recipe:
#   * collect_all('playwright') + Playwright's own bundled PyInstaller hooks
#     make the Node driver importable when frozen. NOTE: no browser is bundled --
#     the app drives the machine's installed Edge/Chrome via channel="msedge"/
#     "chrome" (see scripts/common.launch_browser), so there is no ms-playwright
#     folder and nothing to point PLAYWRIGHT_BROWSERS_PATH at. The Node driver
#     (node.exe) is still required and comes in via collect_all('playwright').
#   * pdfminer ships CMap data files that must be collected or pdfplumber text
#     extraction breaks when frozen -> collect_data_files('pdfminer').
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

ENTRY    = os.environ.get("TSMIS_ENTRY", os.path.join(SPECPATH, "full_smoke.py"))
APP_NAME = os.environ.get("TSMIS_APP_NAME", "TSMIS Exporter")
CONSOLE  = os.environ.get("TSMIS_CONSOLE", "1") == "1"

# The app uses flat modules in scripts/ (imported by bare name) plus version.py
# at the repo root. Put both on pathex so PyInstaller resolves them, and list
# them as hidden imports because several are imported lazily (inside functions).
REPO_ROOT = os.path.dirname(SPECPATH)               # build/ -> repo root
SCRIPTS   = os.path.join(REPO_ROOT, "scripts")
APP_MODULES = [
    "version", "paths", "common", "events", "exporter", "exporter_parallel",
    "run_report", "logging_setup", "cli", "login",
    "export_ramp_summary", "export_ramp_detail", "export_highway_sequence",
    "export_highway_log", "export_multi",
    "consolidate_xlsx_base", "consolidate_ramp_summary", "consolidate_ramp_detail",
    "consolidate_highway_sequence", "consolidate_highway_log",
    "gui_main", "gui_app", "gui_worker", "gui_theme",
]

datas, binaries, hiddenimports = [], [], list(APP_MODULES)

# Playwright: Node driver + package data + hidden imports.
_d, _b, _h = collect_all("playwright")
datas += _d; binaries += _b; hiddenimports += _h

# PDF + Excel consolidators. pdfminer's CMap data is the known frozen-build trap.
datas += collect_data_files("pdfminer")
for _pkg in ("pdfplumber", "openpyxl"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d; binaries += _b; hiddenimports += _h

# Drop optional image libraries the app never needs at runtime: Pillow (PIL) and
# pypdfium2 (pdfplumber.to_image). IMPORTANT: openpyxl imports Pillow EAGERLY at
# import time, so in a normal install PIL *is* loaded -- it is not "never
# imported" (build/full_smoke.py reports `PIL: True` against the venv). What makes
# excluding it safe is that the code paths the app actually uses -- text/table
# extraction and writing plain workbooks, never image insert or rasterizing a PDF
# -- don't need it, and openpyxl tolerates a missing Pillow. The proof is not that
# the import is absent but that the FROZEN self-test (build.ps1 -SelfTest runs
# full_smoke.py) still passes every real code path with PIL excluded. pypdfium2 is
# only touched by pdfplumber.to_image, which the app never calls. Trims ~20 MB.
EXCLUDES = ["PIL", "pypdfium2", "pypdfium2_raw"]
_excl = set(EXCLUDES)
hiddenimports = [h for h in hiddenimports if h.split(".")[0] not in _excl]

# (No browser is bundled -- see the header. The app uses the machine's Edge/Chrome.)

a = Analysis(
    [ENTRY],
    pathex=[SCRIPTS, REPO_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
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
