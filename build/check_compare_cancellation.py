"""Adversarial gate for cancellation inside duplicate-row pairing.

The comparison must remain exact when cancellation is false, but a true poll
must abort exact matrix construction, the Hungarian solver, and capped
positional fallback without returning partial pairing truth or touching an
existing output.

Run with the build venv:
    build/.venv/Scripts/python.exe build/check_compare_cancellation.py
"""
from __future__ import annotations

import random

from _checklib import Checker, patch, scripts_path, temp_dir

scripts_path()

import compare_core as core
import outcome
from errors import RunCancelled
from events import Events


SCHEMA = core.CompareSchema(
    report_name="Cancellation Pairing",
    header=["Key", "Value"],
    side_a="LEFT",
    side_b="RIGHT",
    id_noun="row",
    id_noun_plural="rows",
)


def _duplicate_rows(count, prefix):
    return [["DUP", f"{prefix}-{index}"] for index in range(count)]


def _cancelled_contract(result):
    typed = getattr(result, "comparison_outcome", None)
    return (
        getattr(result, "status", None) == "cancelled"
        and getattr(result, "completion", None) == outcome.CANCELLED
        and typed is not None
        and typed.completion == outcome.CANCELLED
        and typed.verdict == "unknown"
        and not typed.counts.known
        and typed.pairing_quality == "unknown"
        and typed.pairing_trace == ()
        and typed.duplicate_group_count == 0
        and typed.capped_group_diagnostics == ()
    )


def test_hungarian_loop_cancel(c):
    print("\nexact Hungarian loop cancellation:")
    armed = {"value": False}

    class ArmOnSolverRead(list):
        """Arm only when the solver indexes a cost, after validation/setup."""

        def __getitem__(self, index):
            armed["value"] = True
            return super().__getitem__(index)

    matrix = [ArmOnSolverRead([0] * 40) for _ in range(40)]
    caught = None
    try:
        core._min_cost_pairs(matrix, lambda: armed["value"])
    except Exception as exc:
        caught = exc
    c.check(
        "a cancel armed by the first solver cost read interrupts Hungarian",
        armed["value"] and type(caught) is RunCancelled,
        f"armed={armed['value']!r}; exception={caught!r}")


def test_exact_cost_build_and_existing_output(c):
    print("\nexact cost-matrix cancellation and overwrite preservation:")
    rows_a = _duplicate_rows(4, "A")
    rows_b = _duplicate_rows(4, "B")
    # The within-cap matrix build computes its source-identity components via
    # _pair_cost_components (CMP-AUD-220); the capped diagonal below still
    # rides _row_diff_count.
    real_cost = core._pair_cost_components
    armed = {"value": False, "calls": 0}

    def arm_after_first_cost(*args, **kwargs):
        value = real_cost(*args, **kwargs)
        armed["calls"] += 1
        armed["value"] = True
        return value

    with temp_dir("tsmis_pair_cancel_exact_") as tmp:
        output = tmp / "comparison.xlsx"
        sentinel = b"last-good-comparison"
        output.write_bytes(sentinel)
        try:
            with patch(core, "_pair_cost_components", arm_after_first_cost):
                result = core.run_compare(
                    SCHEMA, rows_a, rows_b, False, output,
                    mode="values",
                    events=Events(is_cancelled=lambda: armed["value"]),
                    confirm_overwrite=lambda _path: True,
                )
            error = None
        except Exception as exc:
            result = None
            error = exc
        c.check(
            "cancel after one exact pair-cost returns the cancelled contract",
            error is None and result is not None
            and _cancelled_contract(result) and armed["calls"] == 1,
            f"error={error!r}; result={result!r}; armed={armed!r}")
        c.check(
            "mid-pairing cancel leaves an approved existing output byte-exact",
            output.read_bytes() == sentinel,
            repr(output.read_bytes()))


