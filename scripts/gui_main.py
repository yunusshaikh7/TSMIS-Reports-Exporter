"""GUI entry point for the TSMIS Reports Exporter.

Run in dev:   python scripts\\gui_main.py
Packaged:     this is the PyInstaller entry (Phase 6 sets TSMIS_ENTRY here and
              TSMIS_CONSOLE=0 for a windowed app).

The app drives the browser already installed on the machine (Edge/Chrome), so
there is no bundled Chromium to point Playwright at -- the only bootstrap left is
making the dev import paths work when run from source.
"""
import sys
from pathlib import Path


def _bootstrap():
    # Dev only: make the flat scripts/ modules and the repo-root version.py
    # importable regardless of the working directory. Frozen builds bundle these.
    if not getattr(sys, "frozen", False):
        here = Path(__file__).resolve().parent          # scripts/
        sys.path.insert(0, str(here))                   # common, exporter, gui_app, ...
        sys.path.insert(0, str(here.parent))            # version.py (repo root)


_bootstrap()

from gui_app import App  # noqa: E402  (must follow _bootstrap)


def main():
    from logging_setup import setup_logging
    setup_logging()
    App().mainloop()


if __name__ == "__main__":
    main()
