"""Frozen-build self-test for the GUI (built by `build.ps1 -SelfTest`).

Constructs the real App window *withdrawn* (hidden), forces a full layout pass,
then exits -- so the packaged GUI's import graph and Tk/ttk bundling can be
verified without a visible window or a blocking mainloop. Prints a clear OK line
(or a traceback) so the build can be checked headlessly.
"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "PLAYWRIGHT_BROWSERS_PATH", str(Path(sys._MEIPASS) / "ms-playwright")
    )

import gui_app  # noqa: E402  (frozen: flat modules are bundled top-level)


def main():
    app = gui_app.App()
    app.withdraw()
    app.update()                       # force the full widget/layout/style pass
    print(f"FROZEN GUI OK -- constructed {app.title()!r}")
    app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