def test_capped_fallback_cancel(c):
    print("\ncapped positional-fallback cancellation:")
    # 317 * 317 is the smallest square above the 100,000-cell exact cap.
    rows_a = _duplicate_rows(317, "A")
    rows_b = _duplicate_rows(317, "B")
    real_diff = core._row_diff_count
    armed = {"value": False, "calls": 0}

    def arm_after_first_cost(*args, **kwargs):
        value = real_diff(*args, **kwargs)
        armed["calls"] += 1
        armed["value"] = True
        return value

    with temp_dir("tsmis_pair_cancel_capped_") as tmp:
        output = tmp / "comparison.xlsx"
        try:
            with patch(core, "_row_diff_count", arm_after_first_cost):
                result = core.run_compare(
                    SCHEMA, rows_a, rows_b, False, output,
                    mode="values",
                    events=Events(is_cancelled=lambda: armed["value"]),
                )
            error = None
        except Exception as exc:
            result = None
            error = exc
        c.check(
            "cancel during capped diagonal is cancelled, never partial/capped",
            error is None and result is not None
            and _cancelled_contract(result) and armed["calls"] == 1,
            f"error={error!r}; result={result!r}; armed={armed!r}")
        c.check(
            "capped cancellation creates no workbook",
            not output.exists(),
            str(output))


def test_count_diffs_cancel(c):
    print("\npost-pair count-mirror cancellation:")
    schema = core.CompareSchema(
        report_name="Count Cancellation",
        header=["Key", "F1", "F2", "F3", "F4"],
        side_a="LEFT",
        side_b="RIGHT",
        id_noun="row",
        id_noun_plural="rows",
    )
    rows_a = [["ROW", "a", "b", "c", "d"]]
    rows_b = [["ROW", "a", "b", "c", "d"]]
    real_pair = core.pair_occurrences_by_similarity
    real_cell = core.compared_cell
    state = {
        "pairing_done": False,
        "cell_before_pairing": False,
        "count_cells": 0,
        "cancel": False,
    }

    def mark_pairing_done(*args, **kwargs):
        pairing = real_pair(*args, **kwargs)
        state["pairing_done"] = True
        return pairing

    def arm_after_first_count_cell(*args, **kwargs):
        cell = real_cell(*args, **kwargs)
        if not state["pairing_done"]:
            state["cell_before_pairing"] = True
        state["count_cells"] += 1
        state["cancel"] = True
        return cell

    with temp_dir("tsmis_pair_cancel_count_") as tmp:
        output = tmp / "comparison.xlsx"
        try:
            # A short test cadence makes the second compared field the next
            # deterministic poll after the first one arms cancellation.
            with patch(core, "_PROGRESS_EVERY", 2), patch(
                    core, "pair_occurrences_by_similarity", mark_pairing_done), patch(
                    core, "compared_cell", arm_after_first_count_cell):
                result = core.run_compare(
                    schema, rows_a, rows_b, False, output,
                    mode="values",
                    events=Events(is_cancelled=lambda: state["cancel"]),
                )
            error = None
        except Exception as exc:
            result = None
            error = exc
        c.check(
            "cancel armed only after pairing interrupts the field-count scan",
            error is None and result is not None
            and state["pairing_done"] and not state["cell_before_pairing"]
            and state["count_cells"] == 2
            and _cancelled_contract(result),
            f"error={error!r}; result={result!r}; state={state!r}")
        c.check(
            "count cancellation emits no workbook or partial count truth",
            not output.exists(),
            str(output))


