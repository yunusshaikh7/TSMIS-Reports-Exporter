#!/usr/bin/env python3
"""Run the three current Highway Sequence production comparison legs in both modes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from events import Events  # noqa: E402
import compare_highway_sequence_tsn as hsl  # noqa: E402
import compare_highway_sequence_pdf as hsl_pdf  # noqa: E402


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_sequence_product_sources_r2"
EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
TSN_INPUT = (
    VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
    / "highway_sequence" / "consolidated"
    / "tsn_highway_sequence_normalized.xlsx"
)
OUTPUT_ROOT = VISUAL_ROOT / "phase8_highway_sequence_product_comparisons_r1"

INPUT_BINDINGS = {
    "excel": (EXCEL_INPUT, 2_424_212, "cf5905332db3d3eb5a49a87d603f6e36f209cad9a84173b381dace6600168b20"),
    "pdf": (PDF_INPUT, 2_371_547, "070afe51ea3bf84c9704d0a36a02702b65189941badab6374b03461db8ef6ccc"),
    "tsn": (TSN_INPUT, 2_536_901, "9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041"),
}


class WitnessError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(path: Path) -> dict[str, object]:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": _sha(path)}


def _json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _bind_inputs() -> dict[str, object]:
    result = {}
    for label, (path, size, digest) in INPUT_BINDINGS.items():
        observed = _identity(path)
        if observed["bytes"] != size or observed["sha256"] != digest:
            raise WitnessError(f"{label} input identity drift: {observed}")
        result[label] = observed
    return result


def _result_summary(result: object) -> dict[str, object]:
    comparison = getattr(result, "comparison_outcome", None)
    counts = getattr(comparison, "counts", None)
    if counts is None:
        raise WitnessError("product comparison returned no typed counts")
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
    if generation is None:
        raise WitnessError("product comparison returned no artifact generation")
    generation_payload = {
        "completion": generation.completion,
        "publication_state": generation.publication_state,
        "requested_mode": generation.requested_mode,
        "members": [
            {
                "flavor": member["flavor"], "commit_role": member["commit_role"],
                "path": member["path"], "bytes": member["size"],
                "sha256": member["sha256"],
            }
            for member in generation.members
        ],
    }
    payload = {
        "status": getattr(result, "status", None),
        "completion": getattr(result, "completion", None),
        "verdict": getattr(result, "verdict", None),
        "skipped_inputs": getattr(result, "skipped_inputs", None),
        "failed_inputs": getattr(result, "failed_inputs", None),
        "summary_lines": list(getattr(result, "summary_lines", ()) or ()),
        "counts": count_payload,
        "warnings": list(getattr(comparison, "warnings", ()) or ()),
        "failures": list(getattr(comparison, "failures", ()) or ()),
        "pairing_trace_count": len(getattr(comparison, "pairing_trace", ()) or ()),
        "pairing_quality": getattr(comparison, "pairing_quality", None),
        "artifact_generation": generation_payload,
    }
    if (payload["status"], payload["completion"], payload["skipped_inputs"],
            payload["failed_inputs"], generation_payload["publication_state"],
            generation_payload["requested_mode"]) != (
                "ok", "complete", 0, 0, "committed", "both"):
        raise WitnessError(f"product comparison is not a committed complete twin: {payload}")
    return payload


def _paths(base: Path) -> dict[str, Path]:
    return {
        "formulas": base,
        "values": base.with_name(f"{base.stem} (values){base.suffix}"),
    }


def _run(label: str, compare, side_a: Path, side_b: Path) -> dict[str, object]:
    logs: list[str] = []
    outputs = _paths(OUTPUT_ROOT / f"{label}.xlsx")
    result = compare(
        side_a, side_b, outputs["formulas"],
        events=Events(on_log=logs.append),
        confirm_overwrite=lambda _path: False, mode="both",
    )
    summary = _result_summary(result)
    for flavor, path in outputs.items():
        if not path.is_file():
            raise WitnessError(f"{label} omitted {flavor} workbook")
    return {
        "result": summary,
        "outputs": {flavor: _identity(path) for flavor, path in outputs.items()},
        "log_lines": len(logs), "log_sha256": hashlib.sha256(_json(logs)).hexdigest(),
        "logs": logs,
    }


def _tree_manifest(root: Path) -> dict[str, object]:
    entries = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(root).as_posix()):
        entries.append({
            "relative_path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size, "sha256": _sha(path),
        })
    wire = _json(entries)
    return {
        "files": len(entries), "bytes": sum(item["bytes"] for item in entries),
        "canonical_json_sha256": hashlib.sha256(wire).hexdigest(),
        "members": entries,
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
            "module": name, "relative_path": relative,
            "bytes": path.stat().st_size, "sha256": _sha(path),
        })
    return {
        "files": len(entries),
        "canonical_json_sha256": hashlib.sha256(_json(entries)).hexdigest(),
        "members": entries,
    }


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise WitnessError(f"comparison witness root already exists: {OUTPUT_ROOT}")
    inputs = _bind_inputs()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    legs = {
        "excel_vs_normalized_tsn": _run(
            "excel_vs_normalized_tsn", hsl.compare, EXCEL_INPUT, TSN_INPUT,
        ),
        "pdf_vs_normalized_tsn": _run(
            "pdf_vs_normalized_tsn", hsl_pdf.TSMIS_PDF_VS_TSN.compare,
            PDF_INPUT, TSN_INPUT,
        ),
        "pdf_vs_excel": _run(
            "pdf_vs_excel", hsl_pdf.TSMIS_PDF_VS_EXCEL.compare,
            PDF_INPUT, EXCEL_INPUT,
        ),
    }
    inputs_after = _bind_inputs()
    if inputs_after != inputs:
        raise WitnessError("comparison inputs changed across product run")
    artifact_manifest = _tree_manifest(OUTPUT_ROOT)
    result = {
        "audit": "Stage 8 Highway Sequence current product comparison witnesses",
        "inputs": inputs, "inputs_after": inputs_after,
        "loaded_product_code": _loaded_product_manifest(),
        "legs": legs, "artifact_manifest_before_result": artifact_manifest,
        "invariants": {
            "three_legs": len(legs) == 3,
            "six_workbooks": sum(len(leg["outputs"]) for leg in legs.values()) == 6,
            "all_complete": all(leg["result"]["completion"] == "complete" for leg in legs.values()),
            "all_pairing_exact": all(leg["result"]["pairing_quality"] == "exact" for leg in legs.values()),
        },
    }
    if not all(result["invariants"].values()):
        raise WitnessError(f"product comparison invariants failed: {result['invariants']}")
    result_path = OUTPUT_ROOT / "result.json"
    result_path.write_bytes(_json(result))
    print("PASS Highway Sequence product comparisons: " + "; ".join(
        f"{label}={leg['result']['counts']['paired_rows']}/"
        f"{leg['result']['counts']['differing_cells']}"
        for label, leg in legs.items()
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WitnessError as exc:
        print(f"FAIL Highway Sequence product comparisons: {exc}")
        raise SystemExit(1)
