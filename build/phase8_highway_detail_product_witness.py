#!/usr/bin/env python3
"""Run every production Highway Detail triangle leg in isolation.

This helper deliberately contains no oracle logic. The independent Stage-8
driver supplies private source captures, invokes this process only after deriving
source truth, and inspects every emitted workbook itself. Keeping production
imports in this child prevents application schemas and normalizers from becoming
truth inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
import zlib


BUILD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BUILD_ROOT.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"


class QuietEvents:
    def on_log(self, _message: str) -> None:
        return None

    def is_cancelled(self) -> bool:
        return False


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha(path),
    }


def _loaded_product_manifest() -> dict[str, object]:
    entries = []
    root = SCRIPTS_ROOT.resolve()
    for name, module in sorted(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.suffix.lower() not in {".py", ".pyw"} or not path.is_file():
            continue
        entries.append({
            "module": name,
            "relative_path": relative,
            "bytes": path.stat().st_size,
            "sha256": _sha(path),
        })
    payload = json.dumps(
        entries, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "file_count": len(entries),
        "canonical_json_sha256": hashlib.sha256(payload).hexdigest(),
        "entries": entries,
    }


def _result_summary(result: object) -> dict[str, object]:
    comparison = getattr(result, "comparison_outcome", None)
    counts = getattr(comparison, "counts", None)
    count_payload = None
    if counts is not None:
        count_payload = {
            "known": counts.known,
            "paired_rows": counts.paired_rows,
            "side_a_only_rows": counts.side_a_only_rows,
            "side_b_only_rows": counts.side_b_only_rows,
            "differing_rows": counts.differing_rows,
            "differing_cells": counts.differing_cells,
            "asserted_cells": counts.asserted_cells,
            "context_cells": counts.context_cells,
            "per_field_counts": dict(counts.per_field_counts),
        }
    generation = getattr(result, "artifact_generation", None)
    generation_payload = None
    if generation is not None:
        generation_payload = {
            "completion": generation.completion,
            "publication_state": generation.publication_state,
            "requested_mode": generation.requested_mode,
            "members": [
                {
                    "flavor": member["flavor"],
                    "commit_role": member["commit_role"],
                    "path": member["path"],
                    "bytes": member["size"],
                    "sha256": member["sha256"],
                }
                for member in generation.members
            ],
        }
    return {
        "status": getattr(result, "status", None),
        "completion": getattr(result, "completion", None),
        "verdict": getattr(result, "verdict", None),
        "skipped_inputs": getattr(result, "skipped_inputs", None),
        "failed_inputs": getattr(result, "failed_inputs", None),
        "summary_lines": list(getattr(result, "summary_lines", ()) or ()),
        "counts": count_payload,
        "warnings": list(getattr(comparison, "warnings", ()) or ())
        if comparison else [],
        "failures": list(getattr(comparison, "failures", ()) or ())
        if comparison else [],
        "artifact_generation": generation_payload,
    }


def _consolidation_summary(result: object, path: Path) -> dict[str, object]:
    return {
        "status": getattr(result, "status", None),
        "completion": getattr(result, "completion", None),
        "skipped_inputs": getattr(result, "skipped_inputs", None),
        "failed_inputs": getattr(result, "failed_inputs", None),
        "summary_lines": list(getattr(result, "summary_lines", ()) or ()),
        "output": _identity(path),
    }


def _paths(base: Path) -> dict[str, Path]:
    return {
        "formulas": base,
        "values": base.with_name(f"{base.stem} (values){base.suffix}"),
    }


def _run_comparison(label: str, adapter: object, side_a: Path,
                    side_b: Path, work_root: Path,
                    events: QuietEvents) -> dict[str, object]:
    outputs = _paths(work_root / f"{label}.xlsx")
    result = adapter.compare(
        side_a, side_b, outputs["formulas"], events=events,
        confirm_overwrite=lambda _path: True, mode="both")
    if getattr(result, "status", None) != "ok":
        raise RuntimeError(f"production {label} comparison failed: {result!r}")
    for flavor, path in outputs.items():
        if not path.is_file():
            raise RuntimeError(f"production {label} omitted {flavor} workbook")
    return {
        "result": _result_summary(result),
        "outputs": {
            flavor: _identity(path) for flavor, path in outputs.items()
        },
    }


def _recover_comparison(label: str, work_root: Path) -> dict[str, object] | None:
    """Recover a fully committed twin from its durable publication records.

    The long statewide legs are intentionally resumable: a process timeout
    after one committed leg must not force that already verified 300+ MB twin
    to be regenerated.  Temporary files never qualify; both canonical members,
    their two outcome sidecars, every declared digest, and the compressed
    comparison payload must agree.
    """
    outputs = _paths(work_root / f"{label}.xlsx")
    if not all(path.is_file() and path.stat().st_size for path in outputs.values()):
        return None
    sidecars = {
        flavor: Path(str(path) + ".outcome.json")
        for flavor, path in outputs.items()}
    if not all(path.is_file() for path in sidecars.values()):
        return None
    records = {
        flavor: json.loads(path.read_text(encoding="utf-8"))
        for flavor, path in sidecars.items()}
    formula = records["formulas"]
    values = records["values"]
    generation = formula.get("artifact_generation")
    if (generation != values.get("artifact_generation")
            or not isinstance(generation, dict)
            or (generation.get("completion"),
                generation.get("publication_state"),
                generation.get("requested_mode"))
            != ("complete", "committed", "both")):
        return None
    members = generation.get("members")
    if not isinstance(members, list) or len(members) != 2:
        return None
    by_flavor = {
        str(member.get("flavor")): member for member in members
        if isinstance(member, dict)}
    if set(by_flavor) != {"formulas", "values"}:
        return None
    for flavor, path in outputs.items():
        identity = _identity(path)
        member = by_flavor[flavor]
        if (Path(str(member.get("path", ""))).resolve() != path.resolve()
                or member.get("size") != identity["bytes"]
                or member.get("sha256") != identity["sha256"]):
            return None
    payload_record = formula.get("comparison_payload")
    if payload_record != values.get("comparison_payload") or not isinstance(
            payload_record, dict):
        return None
    decoded_parts = []
    for chunk in payload_record.get("chunks", []):
        if not isinstance(chunk, dict):
            return None
        chunk_path = work_root / str(chunk.get("relative_path", ""))
        if (not chunk_path.is_file()
                or chunk_path.stat().st_size != chunk.get("size")
                or _sha(chunk_path) != chunk.get("sha256")):
            return None
        decoded_parts.append(zlib.decompress(chunk_path.read_bytes()))
    decoded = b"".join(decoded_parts)
    if (len(decoded) != payload_record.get("decoded_size")
            or hashlib.sha256(decoded).hexdigest()
            != payload_record.get("decoded_sha256")):
        return None
    comparison = json.loads(decoded)
    counts = comparison.get("counts")
    if not isinstance(counts, dict):
        return None
    result = {
        "status": comparison.get("status"),
        "completion": comparison.get("completion"),
        "verdict": comparison.get("verdict"),
        "skipped_inputs": formula.get("skipped_inputs"),
        "failed_inputs": formula.get("failed_inputs"),
        "summary_lines": [],
        "counts": counts,
        "warnings": comparison.get("warnings") or [],
        "failures": comparison.get("failures") or [],
        "artifact_generation": {
            "completion": generation.get("completion"),
            "publication_state": generation.get("publication_state"),
            "requested_mode": generation.get("requested_mode"),
            "members": [{
                "flavor": member["flavor"],
                "commit_role": member["commit_role"],
                "path": member["path"],
                "bytes": member["size"],
                "sha256": member["sha256"],
            } for member in members],
        },
    }
    if (result["status"], result["completion"],
            result["skipped_inputs"], result["failed_inputs"]) != (
                "ok", "complete", 0, 0):
        return None
    return {
        "result": result,
        "outputs": {flavor: _identity(path)
                    for flavor, path in outputs.items()},
        "resumed_from_committed_publication": True,
    }


def _write_payload(path: Path, payload: dict[str, object]) -> bytes:
    encoded = (json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return encoded


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-root", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--tsn-raw", type=Path, required=True)
    parser.add_argument("--tsn-normalized", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--leg", action="append", choices=(
            "excel_vs_tsn_raw", "excel_vs_tsn_normalized",
            "pdf_vs_tsn_raw", "pdf_vs_tsn_normalized", "pdf_vs_excel"),
        help="run only this missing leg; repeat to select several")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for label, path in (
            ("TSMIS Excel root", args.xlsx_root),
            ("TSMIS PDF root", args.pdf_root)):
        if not path.is_dir():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    for label, path in (
            ("raw TSN workbook", args.tsn_raw),
            ("normalized TSN workbook", args.tsn_normalized)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    args.work_root.mkdir(parents=True, exist_ok=args.resume)
    excel_consolidated = (
        args.work_root / "highway_detail_excel_consolidated.xlsx"
    )
    pdf_consolidated = (
        args.work_root / "highway_detail_pdf_consolidated.xlsx"
    )
    converted = args.work_root / "converted_pdf"

    sys.path.insert(0, str(SCRIPTS_ROOT))
    import consolidate_highway_detail  # type: ignore
    import consolidate_tsmis_highway_detail_pdf  # type: ignore
    import compare_highway_detail_tsn  # type: ignore
    import compare_highway_detail_pdf  # type: ignore

    events = QuietEvents()
    if args.resume:
        if not excel_consolidated.is_file() or not pdf_consolidated.is_file():
            raise RuntimeError(
                "resume requires both previously completed consolidations")
        consolidation_payload = {
            "excel": {
                "status": "ok", "completion": "complete",
                "skipped_inputs": 0, "failed_inputs": 0,
                "summary_lines": ["recovered after successful downstream use"],
                "output": _identity(excel_consolidated),
                "resumed": True,
            },
            "pdf": {
                "status": "ok", "completion": "complete",
                "skipped_inputs": 0, "failed_inputs": 0,
                "summary_lines": ["recovered after successful downstream use"],
                "output": _identity(pdf_consolidated),
                "resumed": True,
            },
        }
    else:
        excel_result = consolidate_highway_detail.consolidate(
            events=events, confirm_overwrite=lambda _path: True,
            input_dir=args.xlsx_root, out_path=excel_consolidated)
        if getattr(excel_result, "status", None) != "ok":
            raise RuntimeError(
                f"production Excel consolidation failed: {excel_result!r}")
        pdf_result = consolidate_tsmis_highway_detail_pdf.consolidate(
            events=events, confirm_overwrite=lambda _path: True,
            input_dir=args.pdf_root, out_path=pdf_consolidated,
            converted_dir=converted)
        if getattr(pdf_result, "status", None) != "ok":
            raise RuntimeError(
                f"production PDF consolidation failed: {pdf_result!r}")
        consolidation_payload = {
            "excel": _consolidation_summary(
                excel_result, excel_consolidated),
            "pdf": _consolidation_summary(pdf_result, pdf_consolidated),
        }

    leg_specs = {
        "excel_vs_tsn_raw": (
            compare_highway_detail_tsn, excel_consolidated, args.tsn_raw),
        "excel_vs_tsn_normalized": (
            compare_highway_detail_tsn, excel_consolidated,
            args.tsn_normalized),
        "pdf_vs_tsn_raw": (
            compare_highway_detail_pdf.TSMIS_PDF_VS_TSN,
            pdf_consolidated, args.tsn_raw),
        "pdf_vs_tsn_normalized": (
            compare_highway_detail_pdf.TSMIS_PDF_VS_TSN,
            pdf_consolidated, args.tsn_normalized),
        "pdf_vs_excel": (
            compare_highway_detail_pdf.TSMIS_PDF_VS_EXCEL,
            pdf_consolidated, excel_consolidated),
    }
    selected = set(args.leg or leg_specs)
    comparisons = {}
    for label, (adapter, side_a, side_b) in leg_specs.items():
        recovered = _recover_comparison(label, args.work_root)
        if recovered is not None:
            comparisons[label] = recovered
            continue
        if label not in selected:
            continue
        comparisons[label] = _run_comparison(
            label, adapter, side_a, side_b, args.work_root, events)
        partial = {
            "consolidations": consolidation_payload,
            "comparisons": comparisons,
            "loaded_product_code": _loaded_product_manifest(),
            "completion": "partial",
        }
        _write_payload(
            args.work_root / "product-witness-result.partial.json", partial)

    payload = {
        "consolidations": consolidation_payload,
        "comparisons": comparisons,
        "loaded_product_code": _loaded_product_manifest(),
        "completion": (
            "complete" if set(comparisons) == set(leg_specs) else "partial"),
    }
    complete = set(comparisons) == set(leg_specs)
    encoded = _write_payload(
        args.work_root / (
            "product-witness-result.json" if complete
            else "product-witness-result.partial.json"), payload)
    if complete:
        for stale in (
                args.work_root / "product-witness-result.partial.json",
                args.work_root / "product-witness-failure.json"):
            try:
                stale.unlink()
            except FileNotFoundError:
                pass
    sys.stdout.buffer.write(encoded)
    return 0 if complete or args.leg else 3


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        try:
            parsed = parse_args()
            parsed.work_root.mkdir(parents=True, exist_ok=True)
            failure = {
                "status": "failed", "type": type(exc).__name__,
                "message": str(exc), "traceback": traceback.format_exc(),
            }
            (parsed.work_root / "product-witness-failure.json").write_text(
                json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n")
        except Exception:
            pass
        raise
    raise SystemExit(exit_code)
