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


def write_comparison_stub(path, rows=1, diffs=0, sheet="Comparison"):
    """Write the MINIMAL schema-valid comparison workbook (CMP-AUD-115).

    A stub comparator in this suite stands in for a real one, so its output has
    to satisfy the same commit-boundary comparison-artifact schema: a sheet named
    `Comparison` whose header carries UNIQUE `Status` and `Diffs` labels, and
    data rows whose status is valid (`Both` rows carry a non-negative integer
    Diffs; one-sided rows carry none). Fixtures that need a deliberately INVALID
    artifact should keep writing their own workbook."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["Route", "Status", "Diffs"])
    for i in range(rows):
        ws.append([f"{i + 1:03d}", "Both", diffs])
    wb.save(str(path))
    wb.close()
    return path


def build_published_comparison(path, schema, rows_a, rows_b, has_route=True):
    """Publish a REAL values comparison workbook for a fixture (CMP-AUD-208).

    Visual evidence now reads the cells a comparison PUBLISHED — its hidden
    state masks and anchored counts — so a fixture can no longer fake a clean
    or a differing comparison by stubbing a loader. Anything that drives
    `visual_evidence.generate` has to hand it bytes the engine actually wrote.
    """
    from compare_core import run_compare
    result = run_compare(schema, rows_a, rows_b, has_route, path,
                         mode="values", confirm_overwrite=lambda _p: True)
    if result.status != "ok":
        raise AssertionError(
            f"fixture comparison did not publish: {result.message}")
    return path
