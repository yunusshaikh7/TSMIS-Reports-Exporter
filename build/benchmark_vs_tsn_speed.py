#!/usr/bin/env python3
"""Repeatable real-corpus benchmark for one values-mode vs-TSN comparison.

The benchmark deliberately times only product work: an optional TSMIS
consolidation followed by the public report comparator.  It records the
published typed outcome and a canonical digest of every workbook ZIP member
except ``docProps/core.xml`` (whose created/modified timestamps are expected to
change).  An output-preserving optimization must therefore keep both the typed
truth and the canonical package digest exact.

Example (PowerShell)::

    python build/benchmark_vs_tsn_speed.py `
      --report intersection_detail `
      --tsmis-dir "C:\\path\\to\\intersection_detail" `
      --tsn "C:\\path\\to\\tsn_intersection_detail_normalized.xlsx" `
      --work-dir tmp/vs-tsn-speed `
      --tag baseline --reconsolidate
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT)]

from events import Events  # noqa: E402


REPORTS = {
    "intersection_detail": (
        "consolidate_intersection_detail", "compare_intersection_detail_tsn"),
    "ramp_detail": (
        "consolidate_ramp_detail", "compare_ramp_detail_tsn"),
    "highway_sequence": (
        "consolidate_highway_sequence", "compare_highway_sequence_tsn"),
}

_VOLATILE_PACKAGE_MEMBERS = {"docProps/core.xml"}


def _package_manifest(path: Path) -> dict[str, object]:
    """Canonical uncompressed-member manifest, independent of ZIP timestamps."""
    members = []
    aggregate = hashlib.sha256()
    with ZipFile(path) as archive:
        names = sorted(
            name for name in archive.namelist()
            if name not in _VOLATILE_PACKAGE_MEMBERS)
        for name in names:
            payload = archive.read(name)
            digest = hashlib.sha256(payload).hexdigest()
            members.append({"name": name, "bytes": len(payload), "sha256": digest})
            encoded = name.encode("utf-8")
            aggregate.update(len(encoded).to_bytes(4, "big"))
            aggregate.update(encoded)
            aggregate.update(len(payload).to_bytes(8, "big"))
            aggregate.update(bytes.fromhex(digest))
    return {
        "excluded_members": sorted(_VOLATILE_PACKAGE_MEMBERS),
        "member_count": len(members),
        "sha256": aggregate.hexdigest(),
        "members": members,
    }


def _typed_outcome(result) -> dict[str, object]:
    typed = getattr(result, "comparison_outcome", None)
    if typed is None:
        raise RuntimeError("comparison succeeded without a typed outcome")
    return typed.to_dict()


def _run(args: argparse.Namespace) -> dict[str, object]:
    consolidator_name, comparator_name = REPORTS[args.report]
    consolidator = importlib.import_module(consolidator_name)
    comparator = importlib.import_module(comparator_name)

    tsmis_dir = args.tsmis_dir.resolve()
    tsn_path = args.tsn.resolve()
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    consolidated = work_dir / f"{args.report}_tsmis_consolidated.xlsx"
    events = Events(on_log=(print if args.product_log else lambda _message: None))

    consolidation_seconds = 0.0
    if args.reconsolidate or not consolidated.is_file():
        print(f"consolidating {args.report} from {tsmis_dir}", flush=True)
        started = time.perf_counter()
        result = consolidator.consolidate(
            input_dir=tsmis_dir, out_path=consolidated, events=events,
            confirm_overwrite=lambda _path: True)
        consolidation_seconds = time.perf_counter() - started
        if result.status != "ok":
            raise RuntimeError(result.message or "TSMIS consolidation failed")
        print(f"consolidation: {consolidation_seconds:.3f}s", flush=True)
    elif not consolidated.is_file():
        raise FileNotFoundError(consolidated)

    runs = []
    for iteration in range(1, args.iterations + 1):
        suffix = "" if args.iterations == 1 else f"-{iteration:02d}"
        output = work_dir / f"{args.tag}-{args.report}{suffix}.xlsx"
        print(f"comparison {iteration}/{args.iterations}: {output.name}", flush=True)
        started = time.perf_counter()
        result = comparator.compare(
            consolidated, tsn_path, output, events=events,
            confirm_overwrite=lambda _path: True, mode="values",
            fast_mode=args.fast_mode)
        elapsed = time.perf_counter() - started
        if result.status != "ok":
            raise RuntimeError(result.message or "vs-TSN comparison failed")
        print(f"comparison: {elapsed:.3f}s", flush=True)
        runs.append({
            "iteration": iteration,
            "seconds": elapsed,
            "output": str(output),
            "output_bytes": output.stat().st_size,
            "typed_outcome": _typed_outcome(result),
            "package": _package_manifest(output),
        })

    seconds = [item["seconds"] for item in runs]
    payload = {
        "schema_version": 1,
        "report": args.report,
        "tsmis_dir": str(tsmis_dir),
        "tsn": str(tsn_path),
        "consolidated": str(consolidated),
        "consolidation_seconds": consolidation_seconds,
        "fast_mode": bool(args.fast_mode),
        "comparison_seconds": {
            "minimum": min(seconds),
            "maximum": max(seconds),
            "mean": sum(seconds) / len(seconds),
        },
        "runs": runs,
    }
    result_json = work_dir / f"{args.tag}-{args.report}.benchmark.json"
    result_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["result_json"] = str(result_json)
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", choices=sorted(REPORTS), required=True)
    parser.add_argument("--tsmis-dir", type=Path, required=True)
    parser.add_argument("--tsn", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path,
                        default=ROOT / "tmp" / "vs-tsn-speed")
    parser.add_argument("--tag", default="benchmark")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--reconsolidate", action="store_true")
    parser.add_argument("--fast-mode", action="store_true")
    parser.add_argument("--product-log", action="store_true")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    if not args.tsmis_dir.is_dir():
        parser.error(f"TSMIS directory does not exist: {args.tsmis_dir}")
    if not args.tsn.is_file():
        parser.error(f"TSN workbook does not exist: {args.tsn}")
    return args


def main() -> int:
    payload = _run(_parse_args())
    compact = {
        "status": "ok",
        "report": payload["report"],
        "consolidation_seconds": payload["consolidation_seconds"],
        "comparison_seconds": payload["comparison_seconds"],
        "package_sha256": payload["runs"][-1]["package"]["sha256"],
        "result_json": payload["result_json"],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
