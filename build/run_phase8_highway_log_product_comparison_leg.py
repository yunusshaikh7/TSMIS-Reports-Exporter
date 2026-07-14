#!/usr/bin/env python3
"""Run one isolated current-product Highway Log Stage-8 comparison leg.

Audit-only program.  It does not alter product code.  Each invocation binds the
accepted source/normalization chain, runs exactly one production comparison in
``both`` mode, validates the committed workbook twins and their sidecars, and
publishes a canonical non-acceptance record for the later family gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zlib


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from events import Events  # noqa: E402
import compare_highway_log as highway_log  # noqa: E402
import compare_highway_log_pdf as highway_log_pdf  # noqa: E402


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_log_product_sources_r1"
EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
SOURCE_RESULT = SOURCE_ROOT / "result.json"
R7_ROOT = VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
TSN_INPUT = (
    R7_ROOT / "highway_log" / "consolidated"
    / "tsn_highway_log_consolidated.xlsx"
)
TSN_SIDECAR = Path(str(TSN_INPUT) + ".outcome.json")
STAGE6_ROOT = VISUAL_ROOT / "phase6_tsn_conservation"
STAGE6_RESULT = STAGE6_ROOT / "highway_log_conservation_r1.json"
STAGE6_ACCEPTANCE = STAGE6_ROOT / "highway_log_conservation_r1.json.acceptance.json"

LEG_CHOICES = ("excel_vs_tsn", "pdf_vs_tsn")
PAYLOAD_RE = re.compile(
    r"\.cmpv3-[0-9a-f]{64}-[0-9]{6}-[0-9a-f]{64}"
    r"(?:-f-(?:0[0-7]|[0-9a-f]{64}-[0-9a-f]{16}))?"
    r"\.comparison-payload\.zlib"
)
INPUT_BINDINGS = {
    "excel": (
        EXCEL_INPUT,
        5_735_685,
        "329ccf68caf0c476d9360cb69dd28c0ab78a588d0e9bd9c816d5b484444fd660",
    ),
    "pdf": (
        PDF_INPUT,
        5_684_466,
        "17c04bb7400eded5c7b372d4ca87728735f8481fd37394c592e7dd0180f0333d",
    ),
    "tsn": (
        TSN_INPUT,
        6_663_062,
        "fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa",
    ),
    "tsn_sidecar": (
        TSN_SIDECAR,
        2_521,
        "6a746ce16773724954391894cbfb61dfccdb30c6c763750644deed081c533b1e",
    ),
    "source_result": (
        SOURCE_RESULT,
        239_655,
        "4fc4009c5b3be05b0be3d90cab5823e8397d34d623543a6215a03a238c27b8a1",
    ),
    "stage6_result": (
        STAGE6_RESULT,
        10_879_397,
        "f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4",
    ),
    "stage6_acceptance": (
        STAGE6_ACCEPTANCE,
        6_502,
        "012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61",
    ),
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
    stat = path.stat()
    if not path.is_file() or path.is_symlink():
        raise WitnessError(f"not an ordinary file: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": stat.st_size,
        "sha256": _sha(path),
    }


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _read_json(path: Path, *, require_compact_canonical: bool = False) -> dict[str, object]:
    payload = path.read_bytes()
    try:
        document = json.loads(payload)
    except Exception as exc:
        raise WitnessError(f"invalid JSON {path.name}: {exc}") from exc
    if not isinstance(document, dict):
        raise WitnessError(f"JSON root is not an object: {path}")
    if require_compact_canonical and payload not in {
        _canonical_bytes(document), _json_bytes(document),
    }:
        raise WitnessError(f"non-canonical compact JSON: {path}")
    return document


def _bind_inputs() -> dict[str, dict[str, object]]:
    observed: dict[str, dict[str, object]] = {}
    for label, (path, size, digest) in INPUT_BINDINGS.items():
        identity = _identity(path)
        if (identity["bytes"], identity["sha256"]) != (size, digest):
            raise WitnessError(f"{label} identity drift: {identity}")
        observed[label] = identity
    return observed


def _validate_chain() -> dict[str, object]:
    source = _read_json(SOURCE_RESULT, require_compact_canonical=True)
    if not all(source.get("invariants", {}).values()):
        raise WitnessError("source witness invariants are not terminally true")
    if source.get("excel", {}).get("output", {}).get("sha256") != INPUT_BINDINGS[
        "excel"
    ][2]:
        raise WitnessError("source witness Excel output binding drift")
    if source.get("pdf", {}).get("output", {}).get("sha256") != INPUT_BINDINGS[
        "pdf"
    ][2]:
        raise WitnessError("source witness PDF output binding drift")

    stage6 = _read_json(STAGE6_RESULT)
    if not (
        stage6.get("accepted") is True
        and stage6.get("stage6_family_audit_complete") is True
        and stage6.get("terminal_status") == "accepted"
        and not stage6.get("failed_invariants")
        and stage6.get("unexplained_projection_residue_count") == 0
        and stage6.get("normalized_full_conservation") is False
    ):
        raise WitnessError("Stage-6 Highway Log chain is not in its accepted red state")
    acceptance = _read_json(STAGE6_ACCEPTANCE)
    required_flags = acceptance.get("required_result_flags", {})
    if not (
        acceptance.get("decision") == "accepted_stage6_family_audit"
        and required_flags.get("accepted") is True
        and required_flags.get("stage6_family_audit_complete") is True
        and required_flags.get("terminal_status") == "accepted"
        and required_flags.get("unexplained_projection_residue_count") == 0
    ):
        raise WitnessError("Stage-6 detached acceptance is not terminally accepted")
    sidecar = _read_json(TSN_SIDECAR)
    if not (
        sidecar.get("completion") == "complete"
        and sidecar.get("skipped_inputs") == 0
        and sidecar.get("failed_inputs") == 0
    ):
        raise WitnessError("r7 Highway Log normalized sidecar is not complete")
    return {
        "source_witness": {
            "invariants": dict(source["invariants"]),
            "excel_output": dict(source["excel"]["output"]),
            "pdf_output": dict(source["pdf"]["output"]),
        },
        "stage6": {
            "accepted": stage6["accepted"],
            "terminal_status": stage6["terminal_status"],
            "projection_exact": stage6["projection_exact"],
            "normalized_full_conservation": stage6["normalized_full_conservation"],
            "product_findings": list(stage6["findings"]["product"]),
        },
        "stage6_acceptance": {
            "decision": acceptance["decision"],
            "required_result_flags": dict(required_flags),
        },
        "tsn_sidecar": {
            "completion": sidecar["completion"],
            "skipped_inputs": sidecar["skipped_inputs"],
            "failed_inputs": sidecar["failed_inputs"],
        },
    }


def _result_summary(result: object) -> dict[str, object]:
    comparison = getattr(result, "comparison_outcome", None)
    counts = getattr(comparison, "counts", None)
    generation = getattr(result, "artifact_generation", None)
    if counts is None or generation is None:
        raise WitnessError("product comparison omitted typed outcome metadata")
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
    generation_payload = {
        "generation_id": generation.generation_id,
        "completion": generation.completion,
        "publication_state": generation.publication_state,
        "requested_mode": generation.requested_mode,
        "members": [dict(member) for member in generation.members],
        "content_digests": dict(generation.content_digests),
        "producer_versions": dict(generation.producer_versions),
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
    if (
        payload["status"],
        payload["completion"],
        payload["skipped_inputs"],
        payload["failed_inputs"],
        generation_payload["publication_state"],
        generation_payload["requested_mode"],
    ) != ("ok", "complete", 0, 0, "committed", "both"):
        raise WitnessError(f"comparison is not a committed complete twin: {payload}")
    if payload["pairing_quality"] != "exact" or not count_payload["known"]:
        raise WitnessError("comparison did not publish exact known counts")
    return payload


def _inflate_payload(
    manifest: dict[str, object], root: Path,
) -> tuple[dict[str, object], list[dict[str, object]], set[Path]]:
    if set(manifest) != {
        "schema_version", "encoding", "decoded_size", "decoded_sha256",
        "binding_sha256", "chunks",
    } or (manifest.get("schema_version"), manifest.get("encoding")) != (
        1, "canonical-json-zlib-chunks-v1",
    ):
        raise WitnessError("comparison payload manifest schema drift")
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise WitnessError("comparison payload chunk manifest is empty")
    decoded_parts: list[bytes] = []
    details = []
    referenced: set[Path] = set()
    for ordinal, descriptor in enumerate(chunks):
        if not isinstance(descriptor, dict) or set(descriptor) != {
            "decoded_size", "relative_path", "sha256", "size",
        }:
            raise WitnessError("comparison payload descriptor shape drift")
        relative = descriptor["relative_path"]
        if (
            not isinstance(relative, str)
            or PAYLOAD_RE.fullmatch(relative) is None
            or Path(relative).name != relative
        ):
            raise WitnessError(f"unsafe comparison payload path: {relative!r}")
        path = (root / relative).resolve()
        if path.parent != root.resolve() or path in referenced:
            raise WitnessError("comparison payload path escapes or repeats")
        referenced.add(path)
        identity = _identity(path)
        if (identity["bytes"], identity["sha256"]) != (
            descriptor["size"], descriptor["sha256"],
        ):
            raise WitnessError("comparison payload chunk identity drift")
        if int(identity["bytes"]) > 67_108_864:
            raise WitnessError("comparison payload chunk exceeds audit bound")
        raw = path.read_bytes()
        inflater = zlib.decompressobj()
        try:
            decoded = inflater.decompress(raw) + inflater.flush()
        except zlib.error as exc:
            raise WitnessError(f"comparison payload cannot inflate: {exc}") from exc
        if (
            not inflater.eof
            or inflater.unused_data
            or inflater.unconsumed_tail
            or len(decoded) != descriptor["decoded_size"]
        ):
            raise WitnessError("comparison payload framing drift")
        decoded_parts.append(decoded)
        details.append(
            {
                "ordinal": ordinal,
                "path": str(path),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "decoded_bytes": len(decoded),
            }
        )
    decoded = b"".join(decoded_parts)
    if (
        len(decoded) != manifest["decoded_size"]
        or hashlib.sha256(decoded).hexdigest() != manifest["decoded_sha256"]
        or len(decoded) > 67_108_864
    ):
        raise WitnessError("comparison payload aggregate identity drift")
    try:
        persisted = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise WitnessError(f"comparison payload JSON drift: {exc}") from exc
    if not isinstance(persisted, dict) or _canonical_bytes(persisted) != decoded:
        raise WitnessError("comparison payload is not canonical JSON")
    return persisted, details, referenced


def _validate_outputs(
    root: Path, summary: dict[str, object],
) -> dict[str, object]:
    generation = summary["artifact_generation"]
    paths = {
        "formulas": root / "comparison.xlsx",
        "values": root / "comparison (values).xlsx",
    }
    sidecars = {
        flavor: Path(str(path) + ".outcome.json") for flavor, path in paths.items()
    }
    output_identities = {label: _identity(path) for label, path in paths.items()}
    sidecar_identities = {label: _identity(path) for label, path in sidecars.items()}

    members = {member["flavor"]: member for member in generation["members"]}
    if set(members) != {"formulas", "values"}:
        raise WitnessError(f"unexpected generation members: {members}")
    for flavor, identity in output_identities.items():
        member = members[flavor]
        if (member["size"], member["sha256"]) != (
            identity["bytes"],
            identity["sha256"],
        ):
            raise WitnessError(f"{flavor} generation identity drift")

    sidecar_documents = {}
    full_sidecars = {}
    for flavor, path in sidecars.items():
        document = _read_json(path, require_compact_canonical=True)
        if not (
            document.get("record_type") == "comparison"
            and document.get("comparison_schema_version") == 3
            and document.get("completion") == "complete"
            and document.get("skipped_inputs") == 0
            and document.get("failed_inputs") == 0
            and document.get("artifact_generation", {}).get("publication_state")
            == "committed"
            and document.get("self_member", {}).get("sha256")
            == output_identities[flavor]["sha256"]
        ):
            raise WitnessError(f"{flavor} outcome sidecar contract failed")
        if document["artifact_generation"] != generation:
            raise WitnessError(f"{flavor} sidecar/product generation drift")
        sidecar_documents[flavor] = {
            "record_type": document["record_type"],
            "comparison_schema_version": document["comparison_schema_version"],
            "completion": document["completion"],
            "self_member": document["self_member"],
            "artifact_generation": document["artifact_generation"],
            "comparison_payload": document["comparison_payload"],
        }
        full_sidecars[flavor] = document

    if (
        full_sidecars["formulas"]["artifact_generation"]
        != full_sidecars["values"]["artifact_generation"]
        or full_sidecars["formulas"]["comparison_payload"]
        != full_sidecars["values"]["comparison_payload"]
    ):
        raise WitnessError("formula/value sidecar generation or payload diverges")
    payload_manifest = full_sidecars["formulas"]["comparison_payload"]
    persisted, payload_chunks, referenced = _inflate_payload(payload_manifest, root)
    binding = hashlib.sha256(
        _canonical_bytes(
            {
                "decoded_sha256": payload_manifest["decoded_sha256"],
                "completion": "complete",
                "skipped_inputs": 0,
                "failed_inputs": 0,
                "artifact_generation": generation,
            }
        )
    ).hexdigest()
    if payload_manifest["binding_sha256"] != binding:
        raise WitnessError("comparison payload/generation binding drift")
    if not (
        persisted.get("status") == "ok"
        and persisted.get("completion") == "complete"
        and persisted.get("pairing_quality") == "exact"
        and persisted.get("counts") == summary["counts"]
        and persisted.get("warnings") == []
        and persisted.get("failures") == []
        and persisted.get("capped_group_diagnostics") == []
    ):
        raise WitnessError("decoded comparison payload disagrees with typed result")

    return {
        "workbooks": output_identities,
        "sidecars": sidecar_identities,
        "sidecar_contracts": sidecar_documents,
        "decoded_comparison_payload": {
            "identity": {
                "bytes": payload_manifest["decoded_size"],
                "sha256": payload_manifest["decoded_sha256"],
                "binding_sha256": payload_manifest["binding_sha256"],
            },
            "chunks": payload_chunks,
            "terminal": {
                "status": persisted["status"],
                "completion": persisted["completion"],
                "verdict": persisted["verdict"],
                "pairing_quality": persisted["pairing_quality"],
                "counts": persisted["counts"],
                "pairing_trace_count": len(persisted["pairing_trace"]),
                "duplicate_group_count": persisted["duplicate_group_count"],
            },
        },
        "referenced_payload_paths": sorted(str(path) for path in referenced),
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
        entries.append(
            {
                "module": name,
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    return {
        "files": len(entries),
        "canonical_json_sha256": hashlib.sha256(_json_bytes(entries)).hexdigest(),
        "members": entries,
    }


def _product_universe(root: Path, referenced_payload_paths: list[str]) -> dict[str, object]:
    entries = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            raise WitnessError(f"unexpected non-ordinary product member: {path}")
        entries.append(
            {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha(path)}
        )
    required = {
        "comparison.xlsx",
        "comparison (values).xlsx",
        "comparison.xlsx.outcome.json",
        "comparison (values).xlsx.outcome.json",
        ".tsmis-comparison-publication.lock",
    }
    expected = required | {Path(path).name for path in referenced_payload_paths}
    observed = {entry["name"] for entry in entries}
    if observed != expected:
        raise WitnessError(
            f"product publication universe drift: expected={sorted(expected)!r}, "
            f"observed={sorted(observed)!r}"
        )
    if any(
        ".tmp-" in entry["name"].casefold()
        or entry["name"].casefold().endswith((".tmp", ".partial", ".staging"))
        or entry["name"].casefold().startswith(".cmpv3-payload.tmp-")
        or entry["name"].casefold().startswith(".cmpmeta.tmp-")
        for entry in entries
    ):
        raise WitnessError("product publication left transient residue")
    return {
        "files": len(entries),
        "bytes": sum(int(entry["bytes"]) for entry in entries),
        "canonical_json_sha256": hashlib.sha256(_json_bytes(entries)).hexdigest(),
        "members": entries,
    }


def _select_leg(leg: str):
    if leg == "excel_vs_tsn":
        return highway_log.compare, EXCEL_INPUT, TSN_INPUT
    if leg == "pdf_vs_tsn":
        return highway_log_pdf.TSMIS_PDF_VS_TSN.compare, PDF_INPUT, TSN_INPUT
    raise WitnessError(f"invalid leg: {leg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", required=True, choices=LEG_CHOICES)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    output_root = args.output_root.resolve()
    if (
        output_root.parent != VISUAL_ROOT.resolve()
        or not output_root.name.startswith("phase8_highway_log_product_")
    ):
        raise WitnessError(
            "output root must be a direct, named Stage-8 Highway Log audit child"
        )
    if output_root.exists():
        raise WitnessError(f"output root already exists: {output_root}")

    inputs_before = _bind_inputs()
    chain = _validate_chain()
    compare, side_a, side_b = _select_leg(args.leg)
    output_root.mkdir(parents=True, exist_ok=False)
    logs: list[str] = []
    result = compare(
        side_a,
        side_b,
        output_root / "comparison.xlsx",
        events=Events(on_log=logs.append),
        confirm_overwrite=lambda _path: False,
        mode="both",
    )
    summary = _result_summary(result)
    outputs = _validate_outputs(output_root, summary)
    inputs_after = _bind_inputs()
    if inputs_after != inputs_before:
        raise WitnessError("bound input changed across comparison")
    product_universe = _product_universe(
        output_root, outputs["referenced_payload_paths"]
    )

    document = {
        "schema_version": 1,
        "audit": "Stage 8 Highway Log isolated current-product comparison leg",
        "leg": args.leg,
        "terminal_status": "completed_leg_not_family_acceptance",
        "inputs": inputs_before,
        "inputs_after": inputs_after,
        "accepted_chain": chain,
        "product_result": summary,
        "outputs": outputs,
        "product_universe_before_result": product_universe,
        "loaded_product_code": _loaded_product_manifest(),
        "log_lines": len(logs),
        "log_sha256": hashlib.sha256(_json_bytes(logs)).hexdigest(),
        "known_product_findings": [
            "CMP-AUD-045",
            "CMP-AUD-047",
            "CMP-AUD-048",
            "CMP-AUD-049",
            "CMP-AUD-050",
            "CMP-AUD-066",
            "CMP-AUD-067",
            "CMP-AUD-157",
        ],
        "stage8_family_accepted": False,
        "comparison_end_to_end_perfect": False,
        "evidence_end_to_end_exact": False,
        "product_code_changed_by_runner": False,
    }
    result_path = output_root / "result.json"
    result_path.write_bytes(_json_bytes(document))
    print(
        f"PASS Highway Log {args.leg}: "
        f"paired={summary['counts']['paired_rows']:,}; "
        f"A-only={summary['counts']['side_a_only_rows']:,}; "
        f"TSN-only={summary['counts']['side_b_only_rows']:,}; "
        f"differing rows={summary['counts']['differing_rows']:,}; "
        f"differing cells={summary['counts']['differing_cells']:,}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WitnessError as exc:
        print(f"FAIL Highway Log product comparison leg: {exc}")
        raise SystemExit(1)