def test_source_scan_cancel(c):
    print("\npre-pair source-validation cancellation:")
    schema = core.CompareSchema(
        report_name="Source Scan Cancellation",
        header=["Key", "F1", "F2"],
        side_a="LEFT",
        side_b="RIGHT",
        id_noun="row",
        id_noun_plural="rows",
    )
    rows = [["ROW", "a", "b"]]
    polls = {"count": 0}

    def cancel_on_fourth_poll():
        polls["count"] += 1
        return polls["count"] >= 4

    with temp_dir("tsmis_pair_cancel_source_") as tmp:
        output = tmp / "comparison.xlsx"
        with patch(core, "_PROGRESS_EVERY", 2):
            result = core.run_compare(
                schema, rows, rows, False, output,
                mode="values",
                events=Events(is_cancelled=cancel_on_fourth_poll),
            )
        c.check(
            "a wide-row source scan observes cancellation before pairing",
            polls["count"] == 4 and _cancelled_contract(result),
            f"polls={polls!r}; result={result!r}")
        c.check(
            "source-scan cancellation emits no workbook",
            not output.exists(),
            str(output))


def test_key_and_derived_setup_cancel(c):
    print("\nkey/derived pre-serialization cancellation:")
    key_state = {"cancel": False, "normalizer_calls": 0}

    def arm_during_key_build(row, off, key_field):
        key_state["normalizer_calls"] += 1
        key_state["cancel"] = True
        return str(row[off + key_field])

    key_schema = core.CompareSchema(
        report_name="Key Setup Cancellation",
        header=["Key", "Value"],
        side_a="LEFT",
        side_b="RIGHT",
        id_noun="row",
        id_noun_plural="rows",
        key_normalizer=arm_during_key_build,
    )
    rows = [[f"K{index}", str(index)] for index in range(3)]
    with temp_dir("tsmis_pair_cancel_keys_") as tmp:
        output = tmp / "comparison.xlsx"
        with patch(core, "_PROGRESS_EVERY", 2):
            result = core.run_compare(
                key_schema, rows, rows, False, output,
                mode="values",
                events=Events(is_cancelled=lambda: key_state["cancel"]),
            )
        c.check(
            "cancel armed by key normalization aborts key materialization",
            key_state["normalizer_calls"] == 2
            and _cancelled_contract(result) and not output.exists(),
            f"state={key_state!r}; result={result!r}; output={output}")

    derived_state = {
        "cancel": False,
        "count_done": False,
        "lookup_before_count": False,
        "helper_lookups": 0,
    }
    real_tokens = core._opaque_helper_tokens
    real_count = core.count_diffs

    class ArmOnHelperLookup(dict):
        def __getitem__(self, key):
            if not derived_state["count_done"]:
                derived_state["lookup_before_count"] = True
            derived_state["helper_lookups"] += 1
            derived_state["cancel"] = True
            return super().__getitem__(key)

    def armed_tokens(*args, **kwargs):
        return ArmOnHelperLookup(real_tokens(*args, **kwargs))

    def mark_count_done(*args, **kwargs):
        counts = real_count(*args, **kwargs)
        derived_state["count_done"] = True
        return counts

    with temp_dir("tsmis_pair_cancel_derived_") as tmp:
        output = tmp / "comparison.xlsx"
        try:
            with patch(core, "_PROGRESS_EVERY", 2), patch(
                    core, "_opaque_helper_tokens", armed_tokens), patch(
                    core, "count_diffs", mark_count_done):
                result = core.run_compare(
                    SCHEMA, rows, rows, False, output,
                    mode="values",
                    events=Events(
                        is_cancelled=lambda: derived_state["cancel"]),
                )
            error = None
        except Exception as exc:
            result = None
            error = exc
        c.check(
            "cancel armed only in post-count helper mapping aborts derived setup",
            error is None and result is not None
            and derived_state["count_done"]
            and not derived_state["lookup_before_count"]
            and derived_state["helper_lookups"] == 2
            and _cancelled_contract(result) and not output.exists(),
            f"error={error!r}; state={derived_state!r}; result={result!r}")


