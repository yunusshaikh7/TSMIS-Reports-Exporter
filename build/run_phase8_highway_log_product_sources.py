#!/usr/bin/env python3
"""Build isolated current-product Highway Log TSMIS source witnesses.

Audit-only program.  It consumes the frozen 7.9 per-route Excel/PDF copies,
invokes the shipping consolidators without changing their code, and publishes a
source-bound record beside the two consolidated workbooks.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from events import Events  # noqa: E402
import outcome  # noqa: E402
import consolidate_highway_log as excel_consolidator  # noqa: E402
import consolidate_tsmis_highway_log_pdf as pdf_consolidator  # noqa: E402


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
PRIVATE_ROOT = VISUAL_ROOT / "phase8_highway_log_private_sources_r1"
OUTPUT_ROOT = VISUAL_ROOT / "phase8_highway_log_product_sources_r1"
EXCEL_SOURCE = PRIVATE_ROOT / "current_tsmis_excel"
PDF_SOURCE = PRIVATE_ROOT / "current_tsmis_pdf"

SOURCE_BINDINGS = {
    "excel": (
        252,
        59_441_628,
        "f9cafb2958842550b2eeefd2117b061db45d8a02ace51428d5c97b68f8e9155e",
        ".xlsx",
    ),
    "pdf": (
        252,
        36_545_107,
        "26fec6f7fec944681c96d7970ae6ed5c2791f173379c1e74ce050f44484c9d15",
        ".pdf",
    ),
}


class WitnessError(RuntimeError):
    pass


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _manifest(root: Path, suffix: str) -> dict[str, object]:
    paths = sorted(root.glob(f"*{suffix}"), key=lambda path: path.name)
    entries = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha_file(path)}
        for path in paths
    ]
    wire = "".join(
        f"{item['name']}\t{item['bytes']}\t{item['sha256']}\n" for item in entries
    ).encode("utf-8")
    return {
        "files": len(entries),
        "bytes": sum(int(item["bytes"]) for item in entries),
        "manifest_sha256": _sha_bytes(wire),
        "members": entries,
    }


def _bind_source(label: str, root: Path) -> dict[str, object]:
    files, size, digest, suffix = SOURCE_BINDINGS[label]
    observed = _manifest(root, suffix)
    if (observed["files"], observed["bytes"], observed["manifest_sha256"]) != (
        files,
        size,
        digest,
    ):
        raise WitnessError(f"{label} source binding drift: {observed}")
    return observed


def _identity(path: Path) -> dict[str, object]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": _sha_file(path),
    }


def _result(result: object) -> dict[str, object]:
    serialized = asdict(result)
    if serialized.get("completion") != outcome.COMPLETE:
        raise WitnessError(f"product consolidation is not complete: {serialized}")
    if serialized.get("status") != "ok":
        raise WitnessError(f"product consolidation status is not ok: {serialized}")
    if serialized.get("skipped_inputs") or serialized.get("failed_inputs"):
        raise WitnessError(f"product consolidation omitted an input: {serialized}")
    return serialized


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise WitnessError(f"product witness root already exists: {OUTPUT_ROOT}")

    sources = {
        "excel": _bind_source("excel", EXCEL_SOURCE),
        "pdf": _bind_source("pdf", PDF_SOURCE),
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    excel_output = OUTPUT_ROOT / "current_tsmis_excel_consolidated.xlsx"
    pdf_output = OUTPUT_ROOT / "current_tsmis_pdf_consolidated.xlsx"
    converted = OUTPUT_ROOT / "pdf_converted_members"

    excel_logs: list[str] = []
    excel_result = excel_consolidator.consolidate(
        day=None,
        input_dir=EXCEL_SOURCE,
        out_path=excel_output,
        events=Events(on_log=excel_logs.append),
        confirm_overwrite=lambda _path: False,
    )
    excel_serialized = _result(excel_result)
    if not excel_output.is_file():
        raise WitnessError("Excel consolidation returned complete without output")

    pdf_logs: list[str] = []
    pdf_result = pdf_consolidator.consolidate(
        day=None,
        input_dir=PDF_SOURCE,
        out_path=pdf_output,
        converted_dir=converted,
        events=Events(on_log=pdf_logs.append),
        confirm_overwrite=lambda _path: False,
    )
    pdf_serialized = _result(pdf_result)
    if not pdf_output.is_file():
        raise WitnessError("PDF consolidation returned complete without output")
    converted_manifest = _manifest(converted, ".xlsx")
    if converted_manifest["files"] != 252:
        raise WitnessError(
            f"PDF converted-member count {converted_manifest['files']} != 252"
        )

    source_after = {
        "excel": _bind_source("excel", EXCEL_SOURCE),
        "pdf": _bind_source("pdf", PDF_SOURCE),
    }
    if source_after != sources:
        raise WitnessError("private source changed across product consolidation")

    product_code = {
        path.name: _identity(path)
        for path in (
            SCRIPTS / "consolidate_highway_log.py",
            SCRIPTS / "consolidate_xlsx_base.py",
            SCRIPTS / "consolidate_tsmis_highway_log_pdf.py",
            SCRIPTS / "highway_log_columns.py",
            SCRIPTS / "pdf_table_lib.py",
        )
    }
    result = {
        "audit": "Stage 8 Highway Log product consolidation witnesses",
        "sources": sources,
        "sources_after": source_after,
        "product_code": product_code,
        "excel": {
            "result": excel_serialized,
            "output": _identity(excel_output),
            "log_lines": len(excel_logs),
            "log_sha256": _sha_bytes(_json(excel_logs)),
            "logs": excel_logs,
        },
        "pdf": {
            "result": pdf_serialized,
            "output": _identity(pdf_output),
            "converted_members": converted_manifest,
            "log_lines": len(pdf_logs),
            "log_sha256": _sha_bytes(_json(pdf_logs)),
            "logs": pdf_logs,
        },
        "invariants": {
            "excel_complete": excel_serialized["completion"] == outcome.COMPLETE,
            "pdf_complete": pdf_serialized["completion"] == outcome.COMPLETE,
            "excel_output_present": excel_output.is_file(),
            "pdf_output_present": pdf_output.is_file(),
            "pdf_converted_members_252": converted_manifest["files"] == 252,
            "no_skipped_or_failed_inputs": all(
                item["result"][field] == 0
                for item in (
                    {"result": excel_serialized},
                    {"result": pdf_serialized},
                )
                for field in ("skipped_inputs", "failed_inputs")
            ),
        },
    }
    if not all(result["invariants"].values()):
        raise WitnessError(f"product witness invariants failed: {result['invariants']}")

    result_path = OUTPUT_ROOT / "result.json"
    result_path.write_bytes(_json(result))
    print(
        "PASS Highway Log product source witnesses: "
        f"Excel {excel_output.stat().st_size:,} bytes; "
        f"PDF {pdf_output.stat().st_size:,} bytes; result {result_path}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WitnessError as exc:
        print(f"FAIL Highway Log product source witnesses: {exc}")
        raise SystemExit(1)
