"""GUI entry point for the TSMIS Reports Exporter.

Run in dev:   python scripts\\gui_main.py   (or "run app (GUI preview).bat")
Packaged:     this is the PyInstaller entry (build.ps1 sets TSMIS_ENTRY here
              and TSMIS_CONSOLE=0 for a windowed app).

The window is a pywebview (Edge WebView2) shell rendering scripts/ui/; all
GUI logic lives in gui_api.py, and the browser/file work stays on the same
gui_worker threads the engines have always used. The only bootstrap here is
making the dev import paths work when run from source.
"""
import logging
import os
import sys
from pathlib import Path


def _bootstrap():
    # Dev only: make the flat scripts/ modules and the repo-root version.py
    # importable regardless of the working directory. Frozen builds bundle these.
    if not getattr(sys, "frozen", False):
        here = Path(__file__).resolve().parent          # scripts/
        sys.path.insert(0, str(here))                   # common, exporter, gui_api, ...
        sys.path.insert(0, str(here.parent))            # version.py (repo root)


_bootstrap()


def _unblock_dotnet_assemblies():
    """Frozen builds: strip the Mark-of-the-Web from the bundled .NET files.

    A release zip downloaded from the internet carries the "blocked" flag;
    extracting it without Unblock tags every file with an NTFS Zone.Identifier
    stream, and the .NET Framework then REFUSES to load those assemblies — the
    window dies at startup with "Failed to resolve Python.Runtime.Loader.
    Initialize" (seen in the field on the first v0.8.0 download; dev runs and
    CI never go through a downloaded zip, so only releases hit it). Deleting
    the stream is exactly what right-click → Properties → Unblock does. Only
    the CLR cares: plain Win32 DLL loads ignore the tag, so the .NET trees
    are the only ones that need cleaning. Best-effort — on a read-only
    install this fails and the error box explains the manual Unblock."""
    if not getattr(sys, "frozen", False):
        return
    internal = Path(sys.executable).resolve().parent / "_internal"
    removed = errors = 0
    for sub in ("pythonnet", "clr_loader", "webview"):
        root = internal / sub
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                os.remove(f"{p}:Zone.Identifier")
                removed += 1
            except FileNotFoundError:
                pass                       # not tagged (the normal case)
            except OSError:
                errors += 1                # read-only location etc.
    if removed or errors:
        logging.getLogger("tsmis.gui").info(
            "unblocked %d bundled .NET file(s) (Mark-of-the-Web removed)%s",
            removed, f"; {errors} could not be unblocked" if errors else "")


def main():
    from logging_setup import setup_logging
    # No faulthandler here: it intercepts the CLR's routine first-chance
    # access violations (pythonnet/WebView2) and deadlocks the window -- see
    # setup_logging's docstring. Python-level crashes are still logged by the
    # excepthooks and the GuiApi method wrapper.
    setup_logging(enable_faulthandler=False)
    _unblock_dotnet_assemblies()           # must run BEFORE the CLR loads
    try:
        import gui_api
    except ImportError as e:
        # Dev runs hit this when pywebview isn't installed yet; the packaged
        # app bundles it. Print for the console case, box for the windowed one.
        msg = (f"The GUI could not start: a required component is missing "
               f"({e.name or e}).\n\nRun \"1. setup (one time).bat\" "
               f"(pip install -r requirements.txt) and try again.")
        # A windowed PyInstaller exe has sys.stderr = None -- print() would
        # raise. Console (dev) runs still get the message text.
        if sys.stderr:
            print(msg, file=sys.stderr)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "TSMIS Exporter", 0x10)
        except Exception:
            pass
        raise SystemExit(1)
    gui_api.run()


if __name__ == "__main__":
    main()
