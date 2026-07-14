#!/usr/bin/env python3
"""Run one development Highway Sequence product leg against the raw-TSN twin.

This is deliberately not a source-acceptance oracle.  The bound TSN workbook is
a development twin built from the frozen Stage-8 row cache; final acceptance
must reparse the immutable TSN PDFs.  The runner exists to expose current product
behavior against all 69,804 raw records without weakening the proven one-leg
publication contract used by the normalized-TSN witnesses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable, Mapping
import zlib

import run_phase8_highway_sequence_product_comparison_leg as witness


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VISUAL_ROOT = witness.VISUAL_ROOT
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_sequence_product_sources_r2"
RAW_TWIN_ROOT = VISUAL_ROOT / "phase8_highway_sequence_raw_tsn_twin_dev_r2"

EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
RAW_TSN_INPUT = RAW_TWIN_ROOT / "highway_sequence_raw_tsn_audit_twin.xlsx"
RAW_TSN_PROVENANCE = (
    RAW_TWIN_ROOT / "highway_sequence_raw_tsn_audit_twin.provenance.json"
)
RAW_TSN_MANIFEST = RAW_TWIN_ROOT / "manifest.json"
RAW_TSN_RESULT = RAW_TWIN_ROOT / "result.json"

LEG_CHOICES = ("excel_vs_raw_tsn", "pdf_vs_raw_tsn")
EXPECTED_INPUTS = {
    "current_excel": (
        EXCEL_INPUT,
        2_424_212,
        "cf5905332db3d3eb5a49a87d603f6e36f209cad9a84173b381dace6600168b20",
    ),
    "current_pdf": (
        PDF_INPUT,
        2_371_547,
        "070afe51ea3bf84c9704d0a36a02702b65189941badab6374b03461db8ef6ccc",
    ),
    "raw_tsn_workbook": (
        RAW_TSN_INPUT,
        2_541_734,
        "d594e2441b81c4d4d81c11aa5bbf01418bcd2dcc0bedf3ee9a6221a66cb03fa1",
    ),
    "raw_tsn_provenance": (
        RAW_TSN_PROVENANCE,
        23_610_997,
        "f27c7724f9acc8988bfd65c896e8278853b70690ed36d0317fabf6c5af8920f2",
    ),
    "raw_tsn_manifest": (
        RAW_TSN_MANIFEST,
        6_464,
        "c534e818d4c1aacf7a72ff4a623a4c9c53d8b5d32cb4d3d8b0fc19958e567533",
    ),
    "raw_tsn_result": (
        RAW_TSN_RESULT,
        2_428,
        "51a0cfb70611442fc5b7ca4bb1acbb2779446b7d5400d10590d31c798629d1bc",
    ),
}
EXPECTED_COUNTS = {
    "raw_records": 69_804,
    "data_records": 68_806,
    "equate_records": 998,
    "pre_county_equates": 46,
    "projectable_records": 69_758,
    "pointer_P": 283,
    "pointer_arrow": 282,
    "pointer_total": 565,
}
EXPECTED_HEADERS = [
    "Route", "County", "PM", "City", "HG", "FT",
    "Distance To Next Point", "Description",
]
PRODUCT_MODULES = {
    "compare_highway_sequence_tsn",
    "compare_highway_sequence_pdf",
    "compare_core",
    "consolidation_meta",
}

RESULT_NAME = witness.RESULT_NAME
ARTIFACT_MANIFEST_NAME = witness.ARTIFACT_MANIFEST_NAME
PRODUCT_CODE_MANIFEST_NAME = witness.PRODUCT_CODE_MANIFEST_NAME


class RawWitnessError(witness.WitnessError):
    """The raw-twin binding or product witness contract failed."""


def _reject_constant(value: str) -> None:
    raise RawWitnessError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RawWitnessError(f"duplicate JSON object key is forbidden: {key!r}")
        result[key] = value
    return result


def _strict_json_bytes(raw: bytes, label: str) -> object:
    try:
        text = raw.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RawWitnessError(f"{label} is not strict UTF-8 JSON: {exc}") from exc


def _strict_json_file(path: Path, expected: Mapping[str, object]) -> object:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RawWitnessError(f"cannot read bound JSON input: {path}") from exc
    if (len(raw), hashlib.sha256(raw).hexdigest()) != (
        expected["bytes"], expected["sha256"]
    ):
        raise RawWitnessError(f"bound JSON changed before validation: {path}")
    return _strict_json_bytes(raw, path.name)


def _identity_bound_read(path: Path) -> tuple[bytes, dict[str, object]]:
    """Read one generated file while proving its identity stayed fixed."""
    before = witness._stable_identity(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RawWitnessError(f"cannot read generated artifact: {path}") from exc
    after = witness._stable_identity(path)
    if (
        before != after
        or len(raw) != before["bytes"]
        or hashlib.sha256(raw).hexdigest() != before["sha256"]
    ):
        raise RawWitnessError(f"generated artifact changed while read: {path}")
    return raw, before


def _bind_inputs() -> dict[str, dict[str, object]]:
    observed: dict[str, dict[str, object]] = {}
    for label, (path, expected_bytes, expected_sha) in EXPECTED_INPUTS.items():
        identity = witness._stable_identity(path)
        if (identity["bytes"], identity["sha256"]) != (
            expected_bytes, expected_sha
        ):
            raise RawWitnessError(f"{label} identity drift: {identity}")
        observed[label] = identity
    return observed


def _embedded_identity_matches(
    embedded: object,
    observed: Mapping[str, object],
) -> bool:
    if not isinstance(embedded, Mapping):
        return False
    raw_path = embedded.get("canonical_path", embedded.get("path"))
    try:
        embedded_path = Path(str(raw_path)).resolve(strict=True)
        observed_path = Path(str(observed["path"])).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return False
    size = embedded.get("bytes", embedded.get("size"))
    return (
        embedded_path == observed_path
        and size == observed["bytes"]
        and embedded.get("sha256") == observed["sha256"]
    )


def _validate_raw_twin(
    inputs: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Validate terminal/cache-derived status before any product import."""
    result = _strict_json_file(RAW_TSN_RESULT, inputs["raw_tsn_result"])
    manifest = _strict_json_file(RAW_TSN_MANIFEST, inputs["raw_tsn_manifest"])
    if not isinstance(result, Mapping) or not isinstance(manifest, Mapping):
        raise RawWitnessError("raw-twin result and manifest must be JSON objects")

    if (
        result.get("audit")
        != "Highway Sequence raw-TSN development twin builder"
        or result.get("status") != "PASS"
        or result.get("terminal") is not True
        or result.get("not_an_acceptance_artifact") is not True
        or result.get("inputs_unchanged") is not True
    ):
        raise RawWitnessError("raw-twin result is not terminal PASS/non-acceptance")
    reason = result.get("reason")
    if not isinstance(reason, str) or "Development-only" not in reason:
        raise RawWitnessError("raw-twin result lost its development-only warning")

    result_counts = result.get("counts")
    result_invariants = result.get("invariants")
    if result_counts != EXPECTED_COUNTS:
        raise RawWitnessError(f"raw-twin result count drift: {result_counts!r}")
    if (
        not isinstance(result_invariants, Mapping)
        or not result_invariants
        or any(value is not True for value in result_invariants.values())
        or result_invariants.get("raw_records_69804") is not True
        or result_invariants.get("xlsx_streamed_69805_physical_rows") is not True
        or result_invariants.get("xlsx_streamed_8_logical_columns") is not True
    ):
        raise RawWitnessError("raw-twin terminal invariants are not all exact/true")

    if (
        manifest.get("audit")
        != "Highway Sequence raw-TSN development twin manifest"
        or manifest.get("not_an_acceptance_artifact") is not True
        or manifest.get("inputs_unchanged") is not True
    ):
        raise RawWitnessError("raw-twin manifest lost its non-acceptance contract")
    cache_validation = manifest.get("cache_validation")
    reopen = manifest.get("workbook_reopen")
    if (
        not isinstance(cache_validation, Mapping)
        or cache_validation.get("counts") != EXPECTED_COUNTS
        or not isinstance(reopen, Mapping)
        or reopen.get("data_rows") != 69_804
        or reopen.get("streamed_physical_rows") != 69_805
        or reopen.get("streamed_logical_columns") != 8
        or reopen.get("headers") != EXPECTED_HEADERS
        or reopen.get("headers_exact") is not True
        or reopen.get("typed_rows_exact") is not True
        or reopen.get("blank_county_rows") != 46
    ):
        raise RawWitnessError("raw-twin manifest row/schema conservation drift")
    if (
        reopen.get("ordered_rows_sha256") != result.get("ordered_rows_sha256")
        or cache_validation.get("twin_rows_ordered_sha256")
        != result.get("ordered_rows_sha256")
    ):
        raise RawWitnessError("raw-twin ordered-row digests disagree")

    result_artifacts = result.get("artifacts")
    generated = manifest.get("generated")
    if not isinstance(result_artifacts, Mapping) or not isinstance(generated, Mapping):
        raise RawWitnessError("raw-twin embedded artifact identities are absent")
    identity_map = {
        "workbook": "raw_tsn_workbook",
        "provenance": "raw_tsn_provenance",
        "manifest": "raw_tsn_manifest",
    }
    for artifact, input_label in identity_map.items():
        if not _embedded_identity_matches(
            result_artifacts.get(artifact), inputs[input_label]
        ):
            raise RawWitnessError(
                f"raw-twin result {artifact} identity disagrees with bound bytes"
            )
        if artifact != "manifest" and not _embedded_identity_matches(
            generated.get(artifact), inputs[input_label]
        ):
            raise RawWitnessError(
                f"raw-twin manifest {artifact} identity disagrees with bound bytes"
            )

    return {
        "validated_before_product_import": True,
        "terminal_status": "PASS",
        "terminal": True,
        "not_an_acceptance_artifact": True,
        "reason": reason,
        "counts": dict(result_counts),
        "headers": list(reopen["headers"]),
        "ordered_rows_sha256": result["ordered_rows_sha256"],
        "identity_bound_artifacts": {
            label: dict(inputs[label])
            for label in (
                "raw_tsn_workbook", "raw_tsn_provenance",
                "raw_tsn_manifest", "raw_tsn_result",
            )
        },
    }


