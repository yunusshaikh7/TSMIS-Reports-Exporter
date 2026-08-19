#!/usr/bin/env python3
"""Benchmark canonical TSN certification work before a matrix comparison.

This deliberately measures a conservative pipeline: resolve the canonical
library source, ensure it is current, bind its token and normalized-workbook
identity, then perform one strict final live-source check.  The production
normal path may perform additional guard checks; one here keeps the comparison
fair while proving how much attempt-local certification reuse saves.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from events import Events  # noqa: E402
import matrix  # noqa: E402
import tsn_library  # noqa: E402


def _sequence(report: str, fast_mode: bool) -> dict[str, object]:
    calls = []
    original_status = tsn_library.status

    def counted_status(key):
        started = time.perf_counter()
        result = original_status(key)
        calls.append(time.perf_counter() - started)
        print(
            f"  status #{len(calls)}: {calls[-1]:.3f}s "
            f"(current={bool(result.get('current'))})",
            flush=True)
        return result

    tsn_library.status = counted_status
    started = time.perf_counter()
    try:
        if fast_mode:
            source = matrix.tsn_source(
                None, report, include_certification=True)
        else:
            source = matrix.tsn_source(None, report)
        if source.get("kind") != "consolidated":
            raise RuntimeError(
                f"{report}: canonical source is {source.get('kind')!r}, not consolidated")

        if fast_mode:
            healed = tsn_library.ensure_current(
                report, Events(), source=source,
                certified_status=source.get("_certified_status"))
        else:
            healed = tsn_library.ensure_current(report, Events(), source=source)
        if healed is not None:
            raise RuntimeError(
                "benchmark requires an already-current library; ensure_current did work")

        if not fast_mode:
            source = matrix.tsn_source(None, report)

        token, final_current = matrix.tsn_identity_check_for(
            report, source, fast_mode=fast_mode)
        workbook_identity = matrix.tsn_expected_workbook_identity(
            report, source, token, fast_mode=fast_mode)
        if not final_current():
            raise RuntimeError("strict final TSN source recheck failed")
    finally:
        tsn_library.status = original_status

    return {
        "fast_mode": fast_mode,
        "seconds": time.perf_counter() - started,
        "status_calls": len(calls),
        "status_seconds": calls,
        "identity_token": token,
        "workbook_identity": workbook_identity,
    }


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True,
                        choices=[item.subdir for item in tsn_library.reports()])
    parser.add_argument("--mode", choices=("standard", "fast", "both"),
                        default="both")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    modes = ([False, True] if args.mode == "both"
             else [args.mode == "fast"])
    runs = []
    for fast_mode in modes:
        label = "fast" if fast_mode else "standard"
        print(f"{args.report}: {label} TSN-library preflight", flush=True)
        runs.append(_sequence(args.report, fast_mode))

    payload = {"schema_version": 1, "report": args.report, "runs": runs}
    if len(runs) == 2:
        standard, fast = runs
        if (standard["identity_token"] != fast["identity_token"]
                or standard["workbook_identity"] != fast["workbook_identity"]):
            raise RuntimeError("standard and fast preflight resolved different TSN bytes")
        payload["speedup"] = standard["seconds"] / fast["seconds"]
        payload["reduction_percent"] = (
            1.0 - fast["seconds"] / standard["seconds"]) * 100.0
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["result_json"] = str(args.out.resolve())
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
