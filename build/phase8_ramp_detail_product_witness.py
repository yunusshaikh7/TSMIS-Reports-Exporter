#!/usr/bin/env python3
"""Run every production Ramp Detail triangle leg in an isolated destination.

This helper contains no oracle logic.  The independent Stage-8 driver supplies
private source captures, invokes this process only after deriving source truth,
and inspects every emitted workbook itself.  Keeping production imports in this
child prevents application schemas and normalizers from becoming truth inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


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
        "outputs": {flavor: _identity(path)
                    for flavor, path in outputs.items()},
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-root", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--tsn-raw", type=Path, required=True)
    parser.add_argument("--tsn-normalized", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.work_root.mkdir(parents=True, exist_ok=False)
    excel_consolidated = args.work_root / "ramp_detail_excel_consolidated.xlsx"
    pdf_consolidated = args.work_root / "ramp_detail_pdf_consolidated.xlsx"
    converted = args.work_root / "converted_pdf"

    sys.path.insert(0, str(SCRIPTS_ROOT))
    import consolidate_ramp_detail  # type: ignore
    import consolidate_tsmis_ramp_detail_pdf  # type: ignore
    import compare_ramp_detail_tsn  # type: ignore
    import compare_ramp_detail_pdf  # type: ignore

    events = QuietEvents()
    excel_result = consolidate_ramp_detail.consolidate(
        events=events, confirm_overwrite=lambda _path: True,
        input_dir=args.xlsx_root, out_path=excel_consolidated)
    if getattr(excel_result, "status", None) != "ok":
        raise RuntimeError(
            f"production Excel consolidation failed: {excel_result!r}")

    pdf_result = consolidate_tsmis_ramp_detail_pdf.consolidate(
        events=events, confirm_overwrite=lambda _path: True,
        input_dir=args.pdf_root, out_path=pdf_consolidated,
        converted_dir=converted)
    if getattr(pdf_result, "status", None) != "ok":
        raise RuntimeError(f"production PDF consolidation failed: {pdf_result!r}")

    comparisons = {
        "excel_vs_tsn_raw": _run_comparison(
            "excel_vs_tsn_raw", compare_ramp_detail_tsn,
            excel_consolidated, args.tsn_raw, args.work_root, events),
        "excel_vs_tsn_normalized": _run_comparison(
            "excel_vs_tsn_normalized", compare_ramp_detail_tsn,
            excel_consolidated, args.tsn_normalized, args.work_root, events),
        "pdf_vs_tsn_raw": _run_comparison(
            "pdf_vs_tsn_raw", compare_ramp_detail_pdf.TSMIS_PDF_VS_TSN,
            pdf_consolidated, args.tsn_raw, args.work_root, events),
        "pdf_vs_tsn_normalized": _run_comparison(
            "pdf_vs_tsn_normalized",
            compare_ramp_detail_pdf.TSMIS_PDF_VS_TSN,
            pdf_consolidated, args.tsn_normalized, args.work_root, events),
        "pdf_vs_excel": _run_comparison(
            "pdf_vs_excel", compare_ramp_detail_pdf.TSMIS_PDF_VS_EXCEL,
            pdf_consolidated, excel_consolidated, args.work_root, events),
    }

    payload = {
        "consolidations": {
            "excel": _consolidation_summary(
                excel_result, excel_consolidated),
            "pdf": _consolidation_summary(pdf_result, pdf_consolidated),
        },
        "comparisons": comparisons,
        "loaded_product_code": _loaded_product_manifest(),
    }
    encoded = (json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode("utf-8")
    sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
