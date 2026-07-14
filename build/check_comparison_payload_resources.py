"""Focused schema-v3 payload resource/call-order regression gate."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import consolidation_meta as cm  # noqa: E402
from comparison_contract import (  # noqa: E402
    ArtifactGeneration,
    ComparisonCounts,
    ComparisonOutcome,
)
from events import ConsolidateResult  # noqa: E402


_failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)


def _member(path, flavor):
    path = Path(path)
    raw = path.read_bytes()
    stat = path.stat()
    return {
        "flavor": flavor,
        "relative_path": path.name,
        "path": str(path),
        "canonical_path_at_write": str(path.resolve()),
        "commit_role": "best_effort" if flavor == "formulas" else "canonical",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _result(formulas, values):
    members = (_member(values, "values"), _member(formulas, "formulas"))
    typed = ComparisonOutcome(
        status="ok", completion="complete", verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=2),
        pairing_quality="exact")
    generation = ArtifactGeneration(
        generation_id="payload-resource-gate",
        members=members,
        content_digests={item["flavor"]: item["sha256"] for item in members},
        completion="complete",
        producer_versions={"comparison": "payload-resource-gate"},
        publication_state="committed",
        requested_mode="both",
    )
    return ConsolidateResult(
        status="ok", output_path=str(formulas), verdict="match",
        completion="complete", skipped_inputs=0, failed_inputs=0,
        comparison_outcome=typed, artifact_generation=generation)


def _raw_sidecar(path):
    return json.loads(cm.meta_path(path).read_text(encoding="utf-8"))


def _write_sidecar(path, value):
    cm.meta_path(path).write_bytes(cm._canonical_json_bytes(value))


def _install_manifest(paths, manifest):
    for path in paths:
        envelope = _raw_sidecar(path)
        envelope["comparison_payload"] = copy.deepcopy(manifest)
        _write_sidecar(path, envelope)


def _manifest_for_raw(raw, envelope):
    """Build a one-chunk manifest bound to an existing generation envelope."""
    compressed = zlib.compress(raw, level=6)
    decoded_sha = hashlib.sha256(raw).hexdigest()
    compressed_sha = hashlib.sha256(compressed).hexdigest()
    binding_sha = cm._comparison_payload_binding_sha256(
        decoded_sha, envelope["completion"], envelope["skipped_inputs"],
        envelope["failed_inputs"], envelope["artifact_generation"])
    relative = (
        f".cmpv3-{decoded_sha}-000000-{compressed_sha}"
        f"{cm._COMPARISON_PAYLOAD_SUFFIX}")
    return ({
        "schema_version": cm._COMPARISON_PAYLOAD_SCHEMA_VERSION,
        "encoding": cm._COMPARISON_PAYLOAD_ENCODING,
        "decoded_size": len(raw),
        "decoded_sha256": decoded_sha,
        "binding_sha256": binding_sha,
        "chunks": [{
            "relative_path": relative,
            "size": len(compressed),
            "sha256": compressed_sha,
            "decoded_size": len(raw),
        }],
    }, relative, compressed)


def _count_payload_decodes(callback):
    original = cm._read_comparison_payload
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    cm._read_comparison_payload = counted
    try:
        value = callback()
    finally:
        cm._read_comparison_payload = original
    return value, len(calls)


def main():
    with tempfile.TemporaryDirectory(prefix="tsmis_payload_resources_") as raw:
        root = Path(raw)
        formulas = root / "resource.xlsx"
        values = root / "resource (values).xlsx"
        formulas.write_bytes(b"PK-resource-formulas")
        values.write_bytes(b"PK-resource-values")
        result = _result(formulas, values)
        paths = (formulas, values)

        print("evidence-bounded schema-v3 resource policy:")
        check("decoded resource ceiling is 64 MiB",
              cm._MAX_COMPARISON_PAYLOAD_DECODED_BYTES == 64 * 1024 * 1024)
        check("at most sixteen canonical 4 MiB decoded chunks are accepted",
              cm._MAX_COMPARISON_PAYLOAD_CHUNKS == 16)
        check("expansion ceiling retains measured 16.836:1 with bounded headroom",
              16.836 < cm._MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO <= 32)
        check("baseline two-member schema-v3 publication succeeds",
              cm.write_comparison_outcomes(result))

        print("one shared decode after full peer validation:")
        formula_record, formula_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        values_record, values_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(values))
        check("each member read decodes the shared payload exactly once",
              formula_record.trusted and values_record.trusted
              and formula_calls == 1 and values_calls == 1)

        clean_formula_sidecar = cm.meta_path(formulas).read_bytes()
        clean_values_sidecar = cm.meta_path(values).read_bytes()
        invalid_peer = _raw_sidecar(values)
        invalid_peer["comparison_payload"]["binding_sha256"] = "0" * 64
        _write_sidecar(values, invalid_peer)
        peer_record, peer_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("an invalid peer envelope fails closed before payload decode",
              not peer_record.trusted and peer_calls == 0)
        cm.meta_path(values).write_bytes(clean_values_sidecar)

        peer_bytes = values.read_bytes()
        peer_stat = values.stat()
        values.write_bytes(bytes([peer_bytes[0] ^ 1]) + peer_bytes[1:])
        os.utime(values, ns=(peer_stat.st_atime_ns, peer_stat.st_mtime_ns))
        workbook_record, workbook_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("a content-mismatched peer workbook fails before payload decode",
              not workbook_record.trusted and workbook_calls == 0)
        values.write_bytes(peer_bytes)
        os.utime(values, ns=(peer_stat.st_atime_ns, peer_stat.st_mtime_ns))

        print("schema-v2 compatibility remains inline and decode-free:")
        prepared = cm._prepare_comparison_publication(result)
        for member, workbook, facts in prepared["members"]:
            _write_sidecar(
                workbook,
                cm._comparison_final_payload_v2(prepared, member, facts))
        v2_record, v2_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("a valid schema-v2 peer generation remains trusted",
              v2_record.trusted and v2_record.comparison_outcome
                  == result.comparison_outcome and v2_calls == 0)
        check("republishing restores schema-v3 after the compatibility fixture",
              cm.write_comparison_outcomes(result))
        clean_formula_sidecar = cm.meta_path(formulas).read_bytes()
        clean_values_sidecar = cm.meta_path(values).read_bytes()

        print("high-expansion manifests are rejected before decompression:")
        envelope = _raw_sidecar(formulas)
        bomb_raw = b'"' + (b"A" * (1024 * 1024)) + b'"'
        bomb_manifest, _bomb_relative, _bomb_compressed = _manifest_for_raw(
            bomb_raw, envelope)
        check("the attack fixture is materially above the accepted ratio",
              bomb_manifest["decoded_size"]
                  > bomb_manifest["chunks"][0]["size"]
                    * cm._MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO)
        _install_manifest(paths, bomb_manifest)
        original_decompressobj = cm.zlib.decompressobj
        decompress_calls = []

        def forbidden_decompress(*args, **kwargs):
            decompress_calls.append(1)
            raise AssertionError("over-ratio manifest reached decompression")

        cm.zlib.decompressobj = forbidden_decompress
        try:
            bomb_record = cm.read_comparison_outcome(formulas)
        finally:
            cm.zlib.decompressobj = original_decompressobj
        check("over-ratio peer metadata is untrusted without invoking zlib",
              not bomb_record.trusted and not decompress_calls)

        preflight_rejected = False
        try:
            cm._preflight_comparison_payload(
                {"blob": "A" * (1024 * 1024)},
                completion="complete", skipped_inputs=0, failed_inputs=0,
                artifact_generation=envelope["artifact_generation"])
        except ValueError as error:
            preflight_rejected = "expansion" in str(error)
        check("publisher preflight rejects the same high-expansion class",
              preflight_rejected)
        cm.meta_path(formulas).write_bytes(clean_formula_sidecar)
        cm.meta_path(values).write_bytes(clean_values_sidecar)

        print("streamed canonicality and chunk tamper checks:")
        canonical = cm._canonical_json_bytes(result.comparison_outcome.to_dict())
        noncanonical = b" " + canonical
        noncanonical_manifest, relative, compressed = _manifest_for_raw(
            noncanonical, envelope)
        check("noncanonical fixture remains below the expansion ceiling",
              noncanonical_manifest["decoded_size"]
                  <= noncanonical_manifest["chunks"][0]["size"]
                    * cm._MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO)
        (root / relative).write_bytes(compressed)
        _install_manifest(paths, noncanonical_manifest)
        canonical_record, canonical_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("strict JSON with noncanonical bytes is rejected by one decode",
              not canonical_record.trusted and canonical_calls == 1
              and "not canonical" in (canonical_record.diagnostic or ""))

        check("republishing restores the canonical shared payload",
              cm.write_comparison_outcomes(result))
        manifest = _raw_sidecar(formulas)["comparison_payload"]
        chunk = root / manifest["chunks"][0]["relative_path"]
        chunk_bytes = chunk.read_bytes()
        chunk_stat = chunk.stat()
        chunk.write_bytes(bytes([chunk_bytes[0] ^ 1]) + chunk_bytes[1:])
        os.utime(chunk, ns=(chunk_stat.st_atime_ns, chunk_stat.st_mtime_ns))
        tamper_record, tamper_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("content-addressed chunk tamper fails closed in the sole decode",
              not tamper_record.trusted and tamper_calls == 1)
        chunk.write_bytes(chunk_bytes)
        os.utime(chunk, ns=(chunk_stat.st_atime_ns, chunk_stat.st_mtime_ns))
        restored, restored_calls = _count_payload_decodes(
            lambda: cm.read_comparison_outcome(formulas))
        check("restored canonical bytes return to one-decode trust",
              restored.trusted and restored_calls == 1)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL COMPARISON PAYLOAD RESOURCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
