"""Schema-v3 comparison payload scale regression.

Builds the real typed shape that crossed the legacy 16 MiB inline sidecar
boundary: 41,000 exact 2x2 duplicate groups (82,000 rows per side). The v3
publisher must retain every full PairingTrace while storing one shared,
strictly-bound chunk set for a formulas/values generation.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import consolidation_meta as cm  # noqa: E402
from comparison_contract import (  # noqa: E402
    ArtifactGeneration,
    ComparisonCounts,
    ComparisonOutcome,
    EXACT_PAIRING_ALGORITHM,
    PairingPair,
    PairingTrace,
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
    st = path.stat()
    return {
        "flavor": flavor,
        "relative_path": path.name,
        "path": str(path),
        "canonical_path_at_write": str(path.resolve()),
        "commit_role": "best_effort" if flavor == "formulas" else "canonical",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


def _trace(index):
    source = index * 2
    return PairingTrace(
        key_components=(f"K{index}",),
        side_a_size=2,
        side_b_size=2,
        matrix_cells=4,
        side_a_indices=(source, source + 1),
        side_b_indices=(source, source + 1),
        smaller_side="a",
        assignment_vector=(0, 1),
        pairs=(
            PairingPair(source, source, 0),
            PairingPair(source + 1, source + 1, 0),
        ),
        total_cost=0,
        positional_cost=0,
        algorithm=EXACT_PAIRING_ALGORITHM,
        exact=True,
        quality="exact",
    )


def main():
    group_count = 41_000
    print(f"constructing {group_count:,} exact duplicate traces:")
    traces = tuple(_trace(index) for index in range(group_count))
    outcome = ComparisonOutcome(
        status="ok",
        completion="complete",
        verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=group_count * 2),
        pairing_trace=traces,
        duplicate_group_count=group_count,
        pairing_quality="exact",
    )

    with tempfile.TemporaryDirectory(prefix="tsmis_sidecar_scale_") as raw:
        root = Path(raw)
        formulas = root / "scale.xlsx"
        values = root / "scale (values).xlsx"
        formulas.write_bytes(b"PK-scale-formulas")
        values.write_bytes(b"PK-scale-values")
        members = (_member(values, "values"), _member(formulas, "formulas"))
        generation = ArtifactGeneration(
            generation_id="scale-41000-exact-groups",
            members=members,
            content_digests={item["flavor"]: item["sha256"] for item in members},
            completion="complete",
            producer_versions={"comparison": "schema-v3-scale-gate"},
            publication_state="committed",
            requested_mode="both",
        )
        result = ConsolidateResult(
            status="ok",
            output_path=str(formulas),
            verdict="match",
            completion="complete",
            skipped_inputs=0,
            failed_inputs=0,
            comparison_outcome=outcome,
            artifact_generation=generation,
        )

        print("legacy-boundary precondition:")
        prepared = cm._prepare_comparison_publication(result)
        member, _workbook, facts = prepared["members"][0]
        legacy_raw = cm._canonical_json_bytes(
            cm._comparison_final_payload_v2(prepared, member, facts))
        check("the exact inline schema-v2 final exceeds 16 MiB",
              len(legacy_raw) > cm._MAX_COMPARISON_SIDECAR_BYTES)
        check("every group remains individually exact and under the assignment cap",
              all(trace.exact and trace.matrix_cells == 4 for trace in traces))

        print("schema-v3 shared payload publication:")
        check("large both-mode generation publishes successfully",
              cm.write_comparison_outcomes(result))
        formula_record = cm.read_comparison_outcome(formulas)
        values_record = cm.read_comparison_outcome(values)
        check("both member opening orders strict-round-trip every typed trace",
              formula_record is not None and formula_record.trusted
              and values_record is not None and values_record.trusted
              and formula_record.comparison_outcome == outcome
              and values_record.comparison_outcome == outcome
              and formula_record.comparison_outcome.duplicate_group_count
                  == group_count
              and len(formula_record.comparison_outcome.pairing_trace)
                  == group_count)

        fraw = json.loads(cm.meta_path(formulas).read_text(encoding="utf-8"))
        vraw = json.loads(cm.meta_path(values).read_text(encoding="utf-8"))
        manifest = fraw["comparison_payload"]
        compressed_total = sum(item["size"] for item in manifest["chunks"])
        chunk_paths = tuple(root / item["relative_path"]
                            for item in manifest["chunks"])
        check("measured 41,000-trace shape remains the 16.8 MiB five-chunk boundary",
              manifest["decoded_size"] == 16_795_872
              and len(manifest["chunks"]) == 5)
        check("measured ~16.836:1 expansion remains inside the 32:1 preflight gate",
              compressed_total <= 1_100_000
              and manifest["decoded_size"]
                  <= compressed_total
                    * cm._MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO)
        check("member envelopes stay bounded schema-v3 JSON",
              fraw["comparison_schema_version"] == 3
              and vraw["comparison_schema_version"] == 3
              and cm.meta_path(formulas).stat().st_size
                  <= cm._MAX_COMPARISON_SIDECAR_BYTES
              and cm.meta_path(values).stat().st_size
                  <= cm._MAX_COMPARISON_SIDECAR_BYTES)
        check("both members reference one exact multi-chunk manifest",
              manifest == vraw["comparison_payload"]
              and len(chunk_paths) >= 2
              and len(set(chunk_paths)) == len(chunk_paths)
              and all(path.is_file() for path in chunk_paths)
              and all(path.name.endswith(cm._COMPARISON_PAYLOAD_SUFFIX)
                      for path in chunk_paths))

        clean_fraw = cm.meta_path(formulas).read_bytes()
        clean_vraw = cm.meta_path(values).read_bytes()
        reordered = json.loads(clean_fraw.decode("utf-8"))
        reordered["comparison_payload"]["chunks"][0], \
            reordered["comparison_payload"]["chunks"][1] = (
                reordered["comparison_payload"]["chunks"][1],
                reordered["comparison_payload"]["chunks"][0],
            )
        cm.meta_path(formulas).write_text(
            json.dumps(reordered, sort_keys=True, separators=(",", ":")),
            encoding="utf-8")
        check("reordered chunks make the generation untrusted before decompression",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        cm.meta_path(formulas).write_bytes(clean_fraw)

        duplicated = json.loads(clean_fraw.decode("utf-8"))
        duplicated["comparison_payload"]["chunks"][1] = dict(
            duplicated["comparison_payload"]["chunks"][0])
        cm.meta_path(formulas).write_text(
            json.dumps(duplicated, sort_keys=True, separators=(",", ":")),
            encoding="utf-8")
        check("duplicate chunk descriptors make the generation untrusted",
              not cm.read_comparison_outcome(formulas).trusted
              and not cm.read_comparison_outcome(values).trusted)
        cm.meta_path(formulas).write_bytes(clean_fraw)
        cm.meta_path(values).write_bytes(clean_vraw)
        check("restored canonical manifests return the full generation to trust",
              cm.read_comparison_outcome(formulas).trusted
              and cm.read_comparison_outcome(values).trusted)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL COMPARISON-SIDECAR SCALE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
