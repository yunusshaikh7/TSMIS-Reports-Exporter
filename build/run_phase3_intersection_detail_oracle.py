"""Run the bound CORE-ID-78-XLSX-TSN independent oracle.

The runtime dependencies are the three stdlib-only Phase-3 evidence modules in
``build/``.  No production comparator, loader, sidecar, or prior workbook is an
input.  Evidence files may contain local source references and normalized data;
write them only to a local, non-repository evidence directory.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import phase3_independent_oracle as generic
import phase3_intersection_detail_oracle as report
import phase3_xlsx_stream as xlsx


EXPECTED_MANIFEST_SHA256 = (
    "9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6"
)
EXPECTED_MEMBERS = 218
EXPECTED_SOURCE_BYTES = 26_384_760


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def _write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _typed(value):
    if value is None:
        return {"type": "blank", "value": None}
    if type(value) is bool:
        return {"type": "boolean", "value": value}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": format(value, "f")}
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": repr(value)}
    return {"type": "text", "value": str(value)}


def _key(key) -> list[dict[str, str]]:
    return [{"kind": value.kind, "text": value.text} for value in key]


def _write_jsonl(path: Path, records) -> tuple[int, str]:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count, _sha256(path)


def _trace_records(outcome):
    for trace in outcome.pairing_trace:
        yield {
            "algorithm": trace.algorithm,
            "assignment_vector": list(trace.assignment_vector),
            "exact": trace.exact,
            "key": _key(trace.key),
            "matrix_cells": trace.matrix_cells,
            "quality": trace.quality,
            "side_a_size": trace.side_a_size,
            "side_b_size": trace.side_b_size,
            "smaller_side": trace.smaller_side,
            "source_pairs": [list(pair) for pair in trace.source_pairs],
            "total_cost": trace.total_cost,
        }


def _difference_records(outcome, side_a, side_b):
    a_by_index = {row.source_index: row for row in side_a.rows}
    b_by_index = {row.source_index: row for row in side_b.rows}
    fields = report.ORACLE_SCHEMA.field_rules
    for row in outcome.row_results:
        if not row.differing_fields:
            continue
        source_a = a_by_index[row.source_index_a]
        source_b = b_by_index[row.source_index_b]
        for rule, cell in zip(fields, row.cells):
            if not cell.counts_as_difference:
                continue
            yield {
                "field": rule.name,
                "key": _key(row.key),
                "normalized_a": {
                    "kind": cell.normalized_a.kind,
                    "text": cell.normalized_a.text,
                },
                "normalized_b": {
                    "kind": cell.normalized_b.kind,
                    "text": cell.normalized_b.text,
                },
                "raw_a": _typed(cell.raw_a),
                "raw_b": _typed(cell.raw_b),
                "source_a": source_a.source_ref,
                "source_b": source_b.source_ref,
                "source_index_a": row.source_index_a,
                "source_index_b": row.source_index_b,
            }


def _route_diagnostic_records(side_a):
    for diagnostic in side_a.route_diagnostics:
        yield {
            "derived_token": diagnostic.derived_token,
            "member_token": diagnostic.member_token,
            "source_ref": diagnostic.source_ref,
        }


def _source_manifest() -> dict[str, str]:
    here = Path(__file__).resolve()
    files = (
        here,
        Path(report.__file__).resolve(),
        Path(generic.__file__).resolve(),
        Path(xlsx.__file__).resolve(),
        here.with_name("check_phase3_intersection_detail_oracle.py"),
        here.with_name("check_phase3_independent_oracle.py"),
        here.with_name("check_phase3_xlsx_stream.py"),
    )
    return {path.name: _sha256(path) for path in files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    binding = report.capture_pre_binding(args.corpus_root)
    manifest = binding.pre_manifest
    if (manifest.sha256 != EXPECTED_MANIFEST_SHA256
            or len(manifest.records) != EXPECTED_MEMBERS
            or manifest.source_bytes != EXPECTED_SOURCE_BYTES):
        raise RuntimeError(
            "pre-run corpus binding disagrees with the approved input-bound identity: "
            f"members={len(manifest.records)}, bytes={manifest.source_bytes}, "
            f"sha256={manifest.sha256}")
    manifest_path = evidence / "CORE-ID-78-XLSX-TSN-manifest-v1.tsv"
    _write_bytes(manifest_path, manifest.serialized)

    selection = report.select_corpus(args.corpus_root)
    side_a = report.read_tsmis_workbooks(selection.tsmis_files)
    side_b = report.read_tsn_workbook(selection.tsn_file)
    outcome = report.compare_adapted(side_a, side_b)
    post = report.verify_post_binding(binding)

    trace_path = evidence / "CORE-ID-78-XLSX-TSN-pairing-trace.jsonl"
    trace_count, trace_sha = _write_jsonl(trace_path, _trace_records(outcome))
    diff_path = evidence / "CORE-ID-78-XLSX-TSN-differences.jsonl"
    diff_count, diff_sha = _write_jsonl(
        diff_path, _difference_records(outcome, side_a, side_b))
    route_path = evidence / "CORE-ID-78-XLSX-TSN-route-provenance.jsonl"
    route_count, route_sha = _write_jsonl(
        route_path, _route_diagnostic_records(side_a))

    counts = outcome.counts
    duplicate_traces = [trace for trace in outcome.pairing_trace
                        if trace.side_a_size > 1 or trace.side_b_size > 1]
    result = {
        "canary_id": report.CANARY_ID,
        "completion": outcome.completion,
        "counts": {
            "asserted_cells": counts.asserted_cells,
            "context_cells": counts.context_cells,
            "differing_cells": counts.differing_cells,
            "differing_rows": counts.differing_rows,
            "known": counts.known,
            "paired_rows": counts.paired_rows,
            "per_field_counts": dict(counts.per_field_counts),
            "side_a_only_rows": counts.side_a_only_rows,
            "side_b_only_rows": counts.side_b_only_rows,
        },
        "evidence": {
            "difference_records": diff_count,
            "differences_sha256": diff_sha,
            "pairing_trace_records": trace_count,
            "pairing_trace_sha256": trace_sha,
            "route_provenance_records": route_count,
            "route_provenance_sha256": route_sha,
        },
        "input_binding": {
            "manifest_members": len(manifest.records),
            "manifest_sha256": manifest.sha256,
            "manifest_source_bytes": manifest.source_bytes,
            "post_manifest_sha256": post.sha256,
        },
        "oracle_source_sha256": _source_manifest(),
        "pairing": {
            "capped_groups": len(outcome.capped_diagnostics),
            "duplicate_groups": len(duplicate_traces),
            "exact_duplicate_groups": sum(trace.exact for trace in duplicate_traces),
            "quality": outcome.pairing_quality,
        },
        "runtime": {
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "python": sys.version,
            "platform": platform.platform(),
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
        },
        "side_rows": {
            "tsmis": len(side_a.rows),
            "tsn": len(side_b.rows),
        },
        "verdict": outcome.verdict,
    }
    result_path = evidence / "CORE-ID-78-XLSX-TSN-oracle-result.json"
    _write_json(result_path, result)
    index = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in (manifest_path, trace_path, diff_path, route_path, result_path)
    }
    _write_json(evidence / "CORE-ID-78-XLSX-TSN-evidence-index.json", index)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
