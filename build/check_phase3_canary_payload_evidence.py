"""Focused gate for the production canary's schema-v3 evidence binding."""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT)]

import artifact_store  # noqa: E402
import consolidation_meta as cm  # noqa: E402
import run_phase3_production_canary as canary  # noqa: E402
from check_comparison_publication import _produce  # noqa: E402


_failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)


def _rejects(call):
    try:
        call()
    except (AssertionError, ValueError):
        return True
    return False


def main():
    print("Phase-3 production-canary schema-v3 evidence binding:")
    with tempfile.TemporaryDirectory(prefix="tsmis_canary_payload_") as raw:
        root = Path(raw)
        formulas = root / "CORE-ID-78-XLSX-TSN-formulas.xlsx"
        expected = {}
        result = artifact_store.commit_workbook(
            formulas, _produce("both", expected), twin=True,
            expect_sheet="Comparison", requested_mode="both")
        values = artifact_store._values_twin(formulas)

        publication, chunk_paths, lock_path, expected_facts = (
            canary._comparison_payload_evidence(formulas, values, result))
        paths = (
            formulas, cm.meta_path(formulas), values, cm.meta_path(values),
        ) + chunk_paths + (lock_path,)
        artifacts = canary._artifact_table(paths)

        check("helper requires schema v3 and the returned committed generation",
              publication["comparison_schema_version"] == 3
              and publication["record_schema_version"] == cm.SCHEMA_VERSION
              and publication["artifact_generation"]
                  == result.artifact_generation.to_dict()
              and publication["publication_lock"]["relative_path"]
                  == cm._COMPARISON_PUBLICATION_LOCK_NAME)
        check("one shared manifest contributes every unique payload artifact",
              len(chunk_paths)
                  == len(publication["comparison_payload"]["chunks"])
              and len({path.name.casefold() for path in chunk_paths})
                  == len(chunk_paths))
        check("final identity-bound artifact facts equal parsed sidecar/chunk bytes",
              all(artifacts.get(name) == facts
                  for name, facts in expected_facts.items()))
        check("final workbook facts equal every ArtifactGeneration member",
              all(artifacts.get(member["relative_path"]) == {
                      "bytes": member["size"], "sha256": member["sha256"]}
                  for member in result.artifact_generation.members))
        check("case-insensitive artifact-key collisions are rejected",
              _rejects(lambda: canary._artifact_table((formulas, formulas))))

        manifest = publication["comparison_payload"]
        descriptor = manifest["chunks"][0]
        orphan = root / (
            f".cmpv3-{manifest['decoded_sha256']}-000000-"
            f"{descriptor['sha256']}-f-{manifest['binding_sha256']}-"
            f"deadbeefdeadbeef{cm._COMPARISON_PAYLOAD_SUFFIX}")
        orphan.write_bytes(chunk_paths[0].read_bytes())
        check("an unreferenced exact-namespace payload artifact fails the canary",
              _rejects(lambda: canary._comparison_payload_evidence(
                  formulas, values, result)))
        orphan.unlink()

        sentinel = cm._sentinel_path(formulas)
        sentinel.write_bytes(b"foreign-incomplete-publication")
        check("any lingering publication sentinel fails the canary",
              _rejects(lambda: canary._comparison_payload_evidence(
                  formulas, values, result)))

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL PHASE-3 CANARY PAYLOAD-EVIDENCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
