"""Comprehensive runtime self-test for the bundled libraries (dev / venv tool).

Thin wrapper: the self-test body lives in scripts/self_test.py so the EXACT
shipped windowed exe runs the identical exercise via `gui_main --self-test` (the
build.ps1 -SelfTest release gate). This entry keeps the dev/venv use:

  * Against the build venv, to prove PIL/pypdfium2 are never loaded on the app's
    real code paths (so they can be excluded from the bundle) -- run it directly:
        build\\.venv\\Scripts\\python.exe build\\full_smoke.py

The frozen release gate no longer builds a SEPARATE console exe from this file;
it runs the windowed `TSMIS Exporter.exe --self-test` (the same self_test.run),
so the artifact that ships is the artifact that passed (R1-B04). Exit 0 = all
good; nonzero/raise = something the app needs is broken.
"""
import sys
from pathlib import Path

# Make the app modules importable before importing self_test (frozen builds
# bundle them; dev/venv runs need the repo on sys.path).
if not getattr(sys, "frozen", False):
    _repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_repo / "scripts"))      # self_test, common, gui_api, ...
    sys.path.insert(0, str(_repo))                  # version.py at repo root

from self_test import run                            # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run())
