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
#   * The .exe carries a version-info resource (from version.py), an icon, and a
#     manifest (asInvoker). Those are trust signals that reduce Windows Defender /
#     corporate-IT (DLP/SmartScreen) false-positives on an unsigned build. Code
#     signing is still the only complete fix (see CLAUDE.md).
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

ENTRY    = os.environ.get("TSMIS_ENTRY", os.path.join(SPECPATH, "full_smoke.py"))
APP_NAME = os.environ.get("TSMIS_APP_NAME", "TSMIS Exporter")
CONSOLE  = os.environ.get("TSMIS_CONSOLE", "1") == "1"

# The app uses flat modules in scripts/ (imported by bare name) plus version.py
# at the repo root. Put both on pathex so PyInstaller resolves them, and list
# them as hidden imports because several are imported lazily (inside functions).
REPO_ROOT = os.path.dirname(SPECPATH)               # build/ -> repo root
SCRIPTS   = os.path.join(REPO_ROOT, "scripts")

# --- Windows .exe metadata: version resource + icon + manifest ---------------
# The single source of truth for the version is version.py.
sys.path.insert(0, REPO_ROOT)
from version import __version__ as APP_VERSION       # noqa: E402

_parts  = (APP_VERSION.split(".") + ["0", "0", "0", "0"])[:4]
_vtuple = tuple(int(p) if p.isdigit() else 0 for p in _parts)

from PyInstaller.utils.win32.versioninfo import (   # noqa: E402
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
    VarFileInfo, VarStruct,
)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_vtuple, prodvers=_vtuple, mask=0x3F, flags=0x0,
                      OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "TSMIS Reports Exporter"),
            StringStruct("FileDescription", "TSMIS Reports Bulk Exporter"),
            StringStruct("FileVersion", APP_VERSION),
            StringStruct("InternalName", APP_NAME),
            StringStruct("LegalCopyright", "Internal tool. Provided as-is, no warranty."),
            StringStruct("OriginalFilename", APP_NAME + ".exe"),
            StringStruct("ProductName", "TSMIS Reports Exporter"),
            StringStruct("ProductVersion", APP_VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),  # US English, Unicode
    ],
)

ICON     = os.path.join(SPECPATH, "app.ico")        # built once with Pillow (see CLAUDE.md)
MANIFEST = os.path.join(SPECPATH, "app.manifest")
APP_MODULES = [
    "version", "paths", "common", "events", "exporter", "exporter_parallel",
    "run_report", "logging_setup", "settings", "cli", "login", "reports",
    "updater", "batch_manifest",
    "export_ramp_summary", "export_ramp_detail", "export_highway_sequence",
    "export_highway_log", "export_highway_log_pdf", "export_intersection_summary",
    "export_intersection_detail", "export_multi",
    "highway_log_columns",
    "consolidate_xlsx_base", "consolidate_ramp_summary", "consolidate_ramp_detail",
    "consolidate_highway_sequence", "consolidate_highway_log",
    "consolidate_tsn_highway_log", "consolidate_tsmis_highway_log_pdf",
    "compare_core", "compare_highway_log", "compare_highway_log_pdf", "compare_env",
    "gui_main", "gui_api", "gui_worker",
]

datas, binaries, hiddenimports = [], [], list(APP_MODULES)

# Bundle the icon so the GUI can set the window/taskbar icon at runtime
# (resolved via sys._MEIPASS -> _internal/app.ico). Binary, so the DLP text scan
# in prune_bundle.ps1 skips it.
if os.path.exists(ICON):
    datas += [(ICON, ".")]

# The GUI's web assets (scripts/ui) ship as plain data files; gui_api resolves
# them at runtime via sys._MEIPASS/ui/.
UI_DIR = os.path.join(SCRIPTS, "ui")
datas += [(os.path.join(UI_DIR, f), "ui") for f in os.listdir(UI_DIR)]

# pywebview (Edge WebView2 GUI shell) + its Windows backend: pythonnet/clr need
# their package data (Python.Runtime.dll, the netstandard facade DLLs, the
# ClrLoader natives, webview/lib WebView2 assemblies) or the frozen window
# can't open. collect_all carries each package's data + binaries + imports.
for _pkg in ("webview", "pythonnet", "clr_loader"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d; binaries += _b; hiddenimports += _h
hiddenimports += ["clr"]            # pythonnet's import name

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
# tkinter went with the old Tk GUI (the UI is a WebView now) -- excluding it
# also drops the Tcl/Tk runtime from the bundle.
EXCLUDES = ["PIL", "pypdfium2", "pypdfium2_raw", "tkinter", "_tkinter"]
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
    upx=False,                                       # UPX-packed exes are a classic AV false-positive trigger
    console=CONSOLE,
    disable_windowed_traceback=False,
    icon=(ICON if os.path.exists(ICON) else None),
    version=VERSION_INFO,
    manifest=(MANIFEST if os.path.exists(MANIFEST) else None),
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