def _assert_product_not_loaded() -> None:
    loaded = sorted(PRODUCT_MODULES.intersection(sys.modules))
    if loaded:
        raise RawWitnessError(
            f"product modules loaded before raw-twin validation: {loaded!r}"
        )


def _load_product(
    leg: str,
) -> tuple[Callable[..., object], Path, Path, object, object]:
    sys.path.insert(0, str(SCRIPTS_ROOT))
    from events import Events  # type: ignore
    import consolidation_meta  # type: ignore
    import compare_highway_sequence_tsn as hsl  # type: ignore

    if leg == "excel_vs_raw_tsn":
        compare = hsl.compare
        side_a = EXCEL_INPUT
    elif leg == "pdf_vs_raw_tsn":
        import compare_highway_sequence_pdf as hsl_pdf  # type: ignore
        compare = hsl_pdf.TSMIS_PDF_VS_TSN.compare
        side_a = PDF_INPUT
    else:
        raise RawWitnessError(f"unsupported raw-TSN comparison leg: {leg}")
    return compare, side_a, RAW_TSN_INPUT, Events(), consolidation_meta


def _decode_payload_chunks(
    outputs: Mapping[str, Path],
    result: object,
    consolidation_meta: object,
) -> dict[str, object]:
    """Independently decode every v3 chunk and bind it to the typed outcome."""
    sidecar_payloads: dict[str, Mapping[str, object]] = {}
    for flavor, workbook in outputs.items():
        try:
            persisted = consolidation_meta.require_published_comparison(
                workbook, result
            )
        except (TypeError, ValueError, OSError) as exc:
            raise RawWitnessError(
                f"{flavor} payload could not be decoded by the product reader: {exc}"
            ) from exc
        if persisted.comparison_outcome != result.comparison_outcome:
            raise RawWitnessError(f"{flavor} decoded outcome disagrees with result")
        sidecar_path = Path(str(workbook) + ".outcome.json")
        raw, _sidecar_identity = _identity_bound_read(sidecar_path)
        parsed = _strict_json_bytes(raw, sidecar_path.name)
        if (
            not isinstance(parsed, Mapping)
            or parsed.get("comparison_schema_version") != 3
            or not isinstance(parsed.get("comparison_payload"), Mapping)
        ):
            raise RawWitnessError(f"{flavor} sidecar is not comparison schema v3")
        sidecar_payloads[flavor] = parsed["comparison_payload"]

    formulas_manifest = sidecar_payloads["formulas"]
    if sidecar_payloads["values"] != formulas_manifest:
        raise RawWitnessError("formula/value peers do not share one payload manifest")
    if (
        formulas_manifest.get("schema_version") != 1
        or formulas_manifest.get("encoding")
        != "canonical-json-zlib-chunks-v1"
    ):
        raise RawWitnessError("comparison payload manifest schema/encoding drift")
    chunks = formulas_manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise RawWitnessError("comparison payload manifest has no chunks")

    decoded_parts: list[bytes] = []
    chunk_records: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, descriptor in enumerate(chunks):
        if not isinstance(descriptor, Mapping):
            raise RawWitnessError(f"payload chunk {index} descriptor is not an object")
        relative = descriptor.get("relative_path")
        if (
            not isinstance(relative, str)
            or Path(relative).name != relative
            or relative in seen
            or witness.PAYLOAD_BASENAME_RE.fullmatch(relative) is None
        ):
            raise RawWitnessError(f"unsafe/noncanonical payload chunk name: {relative!r}")
        decoded_sha = formulas_manifest.get("decoded_sha256")
        if not relative.startswith(f".cmpv3-{decoded_sha}-{index:06d}-"):
            raise RawWitnessError(
                f"payload chunk {relative} does not encode manifest/index identity"
            )
        seen.add(relative)
        path = outputs["formulas"].parent / relative
        compressed, identity = _identity_bound_read(path)
        if (
            identity["bytes"] != descriptor.get("size")
            or identity["sha256"] != descriptor.get("sha256")
        ):
            raise RawWitnessError(f"payload chunk {relative} identity mismatch")
        decoder = zlib.decompressobj()
        limit = descriptor.get("decoded_size")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise RawWitnessError(f"payload chunk {relative} decoded_size is invalid")
        try:
            decoded = decoder.decompress(compressed, limit + 1) + decoder.flush()
        except zlib.error as exc:
            raise RawWitnessError(f"payload chunk {relative} is not valid zlib") from exc
        if (
            not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
            or len(decoded) != limit
        ):
            raise RawWitnessError(f"payload chunk {relative} has framing/size drift")
        decoded_parts.append(decoded)
        chunk_records.append({
            "index": index,
            "relative_path": relative,
            "compressed_bytes": identity["bytes"],
            "compressed_sha256": identity["sha256"],
            "decoded_bytes": len(decoded),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        })

    decoded_all = b"".join(decoded_parts)
    if (
        len(decoded_all) != formulas_manifest.get("decoded_size")
        or hashlib.sha256(decoded_all).hexdigest()
        != formulas_manifest.get("decoded_sha256")
    ):
        raise RawWitnessError("aggregate decoded payload identity drift")
    expected_payload = witness._canonical_bytes(
        result.comparison_outcome.to_dict()
    )
    decoded_object = _strict_json_bytes(decoded_all, "decoded comparison payload")
    if decoded_all != expected_payload or decoded_object != result.comparison_outcome.to_dict():
        raise RawWitnessError("decoded canonical payload disagrees with typed outcome")
    return {
        "product_reader_decoded_both_peers": True,
        "independent_decode_exact": True,
        "comparison_schema_version": 3,
        "payload_schema_version": 1,
        "encoding": formulas_manifest["encoding"],
        "decoded_bytes": len(decoded_all),
        "decoded_sha256": hashlib.sha256(decoded_all).hexdigest(),
        "chunks": chunk_records,
    }