def test_never_cancel_semantics(c):
    print("\nnever-cancel semantic parity:")
    rng = random.Random(0xCACE1)
    matrices = [[[0] * 5 for _ in range(5)]]
    matrices.extend(
        [[rng.randrange(5) for _ in range(cols)] for _ in range(rows)]
        for rows, cols in ((1, 9), (9, 1), (4, 6), (6, 4), (5, 5))
    )
    mismatches = []
    for matrix in matrices:
        plain = core._min_cost_pairs(matrix)
        polled = core._min_cost_pairs(matrix, lambda: False)
        if polled != plain:
            mismatches.append((matrix, plain, polled))
    c.check(
        "false cancellation polling preserves every exact assignment and tie",
        not mismatches,
        repr(mismatches[:1]))

    rows_a = [["DUP", "x"], ["DUP", "y"], ["DUP", "z"]]
    rows_b = [["DUP", "z"], ["DUP", "x"], ["DUP", "y"]]
    keys_a = core.keys_for(rows_a, False)
    keys_b = core.keys_for(rows_b, False)
    plain = core.pair_occurrences_by_similarity(
        SCHEMA, rows_a, rows_b, keys_a, keys_b, False)
    polled = core.pair_occurrences_by_similarity(
        SCHEMA, rows_a, rows_b, keys_a, keys_b, False,
        Events(is_cancelled=lambda: False))
    c.check(
        "false polling preserves the complete typed occurrence-pairing result",
        polled == plain,
        f"plain={plain!r}; polled={polled!r}")
    union = core.union_keys(plain.keys_a, plain.keys_b)
    plain_counts = core.count_diffs(
        SCHEMA, rows_a, rows_b, plain.keys_a, plain.keys_b, union, False)
    polled_counts = core.count_diffs(
        SCHEMA, rows_a, rows_b, plain.keys_a, plain.keys_b, union, False,
        lambda: False)
    c.check(
        "false polling preserves the complete count mirror byte-for-byte",
        polled_counts == plain_counts,
        f"plain={plain_counts!r}; polled={polled_counts!r}")

    polled_keys_a = core.keys_for(
        rows_a, False, is_cancelled=lambda: False)
    polled_keys_b = core.keys_for(
        rows_b, False, is_cancelled=lambda: False)
    polled_union = core.union_keys(
        plain.keys_a, plain.keys_b, lambda: False)
    plain_tokens = core._opaque_helper_tokens(union)
    polled_tokens = core._opaque_helper_tokens(union, lambda: False)
    c.check(
        "false polling preserves keys, union order, and opaque helpers",
        polled_keys_a == keys_a and polled_keys_b == keys_b
        and polled_union == union and polled_tokens == plain_tokens,
        f"keys_a={polled_keys_a!r}; keys_b={polled_keys_b!r}; "
        f"union={polled_union!r}; tokens={polled_tokens!r}")

    route_keys_a = [("R1", "A", 1), ("R2", "B", 1)]
    route_keys_b = [("R2", "B", 1), ("R3", "C", 1)]
    plain_routes = core.route_coverage(route_keys_a, route_keys_b)
    polled_routes = core.route_coverage(
        route_keys_a, route_keys_b, lambda: False)
    plain_derived = core._post_count_derivations(
        plain.keys_a, plain.keys_b, union, plain_tokens,
        rows_a, rows_b, True)
    polled_derived = core._post_count_derivations(
        plain.keys_a, plain.keys_b, union, plain_tokens,
        rows_a, rows_b, True, lambda: False)
    c.check(
        "false polling preserves route coverage and every derived lookup",
        polled_routes == plain_routes and polled_derived == plain_derived,
        f"routes={polled_routes!r}; derived={polled_derived!r}")


def main():
    c = Checker()
    print("Comparison duplicate-pairing cancellation gate")
    test_hungarian_loop_cancel(c)
    test_exact_cost_build_and_existing_output(c)
    test_capped_fallback_cancel(c)
    test_count_diffs_cancel(c)
    test_source_scan_cancel(c)
    test_key_and_derived_setup_cancel(c)
    test_never_cancel_semantics(c)
    return c.summary()


if __name__ == "__main__":
    raise SystemExit(main())
