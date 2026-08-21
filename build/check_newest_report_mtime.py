"""Regression lock for the ONE newest-data-mtime reader.

`artifact_store.newest_report_file_mtime` replaced three byte-identical private
copies (`day_matrix`, `baseline_matrix`, `pdf_excel_matrix` each carried their own
`_folder_newest_mtime`). That is only allowed to be a SPEED change: every Matrix
freshness decision keys on this value, so a different answer would silently mark
cells stale or — far worse — fresh.

This holds both halves:
  * the shared reader returns EXACTLY what the historical implementation returned,
    across the CMP-AUD-083 edge cases (Excel locks, sidecars, temps, comparison
    payloads, subdirectories, empty and absent folders);
  * it actually costs less — `os.scandir` answers `is_file()`/`stat()` from the
    directory read, so it makes ZERO `os.stat` syscalls where the historical
    version made two per entry;
  * and no module has grown a private copy back.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT)]

import artifact_store  # noqa: E402

_failures = []


def check(name, condition, detail=""):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)
        if detail:
            print(f"       {detail}")


def _historical(p):
    """The pre-consolidation implementation, verbatim, as the A/B control."""
    newest = None
    try:
        entries = list(Path(p).iterdir())
    except OSError:
        return None
    for e in entries:
        try:
            if e.is_file() and artifact_store.is_report_data_file(e.name):
                m = e.stat().st_mtime
                if newest is None or m > newest:
                    newest = m
        except OSError:
            continue
    return newest


def _fixture(root):
    """A folder exercising every class the predicate has to separate."""
    d = root / "exports"
    d.mkdir()
    # real exports, with deliberately different mtimes so "newest" is decidable
    for i, name in enumerate(("a_route_1.xlsx", "b_route_2.PDF", "c_route_10.xlsx")):
        f = d / name
        f.write_text("data")
        os.utime(f, (1_700_000_000 + i * 60, 1_700_000_000 + i * 60))
    # everything that must NOT count, each stamped NEWER than every real export
    later = 1_900_000_000
    for name in ("~$a_route_1.xlsx",            # Excel lock
                 "notes.txt", "README",          # not a report suffix
                 "route.tmp", "x.tmp-1234",      # our in-flight temps
                 ".fingerprint.json"):           # a sidecar
        f = d / name
        f.write_text("x")
        os.utime(f, (later, later))
    # a DIRECTORY named like an export: is_file() must reject it
    sub = d / "nested_route_9.xlsx"
    sub.mkdir()
    os.utime(sub, (later, later))
    return d


def test_answers_are_identical(root):
    print("the shared reader returns exactly the historical value:")
    populated = _fixture(root)
    empty = root / "empty"; empty.mkdir()
    absent = root / "does-not-exist"
    only_junk = root / "junk"; only_junk.mkdir()
    (only_junk / "~$locked.xlsx").write_text("x")
    (only_junk / "notes.txt").write_text("x")

    cases = {
        "a populated export folder": populated,
        "an empty folder": empty,
        "an absent folder": absent,
        "a folder holding ONLY a lock + notes": only_junk,
    }
    for label, path in cases.items():
        got, want = artifact_store.newest_report_file_mtime(path), _historical(path)
        check(f"{label}: {got!r} == {want!r}", got == want)

    # The fixture has to actually discriminate, or the four cases above prove nothing.
    newest = artifact_store.newest_report_file_mtime(populated)
    check("the fixture really does exclude the newer non-exports",
          newest is not None and newest < 1_900_000_000,
          f"newest={newest!r} — a lock/sidecar/dir leaked into the answer")
    check("an export-less folder really is None",
          artifact_store.newest_report_file_mtime(only_junk) is None
          and artifact_store.newest_report_file_mtime(empty) is None
          and artifact_store.newest_report_file_mtime(absent) is None)
    check("a str path works as well as a Path",
          artifact_store.newest_report_file_mtime(str(populated)) == newest)

    # A file appearing must move the answer — the value has to track reality.
    time.sleep(0.01)
    fresh = populated / "z_route_99.xlsx"
    fresh.write_text("data")
    os.utime(fresh, (1_800_000_000, 1_800_000_000))
    moved = artifact_store.newest_report_file_mtime(populated)
    check("a newer real export moves the answer",
          moved == 1_800_000_000 == _historical(populated), f"got {moved!r}")


def test_it_is_actually_cheaper(root):
    print("it costs zero os.stat syscalls where the old one paid two per entry:")
    d = root / "cost"
    d.mkdir()
    for i in range(25):
        (d / f"r_route_{i}.xlsx").write_text("x")

    counted = {"n": 0}
    real_stat = os.stat

    def counting(*a, **k):
        counted["n"] += 1
        return real_stat(*a, **k)

    os.stat = counting
    try:
        counted["n"] = 0
        artifact_store.newest_report_file_mtime(d)
        new_calls = counted["n"]
        counted["n"] = 0
        _historical(d)
        old_calls = counted["n"]
    finally:
        os.stat = real_stat

    check("the shared reader makes NO os.stat calls (scandir answers both)",
          new_calls == 0, f"made {new_calls}")
    check("the control really did pay per entry (the probe has teeth)",
          old_calls >= 50, f"historical made {old_calls} for 25 files")


def test_one_bad_entry_does_not_abort_the_fold(root):
    """A transiently locked/vanished file must cost only ITSELF. Before the guard
    existed, one such entry aborted the whole scan and the day's export read as
    'not present' — a real field failure. The bad entry goes FIRST so a fold that
    aborts returns None instead of the good file's mtime."""
    print("one locked entry costs only itself:")
    good = root / "survivor" / "r001.xlsx"
    good.parent.mkdir(parents=True, exist_ok=True)
    good.write_bytes(b"PK")

    class _Bad:
        name = "r002.xlsx"

        def is_file(self):
            raise OSError("locked / vanished mid-scan")

    class _Good:
        name = good.name

        def is_file(self):
            return True

        def stat(self):
            return good.stat()

    class _FakeScandir:
        def __init__(self, _p):
            pass

        def __enter__(self):
            return iter([_Bad(), _Good()])

        def __exit__(self, *_exc):
            return False

    saved = artifact_store.os.scandir
    artifact_store.os.scandir = _FakeScandir
    try:
        got = artifact_store.newest_report_file_mtime("ignored")
    finally:
        artifact_store.os.scandir = saved
    check("the good file's mtime still comes back",
          got == good.stat().st_mtime, f"got {got!r}")

    # An unreadable FOLDER (not entry) is still the "no export" answer, not a raise.
    class _Denied:
        def __init__(self, _p):
            raise PermissionError("denied")

    artifact_store.os.scandir = _Denied
    try:
        denied = artifact_store.newest_report_file_mtime("ignored")
    finally:
        artifact_store.os.scandir = saved
    check("an unreadable folder returns None rather than raising", denied is None)


def test_no_module_kept_a_private_copy():
    print("no module carries its own copy any more:")
    owners = ("day_matrix", "baseline_matrix", "pdf_excel_matrix")
    for mod in owners:
        text = (ROOT / "scripts" / f"{mod}.py").read_text(encoding="utf-8")
        check(f"{mod}.py defines no private _folder_newest_mtime",
              "def _folder_newest_mtime" not in text)
        check(f"{mod}.py routes through the shared reader",
              "newest_report_file_mtime" in text)

    # And they must agree at runtime, not just textually.
    import baseline_matrix
    import day_matrix
    import pdf_excel_matrix
    for mod in (day_matrix, baseline_matrix, pdf_excel_matrix):
        fn = getattr(mod, "_folder_newest_mtime", None)
        check(f"{mod.__name__}'s reader IS the shared one",
              fn is None or fn is artifact_store.newest_report_file_mtime,
              f"{fn!r}")


def main():
    print("newest report-data mtime — one shared reader:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_newest_mtime_"))
    try:
        test_answers_are_identical(root)
        test_it_is_actually_cheaper(root)
        test_one_bad_entry_does_not_abort_the_fold(root)
        test_no_module_kept_a_private_copy()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL NEWEST-MTIME CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
