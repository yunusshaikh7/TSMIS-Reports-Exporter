"""Offline lifecycle coverage for export retry bookkeeping and run reports.

No browser, site, or network. Locks the sequential retry pass's total accounting
across success/resume/recovery-stop/cancel, the CSV run-report projection, and
the console multi-export registry view.
"""
import csv
from pathlib import Path

from _checklib import Checker, patch, scripts_path, temp_dir

scripts_path()

import export_multi
import exporter
import reports
import run_report
from events import Events, RunResult
from exporter import ReportSpec

c = Checker()


def _failed_result(routes):
    result = RunResult()
    result.failed = list(routes)
    result.per_route = [(route, "failed") for route in routes]
    return result


def _spec():
    return ReportSpec(
        label="Lifecycle", subdir="lifecycle", data_value="lifecycle",
        filename=lambda route: f"route_{route}.pdf",
        wait_js=lambda route: "() => true", is_empty=lambda page: False,
        save=lambda page, out_path, timeout_ms: None)


def test_sequential_retry_accounting():
    print("sequential slow-retry accounting is total and exactly once:")
    routes = ["001", "002", "003", "004"]
    result = _failed_result(routes)
    notifications = []
    events = Events(on_route=lambda route, status: notifications.append((route, status)))

    with temp_dir("tsmis_retry_lifecycle_") as out_dir:
        # Route 002 completed outside the process (for example, the first pass
        # committed bytes just before its worker failed). Retry must resume it.
        (out_dir / "route_002.pdf").write_bytes(b"%PDF")

        def process(_page, _spec, route, _prefix, _path,
                    route_events, route_result, _timeout):
            if route == "001":
                route_result.saved += 1
                exporter._record(route_result, route_events, route, "saved")
                return True
            return False                 # recovery stop before 003 is recorded

        with patch(exporter, "_recover_or_stop", lambda *_a, **_k: True), \
             patch(exporter, "_wait_while_paused", lambda _events: None), \
             patch(exporter, "_require_safe_destination", lambda *_a, **_k: None), \
             patch(exporter, "_process_route", process):
            exporter._retry_failed_routes(
                object(), _spec(), events, result, out_dir, timeout_ms=900_000)

    expected = [("001", "saved"), ("002", "exists"),
                ("003", "failed"), ("004", "failed")]
    c.check("success + resume replace their old failure records",
            result.saved == 1 and result.exists == ["002"]
            and result.failed == ["003", "004"],
            f"saved={result.saved} exists={result.exists} failed={result.failed}")
    c.check("recovery-stop leaves a total, duplicate-free run report",
            result.per_route == expected, f"rows={result.per_route}")
    c.check("final route notifications mirror the report rows",
            notifications == expected, f"notifications={notifications}")

    cancelled = _failed_result(["010", "011"])
    cancelled_notifications = []
    cancelled_events = Events(
        is_cancelled=lambda: True,
        on_route=lambda route, status:
        cancelled_notifications.append((route, status)))

    def should_not_process(*_args, **_kwargs):
        raise AssertionError("cancelled retry processed a route")

    with patch(exporter, "_recover_or_stop", lambda *_a, **_k: True), \
         patch(exporter, "_wait_while_paused", lambda _events: None), \
         patch(exporter, "_process_route", should_not_process), \
         temp_dir("tsmis_retry_cancel_") as out_dir:
        exporter._retry_failed_routes(
            object(), _spec(), cancelled_events, cancelled, out_dir,
            timeout_ms=900_000)
    cancelled_rows = [("010", "failed"), ("011", "failed")]
    c.check("cancel-at-start restores every removed first-pass failure",
            cancelled.failed == ["010", "011"]
            and cancelled.per_route == cancelled_rows
            and cancelled_notifications == cancelled_rows,
            f"failed={cancelled.failed} rows={cancelled.per_route}")


def test_run_report_projection():
    print("run_report writes stable, friendly CSV rows for one or many reports:")
    first = RunResult(per_route=[
        ("001", "saved"), ("002", "empty"), ("003", "skipped"),
        ("004", "failed"), ("005", "exists"), ("006", "future-status")])
    second = RunResult(per_route=[("101", "saved")])

    def fixed_time(fmt):
        return {"%Y%m%d_%H%M%S": "20260717_142233",
                "%Y-%m-%d %H:%M:%S": "2026-07-17 14:22:33"}[fmt]

    with temp_dir("tsmis_run_report_") as tmp, \
         patch(run_report.time, "strftime", fixed_time):
        auto = run_report.auto_report_path("highway_log", "ssor-prod")
        c.check("auto path includes report/site/timestamp",
                auto.name == "highway_log_ssor-prod_run_20260717_142233.csv",
                str(auto))

        single_path = tmp / "nested" / "single.csv"
        returned = run_report.write_run_report(first, "Highway, Log", single_path)
        with open(single_path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        c.check("single writer creates parents and returns the written path",
                returned == single_path and single_path.is_file())
        c.check("all friendly statuses map and an unknown status is conserved",
                [row["Status"] for row in rows]
                == ["Saved", "No data", "Skipped", "Failed", "Already had",
                    "future-status"])
        c.check("CSV quoting preserves a comma-bearing label and exact route order",
                all(row["Report"] == "Highway, Log" for row in rows)
                and [row["Route"] for row in rows]
                == ["001", "002", "003", "004", "005", "006"])
        c.check("one build-time timestamp is stamped on every row",
                {row["Run At"] for row in rows} == {"2026-07-17 14:22:33"})

        multi_path = tmp / "multi.csv"
        run_report.write_run_report_multi(
            [("First", first), ("Second", second)], multi_path)
        with open(multi_path, newline="", encoding="utf-8") as handle:
            multi = list(csv.DictReader(handle))
        c.check("multi writer preserves report grouping + row order",
                [(row["Report"], row["Route"]) for row in multi]
                == [("First", route) for route in
                    ["001", "002", "003", "004", "005", "006"]]
                + [("Second", "101")])

        empty_path = tmp / "empty.csv"
        run_report.write_run_report_multi([], empty_path)
        with open(empty_path, newline="", encoding="utf-8") as handle:
            c.check("an empty multi-report still carries the canonical header",
                    list(csv.reader(handle))
                    == [["Report", "Route", "Status", "Run At"]])


def test_console_registry_view():
    print("export_multi remains a derived view of the export registry:")
    expected = [(label, spec) for label, _fmt, spec in reports.EXPORT_REPORTS]
    c.check("menu labels/order match EXPORT_REPORTS exactly",
            [label for label, _spec in export_multi.REPORTS]
            == [label for label, _spec in expected])
    c.check("menu carries the exact registry ReportSpec objects",
            len(export_multi.REPORTS) == len(expected)
            and all(actual is wanted
                    for (_label, actual), (_label2, wanted)
                    in zip(export_multi.REPORTS, expected)))


if __name__ == "__main__":
    print("export lifecycle + run-report contract:")
    test_sequential_retry_accounting()
    test_run_report_projection()
    test_console_registry_view()
    raise SystemExit(c.summary())
