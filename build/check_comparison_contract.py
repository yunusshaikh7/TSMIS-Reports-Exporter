"""Focused Phase-2 gate for typed, fail-closed comparison contracts."""
import ast
import json
import math
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path[:0] = [str(SCRIPTS), str(ROOT)]

import comparison_contract as cc  # noqa: E402
from events import ConsolidateResult  # noqa: E402


def rejects(fn):
    try:
        fn()
    except (TypeError, ValueError):
        return True
    return False


def counts(**changes):
    values = dict(
        known=True, paired_rows=2, side_a_only_rows=0,
        side_b_only_rows=0, differing_rows=0, differing_cells=0,
        per_field_counts={}, asserted_cells=4, context_cells=2)
    values.update(changes)
    return cc.ComparisonCounts(**values)


def main():
    raw_claims_a = (
        cc.RawIdentityClaim("route", "1"),
        cc.RawIdentityClaim("county", "Ora."),
        cc.RawIdentityClaim("postmile", "R01.200"),
    )
    raw_claims_b = (
        cc.RawIdentityClaim("route", "001"),
        cc.RawIdentityClaim("county", "ORA"),
        cc.RawIdentityClaim("postmile", "R1.2"),
    )
    physical_a = cc.make_physical_identity(
        "001", "ORA", "R1.200", raw_claims_a, "001 / ORA / R1.200")
    physical_b = cc.make_physical_identity(
        "001", "ORA", "R1.200", raw_claims_b, "alternate display")
    physical_key_a = cc.physical_key("raw A cell", physical_a)
    physical_key_b = cc.physical_key("raw B cell", physical_b)
    loaded_physical = cc.LoadedSide(
        rows=(("001", physical_key_a, "payload"),), completion="partial")
    source = cc.SourceIdentity(
        recipe_key="cmp:highway_log:tsn", report_key="highway_log",
        role="side_a", format="xlsx", canonical_path=r"C:\inputs\a.xlsx",
        content_digest="a" * 64, producer_version="1", parser_version="2",
        normalizer_version="3", selection_kind="explicit")
    loaded = cc.loaded_side_from_legacy(
        [["001", 1]], declared_schema=("Route", "Value"),
        route_universe=("001",), record_universe=("001:1",),
        completion="complete", source_identity=source,
        raw_identity_claims={"file_id": "7"}, display_metrics={"rows": 1})
    exact = counts()
    diff_counts = counts(
        side_a_only_rows=1, side_b_only_rows=2, differing_rows=1,
        differing_cells=2,
        per_field_counts={"1:Status": 1, "2:Description": 1})
    exact_trace = cc.PairingTrace(
        key_components=("001", "000.100"),
        side_a_size=2, side_b_size=3, matrix_cells=6,
        side_a_indices=(10, 11), side_b_indices=(20, 21, 22),
        smaller_side="a", assignment_vector=(1, 0),
        pairs=(
            cc.PairingPair(side_a_index=10, side_b_index=21, cost=0),
            cc.PairingPair(side_a_index=11, side_b_index=20, cost=2),
        ),
        total_cost=2, positional_cost=3,
        algorithm=cc.EXACT_PAIRING_ALGORITHM, exact=True, quality="exact")
    match = cc.ComparisonOutcome(
        status="ok", completion="complete", verdict="match", counts=exact,
        source_identities=(source,), pairing_quality="exact")
    diff = cc.ComparisonOutcome(
        status="ok", completion="partial", verdict="diff", counts=diff_counts,
        warnings=("route 2 unreadable",), source_identities=(source,),
        pairing_trace=(exact_trace,), duplicate_group_count=1,
        pairing_quality="exact")
    capped_trace = cc.PairingTrace(
        key_components=("317x316",),
        side_a_size=3, side_b_size=2, matrix_cells=6,
        side_a_indices=(30, 31, 32), side_b_indices=(40, 41),
        smaller_side="b", assignment_vector=(0, 1),
        pairs=(
            cc.PairingPair(side_a_index=30, side_b_index=40, cost=2),
            cc.PairingPair(side_a_index=31, side_b_index=41, cost=3),
        ),
        total_cost=5, positional_cost=5,
        algorithm=cc.CAPPED_PAIRING_ALGORITHM, exact=False, quality="capped")
    capped_diagnostic = cc.CappedGroupDiagnostic(
        key_components=("317x316",), side_a_size=3, side_b_size=2,
        matrix_cells=6, cap=5,
        fallback_policy=cc.CAPPED_FALLBACK_POLICY, fallback_cost=5)
    capped = cc.ComparisonOutcome(
        status="ok", completion="partial", verdict="diff",
        counts=counts(
            paired_rows=2, side_a_only_rows=1, differing_rows=2,
            differing_cells=5, per_field_counts={"1:Value": 5},
            asserted_cells=6),
        pairing_trace=(capped_trace,), duplicate_group_count=1,
        pairing_quality="capped",
        capped_group_diagnostics=(capped_diagnostic,))
    generation = cc.ArtifactGeneration(
        generation_id="g1",
        members=({
            "flavor": "values",
            "relative_path": "result (values).xlsx",
            "path": r"C:\out\result (values).xlsx",
            "canonical_path_at_write": r"c:\out\result (values).xlsx",
            "commit_role": "canonical",
            "sha256": "b" * 64,
            "size": 123,
            "mtime_ns": 456,
        },),
        content_digests={"values": "b" * 64}, completion="partial",
        producer_versions={"app": "1"}, publication_state="committed",
        requested_mode="both")
    attempt = cc.AttemptState(state="succeeded", generation_id="g1")

    assert loaded.rows == (("001", 1),) and loaded.is_comparable
    assert exact.identical_rows == 2 and exact.union_rows == 2
    assert diff_counts.identical_rows == 1 and diff_counts.union_rows == 5
    assert match.is_complete and match.is_comparable
    assert not diff.is_complete and diff.is_comparable
    assert capped.pairing_quality == "capped" and capped.is_comparable
    assert exact_trace.pairs == (
        cc.PairingPair(10, 21, 0), cc.PairingPair(11, 20, 2))
    assert exact_trace.assignment_vector == (1, 0)
    assert capped_trace.smaller_side == "b"
    assert capped_trace.pairs == (
        cc.PairingPair(30, 40, 2), cc.PairingPair(31, 41, 3))
    assert ("R|X", "K") != ("R", "X|K")
    assert generation.publication_state == "committed"
    assert attempt.succeeded
    assert physical_a == physical_b and hash(physical_a) == hash(physical_b)
    assert physical_a.display == physical_b.display == "001 / ORA / R1.200"
    assert cc.RawIdentityClaim("typed", True) != cc.RawIdentityClaim("typed", 1)
    assert cc.RawIdentityClaim("typed", 1) != cc.RawIdentityClaim("typed", 1.0)
    assert cc.RawIdentityClaim("typed", -0.0) != cc.RawIdentityClaim("typed", 0.0)
    assert physical_key_a == physical_key_b
    assert hash(physical_key_a) == hash(physical_key_b)
    assert str(physical_key_a) == "raw A cell"
    assert physical_key_a.physical_identity is physical_a
    assert cc.physical_identity_from_key(
        ["001", physical_key_a], 1, 0) is physical_a
    assert cc.physical_identity_from_key(["001", "legacy"], 1, 0) is None
    restored_loaded = cc.from_json(cc.to_json(loaded_physical))
    restored_key = restored_loaded.rows[0][1]
    assert type(restored_key) is cc.PhysicalKey
    assert str(restored_key) == "raw A cell"
    assert restored_key.physical_identity == physical_a
    assert restored_key.physical_identity.raw_claims == raw_claims_a
    assert not (physical_key_a < physical_key_b)
    assert physical_key_a <= physical_key_b
    for compare in (
            lambda: physical_key_a < "legacy",
            lambda: "legacy" < physical_key_a):
        try:
            compare()
        except TypeError:
            pass
        else:
            raise AssertionError("mixed PhysicalKey ordering must fail closed")

    for obj in (
            raw_claims_a[0], physical_a, physical_b,
            source, loaded, loaded_physical, exact, diff_counts,
            exact_trace.pairs[0],
            exact_trace, capped_trace, capped_diagnostic, match, diff, capped,
            generation, attempt):
        encoded = cc.to_json(obj)
        assert encoded == cc.to_json(obj), type(obj).__name__
        assert cc.from_json(encoded) == obj, type(obj).__name__
        payload = cc.to_dict(obj)
        assert payload["schema_version"] == cc.CONTRACT_SCHEMA_VERSION
        assert json.loads(json.dumps(payload)) == payload

    try:
        match.verdict = "diff"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("contract dataclasses must be frozen")

    # CMP-AUD-238: the public decoder must be strict and symmetric with to_json.
    # A canonical counts envelope for mutation.
    counts_env = cc.to_dict(cc.ComparisonCounts(
        known=True, paired_rows=1, differing_rows=1, differing_cells=1,
        per_field_counts={"f": 1}, asserted_cells=1))
    counts_body = json.dumps(counts_env["value"])
    ok_json = json.dumps(counts_env)
    assert cc.from_json(ok_json) is not None      # the canonical form still round-trips
    # non-finite literals are rejected at the parse layer (to_json forbids them too)
    for lit in ("NaN", "Infinity", "-Infinity"):
        bad = ('{"schema_version":%d,"type":"ComparisonCounts","value":%s}'
               % (cc.CONTRACT_SCHEMA_VERSION,
                  counts_body.replace('"differing_cells": 1', f'"differing_cells": {lit}')))
        assert rejects(lambda text=bad: cc.from_json(text)), f"non-finite {lit} accepted"
    # duplicate object keys are rejected, not last-wins
    dup = ('{"schema_version":%d,"schema_version":%d,"type":"ComparisonCounts","value":%s}'
           % (cc.CONTRACT_SCHEMA_VERSION, cc.CONTRACT_SCHEMA_VERSION, counts_body))
    assert rejects(lambda: cc.from_json(dup)), "duplicate top-level key accepted"
    # unknown envelope fields are rejected
    unknown = dict(counts_env, unexpected_field=1)
    assert rejects(lambda: cc.from_dict(unknown)), "unknown envelope field accepted"

    assert rejects(lambda: cc.RawIdentityClaim("", "raw"))
    for invalid_claim_value in (
            [], {}, ("tuple",), math.nan, math.inf, object()):
        assert rejects(lambda value=invalid_claim_value:
                       cc.RawIdentityClaim("raw", value))
    assert rejects(lambda: cc.PhysicalIdentity(
        (("county", "ORA"), ("route", "001"), ("postmile", "1.2")),
        raw_claims_a, "display"))
    assert rejects(lambda: cc.make_physical_identity(
        "001", "", "1.2", raw_claims_a, "display"))
    assert rejects(lambda: cc.make_physical_identity(
        "001", "ORA", "1.2", (), "display"))
    assert rejects(lambda: cc.make_physical_identity(
        "001", "ORA", "1.2", ("untyped",), "display"))
    assert rejects(lambda: cc.make_physical_identity(
        "001", "ORA", "1.2", raw_claims_a, ""))
    assert rejects(lambda: cc.physical_key("display", "not-an-identity"))
    try:
        physical_key_a.physical_identity = physical_b
    except AttributeError:
        pass
    else:
        raise AssertionError("PhysicalKey must be immutable")

    assert rejects(lambda: cc.ComparisonCounts(known=True, paired_rows=-1))
    assert rejects(lambda: cc.ComparisonCounts(paired_rows=1))
    assert rejects(lambda: counts(
        differing_rows=1, differing_cells=1,
        per_field_counts={"1:A": 2}))
    assert rejects(lambda: cc.ComparisonOutcome(
        completion="complete", verdict="match"))
    assert rejects(lambda: cc.ComparisonOutcome(
        completion="partial", verdict="match", counts=exact))
    assert rejects(lambda: cc.ComparisonOutcome(
        completion="complete", verdict="match",
        counts=counts(side_b_only_rows=1)))
    assert rejects(lambda: cc.ComparisonOutcome(
        status="error", completion="complete", verdict="match", counts=exact))
    assert rejects(lambda: cc.LoadedSide(
        completion="complete", skipped_inputs=1))
    assert rejects(lambda: cc.ComparisonOutcome(pairing_quality="magic"))
    for uncertified_quality in (cc.UNKNOWN, "heuristic", "ambiguous"):
        assert rejects(lambda quality=uncertified_quality: cc.ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=exact, pairing_quality=quality))
        assert rejects(lambda quality=uncertified_quality: cc.ComparisonOutcome(
            status="ok", completion="partial", verdict="diff",
            counts=exact, pairing_quality=quality))

    # E2 records are strict about primitive types, canonical sequence shapes,
    # local assignment coordinates, original/global source rows, and cost truth.
    assert rejects(lambda: cc.PairingPair(True, 1, 0))
    assert rejects(lambda: cc.PairingPair(0, -1, 0))
    assert rejects(lambda: cc.PairingPair(0, 1, -1))
    assert rejects(lambda: cc.PairingPair.from_dict({
        "side_a_index": 0, "side_b_index": 1}))
    assert rejects(lambda: cc.PairingPair.from_dict({
        "side_a_index": 0, "side_b_index": 1, "cost": 0,
        "surprise": 1}))
    assert rejects(lambda: replace(exact_trace, key_components=()))
    assert rejects(lambda: replace(exact_trace, key_components=("001", 1)))
    assert rejects(lambda: replace(exact_trace, side_a_size=True))
    assert rejects(lambda: replace(exact_trace, side_a_size=3))
    assert rejects(lambda: replace(exact_trace, matrix_cells=5))
    assert rejects(lambda: replace(exact_trace, smaller_side="b"))
    assert rejects(lambda: replace(exact_trace, assignment_vector=(1,)))
    assert rejects(lambda: replace(exact_trace, assignment_vector=(1, 1)))
    assert rejects(lambda: replace(exact_trace, assignment_vector=(3, 0)))
    assert rejects(lambda: replace(
        exact_trace, side_a_indices=(10, 10)))
    assert rejects(lambda: replace(
        exact_trace,
        pairs=(cc.PairingPair(10, 20, 0),
               cc.PairingPair(11, 21, 2))))
    assert rejects(lambda: replace(exact_trace, total_cost=1))
    assert rejects(lambda: replace(exact_trace, positional_cost=1))
    assert rejects(lambda: replace(exact_trace, algorithm="hungarian"))
    assert rejects(lambda: replace(exact_trace, exact=False))
    assert rejects(lambda: replace(exact_trace, quality="capped"))
    assert rejects(lambda: replace(
        capped_trace, assignment_vector=(1, 0)))
    assert rejects(lambda: replace(capped_trace, total_cost=4))
    assert rejects(lambda: replace(capped_trace, exact=True))
    assert rejects(lambda: replace(
        capped_trace, algorithm=cc.EXACT_PAIRING_ALGORITHM))

    malformed_trace = exact_trace.to_dict()
    malformed_trace["pairs"][0].pop("cost")
    assert rejects(lambda: cc.PairingTrace.from_dict(malformed_trace))
    malformed_trace = exact_trace.to_dict()
    malformed_trace["extra"] = 1
    assert rejects(lambda: cc.PairingTrace.from_dict(malformed_trace))
    malformed_trace = exact_trace.to_dict()
    malformed_trace["pairs"] = ["not-an-object"]
    assert rejects(lambda: cc.PairingTrace.from_dict(malformed_trace))

    assert rejects(lambda: replace(capped_diagnostic, matrix_cells=7))
    assert rejects(lambda: replace(capped_diagnostic, cap=6))
    assert rejects(lambda: replace(capped_diagnostic, cap=True))
    assert rejects(lambda: replace(
        capped_diagnostic, fallback_policy="greedy"))
    bad_capped_shape = capped_diagnostic.to_dict()
    bad_capped_shape.pop("fallback_cost")
    assert rejects(lambda: cc.CappedGroupDiagnostic.from_dict(bad_capped_shape))

    assert rejects(lambda: replace(diff, pairing_quality=cc.UNKNOWN))
    assert rejects(lambda: cc.ComparisonOutcome(
        pairing_trace=(exact_trace,), pairing_quality="exact"))
    assert rejects(lambda: replace(
        diff, counts=counts(
            paired_rows=2, differing_rows=1, differing_cells=1,
            per_field_counts={"1:A": 1})))
    assert rejects(lambda: replace(
        diff, counts=counts(
            paired_rows=2, differing_rows=0, differing_cells=2,
            per_field_counts={"1:A": 2})))
    duplicate_trace_subset = replace(
        diff, counts=counts(
            paired_rows=3, side_b_only_rows=1,
            differing_rows=2, differing_cells=3,
            per_field_counts={"1:A": 3}))
    assert duplicate_trace_subset.pairing_trace == (exact_trace,)
    same_key_trace = replace(
        exact_trace,
        side_a_indices=(100, 101), side_b_indices=(200, 201, 202),
        pairs=(cc.PairingPair(100, 201, 0), cc.PairingPair(101, 200, 2)))
    assert rejects(lambda: replace(
        diff, pairing_trace=(exact_trace, same_key_trace),
        duplicate_group_count=2))
    reused_index_trace = replace(
        exact_trace, key_components=("different",),
        side_b_indices=(200, 201, 202),
        pairs=(cc.PairingPair(10, 201, 0), cc.PairingPair(11, 200, 2)))
    assert rejects(lambda: replace(
        diff, pairing_trace=(exact_trace, reused_index_trace),
        duplicate_group_count=2,
        counts=counts(
            paired_rows=4, differing_rows=2, differing_cells=4,
            per_field_counts={"1:A": 4})))
    assert rejects(lambda: replace(capped, capped_group_diagnostics=()))
    assert rejects(lambda: replace(
        capped, capped_group_diagnostics=(replace(
            capped_diagnostic, fallback_cost=4),)))
    assert rejects(lambda: replace(
        capped, completion="complete", verdict="diff"))
    assert rejects(lambda: replace(capped, verdict="match"))
    assert rejects(lambda: cc.ComparisonOutcome(
        status="ok", completion="partial", verdict="diff",
        counts=counts(), pairing_quality="capped"))

    # The one compatibility migration is explicit and narrow: only the exact
    # Phase-2 loaded-side kind is moved out of the old cap slot.  Generic or
    # malformed dictionaries fail closed instead of being guessed as coverage.
    legacy_coverage = {
        "kind": "loaded_side_coverage", "role": "side_a",
        "completion": "partial", "skipped_inputs": 1,
    }
    explicit_coverage = {"kind": "route_universe", "missing": ["002"]}
    migrated = cc.ComparisonOutcome(
        capped_group_diagnostics=(legacy_coverage,),
        coverage_diagnostics=(explicit_coverage,))
    assert migrated.capped_group_diagnostics == ()
    assert migrated.coverage_diagnostics == (
        explicit_coverage, legacy_coverage)
    assert cc.from_json(cc.to_json(migrated)) == migrated
    assert rejects(lambda: cc.ComparisonOutcome(
        capped_group_diagnostics=({"kind": "mystery"},)))
    assert rejects(lambda: cc.ComparisonOutcome(
        capped_group_diagnostics=({"key_components": ["001"]},)))
    assert rejects(lambda: cc.ComparisonOutcome(
        coverage_diagnostics=("not-an-object",)))
    malformed_outcome = cc.to_dict(diff)
    malformed_outcome["value"]["pairing_trace"][0]["pairs"] = []
    assert rejects(lambda: cc.from_dict(malformed_outcome))

    assert rejects(lambda: cc.ArtifactGeneration(
        generation_id="g", members=(), completion="complete",
        publication_state="committed", requested_mode="values"))
    assert rejects(lambda: cc.from_dict({
        "schema_version": 999, "type": "ComparisonCounts", "value": {}}))
    assert rejects(lambda: cc.from_dict({
        "schema_version": cc.CONTRACT_SCHEMA_VERSION,
        "type": "foreign", "value": {}}))
    bad_sources = cc.to_dict(match)
    bad_sources["value"]["source_identities"] = ["not-an-object"]
    assert rejects(lambda: cc.from_dict(bad_sources))
    bad_members = cc.to_dict(generation)
    bad_members["value"]["members"] = ["not-an-object"]
    assert rejects(lambda: cc.from_dict(bad_members))
    nonfinite = cc.LoadedSide(display_metrics={"bad": math.nan})
    assert rejects(lambda: cc.to_json(nonfinite))
    assert rejects(lambda: cc.from_json("{not json"))

    legacy = ConsolidateResult(status="ok", verdict="match")
    adapted = cc.comparison_outcome_from_legacy(legacy)
    assert adapted.completion == cc.UNKNOWN and adapted.verdict == cc.UNKNOWN
    assert not adapted.is_complete and not adapted.is_comparable
    explicit_unstructured = ConsolidateResult(
        status="ok", completion="complete", verdict="match")
    adapted = cc.comparison_outcome_from_legacy(explicit_unstructured)
    assert adapted.completion == cc.UNKNOWN and adapted.verdict == cc.UNKNOWN
    adapted = cc.comparison_outcome_from_legacy(
        explicit_unstructured, counts=exact, pairing_quality="exact")
    assert adapted.completion == "complete" and adapted.is_complete
    adapted_coverage = cc.comparison_outcome_from_legacy(
        legacy,
        capped_group_diagnostics=({
            "kind": "loaded_side_coverage", "role": "side_a"},),
        coverage_diagnostics=({
            "kind": "route_universe", "missing": ["002"]},))
    assert adapted_coverage.capped_group_diagnostics == ()
    assert tuple(item["kind"] for item in
                 adapted_coverage.coverage_diagnostics) == (
                     "route_universe", "loaded_side_coverage")
    contradiction = ConsolidateResult(
        status="error", message="boom", completion="complete", verdict="match")
    adapted = cc.comparison_outcome_from_legacy(contradiction, counts=exact)
    assert adapted.completion == "failed" and adapted.verdict == cc.UNKNOWN
    assert adapted.failures == ("boom",) and not adapted.is_comparable
    cancelled = cc.comparison_outcome_from_legacy(
        ConsolidateResult(status="cancelled", completion="complete"))
    assert cancelled.completion == "cancelled" and not cancelled.is_comparable
    wrapped = ConsolidateResult(status="ok", comparison_outcome=match)
    assert cc.comparison_outcome_from_legacy(wrapped) is match

    terminal_error = cc.finalize_comparison_result(
        ConsolidateResult(status="error", message="missing input"))
    assert terminal_error.completion == "failed"
    assert terminal_error.comparison_outcome == cc.ComparisonOutcome(
        status="error", completion="failed", verdict="unknown",
        failures=("missing input",))
    assert terminal_error.attempt_state == cc.AttemptState(
        state="failed", message="missing input")
    assert terminal_error.artifact_generation is None

    terminal_cancel = cc.finalize_comparison_result(
        ConsolidateResult(status="cancelled", message="declined",
                          completion="complete", verdict="match"))
    assert terminal_cancel.completion == "cancelled"
    assert terminal_cancel.comparison_outcome.status == "cancelled"
    assert terminal_cancel.comparison_outcome.completion == "cancelled"
    assert terminal_cancel.comparison_outcome.verdict == "unknown"
    assert terminal_cancel.attempt_state.state == "cancelled"

    terminal_no_data = cc.finalize_comparison_result(
        ConsolidateResult(status="ok", message="nothing to compare",
                          completion="no_data"))
    assert terminal_no_data.comparison_outcome.completion == "no_data"
    assert terminal_no_data.attempt_state.state == "failed"

    existing_attempt = cc.AttemptState(state="cancelled", message="kept")
    already_typed = ConsolidateResult(
        status="cancelled", completion="cancelled",
        comparison_outcome=cc.ComparisonOutcome(
            status="cancelled", completion="cancelled"),
        attempt_state=existing_attempt)
    cc.finalize_comparison_result(already_typed)
    assert already_typed.attempt_state is existing_attempt

    @cc.comparison_result_boundary
    def terminal_fn():
        return ConsolidateResult(status="error", message="wrapped")

    assert terminal_fn().comparison_outcome.failures == ("wrapped",)

    old_positional = ConsolidateResult(
        "ok", "m", "p", ["s"], "diff", "partial", 1, 2)
    assert (old_positional.status, old_positional.message,
            old_positional.output_path, old_positional.summary_lines,
            old_positional.verdict, old_positional.completion,
            old_positional.skipped_inputs, old_positional.failed_inputs) == (
                "ok", "m", "p", ["s"], "diff", "partial", 1, 2)
    assert old_positional.comparison_outcome is None
    assert old_positional.artifact_generation is None
    assert old_positional.attempt_state is None

    tree = ast.parse((SCRIPTS / "comparison_contract.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {
        "__future__", "dataclasses", "functools", "json", "math", "re",
        "typing",
    }, imported

    print("OK  comparison contract: tagged nested physical-key round-trips, "
          "exact raw scalars, canonical display, ordering, and key attachment; "
          "deterministic E2 pairing/trace/cap "
          "round-trips, local/global index and aggregate cost invariants, "
          "separate coverage diagnostics, fail-closed malformed shapes, typed "
          "terminal attempts, and additive ConsolidateResult compatibility.")


if __name__ == "__main__":
    main()
