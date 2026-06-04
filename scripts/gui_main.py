"""GUI entry point for the TSMIS Reports Exporter.

Run in dev:   python scripts\\gui_main.py
Packaged:     this is the PyInstaller entry (Phase 6 sets TSMIS_ENTRY here and
              TSMIS_CONSOLE=0 for a windowed app).

Sets PLAYWRIGHT_BROWSERS_PATH to the bundled browsers BEFORE importing anything
that imports Playwright -- the same pattern proven in build/smoke_entry.py.
"""
import os
import sys
from pathlib import Path


def _bootstrap():
    if getattr(sys, "frozen", False):
        # onefolder: bundled browsers live under _internal (sys._MEIPASS).
        os.environ.setdefault(
            "PLAYWRIGHT_BROWSERS_PATH",
            str(Path(sys._MEIPASS) / "ms-playwright"),
        )
    else:
        # dev: make both the flat scripts/ modules and the repo-root version.py
        # importable, regardless of the current working directory.
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
