#!/usr/bin/env python3
"""Run the production Ramp Summary pipeline in an isolated destination.

This helper deliberately contains no oracle logic.  The independent Stage-8
driver invokes it in a child process only after deriving source truth, then
parses the emitted workbooks itself.  Keeping the product imports here prevents
production parser/schema objects from becoming accidental oracle dependencies.
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
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
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
        "warnings": list(getattr(comparison, "warnings", ()) or ()) if comparison else [],
        "failures": list(getattr(comparison, "failures", ()) or ()) if comparison else [],
        "artifact_generation": generation_payload,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--tsn-xlsx", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.work_root.mkdir(parents=True, exist_ok=True)
    consolidated = args.work_root / "ramp_summary_consolidated.xlsx"
    comparison = args.work_root / "ramp_summary_comparison.xlsx"
    for path in (
        consolidated,
        comparison,
        comparison.with_name(f"{comparison.stem} (values){comparison.suffix}"),
    ):
        if path.exists():
            path.unlink()

    sys.path.insert(0, str(SCRIPTS_ROOT))
    import consolidate_ramp_summary  # type: ignore
    import compare_ramp_summary_tsn  # type: ignore

    events = QuietEvents()
    consolidation = consolidate_ramp_summary.consolidate(
        events=events,
        confirm_overwrite=lambda _path: True,
        input_dir=args.pdf_root,
        out_path=consolidated,
    )
    if consolidation.status != "ok":
        raise RuntimeError(f"production consolidation failed: {consolidation!r}")

    compared = compare_ramp_summary_tsn.compare(
        consolidated,
        args.tsn_xlsx,
        comparison,
        events=events,
        confirm_overwrite=lambda _path: True,
        mode="both",
    )
    if compared.status != "ok":
        raise RuntimeError(f"production comparison failed: {compared!r}")

    values = comparison.with_name(f"{comparison.stem} (values){comparison.suffix}")
    payload = {
        "consolidation": {
            "status": consolidation.status,
            "completion": consolidation.completion,
            "skipped_inputs": consolidation.skipped_inputs,
            "failed_inputs": consolidation.failed_inputs,
            "summary_lines": list(consolidation.summary_lines),
            "path": str(consolidated),
            "bytes": consolidated.stat().st_size,
            "sha256": _sha(consolidated),
        },
        "comparison": _result_summary(compared),
        "outputs": {
            "consolidated": str(consolidated),
            "formulas": str(comparison),
            "values": str(values),
        },
        "loaded_product_code": _loaded_product_manifest(),
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
