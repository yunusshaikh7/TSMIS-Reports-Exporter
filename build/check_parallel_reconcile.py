"""Golden check for the parallel-engine crash reconciliation
(scripts/exporter_parallel._reconcile_unaccounted).

Locks two Phase-3 audit fixes:
  * `parallel-reconcile-uses-read-strict-not-lock-tolerant` — reconciliation now
    uses the lock-tolerant _can_resume, so a route whose file is on disk but
    locked open (Excel sharing-deny) is TRUSTED as present, not re-marked failed.
  * `parallel-crash-plus-cancel-skips-reconciliation` — reconciliation is skipped
    on a clean cancel (unreached routes are simply not-done) BUT runs when a
    worker CRASHED even on cancel, so the crash's orphaned routes still appear in
    the run report.

Pure Python, no threads/browsers — drives the extracted helper directly.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_parallel_reconcile.py
"""
import builtins
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import openpyxl  # noqa: E402

from events import Events, RunResult  # noqa: E402
from exporter import ReportSpec, _record  # noqa: E402
from exporter_parallel import _reconcile_unaccounted  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


SPEC = ReportSpec(
    label="X", subdir="x", filename=lambda r: f"r_{r}.xlsx",
    wait_js=lambda r: "() => true", is_empty=lambda p: False, save=lambda *a: None)


def _valid_xlsx(path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "hi"
    wb.save(path)


def _result_with(out_dir, per_route):
    r = RunResult(output_dir=str(out_dir))
    for route, status in per_route:
        _record(r, Events(), route, status)
    return r


def test_lock_tolerant(tmp):
    print("reconciliation is lock-tolerant (does not re-fail a locked-but-present file):")
    routes = ["001", "002", "003"]
    # 001 saved + complete on disk; 002 saved but LOCKED (unreadable); 003 absent.
    _valid_xlsx(tmp / "r_001.xlsx")
    locked = tmp / "r_002.xlsx"
    _valid_xlsx(locked)
    # none recorded (the worker crashed before _record ran for any)
    result = _result_with(tmp, [])

    real_open = builtins.open

    def _deny(path, *a, **k):
        if str(path) == str(locked):
            raise PermissionError("open in Excel")
        return real_open(path, *a, **k)

    builtins.open = _deny
    try:
        missing = _reconcile_unaccounted(routes, result, tmp, SPEC, Events(),
                                         cancelled=False, worker_crashed=True)
    finally:
        builtins.open = real_open

    check("complete file NOT marked failed (001)", "001" not in missing)
    check("locked-but-present file NOT marked failed (002)", "002" not in missing)
    check("absent file marked failed (003)", "003" in missing)
    check("locked file was NOT deleted", locked.exists())
    check("only the absent route recorded failed", result.failed == ["003"])


def test_truncated_marked(tmp):
    print("reconciliation re-pulls a readably-truncated file:")
    (tmp / "r_010.xlsx").write_bytes(b"")        # 0-byte / truncated
    result = _result_with(tmp, [])
    missing = _reconcile_unaccounted(["010"], result, tmp, SPEC, Events(),
                                     cancelled=False, worker_crashed=True)
    check("truncated file marked failed", missing == ["010"])
    check("truncated file removed for re-pull", not (tmp / "r_010.xlsx").exists())


def test_cancel_gate(tmp):
    print("cancel gate: skip on clean cancel, reconcile on crash+cancel:")
    routes = ["020", "021"]
    # 020 was completed (recorded); 021 is unaccounted + no file.
    result1 = _result_with(tmp, [("020", "saved")])
    # Clean cancel (no crash): unreached 021 is NOT marked failed.
    missing_clean = _reconcile_unaccounted(routes, result1, tmp, SPEC, Events(),
                                           cancelled=True, worker_crashed=False)
    check("clean cancel skips reconciliation (021 not failed)", missing_clean == [])
    check("clean cancel leaves failed list empty", result1.failed == [])

    # Crash + cancel: the crash's orphaned 021 IS surfaced.
    result2 = _result_with(tmp, [("020", "saved")])
    missing_crash = _reconcile_unaccounted(routes, result2, tmp, SPEC, Events(),
                                           cancelled=True, worker_crashed=True)
    check("crash+cancel reconciles (021 marked failed)", missing_crash == ["021"])
    check("crash+cancel records the orphan", result2.failed == ["021"])


def test_no_double_count(tmp):
    print("already-accounted routes are never re-marked:")
    _valid_xlsx(tmp / "r_030.xlsx")
    result = _result_with(tmp, [("030", "saved"), ("031", "empty")])
    missing = _reconcile_unaccounted(["030", "031"], result, tmp, SPEC, Events(),
                                     cancelled=False, worker_crashed=False)
    check("recorded routes not reconciled", missing == [])
    check("failed list stays empty", result.failed == [])


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_recon_"))
    test_lock_tolerant(tmp)
    test_truncated_marked(tmp)
    test_cancel_gate(tmp)
    test_no_double_count(tmp)
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL PARALLEL-RECONCILE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
