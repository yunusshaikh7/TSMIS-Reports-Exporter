"""Focused Phase-2 check for PDF cross-environment coverage propagation.

Locks all five convert-then-compare families:
  Highway Log, Highway Sequence, Highway Detail, Intersection Detail, Ramp Detail.

The consolidator's structured completion/skipped/failed fields must survive the
converted-XLSX loader and the atomic comparison commit without parsing summary text.
Symmetric partial inputs may compare equal at every loaded cell, but can never claim
complete/match.  Clean controls retain complete/match behavior.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_env
import consolidate_tsmis_highway_detail_pdf as hdpdf
import consolidate_tsmis_highway_log_pdf as hlpdf
import consolidate_tsmis_highway_sequence_pdf as hspdf
import consolidate_tsmis_intersection_detail_pdf as idpdf
import consolidate_tsmis_ramp_detail_pdf as rdpdf
from comparison_contract import ComparisonOutcome, LoadedSide
from events import ConsolidateResult, Events


CASES = (
    ("highway_log_pdf", "Highway Log (PDF)", hlpdf,
     compare_env._load_highway_log_pdf_side),
    ("highway_sequence_pdf", "Highway Sequence (PDF)", hspdf,
     compare_env._load_highway_sequence_pdf_side),
    ("highway_detail_pdf", "Highway Detail (PDF)", hdpdf,
     compare_env._load_highway_detail_pdf_side),
    ("intersection_detail_pdf", "Intersection Detail (PDF)", idpdf,
     compare_env._load_intersection_detail_pdf_side),
    ("ramp_detail_pdf", "Ramp Detail (PDF)", rdpdf,
     compare_env._load_ramp_detail_pdf_side),
)

_fail = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _fail.append(name)


def _converted_rows(expected_header=None):
    header = list(expected_header) if expected_header else ["PM", "Value"]
    values = ["000.100"] + ["same"] * max(0, len(header) - 1)
    return [["001"] + values], header


def test_each_converter_result_becomes_a_loaded_side():
    print("five PDF converters -> LoadedSide (no summary-text state parsing):")
    original_xlsx_loader = compare_env._load_xlsx_side
    poison = "POISON SUMMARY: skipped_inputs=999 failed_inputs=888 complete"
    state = {"partial": True}

    def stub_xlsx(_folder, _label, _subdir, _sheet, _report, _events,
                  expected_header=None, value_normalizer=None):
        rows, header = _converted_rows(expected_header)
        skips = ["converted workbook could not be read"] if state["partial"] else []
        return rows, header, skips

    compare_env._load_xlsx_side = stub_xlsx
    try:
        for key, report_name, module, loader in CASES:
            original_consolidate = module.consolidate

            def stub_consolidate(**_kwargs):
                return ConsolidateResult(
                    status="ok", completion="partial" if state["partial"] else "complete",
                    skipped_inputs=2 if state["partial"] else 0,
                    failed_inputs=3 if state["partial"] else 0,
                    summary_lines=[poison])

            module.consolidate = stub_consolidate
            try:
                with tempfile.TemporaryDirectory(prefix=f"p2env_{key}_") as td:
                    source = Path(td)
                    pdf_dir = source / module.SUBDIR
                    pdf_dir.mkdir(parents=True)
                    (pdf_dir / "route_001.pdf").write_bytes(b"test")

                    state["partial"] = True
                    partial = loader(source, "SIDE", Events())
                    raw = partial.raw_identity_claims["pdf_consolidation"]
                    check(f"{report_name}: typed loader result", isinstance(partial, LoadedSide))
                    check(f"{report_name}: exact producer completion preserved",
                          raw["completion"] == "partial")
                    check(f"{report_name}: exact skipped count survives both stages",
                          partial.skipped_inputs == 3 and raw["skipped_inputs"] == 2)
                    check(f"{report_name}: exact failed count preserved",
                          partial.failed_inputs == 3 and raw["failed_inputs"] == 3)
                    check(f"{report_name}: display summary is not parsed",
                          poison not in " ".join(partial.warnings + partial.failures))

                    state["partial"] = False
                    clean = loader(source, "SIDE", Events())
                    check(f"{report_name}: clean producer stays complete",
                          clean.completion == "complete"
                          and clean.skipped_inputs == 0 and clean.failed_inputs == 0
                          and not clean.warnings and not clean.failures)
            finally:
                module.consolidate = original_consolidate
    finally:
        compare_env._load_xlsx_side = original_xlsx_loader


def test_missing_or_invalid_completion_fails_closed():
    print("producer completion policy (only explicit clean complete is trusted):")
    rows, header = _converted_rows()
    loaded = (rows, header, [])
    missing = compare_env._pdf_loaded_side(
        ConsolidateResult(status="ok", completion=None), loaded,
        label="A", report_name="Test PDF", source_pdf_count=1)
    invalid = compare_env._pdf_loaded_side(
        ConsolidateResult(status="ok", completion="mystery"), loaded,
        label="A", report_name="Test PDF", source_pdf_count=1)
    count_loss = compare_env._pdf_loaded_side(
        ConsolidateResult(status="ok", completion="complete", skipped_inputs=4),
        loaded, label="A", report_name="Test PDF", source_pdf_count=1)
    terminal_errors = []
    for completion in ("failed", "no_data", "cancelled"):
        try:
            compare_env._pdf_loaded_side(
                ConsolidateResult(status="ok", completion=completion), loaded,
                label="A", report_name="Test PDF", source_pdf_count=1)
        except ValueError as error:
            terminal_errors.append(str(error))
    check("missing completion becomes partial and preserves unknown raw claim",
          missing.completion == "partial"
          and missing.raw_identity_claims["pdf_consolidation"]["completion"] == "unknown")
    check("invalid completion becomes partial with structured diagnostic",
          invalid.completion == "partial" and bool(invalid.warnings))
    check("nonzero loss overrides a producer's complete claim without synthetic count",
          count_loss.completion == "partial" and count_loss.skipped_inputs == 4
          and len(count_loss.warnings) == 1)
    check("status-ok terminal completion states are unusable, not partial",
          len(terminal_errors) == 3
          and all("cannot be compared" in message for message in terminal_errors))


def test_publication_failure_retains_loaded_side_truth():
    print("legacy/publication exit adapts explicitly and fails closed:")
    side_a, side_b = _side("A", True), _side("B", True)
    poison = "POISON SUMMARY: status=ok completion=complete verdict=match"
    failed = compare_env._apply_pdf_coverage(
        ConsolidateResult(status="error", message="late publication failed",
                          summary_lines=[poison]),
        (("side_a", "A", side_a), ("side_b", "B", side_b)))
    typed = failed.comparison_outcome
    diagnostics = [item for item in typed.coverage_diagnostics
                   if item.get("kind") == "loaded_side_coverage"]
    check("terminal result keeps exact aggregate counts",
          failed.skipped_inputs == 6 and failed.failed_inputs == 6)
    check("terminal typed outcome remains failed and includes publication error",
          failed.completion == "failed"
          and typed.status == "error" and typed.completion == "failed"
          and "late publication failed" in typed.failures)
    check("terminal adapter never parses display summary state",
          poison not in " ".join(typed.warnings + typed.failures))
    check("both per-side producer claims survive the failed commit",
          len(diagnostics) == 2
          and all(item["raw_identity_claims"]["pdf_consolidation"]
                  ["completion"] == "partial" for item in diagnostics))

    # A hypothetical legacy successful engine result has no machine counts.  Even
    # if its display prose claims success, adapting it may not manufacture a typed
    # complete/match outcome.
    legacy_ok = compare_env._apply_pdf_coverage(
        ConsolidateResult(status="ok", completion="complete", verdict="match",
                          summary_lines=[poison]),
        (("side_a", "A", side_a), ("side_b", "B", side_b)))
    check("legacy ok without typed counts stays fail-closed unknown",
          legacy_ok.completion is None and legacy_ok.verdict is None
          and legacy_ok.comparison_outcome.status == "ok"
          and legacy_ok.comparison_outcome.completion == "unknown"
          and legacy_ok.comparison_outcome.verdict == "unknown"
          and not legacy_ok.comparison_outcome.counts.known)


def _side(label, partial):
    raw = {
        "pdf_consolidation": {
            "status": "ok",
            "completion": "partial" if partial else "complete",
            "skipped_inputs": 2 if partial else 0,
            "failed_inputs": 3 if partial else 0,
        },
    }
    return LoadedSide(
        rows=(("001", "000.100", "same"),),
        declared_schema=("PM", "Value"),
        completion="partial" if partial else "complete",
        warnings=((f"{label}: 2 skipped input items",) if partial else ()),
        failures=((f"{label}: 3 failed input files",) if partial else ()),
        # Includes one converted-XLSX skip in addition to the producer's two.
        skipped_inputs=3 if partial else 0,
        failed_inputs=3 if partial else 0,
        raw_identity_claims=raw,
        display_metrics={"source_pdf_count": 1},
    )


def test_returned_comparison_truth_for_every_family():
    print("returned comparison coverage across formulas/values/both, all five families:")
    scenarios = (
        # name, side A partial, side B partial, skipped total, failed total
        ("symmetric_partial", True, True, 6, 6),
        ("side_a_partial", True, False, 3, 3),
        ("side_b_partial", False, True, 3, 3),
        ("clean", False, False, 0, 0),
    )
    for key, report_name, _module, _loader in CASES:
        with tempfile.TemporaryDirectory(prefix=f"p2env_cmp_{key}_") as td:
            root = Path(td)
            side_a = root / "2026-07-10 ssor-prod" / key
            side_b = root / "2026-07-10 ars-prod" / key
            side_a.mkdir(parents=True)
            side_b.mkdir(parents=True)
            (side_a / "a.pdf").write_bytes(b"a")
            (side_b / "b.pdf").write_bytes(b"b")
            state = {"side_a": False, "side_b": False}

            def side_loader(folder, label, _events):
                role = "side_a" if "ssor-prod" in str(folder).lower() else "side_b"
                return _side(label, state[role])

            adapter = compare_env.EnvCompare(
                key, report_name, key, sheet_name="Data",
                flat_pdf_loader=side_loader, key_col="PM")

            for mode in ("formulas", "values", "both"):
                for scenario, a_partial, b_partial, n_skipped, n_failed in scenarios:
                    state.update(side_a=a_partial, side_b=b_partial)
                    out = root / f"{mode}-{scenario}.xlsx"
                    result = adapter.compare_folders(
                        side_a.parent, side_b.parent, out,
                        events=Events(), confirm_overwrite=lambda _path: True,
                        mode=mode)
                    typed = result.comparison_outcome
                    expected_partial = a_partial or b_partial
                    expected_issue_sides = int(a_partial) + int(b_partial)
                    side_diags = [
                        item for item in typed.coverage_diagnostics
                        if item.get("kind") == "loaded_side_coverage"]
                    by_role = {item["role"]: item for item in side_diags}
                    expected_raw = {
                        "side_a": "partial" if a_partial else "complete",
                        "side_b": "partial" if b_partial else "complete",
                    }
                    paths = compare_env.artifact_store.comparison_output_paths(out, mode)
                    all_outputs_exist = all(Path(path).is_file() for path in paths)
                    exact_loaded_counts = (
                        typed.counts.known and typed.counts.paired_rows == 1
                        and typed.counts.differing_rows == 0
                        and typed.counts.differing_cells == 0
                        and typed.counts.side_a_only_rows == 0
                        and typed.counts.side_b_only_rows == 0)
                    exact_side_truth = (
                        len(side_diags) == 2
                        and all(by_role[role]["raw_identity_claims"]
                                ["pdf_consolidation"]["completion"] == completion
                                for role, completion in expected_raw.items()))
                    if expected_partial:
                        truth = (
                            result.status == "ok" and result.completion == "partial"
                            and result.verdict == "diff"
                            and typed.completion == "partial" and typed.verdict == "diff"
                            and len(typed.warnings) == expected_issue_sides
                            and len(typed.failures) == expected_issue_sides)
                    else:
                        truth = (
                            result.status == "ok" and result.completion == "complete"
                            and result.verdict == "match"
                            and typed.completion == "complete" and typed.verdict == "match"
                            and not typed.warnings and not typed.failures)
                    check(
                        f"{report_name} / {mode} / {scenario}: exact fail-closed truth",
                        isinstance(typed, ComparisonOutcome) and truth
                        and result.skipped_inputs == n_skipped
                        and result.failed_inputs == n_failed
                        and exact_loaded_counts and exact_side_truth
                        and all_outputs_exist)


def main():
    test_each_converter_result_becomes_a_loaded_side()
    test_missing_or_invalid_completion_fails_closed()
    test_publication_failure_retains_loaded_side_truth()
    test_returned_comparison_truth_for_every_family()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-ENV PDF COMPLETION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
