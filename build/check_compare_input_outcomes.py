"""Phase-2B: direct file comparisons preserve producer completeness."""
import inspect
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_tsn_common as ctc  # noqa: E402
import compare_env  # noqa: E402
import compare_highway_log  # noqa: E402
import comparison_contract as cc  # noqa: E402
import consolidation_meta as cm  # noqa: E402
from events import ConsolidateResult  # noqa: E402


failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        failures.append(name)


def check_terminal(label, result, *, status, completion, attempt):
    typed = getattr(result, "comparison_outcome", None)
    state = getattr(result, "attempt_state", None)
    check(f"{label}: outer structural state is explicit",
          result.status == status and result.completion == completion)
    check(f"{label}: returned comparison outcome is typed/fail-closed",
          isinstance(typed, cc.ComparisonOutcome)
          and typed.status == status and typed.completion == completion
          and typed.verdict == cc.UNKNOWN and not typed.counts.known)
    check(f"{label}: returned attempt is typed without invented generation",
          isinstance(state, cc.AttemptState) and state.state == attempt
          and state.generation_id == ""
          and result.artifact_generation is None)


def record(completion, skipped=0, failed=0, *, trusted=True,
           diagnostic=None, source="sidecar"):
    return cm.ConsolidationOutcome(
        completion=completion, skipped_inputs=skipped, failed_inputs=failed,
        trusted=trusted, current=True, diagnostic=diagnostic, source=source)


def run_case(mode, record_a, record_b, loader_warnings=None):
    root = Path(tempfile.mkdtemp(prefix="tsmis_direct_outcome_"))
    a, b, out = root / "a.xlsx", root / "b.xlsx", root / "result.xlsx"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    records = {a: record_a, b: record_b}
    observed = {"reads": [], "commits": []}

    def read_outcome(path):
        path = Path(path)
        observed["reads"].append(path)
        return records[path]

    def fake_run_compare(sc, rows_a, rows_b, has_route, temp_path, **kwargs):
        observed.update(sc=sc, rows_a=rows_a, rows_b=rows_b,
                        has_route=has_route, temp_path=Path(temp_path),
                        compare_kwargs=kwargs)
        return ConsolidateResult(status="ok", completion="partial"
                                 if kwargs.get("input_completion") == "partial"
                                 else "complete")

    def fake_commit(out_path, build, **kwargs):
        observed["commits"].append((Path(out_path), kwargs))
        return build(root / "transaction.xlsx")

    with (patch.object(ctc.consolidation_meta, "read_outcome", read_outcome),
          patch.object(ctc, "run_compare", fake_run_compare),
          patch.object(ctc.artifact_store, "commit_workbook", fake_commit)):
        result = ctc.run_files_compare(
            "SCHEMA", a, b, out, banner="B", has_route=True,
            loader=lambda _a, _b: ([['same']], [['same']], loader_warnings),
            mode=mode)
    return result, observed, a, b


def test_current_complete_and_absent_stale():
    print("current complete versus absent/stale authority:")
    complete = record("complete")
    result, seen, a, b = run_case("values", complete, complete)
    kw = seen["compare_kwargs"]
    # CMP-AUD-076: the provenance capture reads each side's coupled outcome
    # record too (for the per-input producer completion), so each side is read
    # through the SAME mtime-validated reader twice — capture, then merge.
    check("both current complete records are read via the coupled reader "
          "(capture + merge)", seen["reads"] == [a, b, a, b])
    check("both current complete records authorize complete input coverage",
          kw["input_completion"] == "complete"
          and kw["warnings"] == () and kw["skipped_inputs"] is None
          and kw["failed_inputs"] == 0 and kw["failures"] == ())
    check("complete direct comparison reaches build", result.status == "ok")

    for label, left, right in (
            ("missing", None, None),
            ("stale", None, None),
            ("one current complete plus one missing", complete, None)):
        _result, seen, _a, _b = run_case("values", left, right)
        kw = seen["compare_kwargs"]
        check(f"{label}: no trusted completion is invented",
              kw["input_completion"] is None)
        check(f"{label}: legacy/raw warnings and counters stay untouched",
              kw["warnings"] == () and kw["skipped_inputs"] is None
              and kw["failed_inputs"] == 0 and kw["failures"] == ())


def test_partial_and_malformed_merge():
    print("symmetric/asymmetric partial and malformed-current metadata:")
    complete = record("complete")
    cases = (
        ("asymmetric partial", record("partial", skipped=2, failed=1), complete,
         None, 2, 1, 1),
        ("symmetric partial", record("partial", skipped=2),
         record("partial", skipped=1, failed=3), None, 3, 3, 2),
        ("loader + sidecar diagnostics", record("partial", skipped=2), complete,
         ["loader skipped one input"], 3, 0, 2),
        ("malformed current", record("partial", skipped=None, failed=None,
                                     trusted=False,
                                     diagnostic="outcome metadata is not valid JSON"),
         complete, None, 0, 0, 1),
    )
    for label, left, right, loader_warnings, skipped, failed, n_warnings in cases:
        result, seen, _a, _b = run_case("values", left, right, loader_warnings)
        kw = seen["compare_kwargs"]
        check(f"{label}: build is forced partial",
              result.status == "ok" and kw["input_completion"] == "partial")
        check(f"{label}: exact available skipped/failed counters survive",
              kw["skipped_inputs"] == skipped and kw["failed_inputs"] == failed)
        check(f"{label}: loader and producer diagnostics merge",
              len(kw["warnings"]) == n_warnings)
        check(f"{label}: every producer note names its selected side/file",
              all(("input 'a.xlsx'" in warning or "input 'b.xlsx'" in warning
                   or warning == "loader skipped one input")
                  for warning in kw["warnings"]))

    _result, seen, _a, _b = run_case(
        "values", record("partial", skipped=0, failed=2), complete)
    kw = seen["compare_kwargs"]
    check("upstream failed inputs remain structured failures",
          kw["failed_inputs"] == 2 and len(kw["failures"]) == 1
          and kw["failures"][0] in kw["warnings"])

    _result, seen, _a, _b = run_case(
        "values", record("partial", skipped=None, failed=None, trusted=False,
                         diagnostic="bad counters", source="sentinel"), complete)
    kw = seen["compare_kwargs"]
    check("untrusted current metadata never invents unavailable counters",
          kw["skipped_inputs"] == 0 and kw["failed_inputs"] == 0)
    check("untrusted current diagnostic remains visible + structured",
          len(kw["warnings"]) == 1 and kw["failures"] == tuple(kw["warnings"])
          and "untrusted" in kw["warnings"][0]
          and "bad counters" in kw["warnings"][0])


