"""End-to-end gate for comparison artifact + strict-sidecar publication.

Unlike ``check_comparison_sidecars.py`` (which exercises the metadata boundary
directly), this check enters through the production ``commit_workbook`` transaction.
It proves that every typed formulas/values member is published and readable as one
strict generation, and that a metadata interruption is visible and fail-closed.

No browser/network. Run from the repository root:
    build\\.venv\\Scripts\\python.exe build\\check_comparison_publication.py
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from _checklib import write_comparison_stub  # noqa: E402

import artifact_store  # noqa: E402
import consolidation_meta  # noqa: E402
from comparison_contract import AttemptState, ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402


_failures: list[str] = []


def check(name: str, condition: bool) -> None:
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)


@contextlib.contextmanager
def _patch(obj, attr, value):
    old = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        setattr(obj, attr, old)


def _save(path: Path, value: str) -> bytes:
    # `value` distinguishes the flavors only in the caller's bookkeeping; the
    # bytes must satisfy the comparison-artifact schema either way.
    write_comparison_stub(path, rows=1 + (len(value) % 3))
    return path.read_bytes()


def _typed_result(path: Path) -> ConsolidateResult:
    outcome = ComparisonOutcome(
        status="ok",
        completion="complete",
        verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=1),
        pairing_quality="exact",
    )
    return ConsolidateResult(
        status="ok",
        output_path=str(path),
        verdict="match",
        completion="complete",
        skipped_inputs=0,
        failed_inputs=0,
        comparison_outcome=outcome,
    )


def _produce(mode: str, expected: dict[str, bytes]):
    def producer(path: Path):
        expected["formulas" if mode in ("formulas", "both") else "values"] = (
            _save(path, f"{mode}-primary")
        )
        if mode == "both":
            expected["values"] = _save(
                artifact_store._values_twin(path), "both-values")
        return _typed_result(path)

    return producer


def _assert_generation(mode: str, final: Path, result, expected) -> None:
    members = tuple(result.artifact_generation.members)
    expected_paths = (
        (("values", artifact_store._values_twin(final)),
         ("formulas", final))
        if mode == "both" else ((mode, final),)
    )
    check(f"{mode}: transaction returns a committed succeeded generation",
          result.status == "ok"
          and result.artifact_generation.publication_state == "committed"
          and result.artifact_generation.requested_mode == mode
          and result.attempt_state.state == "succeeded"
          and result.attempt_state.generation_id
          == result.artifact_generation.generation_id)
    check(f"{mode}: exact committed member order and bytes survive publication",
          tuple(member["flavor"] for member in members)
          == tuple(flavor for flavor, _path in expected_paths)
          and all(path.read_bytes() == expected[flavor]
                  for flavor, path in expected_paths))

    strict = [consolidation_meta.read_comparison_outcome(path)
              for _flavor, path in expected_paths]
    check(f"{mode}: every member strict-reads the same typed generation",
          all(record is not None and record.trusted and record.current
              and record.comparison_outcome == result.comparison_outcome
              and record.artifact_generation == result.artifact_generation
              for record in strict)
          and len({record.artifact_generation.generation_id
                   for record in strict}) == 1)
    check(f"{mode}: shared consumer reducer accepts returned + persisted truth",
          consolidation_meta.require_published_comparison(
              expected_paths[0][1], result).artifact_generation
          == result.artifact_generation)
    check(f"{mode}: compatibility reader delegates without losing completion",
          all(consolidation_meta.read_outcome(path).trusted
              and consolidation_meta.read_completion(path) == "complete"
              for _flavor, path in expected_paths))
    check(f"{mode}: successful publication leaves no fixed sentinel",
          all(not consolidation_meta._sentinel_path(path).exists()
              for _flavor, path in expected_paths))


def _successful_modes(root: Path) -> None:
    print("production artifact transaction publishes strict comparison generations:")
    for mode in ("formulas", "values", "both"):
        final = root / f"{mode}.xlsx"
        expected: dict[str, bytes] = {}
        result = artifact_store.commit_workbook(
            final,
            _produce(mode, expected),
            twin=(mode == "both"),
            expect_sheet="Comparison",
            requested_mode=mode,
        )
        _assert_generation(mode, final, result, expected)
        if mode == "values":
            original_attempt = result.attempt_state
            result.attempt_state = AttemptState(
                state="succeeded", generation_id="wrong-generation")
            try:
                consolidation_meta.require_published_comparison(final, result)
            except ValueError:
                rejected = True
            else:
                rejected = False
            finally:
                result.attempt_state = original_attempt
            check("values: mismatched attempt generation is rejected", rejected)

    uppercase = root / "CORE-ID-78-Uppercase.xlsx"
    expected = {}
    uppercase_result = artifact_store.commit_workbook(
        uppercase, _produce("values", expected),
        expect_sheet="Comparison", requested_mode="values")
    uppercase_record = consolidation_meta.read_comparison_outcome(uppercase)
    check("Windows canonical normcase does not reject an uppercase basename",
          uppercase_result.status == "ok"
          and uppercase_record is not None and uppercase_record.trusted
          and uppercase_record.artifact_generation
              == uppercase_result.artifact_generation)


def _interrupted_publication(root: Path) -> None:
    print("metadata interruption is visible and leaves the workbook untrusted:")
    final = root / "interrupted.xlsx"
    expected: dict[str, bytes] = {}
    real_atomic = consolidation_meta._atomic_write_json

    def fail_final(path, payload, commit_guard=None):
        if (Path(path) == consolidation_meta.meta_path(final)
                and payload.get("publication_sentinel") is not True):
            return False
        return real_atomic(path, payload, commit_guard)

    with _patch(consolidation_meta, "_atomic_write_json", fail_final):
        result = artifact_store.commit_workbook(
            final,
            _produce("values", expected),
            expect_sheet="Comparison",
            requested_mode="values",
        )

    record = consolidation_meta.read_comparison_outcome(final)
    check("publication failure is not returned as success",
          result.status == "error"
          and result.artifact_generation.publication_state == "partial"
          and result.attempt_state.state == "failed")
    check("comparison truth survives independently of publication failure",
          result.comparison_outcome is not None
          and result.comparison_outcome.completion == "complete"
          and result.comparison_outcome.verdict == "match")
    check("committed workbook bytes are never rewritten by failed metadata",
          final.read_bytes() == expected["values"])
    check("strict and compatibility readers expose only untrusted partial state",
          record is not None and not record.trusted
          and record.completion == "partial"
          and record.comparison_outcome is None
          and consolidation_meta.read_completion(final) == "partial")
    check("fixed sentinel remains to dominate any incomplete final publication",
          consolidation_meta._sentinel_path(final).exists())


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tsmis_comparison_publication_") as raw:
        root = Path(raw)
        _successful_modes(root)
        _interrupted_publication(root)
    if _failures:
        print(f"\nFAILED {len(_failures)} check(s): {_failures}")
        raise SystemExit(1)
    print("\nALL END-TO-END COMPARISON PUBLICATION CHECKS PASSED")


if __name__ == "__main__":
    main()
