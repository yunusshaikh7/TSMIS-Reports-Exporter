#!/usr/bin/env python3
"""Build a non-acceptance TSN row cache for Highway Sequence Stage-8 analysis.

The cache accelerates identity-policy development.  Final acceptance reparses the
immutable PDFs and never treats this cache as evidence.  Raw parsing is delegated
to the already accepted independent Stage-6 conservation oracle, not to product
normalization code.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys


BUILD_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_ROOT))

import phase6_highway_sequence_conservation as stage6  # noqa: E402
from phase3_xlsx_stream import (  # noqa: E402
    ColumnSpec, SheetSpec, XlsxLimits, capture_file_identity, read_sheet,
)


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
PRIVATE_TSN = (
    VISUAL_ROOT / "phase8_highway_sequence_private_sources_r1"
    / "authoritative_tsn_pdf"
)
STAGE6_RESULT = (
    VISUAL_ROOT / "phase6_tsn_conservation"
    / "highway_sequence_conservation_r7.json"
)
STAGE6_ACCEPTANCE = Path(str(STAGE6_RESULT) + ".acceptance.json")
NORMALIZED = (
    VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
    / "highway_sequence" / "consolidated"
    / "tsn_highway_sequence_normalized.xlsx"
)
DEFAULT_OUTPUT = VISUAL_ROOT / "phase8_highway_sequence_tsn_rows_draft_r1.json"

FILE_BINDINGS = {
    "stage6_result": {
        "path": STAGE6_RESULT, "bytes": 1_276_684,
        "sha256": "bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2",
    },
    "stage6_acceptance": {
        "path": STAGE6_ACCEPTANCE, "bytes": 5_934,
        "sha256": "71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2",
    },
    "normalized": {
        "path": NORMALIZED, "bytes": 2_536_901,
        "sha256": "9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041",
    },
}


class CacheError(RuntimeError):
    pass


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _bind_file(label: str) -> dict[str, object]:
    spec = FILE_BINDINGS[label]
    identity = capture_file_identity(Path(spec["path"]))
    if identity.size != spec["bytes"] or identity.sha256 != spec["sha256"]:
        raise CacheError(f"{label} identity drift: {identity}")
    return asdict(identity)


def main() -> int:
    bindings = {label: _bind_file(label) for label in FILE_BINDINGS}
    raw_records = []
    documents = []
    raw_members = []
    for name, size, digest in stage6.RAW_BINDINGS:
        path = PRIVATE_TSN / name
        payload = path.read_bytes()
        if len(payload) != size or _sha(payload) != digest:
            raise CacheError(f"private TSN identity drift: {name}")
        records, document = stage6._parse_document(name, payload)
        raw_records.extend(records)
        documents.append(document)
        raw_members.append({"name": name, "bytes": size, "sha256": digest})
    raw_records = stage6._sorted_source(raw_records)
    if len(raw_records) != stage6.EXPECTED["source_records"]:
        raise CacheError(f"raw record count drift: {len(raw_records)}")

    normalized_spec = SheetSpec(
        stage6.SHEET_NAME,
        tuple(ColumnSpec(header) for header in stage6.HEADERS),
        exact_schema=True,
    )
    normalized = read_sheet(
        NORMALIZED, normalized_spec,
        limits=XlsxLimits(max_source_bytes=32 * 1024 * 1024),
    )
    if len(normalized.rows) != stage6.EXPECTED["projected_rows"]:
        raise CacheError(f"normalized row count drift: {len(normalized.rows)}")

    result = {
        "audit": "Highway Sequence TSN development row cache",
        "not_an_acceptance_artifact": True,
        "bindings": bindings,
        "raw_members": raw_members,
        "raw_records": raw_records,
        "raw_documents": documents,
        "normalized": {
            "headers": list(stage6.HEADERS),
            "rows": [
                {"source_row": row.source_row, "values": row.values}
                for row in normalized.rows
            ],
        },
        "invariants": {
            "raw_records_69804": len(raw_records) == 69_804,
            "raw_data_rows_68806": sum(row["kind"] == "data" for row in raw_records) == 68_806,
            "raw_equates_998": sum(row["kind"] == "equate" for row in raw_records) == 998,
            "raw_pre_county_equates_46": sum(
                row["kind"] == "equate" and row["county"] is None
                for row in raw_records
            ) == 46,
            "normalized_rows_69758": len(normalized.rows) == 69_758,
        },
    }
    if not all(result["invariants"].values()):
        raise CacheError(f"cache invariants failed: {result['invariants']}")
    DEFAULT_OUTPUT.write_bytes(_json(result))
    print(
        "PASS Highway Sequence TSN development cache: "
        f"{len(raw_records):,} raw records; {len(normalized.rows):,} normalized rows; "
        f"{DEFAULT_OUTPUT}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CacheError as exc:
        print(f"FAIL Highway Sequence TSN development cache: {exc}")
        raise SystemExit(1)