def _write_canonical(path: Path, payload: object) -> dict[str, object]:
    expected = witness._canonical_bytes(payload, newline=True)
    identity = witness._write_exclusive(path, payload)
    if (
        identity["bytes"] != len(expected)
        or identity["sha256"] != hashlib.sha256(expected).hexdigest()
        or path.read_bytes() != expected
    ):
        raise RawWitnessError(f"canonical audit serialization drift: {path}")
    return identity


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one development Highway Sequence product witness against the "
            "identity-bound 69,804-row raw-TSN twin."
        )
    )
    parser.add_argument(
        "--leg", choices=LEG_CHOICES, required=True, default=None,
        action=witness._SingleValue,
    )
    parser.add_argument(
        "--output-root", type=Path, required=True, default=None,
        action=witness._SingleValue,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _assert_product_not_loaded()
    inputs = _bind_inputs()
    raw_twin = _validate_raw_twin(inputs)
    _assert_product_not_loaded()
    lease_policy = witness._source_backed_lease_policy()
    root = witness._create_clean_root(args.output_root)

    compare, side_a, side_b, events, consolidation_meta = _load_product(args.leg)
    outputs = witness._comparison_paths(root)
    result = compare(
        side_a,
        side_b,
        outputs["formulas"],
        events=events,
        confirm_overwrite=lambda _path: False,
        mode="both",
    )
    result_summary, declared_outputs = witness._validate_product_result(
        result, outputs, consolidation_meta
    )
    decoded_payload = _decode_payload_chunks(
        outputs, result, consolidation_meta
    )
    residue = witness._residue_gate(
        root, lease_policy, allowed_audit_names=set()
    )
    decoded_chunk_names = {
        str(item["relative_path"])
        for item in decoded_payload["chunks"]
    }
    inventoried_chunk_names = set(
        residue["exact_artifact_universe"]["payload_chunks"]
    )
    if decoded_chunk_names != inventoried_chunk_names:
        raise RawWitnessError(
            "payload artifact universe contains a missing or orphan chunk"
        )

    normalized_leg = (
        "excel_vs_normalized_tsn"
        if args.leg == "excel_vs_raw_tsn"
        else "pdf_vs_normalized_tsn"
    )
    loaded_product_code = witness._loaded_product_manifest(normalized_leg)
    product_manifest_identity = _write_canonical(
        root / PRODUCT_CODE_MANIFEST_NAME, loaded_product_code
    )
    residue = witness._residue_gate(
        root,
        lease_policy,
        allowed_audit_names={PRODUCT_CODE_MANIFEST_NAME},
    )

    artifact_manifest_before_result = witness._artifact_manifest(
        root, excluded_names={ARTIFACT_MANIFEST_NAME, RESULT_NAME}
    )
    artifact_manifest_identity = _write_canonical(
        root / ARTIFACT_MANIFEST_NAME, artifact_manifest_before_result
    )
    residue = witness._residue_gate(
        root,
        lease_policy,
        allowed_audit_names={
            PRODUCT_CODE_MANIFEST_NAME, ARTIFACT_MANIFEST_NAME,
        },
    )

    inputs_after = _bind_inputs()
    if inputs_after != inputs:
        raise RawWitnessError("bound source/twin artifacts changed during product run")

    payload = {
        "audit": "Stage 8 Highway Sequence development raw-twin product comparison leg",
        "leg": args.leg,
        "output_root": str(root),
        "not_an_acceptance_artifact": True,
        "reason": (
            "Development-only product witness against a cache-derived raw-TSN twin; "
            "final source acceptance must reparse the immutable TSN PDFs."
        ),
        "inputs": inputs,
        "inputs_after": inputs_after,
        "raw_twin_preimport_validation": raw_twin,
        "result": result_summary,
        "outputs": declared_outputs["workbooks"],
        "outcome_sidecars": declared_outputs["outcome_sidecars"],
        "decoded_comparison_payload": decoded_payload,
        "publication_artifacts": {
            "payload_chunks": decoded_payload["chunks"],
            "outcome_sidecars": declared_outputs["outcome_sidecars"],
            "permanent_lease": residue["permanent_lease"],
        },
        "residue_gate": residue,
        "loaded_product_code": loaded_product_code,
        "product_code_manifest": product_manifest_identity,
        "artifact_manifest_before_result": artifact_manifest_before_result,
        "artifact_manifest": artifact_manifest_identity,
        "deterministic_serialization": {
            "json": "UTF-8 canonical JSON; sorted keys; compact separators; LF terminator",
            "product_code_manifest_canonical": True,
            "artifact_manifest_canonical": True,
            "result_canonical": True,
        },
        "expected_final_artifact_names": sorted(
            set(residue["exact_artifact_universe"]["core_names"])
            | set(residue["exact_artifact_universe"]["payload_chunks"])
            | {
                PRODUCT_CODE_MANIFEST_NAME,
                ARTIFACT_MANIFEST_NAME,
                RESULT_NAME,
            }
        ),
        "invariants": {
            "one_leg": args.leg in LEG_CHOICES,
            "development_non_acceptance_labeled": True,
            "raw_twin_validated_before_product_import": True,
            "raw_twin_exactly_69804_records":
                raw_twin["counts"]["raw_records"] == 69_804,
            "complete_ok_zero_zero": True,
            "pairing_exact": True,
            "committed_formula_value_twin": True,
            "two_trusted_outcome_sidecars": True,
            "payload_chunks_decoded_and_bound": True,
            "no_missing_or_orphan_payload_chunks":
                decoded_chunk_names == inventoried_chunk_names,
            "inputs_unchanged": inputs_after == inputs,
            "exact_artifact_universe": True,
            "no_transient_residue": not residue["transient_residue"],
            "only_zero_byte_source_backed_permanent_lease":
                residue["permanent_lease"]["bytes"] == 0,
            "canonical_deterministic_audit_json": True,
            "loaded_product_code_manifested": True,
            "no_delete_or_overwrite": True,
        },
    }
    if not all(payload["invariants"].values()):
        raise RawWitnessError(f"raw product witness invariants failed: {payload['invariants']}")
    result_identity = _write_canonical(root / RESULT_NAME, payload)

    final_residue = witness._residue_gate(
        root,
        lease_policy,
        allowed_audit_names={
            PRODUCT_CODE_MANIFEST_NAME, ARTIFACT_MANIFEST_NAME, RESULT_NAME,
        },
    )
    final_names = sorted(path.name for path in root.iterdir())
    if final_names != payload["expected_final_artifact_names"]:
        raise RawWitnessError("post-result artifact universe disagrees with declaration")
    if final_residue["transient_residue"]:
        raise RawWitnessError("post-result transient residue gate failed")

    print(json.dumps({
        "status": "PASS",
        "leg": args.leg,
        "not_an_acceptance_artifact": True,
        "result": result_identity,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except witness.WitnessError as exc:
        print(f"FAIL Highway Sequence raw-twin product leg: {exc}")
        raise SystemExit(1)
