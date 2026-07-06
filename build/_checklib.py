"""Shared scaffolding for the build/check_*.py suite (U4 / TST-01, v0.19.0).

Every check hand-rolls the same four pieces: the scripts/ sys.path setup, a
check()/fail counter, a monkeypatch context, and a temp-dir context. NEW checks
import them from here; existing checks migrate opportunistically (they are
self-contained on purpose — no forced churn).

    from _checklib import Checker, patch, scripts_path, temp_dir

    scripts_path()                       # scripts/ (+ repo root) importable
    c = Checker()
    with patch(settings, "get_batch_dest", lambda: "X"), temp_dir("tsmis_x_") as tmp:
        c.check("thing happened", thing() == 42, "detail shown on failure")
    raise SystemExit(c.summary())
"""
import contextlib
import shutil
import sys
import tempfile
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent


def scripts_path():
    """Make scripts/ (and the repo root, for version.py) importable."""
    for p in (str(ROOT / "scripts"), str(ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


class Checker:
    """The standard check()/summary() pair with a failure list."""

    def __init__(self):
        self.failures = []

    def check(self, name, cond, detail=""):
        if cond:
            print(f"  ok: {name}")
        else:
            print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
            self.failures.append(name)

    def summary(self):
        """Print the verdict; return the process exit code."""
        if self.failures:
            print(f"\n{len(self.failures)} check(s) FAILED")
            return 1
        print("\nall good")
        return 0


@contextlib.contextmanager
def patch(obj, name, value):
    """Set obj.name = value for the block, restoring the original after."""
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextlib.contextmanager
def temp_dir(prefix="tsmis_check_"):
    """A temp directory removed (best-effort) when the block exits."""
    d = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


class FakeEvents:
    """An events sink that records log lines and supports scripted cancel."""

    def __init__(self, cancelled=False):
        self.lines = []
        self.cancelled = cancelled

    def on_log(self, text):
        self.lines.append(text)

    def is_cancelled(self):
        return self.cancelled
