"""Phase-2 comparison generation sidecar publication/read regression gate.

No browser/network. Run from the repository root:
    build\.venv\Scripts\python.exe build\check_comparison_sidecars.py
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import consolidation_meta as cm  # noqa: E402
from comparison_contract import (  # noqa: E402
    ArtifactGeneration,
    CAPPED_FALLBACK_POLICY,
    CAPPED_PAIRING_ALGORITHM,
    EXACT_PAIRING_ALGORITHM,
    SOURCE_PAIRING_ALGORITHM,
    CappedGroupDiagnostic,
    ComparisonCounts,
    ComparisonOutcome,
    PairingPair,
    PairingTrace,
)
from events import ConsolidateResult  # noqa: E402


_failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)


def _facts(path):
    path = Path(path)
    st = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), st.st_size, st.st_mtime_ns


def _member(path, flavor, requested_mode):
    path = Path(path)
    digest, size, mtime_ns = _facts(path)
    return {
        "flavor": flavor,
        "relative_path": path.name,
        "path": str(path),
        "canonical_path_at_write": str(path.resolve()),
        "commit_role": ("best_effort" if requested_mode == "both"
                        and flavor == "formulas" else "canonical"),
        "sha256": digest,
        "size": size,
        "mtime_ns": mtime_ns,
    }


def _result(paths, requested_mode, generation_id, completion="complete", status="ok"):
    if requested_mode == "both":
        paths = tuple(sorted(paths, key=lambda item: 0 if item[0] == "values" else 1))
    members = tuple(_member(path, flavor, requested_mode) for flavor, path in paths)
    if completion == "complete":
        counts = ComparisonCounts(known=True, paired_rows=2)
        typed_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match", counts=counts,
            pairing_quality="exact")
        skipped = failed = 0
    else:
        counts = ComparisonCounts(
            known=True, paired_rows=2, differing_rows=1, differing_cells=1,
            per_field_counts={"0:A": 1}, asserted_cells=1)
        typed_outcome = ComparisonOutcome(
            status="ok", completion="partial", verdict="diff", counts=counts,
            warnings=("one input was incomplete",), pairing_quality="exact")
        skipped, failed = 1, 0
    generation = ArtifactGeneration(
        generation_id=generation_id,
        members=members,
        content_digests={member["flavor"]: member["sha256"] for member in members},
        completion=completion,
        producer_versions={"comparison": "test-v1"},
        publication_state="committed",
        requested_mode=requested_mode,
    )
    return ConsolidateResult(
        status=status,
        message=("formulas finalization failed after values committed"
                 if status == "error" else ""),
        output_path=str(next((path for flavor, path in paths if flavor == "formulas"),
                             paths[0][1])),
        verdict=typed_outcome.verdict,
        completion=completion,
        skipped_inputs=skipped,
        failed_inputs=failed,
        comparison_outcome=typed_outcome,
        artifact_generation=generation,
    )


def _raw_sidecar(path):
    return json.loads(cm.meta_path(path).read_text(encoding="utf-8"))


def _write_raw_sidecar(path, value):
    cm.meta_path(path).write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _payload_chunk_paths(path):
    raw = _raw_sidecar(path)
    manifest = raw["comparison_payload"]
    return tuple(Path(path).parent / item["relative_path"]
                 for item in manifest["chunks"])


def _payload_value(path):
    raw = _raw_sidecar(path)
    return cm._read_comparison_payload(
        raw["comparison_payload"], Path(path).parent).to_dict()


def _install_payload(paths, value):
    first_raw = _raw_sidecar(paths[0])
    manifest, chunks = cm._preflight_comparison_payload(
        value,
        completion=first_raw["completion"],
        skipped_inputs=first_raw["skipped_inputs"],
        failed_inputs=first_raw["failed_inputs"],
        artifact_generation=first_raw["artifact_generation"])
    parent = Path(paths[0]).parent
    for relative, compressed in chunks:
        (parent / relative).write_bytes(compressed)
    for path in paths:
        raw = _raw_sidecar(path)
        raw["comparison_schema_version"] = 3
        raw.pop("comparison_outcome", None)
        raw["comparison_payload"] = manifest
        _write_raw_sidecar(path, raw)
    return manifest


def _install_manifest(paths, manifest):
    for path in paths:
        raw = _raw_sidecar(path)
        raw["comparison_payload"] = copy.deepcopy(manifest)
        _write_raw_sidecar(path, raw)


def _mutated_chunk_manifest(path, compressed, index=0):
    raw = _raw_sidecar(path)
    manifest = copy.deepcopy(raw["comparison_payload"])
    descriptor = manifest["chunks"][index]
    digest = hashlib.sha256(compressed).hexdigest()
    descriptor["size"] = len(compressed)
    descriptor["sha256"] = digest
    descriptor["relative_path"] = (
        f".cmpv3-{manifest['decoded_sha256']}-{index:06d}-{digest}"
        f"{cm._COMPARISON_PAYLOAD_SUFFIX}")
    chunk_path = Path(path).parent / descriptor["relative_path"]
    chunk_path.write_bytes(compressed)
    return manifest, chunk_path


def _rebind_raw_payload(raw):
    manifest = raw["comparison_payload"]
    manifest["binding_sha256"] = cm._comparison_payload_binding_sha256(
        manifest["decoded_sha256"], raw["completion"],
        raw["skipped_inputs"], raw["failed_inputs"],
        raw["artifact_generation"])


def _same_bytes(paths, before):
    return all(Path(path).read_bytes() == before[Path(path)] for path in paths)


def _exact_pairing_trace():
    return PairingTrace(
        key_components=("R|X", "K"),
        side_a_size=2, side_b_size=2, matrix_cells=4,
        side_a_indices=(10, 11), side_b_indices=(20, 21),
        smaller_side="a", assignment_vector=(1, 0),
        pairs=(PairingPair(10, 21, 0), PairingPair(11, 20, 1)),
        total_cost=1, positional_cost=2,
        algorithm=EXACT_PAIRING_ALGORITHM, exact=True, quality="exact")


def _source_pairing_trace():
    """The CMP-AUD-220 v2 shape: per-pair source objectives + group totals."""
    return PairingTrace(
        key_components=("R|X", "K2"),
        side_a_size=2, side_b_size=2, matrix_cells=4,
        side_a_indices=(10, 11), side_b_indices=(20, 21),
        smaller_side="a", assignment_vector=(1, 0),
        pairs=(PairingPair(10, 21, 0, objective=(0, 0, 1)),
               PairingPair(11, 20, 1, objective=(1, 1, 1))),
        total_cost=1, positional_cost=2,
        algorithm=SOURCE_PAIRING_ALGORITHM, exact=True, quality="exact",
        objective_total=(1, 1, 2), objective_positional=(2, 2, 0))


def _capped_pairing_trace():
    side_a = tuple(range(317))
    side_b = tuple(range(316))
    pairs = tuple(PairingPair(index, index, 0) for index in side_b)
    trace = PairingTrace(
        key_components=("CAP",),
        side_a_size=317, side_b_size=316, matrix_cells=317 * 316,
        side_a_indices=side_a, side_b_indices=side_b,
        smaller_side="b", assignment_vector=side_b, pairs=pairs,
        total_cost=0, positional_cost=0,
        algorithm=CAPPED_PAIRING_ALGORITHM, exact=False, quality="capped")
    diagnostic = CappedGroupDiagnostic(
        key_components=("CAP",),
        side_a_size=317, side_b_size=316, matrix_cells=317 * 316,
        cap=100_000, fallback_policy=CAPPED_FALLBACK_POLICY,
        fallback_cost=0)
    return trace, diagnostic


def main():
    with tempfile.TemporaryDirectory(prefix="tsmis_comparison_sidecars_") as raw:
        root = Path(raw)

        print("single-member complete + partial round trips:")
        single = root / "single.xlsx"
        single.write_bytes(b"PK-single-comparison-workbook")
        before = {single: single.read_bytes()}
        single_result = _result((("values", single),), "values", "g-single")
        check("single publication succeeds", cm.write_comparison_outcomes(single_result))
        single_read = cm.read_comparison_outcome(single)
        check("single record is trusted/current with typed truth",
              single_read is not None and single_read.trusted and single_read.current
              and single_read.completion == "complete"
              and single_read.comparison_outcome == single_result.comparison_outcome
              and single_read.artifact_generation.generation_id == "g-single"
              and single_read.self_member["flavor"] == "values")
        check("legacy read delegates to strict comparison validation",
              cm.read_completion(single) == "complete"
              and cm.read_outcome(single).trusted is True)
        check("single publication never resaves workbook bytes",
              _same_bytes((single,), before))
        check("successful publication removes fixed/unpredictable temps",
              not cm._sentinel_path(single).exists()
              and not any(".tmp-" in child.name for child in root.iterdir()))

        print("E2 typed pairing trace + schema-v3 persistence / v2 compatibility:")
        trace_book = root / "pairing-trace.xlsx"
        trace_book.write_bytes(b"PK-pairing-trace-workbook")
        trace_result = _result(
            (("values", trace_book),), "values", "g-pairing-trace")
        trace_result.verdict = "diff"
        trace_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="diff",
            counts=ComparisonCounts(
                known=True, paired_rows=2, differing_rows=1,
                differing_cells=1, per_field_counts={"1:Value": 1},
                asserted_cells=1),
            pairing_trace=(_exact_pairing_trace(),), duplicate_group_count=1,
            pairing_quality="exact")
        check("exact pairing trace publication succeeds",
              cm.write_comparison_outcomes(trace_result))
        trace_read = cm.read_comparison_outcome(trace_book)
        check("exact original-index pairs and lex vector strict-round-trip",
              trace_read is not None and trace_read.trusted
              and trace_read.comparison_outcome == trace_result.comparison_outcome
              and trace_read.comparison_outcome.pairing_trace[0]
                  .assignment_vector == (1, 0))

        source_book = root / "pairing-source.xlsx"
        source_book.write_bytes(b"PK-pairing-source-workbook")
        source_result = _result(
            (("values", source_book),), "values", "g-pairing-source")
        source_result.verdict = "diff"
        source_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="diff",
            counts=ComparisonCounts(
                known=True, paired_rows=2, differing_rows=1,
                differing_cells=1, per_field_counts={"1:Value": 1},
                asserted_cells=1),
            pairing_trace=(_source_pairing_trace(),), duplicate_group_count=1,
            pairing_quality="exact")
        check("source-objective (v2) pairing trace publication succeeds",
              cm.write_comparison_outcomes(source_result))
        source_read = cm.read_comparison_outcome(source_book)
        check("v2 objectives and per-pair triples strict-round-trip",
              source_read is not None and source_read.trusted
              and source_read.comparison_outcome
                  == source_result.comparison_outcome
              and source_read.comparison_outcome.pairing_trace[0]
                  .objective_total == (1, 1, 2)
              and source_read.comparison_outcome.pairing_trace[0]
                  .pairs[0].objective == (0, 0, 1))

        capped_book = root / "pairing-capped.xlsx"
        capped_book.write_bytes(b"PK-pairing-capped-workbook")
        capped_result = _result(
            (("values", capped_book),), "values", "g-pairing-capped")
        capped_trace, capped_diagnostic = _capped_pairing_trace()
        capped_result.completion = "partial"
        capped_result.verdict = "diff"
        capped_result.artifact_generation = replace(
            capped_result.artifact_generation, completion="partial")
        capped_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="partial", verdict="diff",
            counts=ComparisonCounts(
                known=True, paired_rows=316, side_a_only_rows=1),
            pairing_trace=(capped_trace,), duplicate_group_count=1,
            pairing_quality="capped",
            capped_group_diagnostics=(capped_diagnostic,))
        check("partial/capped pairing publication succeeds",
              cm.write_comparison_outcomes(capped_result))
        capped_read = cm.read_comparison_outcome(capped_book)
        check("capped quality, trace, and diagnostic strict-round-trip",
              capped_read is not None and capped_read.trusted
              and capped_read.comparison_outcome == capped_result.comparison_outcome
              and capped_read.comparison_outcome.pairing_quality == "capped")

        prepared_capped = cm._prepare_comparison_publication(capped_result)
        capped_member, _capped_path, capped_facts = prepared_capped["members"][0]
        _write_raw_sidecar(
            capped_book,
            cm._comparison_final_payload_v2(
                prepared_capped, capped_member, capped_facts))
        v2_pairing = cm.read_comparison_outcome(capped_book)
        check("inline comparison schema v2 remains trusted and strictly typed",
              v2_pairing is not None and v2_pairing.trusted
              and v2_pairing.comparison_outcome == capped_result.comparison_outcome
              and v2_pairing.artifact_generation == capped_result.artifact_generation)
        check("new publication migrates the member back to schema v3",
              cm.write_comparison_outcomes(capped_result)
              and _raw_sidecar(capped_book)["comparison_schema_version"] == 3)

        capped_raw = _raw_sidecar(capped_book)
        capped_raw["comparison_schema_version"] = 1
        _write_raw_sidecar(capped_book, capped_raw)
        legacy_pairing = cm.read_comparison_outcome(capped_book)
        check("pre-E2 comparison sidecar version is never accepted as fresh truth",
              legacy_pairing is not None and not legacy_pairing.trusted)
        check("republishing restores the current pairing schema",
              cm.write_comparison_outcomes(capped_result)
              and cm.read_comparison_outcome(capped_book).trusted)
        clean_sidecar = cm.meta_path(single).read_bytes()
        complete_with_warning = _result(
            (("values", single),), "values", "g-complete-warning")
        complete_with_warning.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=2),
            warnings=("coverage warning",), pairing_quality="exact")
        check("publisher rejects complete typed outcome with warnings/failures",
              cm.write_comparison_outcomes(complete_with_warning) is False)
        check("...rejection happens before touching the last trusted sidecar",
              cm.meta_path(single).read_bytes() == clean_sidecar
              and not cm._sentinel_path(single).exists())

        partial = root / "partial.xlsx"
        partial.write_bytes(b"PK-partial-comparison-workbook")
        partial_before = partial.read_bytes()
        partial_result = _result(
            (("formulas", partial),), "formulas", "g-partial", completion="partial")
        check("partial publication succeeds", cm.write_comparison_outcomes(partial_result))
        partial_read = cm.read_comparison_outcome(partial)
        check("partial completion/counters round-trip without prose inference",
              partial_read is not None and partial_read.trusted
              and partial_read.completion == "partial"
              and partial_read.skipped_inputs == 1 and partial_read.failed_inputs == 0
              and partial_read.comparison_outcome.counts.differing_cells == 1)
        check("partial publication leaves workbook bytes identical",
              partial.read_bytes() == partial_before)
        partial_raw = _raw_sidecar(partial)
        partial_raw["skipped_inputs"] = 2
        _write_raw_sidecar(partial, partial_raw)
        check("positive compatibility-counter tamper breaks payload binding",
              not cm.read_comparison_outcome(partial).trusted)
        check("republishing restores compatibility/payload binding",
              cm.write_comparison_outcomes(partial_result))

        print("two-member generation + values-canonical formulas-missing policy:")
        formulas = root / "both.xlsx"
        values = root / "both (values).xlsx"
        formulas.write_bytes(b"PK-formulas-workbook-v1")
        values.write_bytes(b"PK-values-workbook-v1")
        both_before = {formulas: formulas.read_bytes(), values: values.read_bytes()}
        both_result = _result(
            (("formulas", formulas), ("values", values)), "both", "g-both")
        check("both publication succeeds", cm.write_comparison_outcomes(both_result))
        fr = cm.read_comparison_outcome(formulas)
        vr = cm.read_comparison_outcome(values)
        check("both opening orders validate the same generation",
              fr is not None and vr is not None and fr.trusted and vr.trusted
              and fr.artifact_generation == vr.artifact_generation
              and fr.comparison_outcome == vr.comparison_outcome
              and fr.self_member["flavor"] == "formulas"
              and vr.self_member["flavor"] == "values")
        fraw, vraw = _raw_sidecar(formulas), _raw_sidecar(values)
        varying = {"self_member", "built_at_mtime"}
        check("member finals differ only by self_member and workbook mtime",
              {k: v for k, v in fraw.items() if k not in varying}
              == {k: v for k, v in vraw.items() if k not in varying})
        check("each final carries schema/type/top compatibility + one shared payload manifest",
              fraw["schema_version"] == 1 and fraw["record_type"] == "comparison"
              and fraw["comparison_schema_version"] == 3
              and fraw["completion"] == "complete"
              and isinstance(fraw["comparison_payload"], dict)
              and fraw["comparison_payload"] == vraw["comparison_payload"]
              and isinstance(fraw["artifact_generation"], dict)
              and _payload_chunk_paths(formulas) == _payload_chunk_paths(values)
              and all(path.is_file() for path in _payload_chunk_paths(formulas)))
        check("both publication never changes either workbook",
              _same_bytes((formulas, values), both_before))

        canonical_only = root / "missing-formulas (values).xlsx"
        canonical_only.write_bytes(b"PK-values-canonical-only")
        missing_result = _result(
            (("values", canonical_only),), "both", "g-formulas-missing")
        check("one-member requested-both generation is accepted",
              cm.write_comparison_outcomes(missing_result))
        missing_read = cm.read_comparison_outcome(canonical_only)
        check("formulas-missing stays comparison-complete and publication committed",
              missing_read is not None and missing_read.trusted
              and missing_read.completion == "complete"
              and missing_read.artifact_generation.requested_mode == "both"
              and missing_read.artifact_generation.publication_state == "committed"
              and len(missing_read.artifact_generation.members) == 1
              and missing_read.self_member["flavor"] == "values")

        committed_error = root / "error-after-values (values).xlsx"
        committed_error.write_bytes(b"PK-values-survived-post-commit-error")
        error_result = _result(
            (("values", committed_error),), "both", "g-error-values", status="error")
        check("status=error with a committed values generation still publishes",
              cm.write_comparison_outcomes(error_result))
        error_read = cm.read_comparison_outcome(committed_error)
        check("...published truth comes from typed comparison/generation, not coarse status",
              error_read is not None and error_read.trusted
              and error_read.completion == "complete"
              and error_read.artifact_generation.generation_id == "g-error-values")

        print("strict peer/path/digest validation:")
        # Serialized absolute provenance is deliberately not lookup authority.
        fraw, vraw = _raw_sidecar(formulas), _raw_sidecar(values)
        for payload in (fraw, vraw):
            for member in payload["artifact_generation"]["members"]:
                member["path"] = str(root / "attacker" / member["relative_path"])
                member["canonical_path_at_write"] = str(
                    root / "elsewhere" / member["relative_path"])
                if member["flavor"] == payload["self_member"]["flavor"]:
                    payload["self_member"] = dict(member)
            _rebind_raw_payload(payload)
        _write_raw_sidecar(formulas, fraw)
        _write_raw_sidecar(values, vraw)
        check("peer lookup ignores serialized absolute paths and uses safe basename siblings",
              cm.read_comparison_outcome(formulas).trusted
              and cm.read_comparison_outcome(values).trusted)
        check("normal publication restores canonical generation payload",
              cm.write_comparison_outcomes(both_result))

        cm.meta_path(values).unlink()
        missing_peer = cm.read_comparison_outcome(formulas)
        check("missing peer sidecar makes the surviving member untrusted/partial",
              missing_peer is not None and not missing_peer.trusted
              and missing_peer.completion == "partial"
              and missing_peer.comparison_outcome is None
              and cm.read_completion(formulas) == "partial")
        check("republishing restores the missing peer", cm.write_comparison_outcomes(both_result))

        vraw = _raw_sidecar(values)
        vraw["artifact_generation"]["generation_id"] = "g-mismatch"
        _rebind_raw_payload(vraw)
        _write_raw_sidecar(values, vraw)
        mismatch = cm.read_comparison_outcome(formulas)
        check("peer generation mismatch fails closed",
              mismatch is not None and not mismatch.trusted
              and mismatch.completion == "partial"
              and "disagrees" in (mismatch.diagnostic or ""))
        check("republishing restores peer agreement", cm.write_comparison_outcomes(both_result))

        values_original = values.read_bytes()
        values_stat = values.stat()
        values.write_bytes(b"XX" + values_original[2:])
        os.utime(values, ns=(values_stat.st_atime_ns, values_stat.st_mtime_ns))
        digest_tamper = cm.read_comparison_outcome(formulas)
        check("same-size/same-mtime peer workbook tamper is caught by SHA-256",
              digest_tamper is not None and not digest_tamper.trusted
              and digest_tamper.completion == "partial")
        values.write_bytes(values_original)
        os.utime(values, ns=(values_stat.st_atime_ns, values_stat.st_mtime_ns))
        check("restored exact peer bytes validate again",
              cm.read_comparison_outcome(formulas).trusted)

        print("schema-v3 payload manifest/chunk tamper rejection:")
        shared_chunk = _payload_chunk_paths(formulas)[0]
        shared_bytes = shared_chunk.read_bytes()
        shared_stat = shared_chunk.stat()
        flipped = bytes([shared_bytes[0] ^ 1]) + shared_bytes[1:]
        shared_chunk.write_bytes(flipped)
        os.utime(shared_chunk, ns=(shared_stat.st_atime_ns, shared_stat.st_mtime_ns))
        check("same-size/same-mtime shared chunk tamper makes both peers untrusted",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        shared_chunk.write_bytes(shared_bytes)
        os.utime(shared_chunk, ns=(shared_stat.st_atime_ns, shared_stat.st_mtime_ns))
        check("restoring exact shared chunk bytes restores both peers",
              cm.read_comparison_outcome(formulas).trusted
              and cm.read_comparison_outcome(values).trusted)

        shared_chunk.unlink()
        check("one missing shared chunk makes both peers untrusted",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        shared_chunk.write_bytes(shared_bytes)
        check("restoring the missing chunk restores both peers",
              cm.read_comparison_outcome(formulas).trusted
              and cm.read_comparison_outcome(values).trusted)

        trailing_manifest, _trailing_path = _mutated_chunk_manifest(
            formulas, shared_bytes + b"trailing")
        _install_manifest((formulas, values), trailing_manifest)
        check("trailing bytes after a valid zlib stream are rejected",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("republishing restores the canonical payload after trailing-data rejection",
              cm.write_comparison_outcomes(both_result))

        shared_chunk = _payload_chunk_paths(formulas)[0]
        shared_bytes = shared_chunk.read_bytes()
        concat_manifest, _concat_path = _mutated_chunk_manifest(
            formulas, shared_bytes + zlib.compress(b"second-stream"))
        _install_manifest((formulas, values), concat_manifest)
        check("concatenated zlib streams are rejected",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("republishing restores the canonical payload after stream rejection",
              cm.write_comparison_outcomes(both_result))

        shared_chunk = _payload_chunk_paths(formulas)[0]
        shared_bytes = shared_chunk.read_bytes()
        truncated_manifest, _truncated_path = _mutated_chunk_manifest(
            formulas, shared_bytes[:-1])
        _install_manifest((formulas, values), truncated_manifest)
        check("a truncated zlib stream is rejected",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("republishing restores the canonical payload after truncation",
              cm.write_comparison_outcomes(both_result))

        payload_raw = cm._canonical_json_bytes(_payload_value(formulas))
        oversized_decoded = zlib.compress(payload_raw + b"x")
        oversized_manifest, _oversized_path = _mutated_chunk_manifest(
            formulas, oversized_decoded)
        _install_manifest((formulas, values), oversized_manifest)
        check("decoded output beyond the declared size is rejected as a bomb",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("republishing restores the canonical payload after decoded-limit rejection",
              cm.write_comparison_outcomes(both_result))

        bad_encoding_raw = _raw_sidecar(formulas)
        bad_encoding_raw["comparison_payload"]["encoding"] = "gzip-json"
        _write_raw_sidecar(formulas, bad_encoding_raw)
        check("unknown payload encoding is rejected",
              not cm.read_comparison_outcome(formulas).trusted)
        check("republishing restores the declared payload encoding",
              cm.write_comparison_outcomes(both_result))

        bad_path_raw = _raw_sidecar(formulas)
        bad_path_raw["comparison_payload"]["chunks"][0]["relative_path"] = "../escape.zlib"
        _write_raw_sidecar(formulas, bad_path_raw)
        check("unsafe payload chunk path is rejected before sibling lookup",
              not cm.read_comparison_outcome(formulas).trusted)
        check("republishing restores the safe payload path",
              cm.write_comparison_outcomes(both_result))

        alternate = ComparisonOutcome(
            status="ok", completion="complete", verdict="diff",
            counts=ComparisonCounts(
                known=True, paired_rows=2, differing_rows=1,
                differing_cells=1, per_field_counts={"0:A": 1},
                asserted_cells=1),
            pairing_quality="exact")
        _install_payload((formulas,), alternate.to_dict())
        check("valid but different payload manifests cannot be mixed across peers",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("republishing restores exact peer-manifest agreement",
              cm.write_comparison_outcomes(both_result))

        print("malformed/stale sidecars fail closed:")
        cm.meta_path(single).write_text("{broken-json", encoding="utf-8")
        malformed = cm.read_comparison_outcome(single)
        check("malformed current sidecar -> partial/untrusted diagnostic",
              malformed is not None and not malformed.trusted
              and malformed.completion == "partial" and bool(malformed.diagnostic)
              and cm.read_completion(single) == "partial")
        check("republishing repairs malformed final", cm.write_comparison_outcomes(single_result))

        sraw = _raw_sidecar(single)
        sraw["skipped_inputs"] = -1
        _write_raw_sidecar(single, sraw)
        invalid_count = cm.read_comparison_outcome(single)
        check("negative top compatibility count can never read complete",
              invalid_count is not None and not invalid_count.trusted
              and invalid_count.completion == "partial")
        check("republishing repairs invalid count", cm.write_comparison_outcomes(single_result))

        planted_outcome = _payload_value(single)
        planted_outcome["counts"]["differing_cells"] = 1
        _install_payload((single,), planted_outcome)
        invalid_typed = cm.read_comparison_outcome(single)
        check("typed count invariant tamper can never read complete",
              invalid_typed is not None and not invalid_typed.trusted
              and invalid_typed.completion == "partial")
        check("republishing repairs typed invariant", cm.write_comparison_outcomes(single_result))

        sraw = _raw_sidecar(single)
        sraw["artifact_generation"]["members"][0]["size"] += 1
        sraw["self_member"] = dict(sraw["artifact_generation"]["members"][0])
        _write_raw_sidecar(single, sraw)
        invalid_size = cm.read_comparison_outcome(single)
        check("member size claim tamper is checked against the actual workbook",
              invalid_size is not None and not invalid_size.trusted
              and invalid_size.completion == "partial")
        check("republishing repairs size claim", cm.write_comparison_outcomes(single_result))

        sraw = _raw_sidecar(single)
        sraw["artifact_generation"]["members"][0]["relative_path"] = "../single.xlsx"
        sraw["self_member"] = dict(sraw["artifact_generation"]["members"][0])
        _write_raw_sidecar(single, sraw)
        traversal = cm.read_comparison_outcome(single)
        check("unsafe/traversing relative_path fails closed before peer lookup",
              traversal is not None and not traversal.trusted
              and traversal.completion == "partial")
        check("republishing repairs unsafe member table", cm.write_comparison_outcomes(single_result))

        sraw = _raw_sidecar(single)
        sraw["unexpected_outer_field"] = "must require a schema bump"
        _write_raw_sidecar(single, sraw)
        unknown_outer = cm.read_comparison_outcome(single)
        check("unknown final outer key is rejected by the versioned schema",
              unknown_outer is not None and not unknown_outer.trusted
              and "outer fields" in (unknown_outer.diagnostic or ""))
        check("republishing repairs unknown outer key", cm.write_comparison_outcomes(single_result))

        planted_outcome = _payload_value(single)
        planted_outcome["warnings"] = ["coverage warning planted on complete"]
        _install_payload((single,), planted_outcome)
        complete_warning = cm.read_comparison_outcome(single)
        check("complete typed outcome with warnings/failures is not trusted",
              complete_warning is not None and not complete_warning.trusted
              and complete_warning.completion == "partial")
        check("republishing repairs contradictory complete warning",
              cm.write_comparison_outcomes(single_result))

        prepared_single = cm._prepare_comparison_publication(single_result)
        smember, _sworkbook, sfacts = prepared_single["members"][0]
        sentinel_extra = cm._comparison_sentinel_payload(
            prepared_single, smember, sfacts)
        sentinel_extra["unexpected_outer_field"] = True
        cm._sentinel_path(single).write_text(
            json.dumps(sentinel_extra), encoding="utf-8")
        unknown_sentinel = cm.read_comparison_outcome(single)
        check("unknown sentinel outer key remains partial/untrusted",
              unknown_sentinel is not None and not unknown_sentinel.trusted
              and unknown_sentinel.source == "sentinel"
              and "outer fields" in (unknown_sentinel.diagnostic or ""))
        cm._sentinel_path(single).unlink()
        check("trusted final is visible again after foreign sentinel removal",
              cm.read_comparison_outcome(single).trusted)

        cm.write_outcome(single, ConsolidateResult(status="ok", completion="complete"))
        ordinary_replacement = cm.read_comparison_outcome(single)
        check("ordinary-looking current replacement record is never trusted as comparison",
              ordinary_replacement is not None and not ordinary_replacement.trusted
              and ordinary_replacement.completion == "partial")
        check("republishing restores strict comparison record",
              cm.write_comparison_outcomes(single_result))

        old_stat = single.stat()
        os.utime(single, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 5_000_000_000))
        check("demonstrably stale old sidecar returns None",
              cm.read_comparison_outcome(single) is None and cm.read_completion(single) is None)
        os.utime(single, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        check("restoring the bound generation mtime restores trust",
              cm.read_comparison_outcome(single).trusted)

        print("all-member-safe publication failure protocol:")
        blocked = root / "payload-no-clobber.xlsx"
        blocked.write_bytes(b"PK-payload-no-clobber")
        blocked_result = _result(
            (("values", blocked),), "values", "g-payload-no-clobber")
        blocked_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=3),
            pairing_quality="exact")
        blocked_prepared = cm._prepare_comparison_publication(blocked_result)
        blocked_relative, _blocked_bytes = blocked_prepared["payload_chunks"][0]
        blocked_chunk = root / blocked_relative
        blocked_chunk.write_bytes(b"foreign-preexisting-bytes")
        foreign_bytes = blocked_chunk.read_bytes()
        check("wrong pre-existing primary selects a bounded fallback publication",
              cm.write_comparison_outcomes(blocked_result))
        fallback_raw = _raw_sidecar(blocked)
        fallback_manifest = fallback_raw["comparison_payload"]
        fallback_relative = fallback_manifest["chunks"][0]["relative_path"]
        fallback_path = root / fallback_relative
        fallback_prefix = (
            f".cmpv3-{fallback_manifest['decoded_sha256']}-000000-"
            f"{fallback_manifest['chunks'][0]['sha256']}-f-")
        check("fallback is a strict bounded slot and never clobbers the conflicting primary",
              blocked_chunk.read_bytes() == foreign_bytes
              and fallback_relative == fallback_prefix + "00" + cm._COMPARISON_PAYLOAD_SUFFIX
              and fallback_relative.endswith(cm._COMPARISON_PAYLOAD_SUFFIX)
              and fallback_path.is_file()
              and cm.read_comparison_outcome(blocked).trusted)
        first_fallback = fallback_relative
        first_fallback_stat = fallback_path.stat()
        check("same-result retry reuses one slot without leak or poisoned-primary deletion",
              cm.write_comparison_outcomes(blocked_result)
              and blocked_chunk.read_bytes() == foreign_bytes
              and cm.read_comparison_outcome(blocked).trusted
              and _raw_sidecar(blocked)["comparison_payload"]["chunks"][0]
                  ["relative_path"] == first_fallback
              and fallback_path.stat().st_mtime_ns == first_fallback_stat.st_mtime_ns
              and len(tuple(root.glob(
                  fallback_prefix + "*" + cm._COMPARISON_PAYLOAD_SUFFIX))) == 1)

        # Existing schema-v3 records may already name the older binding+nonce
        # fallback. Readers retain compatibility even though writers no longer
        # create a fresh nonce on every retry.
        legacy_relative = (
            fallback_prefix + fallback_manifest["binding_sha256"] + "-" + "d" * 16
            + cm._COMPARISON_PAYLOAD_SUFFIX)
        (root / legacy_relative).write_bytes(fallback_path.read_bytes())
        legacy_raw = _raw_sidecar(blocked)
        legacy_raw["comparison_payload"]["chunks"][0]["relative_path"] = legacy_relative
        _write_raw_sidecar(blocked, legacy_raw)
        check("legacy binding+nonce fallback manifests remain readable",
              cm.read_comparison_outcome(blocked).trusted)
        check("republishing legacy fallback converges back to bounded slot 00",
              cm.write_comparison_outcomes(blocked_result)
              and _raw_sidecar(blocked)["comparison_payload"]["chunks"][0]
                  ["relative_path"] == first_fallback)

        exhausted = root / "payload-fallback-exhausted.xlsx"
        exhausted.write_bytes(b"PK-payload-fallback-exhausted")
        exhausted_result = _result(
            (("values", exhausted),), "values", "g-payload-fallback-exhausted")
        exhausted_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=456),
            pairing_quality="exact")
        exhausted_prepared = cm._prepare_comparison_publication(exhausted_result)
        exhausted_descriptor = exhausted_prepared["payload_manifest"]["chunks"][0]
        exhausted_relative, _exhausted_bytes = exhausted_prepared["payload_chunks"][0]
        exhausted_primary = root / exhausted_relative
        exhausted_primary.write_bytes(b"foreign-primary")
        exhausted_slots = []
        exhausted_base = (
            f".cmpv3-{exhausted_prepared['payload_manifest']['decoded_sha256']}-000000-"
            f"{exhausted_descriptor['sha256']}-f-")
        for slot in range(cm._PAYLOAD_FALLBACK_SLOT_COUNT):
            slot_path = root / (
                exhausted_base + f"{slot:02d}" + cm._COMPARISON_PAYLOAD_SUFFIX)
            slot_path.write_bytes(f"foreign-slot-{slot}".encode("ascii"))
            exhausted_slots.append(slot_path)
        exhausted_before = {path: path.read_bytes()
                            for path in (exhausted_primary, *exhausted_slots)}
        check("all eight poisoned fallback slots fail closed without clobber",
              cm.write_comparison_outcomes(exhausted_result) is False
              and all(path.read_bytes() == value
                      for path, value in exhausted_before.items())
              and cm._sentinel_path(exhausted).is_file())
        for path in (exhausted_primary, *exhausted_slots):
            path.unlink()
        check("retry after bounded-slot conflicts are removed succeeds",
              cm.write_comparison_outcomes(exhausted_result)
              and cm.read_comparison_outcome(exhausted).trusted)
        blocked_chunk.unlink()
        check("removing the conflict lets the stable primary publish again",
              cm.write_comparison_outcomes(blocked_result)
              and cm.read_comparison_outcome(blocked).trusted)
        exact_chunk = _payload_chunk_paths(blocked)[0]
        exact_stat = exact_chunk.stat()
        exact_bytes = exact_chunk.read_bytes()
        check("byte-identical existing chunks are reused without replacement",
              cm.write_comparison_outcomes(blocked_result)
              and exact_chunk.read_bytes() == exact_bytes
              and cm._entry_identity(exact_chunk.stat())
                  == cm._entry_identity(exact_stat)
              and exact_chunk.stat().st_mtime_ns == exact_stat.st_mtime_ns)

        print("parent-scoped publication lease + exact winning generation:")
        publication_lock = root / cm._COMPARISON_PUBLICATION_LOCK_NAME
        lock_identity = cm._ordinary_file_stat(publication_lock)
        check("successful publication retains one permanent ordinary lock anchor",
              lock_identity is not None and publication_lock.is_file())

        local_book = root / "local-overlap.xlsx"
        local_book.write_bytes(b"PK-local-overlap")
        local_result = _result(
            (("values", local_book),), "values", "g-local-overlap")
        local_done = threading.Event()
        local_values = []

        def publish_local_overlap():
            local_values.append(cm.write_comparison_outcomes(local_result))
            local_done.set()

        with cm._comparison_publication_lease(root):
            local_thread = threading.Thread(target=publish_local_overlap, daemon=True)
            local_thread.start()
            time.sleep(0.15)
            local_was_blocked = not local_done.is_set()
        local_thread.join(timeout=10)
        check("overlapping local thread waits for the held parent lease",
              local_was_blocked and local_done.is_set() and local_values == [True]
              and cm.read_comparison_outcome(local_book).trusted)

        process_root = root / "process-overlap"
        process_root.mkdir()
        process_book = process_root / "process-overlap.xlsx"
        process_book.write_bytes(b"PK-process-overlap")
        process_result = _result(
            (("values", process_book),), "values", "g-process-overlap")
        held_marker = process_root / "holder-ready"
        release_marker = process_root / "holder-release"
        child_code = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import consolidation_meta as cm
parent, held, release = map(Path, sys.argv[2:5])
with cm._comparison_publication_lease(parent):
    held.write_text('held', encoding='ascii')
    while not release.exists():
        time.sleep(0.02)
"""
        child = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-c", child_code,
             str(ROOT / "scripts"), str(process_root),
             str(held_marker), str(release_marker)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 10
        while (not held_marker.exists() and child.poll() is None
               and time.monotonic() < deadline):
            time.sleep(0.02)
        process_ready = held_marker.exists()
        process_done = threading.Event()
        process_values = []

        def publish_process_overlap():
            process_values.append(cm.write_comparison_outcomes(process_result))
            process_done.set()

        process_thread = None
        if process_ready:
            process_thread = threading.Thread(
                target=publish_process_overlap, daemon=True)
            process_thread.start()
            time.sleep(0.2)
        process_was_blocked = process_ready and not process_done.is_set()
        release_marker.write_text("release", encoding="ascii")
        try:
            child_stdout, child_stderr = child.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child_stdout, child_stderr = child.communicate()
        if process_thread is not None:
            process_thread.join(timeout=10)
        check("separate process byte-range lock serializes publication",
              process_was_blocked and child.returncode == 0
              and process_done.is_set() and process_values == [True]
              and cm.read_comparison_outcome(process_book).trusted)
        if child.returncode != 0:
            print("    child lock stderr:", child_stderr.strip() or child_stdout.strip())

        winner_book = root / "trusted-winner.xlsx"
        winner_book.write_bytes(b"PK-trusted-winner")
        losing_result = _result(
            (("values", winner_book),), "values", "generation-loser")
        winning_result = _result(
            (("values", winner_book),), "values", "generation-winner")
        winning_result.verdict = "diff"
        winning_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="diff",
            counts=ComparisonCounts(
                known=True, paired_rows=2, differing_rows=1,
                differing_cells=1, per_field_counts={"0:X": 1},
                asserted_cells=1),
            pairing_quality="exact")
        winning_prepared = cm._prepare_comparison_publication(winning_result)
        for descriptor, (relative, raw) in zip(
                winning_prepared["payload_manifest"]["chunks"],
                winning_prepared["payload_chunks"]):
            check("winning fixture payload path agrees with its manifest",
                  descriptor["relative_path"] == relative)
            (root / relative).write_bytes(raw)
        winning_member, _winning_path, winning_facts = winning_prepared["members"][0]
        original_safe_unlink = cm._safe_unlink_sidecar
        winner_installed = []

        def install_trusted_winner_after_cleanup(path, commit_guard=None):
            removed = original_safe_unlink(path, commit_guard)
            if (removed and Path(path) == cm._sentinel_path(winner_book)
                    and not winner_installed):
                winner_installed.append(True)
                cm._atomic_write_json(
                    cm.meta_path(winner_book),
                    cm._comparison_final_payload(
                        winning_prepared, winning_member, winning_facts))
            return removed

        cm._safe_unlink_sidecar = install_trusted_winner_after_cleanup
        try:
            loser_claim = cm.write_comparison_outcomes(losing_result)
        finally:
            cm._safe_unlink_sidecar = original_safe_unlink
        winning_record = cm.read_comparison_outcome(winner_book)
        check("superseded attempt cannot claim a different trusted generation",
              loser_claim is False and winner_installed
              and winning_record is not None and winning_record.trusted
              and winning_record.artifact_generation.generation_id
                  == "generation-winner"
              and winning_record.comparison_outcome
                  == winning_result.comparison_outcome)
        check("superseded attempt does not poison/quarantine the trusted winner",
              winner_book.is_file() and not cm._sentinel_path(winner_book).exists())

        crashsafe = root / "payload-crashsafe.xlsx"
        crashsafe.write_bytes(b"PK-payload-crashsafe")
        crashsafe_result = _result(
            (("values", crashsafe),), "values", "g-payload-crashsafe")
        crashsafe_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=987),
            pairing_quality="exact")
        crashsafe_prepared = cm._prepare_comparison_publication(crashsafe_result)
        crashsafe_relative, _crashsafe_bytes = (
            crashsafe_prepared["payload_chunks"][0])
        crashsafe_primary = root / crashsafe_relative
        original_write = cm.os.write
        original_temp_cleanup = cm._unlink_bound_payload_temp
        partial_writes = []

        def fail_after_partial_temp_write(fd, data):
            data = bytes(data)
            partial_writes.append(len(data))
            original_write(fd, data[:max(1, len(data) // 2)])
            raise OSError("simulated kill during payload temp write")

        cm.os.write = fail_after_partial_temp_write
        cm._unlink_bound_payload_temp = lambda *_args, **_kwargs: None
        try:
            interrupted = cm.write_comparison_outcomes(crashsafe_result)
        finally:
            cm.os.write = original_write
            cm._unlink_bound_payload_temp = original_temp_cleanup
        partial_temps = tuple(root.glob(".cmpv3-payload.tmp-*"))
        check("partial temp failure cannot reserve/poison the deterministic final",
              interrupted is False and partial_writes
              and not crashsafe_primary.exists()
              and partial_temps
              and all(0 < item.stat().st_size < len(_crashsafe_bytes)
                      for item in partial_temps))
        check("retry succeeds with partial temp residue still present",
              cm.write_comparison_outcomes(crashsafe_result)
              and crashsafe_primary.is_file()
              and cm.read_comparison_outcome(crashsafe).trusted
              and all(item.exists() for item in partial_temps))
        for item in partial_temps:
            item.unlink()

        install_race = root / "payload-install-race.xlsx"
        install_race.write_bytes(b"PK-payload-install-race")
        install_result = _result(
            (("values", install_race),), "values", "g-payload-install-race")
        install_result.comparison_outcome = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=988),
            pairing_quality="exact")
        install_prepared = cm._prepare_comparison_publication(install_result)
        install_descriptor = install_prepared["payload_manifest"]["chunks"][0]
        install_relative, install_bytes = install_prepared["payload_chunks"][0]
        install_path = root / install_relative
        original_install = cm._install_payload_temp_no_replace
        install_races = []

        def race_exact_destination(source, destination):
            install_races.append(Path(source))
            Path(destination).write_bytes(install_bytes)
            return original_install(source, destination)

        cm._install_payload_temp_no_replace = race_exact_destination
        try:
            race_reused = cm._publish_payload_chunk(
                install_path, install_bytes, install_descriptor)
        finally:
            cm._install_payload_temp_no_replace = original_install
        check("atomic install race reuses only the byte-identical winner",
              race_reused and install_races
              and install_path.read_bytes() == install_bytes
              and not list(root.glob(".cmpv3-payload.tmp-*")))

        blocked_prepared = cm._prepare_comparison_publication(blocked_result)
        bmember, _bworkbook, bfacts = blocked_prepared["members"][0]
        check("sentinel-first fixture is established",
              cm._atomic_write_json(
                  cm._sentinel_path(blocked),
                  cm._comparison_sentinel_payload(
                      blocked_prepared, bmember, bfacts)))
        original_payload_reader = cm._read_comparison_payload
        payload_reads = []

        def forbidden_payload_read(*_args, **_kwargs):
            payload_reads.append(True)
            raise AssertionError("sentinel must short-circuit payload decompression")

        cm._read_comparison_payload = forbidden_payload_read
        try:
            sentinel_first = cm.read_comparison_outcome(blocked)
        finally:
            cm._read_comparison_payload = original_payload_reader
        check("current sentinel returns partial before any payload decompression",
              sentinel_first is not None and not sentinel_first.trusted
              and sentinel_first.source == "sentinel" and not payload_reads)
        cm._sentinel_path(blocked).unlink()
        check("trusted final returns after sentinel-first fixture cleanup",
              cm.read_comparison_outcome(blocked).trusted)

        race_parent = root / "payload-race"
        race_parent.mkdir()
        race_moved = root / "payload-race-original"
        race_descriptor = blocked_prepared["payload_manifest"]["chunks"][0]
        race_relative, race_bytes = blocked_prepared["payload_chunks"][0]
        race_path = race_parent / race_relative
        captured_parent = cm._entry_identity(race_parent.stat())
        path_checks = []

        def replace_before_exclusive_create(target):
            target = Path(target)
            if target == race_path:
                path_checks.append(True)
                if len(path_checks) == 2:
                    race_parent.rename(race_moved)
                    race_parent.mkdir()
            try:
                return cm._entry_identity(race_parent.stat()) == captured_parent
            except OSError:
                return False

        check("payload chunk guard is rechecked immediately before exclusive create",
              cm._publish_payload_chunk(
                  race_path, race_bytes, race_descriptor,
                  replace_before_exclusive_create) is False
              and len(path_checks) >= 2)
        check("parent replacement race writes no payload into either directory",
              not race_path.exists()
              and not (race_moved / race_relative).exists())

        lock_result = _result(
            (("formulas", formulas), ("values", values)), "both", "g-lock")
        original_replace = cm.os.replace
        locked_final = cm.meta_path(values)

        def fail_second_final(source, destination):
            if Path(destination) == locked_final:
                raise PermissionError("second final locked")
            return original_replace(source, destination)

        cm.os.replace = fail_second_final
        try:
            published = cm.write_comparison_outcomes(lock_result)
        finally:
            cm.os.replace = original_replace
        check("one locked final makes publication return False", published is False)
        check("all fixed sentinels remain after sequential-final failure",
              cm._sentinel_path(formulas).is_file()
              and cm._sentinel_path(values).is_file())
        check("both opening orders remain partial/untrusted while publication is incomplete",
              cm.read_completion(formulas) == "partial"
              and cm.read_completion(values) == "partial"
              and not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        check("locked-sidecar failure never changes workbook bytes",
              _same_bytes((formulas, values), both_before))
        check("retry publishes the full generation and clears sentinels",
              cm.write_comparison_outcomes(lock_result)
              and not cm._sentinel_path(formulas).exists()
              and not cm._sentinel_path(values).exists())

        initial_result = _result(
            (("formulas", formulas), ("values", values)), "both", "g-initial-fail")
        locked_sentinel = cm._sentinel_path(values)

        def fail_second_sentinel(source, destination):
            if Path(destination) == locked_sentinel:
                raise PermissionError("second sentinel locked")
            return original_replace(source, destination)

        cm.os.replace = fail_second_sentinel
        try:
            initial_ok = cm.write_comparison_outcomes(initial_result)
        finally:
            cm.os.replace = original_replace
        check("failure to establish every initial sentinel returns False", initial_ok is False)
        check("already-sentinelled member is partial", cm.read_completion(formulas) == "partial")
        check("unprotected member receives an emergency partial marker",
              cm.read_completion(values) == "partial")
        check("retry after initial-sentinel failure restores a trusted generation",
              cm.write_comparison_outcomes(initial_result)
              and cm.read_comparison_outcome(formulas).trusted
              and cm.read_comparison_outcome(values).trusted)

        quarantine = root / "quarantine-on-sentinel-failure.xlsx"
        quarantine.write_bytes(b"PK-only-committed-copy")
        quarantine_bytes = quarantine.read_bytes()
        quarantine_result = _result(
            (("values", quarantine),), "values", "g-quarantine")
        quarantine_sentinel = cm._sentinel_path(quarantine)
        original_marker = cm._mark_untrusted

        def fail_quarantine_sentinel(source, destination):
            if Path(destination) == quarantine_sentinel:
                raise PermissionError("sentinel and marker unavailable")
            return original_replace(source, destination)

        cm.os.replace = fail_quarantine_sentinel
        cm._mark_untrusted = lambda *_args, **_kwargs: False
        try:
            quarantine_ok = cm.write_comparison_outcomes(quarantine_result)
        finally:
            cm.os.replace = original_replace
            cm._mark_untrusted = original_marker
        quarantined = quarantine.with_name(quarantine.name + ".unverified")
        check("sentinel+marker failure never claims publication success",
              quarantine_ok is False)
        check("...unprotectable committed workbook is quarantined, not false-green",
              not quarantine.exists() and quarantined.is_file()
              and quarantined.read_bytes() == quarantine_bytes)

        print()
        if _failures:
            print(f"FAILED: {len(_failures)} check(s): {_failures}")
            return 1
        print("ALL COMPARISON-SIDECAR CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