def test_all_output_modes():
    print("one merge feeds formulas / values / both identically:")
    partial = record("partial", skipped=4, failed=2)
    complete = record("complete")
    snapshots = []
    for mode in ("formulas", "values", "both"):
        _result, seen, _a, _b = run_case(mode, partial, complete)
        kw = seen["compare_kwargs"]
        snapshots.append((kw["input_completion"], kw["skipped_inputs"],
                          kw["failed_inputs"], tuple(kw["warnings"]),
                          tuple(kw["failures"])))
        check(f"{mode}: selected mode reaches the single comparison build",
              kw["mode"] == mode)
        commit_kwargs = seen["commits"][0][1]
        check(f"{mode}: transaction uses the expected twin policy",
              commit_kwargs["twin"] is (mode == "both"))
    check("all modes receive identical producer truth",
          snapshots[0] == snapshots[1] == snapshots[2])


def test_noncomparable_producer_outcomes_block():
    print("failed/no-data/cancelled producer artifacts are unusable:")
    for completion in ("failed", "no_data", "cancelled"):
        result, seen, _a, _b = run_case(
            "values", record(completion), record("complete"))
        check(f"{completion}: returns a user-safe error before compare_core",
              result.status == "error" and "not usable for comparison" in result.message
              and "a.xlsx" in result.message and "compare_kwargs" not in seen)
        check(f"{completion}: does not enter the artifact transaction",
              seen["commits"] == [])
        check_terminal(
            f"{completion}: blocked public result", result,
            status="error", completion="failed", attempt="failed")


def test_public_terminal_paths_are_typed():
    print("public early/preflight/cancel/commit terminal paths are typed:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_terminal_outcomes_"))

    direct = compare_highway_log.compare(
        root / "missing-a.xlsx", root / "missing-b.xlsx", root / "direct.xlsx",
        mode="values")
    check_terminal("direct missing input", direct, status="error",
                   completion="failed", attempt="failed")
    check("direct missing input retains the user-safe failure",
          "doesn't exist" in direct.message
          and direct.comparison_outcome.failures == (direct.message,))

    env = compare_env.HIGHWAY_LOG.compare_folders(
        root / "missing-a", root / "missing-b", root / "env.xlsx",
        mode="values")
    check_terminal("environment missing input", env, status="error",
                   completion="failed", attempt="failed")

    a, b = root / "a.xlsx", root / "b.xlsx"
    a.write_bytes(b"a")
    b.write_bytes(b"b")

    def malformed(_a, _b):
        raise ValueError("wrong comparison shape")

    malformed_result = ctc.run_files_compare(
        "SCHEMA", a, b, root / "malformed.xlsx", banner="B",
        has_route=True, loader=malformed, mode="values")
    check_terminal("loader shape failure", malformed_result, status="error",
                   completion="failed", attempt="failed")
    check("loader shape failure remains structured",
          malformed_result.comparison_outcome.failures
          == ("wrong comparison shape",))

    def loader(_a, _b):
        return [["same"]], [["same"]], None

    for label, returned, status, completion, attempt in (
            ("overwrite cancellation",
             ConsolidateResult(status="cancelled", message="declined"),
             "cancelled", "cancelled", "cancelled"),
            ("artifact commit failure",
             ConsolidateResult(status="error", message="locked destination"),
             "error", "failed", "failed")):
        with patch.object(ctc.artifact_store, "commit_workbook",
                          return_value=returned):
            result = ctc.run_files_compare(
                "SCHEMA", a, b, root / f"{label}.xlsx", banner="B",
                has_route=True, loader=loader, mode="values")
        check_terminal(label, result, status=status, completion=completion,
                       attempt=attempt)


def test_single_coupled_reader_only():
    print("metadata truth comes from the coupled reader only:")
    source = inspect.getsource(ctc._merge_input_outcomes)
    check("uses read_outcome", "read_outcome" in source)
    check("never reads additive fields independently", "read_extra" not in source)
    check("never parses summary prose", "summary_lines" not in source)


if __name__ == "__main__":
    test_current_complete_and_absent_stale()
    test_partial_and_malformed_merge()
    test_all_output_modes()
    test_noncomparable_producer_outcomes_block()
    test_public_terminal_paths_are_typed()
    test_single_coupled_reader_only()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {failures}")
        raise SystemExit(1)
    print("ALL DIRECT COMPARISON INPUT-OUTCOME CHECKS PASSED")
