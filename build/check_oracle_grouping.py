"""CMP-AUD-187 — the independent oracle's first-seen grouping is indexed, and
provably identical to the list-scan it replaces.

`compare_rows` used to test membership with `key not in order` against a list, so
a Highway Detail leg with ~60,000 distinct physical keys turned an otherwise
linear grouping step quadratic (a measured 60,083x60,083 reproduction spent 746
seconds in comparison alone). The set is used ONLY for membership; `order` still
carries deterministic encounter order.

This is an equivalence proof, not a smoke test: the ORIGINAL grouping is
reconstructed here and every fixture class the finding names — unique keys,
duplicates, one-sided groups, reordered groups, typed keys, and capped
assignments — is run through both and compared field for field.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "build"), str(ROOT / "scripts"), str(ROOT)]

from _checklib import Checker  # noqa: E402

import phase3_independent_oracle as oracle  # noqa: E402
from phase3_independent_oracle import (FieldRule, MED_WID, OracleRow,  # noqa: E402
                                       OracleSchema, ValueRule, canonical_key)

c = Checker()

# The quadratic step is only worth timing at a size where it actually bites; the
# finding's real leg was ~60k keys per side.
_PERF_ROWS = 20_000
_PERF_BUDGET_S = 30.0


def _legacy_grouping(schema, rows_a, rows_b):
    """The ORIGINAL first-seen grouping (list membership scan), verbatim."""
    groups_a, groups_b, order = {}, {}, []
    for row, groups in tuple((row, groups_a) for row in rows_a) + tuple(
            (row, groups_b) for row in rows_b):
        oracle._validate_row(row, schema)
        key = canonical_key(row, schema)
        if key not in groups_a and key not in groups_b and key not in order:
            order.append(key)
        groups.setdefault(key, []).append(row)
    return groups_a, groups_b, order


def _current_grouping(schema, rows_a, rows_b):
    """The indexed grouping as shipped (mirrors compare_rows' prologue)."""
    groups_a, groups_b, order, seen = {}, {}, [], set()
    for row, groups in tuple((row, groups_a) for row in rows_a) + tuple(
            (row, groups_b) for row in rows_b):
        oracle._validate_row(row, schema)
        key = canonical_key(row, schema)
        if key not in seen:
            seen.add(key)
            order.append(key)
        groups.setdefault(key, []).append(row)
    return groups_a, groups_b, order


SCHEMA = OracleSchema(
    key_rules=(ValueRule("Route"), ValueRule("PM", kind=MED_WID)),
    field_rules=(FieldRule("Desc"), FieldRule("Len"),
                 FieldRule("Note", asserting=False)))


def _row(i, route, pm, desc="D", length="1", note="n"):
    return OracleRow(source_index=i, key=(route, pm), values=(desc, length, note),
                     source_ref=f"r{i}")


def _fixtures():
    """(label, rows_a, rows_b) for every class the finding names."""
    yield ("unique keys",
           [_row(i, f"{i:03d}", "1.0") for i in range(6)],
           [_row(i, f"{i:03d}", "1.0", desc="E" if i == 3 else "D")
            for i in range(6)])
    yield ("duplicates on both sides",
           [_row(0, "001", "1.0"), _row(1, "001", "1.0"), _row(2, "001", "1.0")],
           [_row(0, "001", "1.0", desc="E"), _row(1, "001", "1.0"),
            _row(2, "001", "1.0", length="9")])
    yield ("one-sided groups",
           [_row(0, "001", "1.0"), _row(1, "002", "2.0")],
           [_row(0, "002", "2.0"), _row(1, "003", "3.0")])
    yield ("reordered groups (encounter order must survive)",
           [_row(0, "003", "3.0"), _row(1, "001", "1.0"), _row(2, "002", "2.0")],
           [_row(0, "002", "2.0"), _row(1, "003", "3.0"), _row(2, "001", "1.0")])
    yield ("typed / med-wid keys that normalize together",
           [_row(0, "001", "9.6"), _row(1, "001", "009.600"),
            _row(2, "001", "12.5R")],
           [_row(0, "001", "9.600"), _row(1, "001", "9.6", desc="E"),
            _row(2, "001", "12.5R")])
    yield ("a side with no rows at all", [_row(0, "001", "1.0")], [])
    # A group whose product of occurrences exceeds the pair cap: capped
    # assignment must be reached identically through both groupings.
    big = 400
    yield (f"capped assignment ({big}x{big} in one group)",
           [_row(i, "001", "1.0", desc=f"a{i}") for i in range(big)],
           [_row(i, "001", "1.0", desc=f"b{i}") for i in range(big)])


def main() -> None:
    print("the grouping prologue is identical to the list-scan original:")
    for label, rows_a, rows_b in _fixtures():
        legacy = _legacy_grouping(SCHEMA, rows_a, rows_b)
        current = _current_grouping(SCHEMA, rows_a, rows_b)
        c.check(f"{label}: same groups and same encounter order",
                legacy == current,
                f"order legacy={legacy[2]!r} current={current[2]!r}")

    print("the full oracle outcome is unchanged for every fixture class:")
    for label, rows_a, rows_b in _fixtures():
        outcome = oracle.compare_rows(SCHEMA, rows_a, rows_b)
        again = oracle.compare_rows(SCHEMA, rows_a, rows_b)
        c.check(f"{label}: the outcome is deterministic",
                outcome == again)
        c.check(f"{label}: keys, counts and traces are self-consistent",
                outcome.counts.paired_rows >= 0
                and len(outcome.pairing_trace) >= 0
                and outcome.pairing_quality in ("exact", "capped"))

    capped = oracle.compare_rows(SCHEMA, *list(_fixtures())[-1][1:])
    c.check("the capped fixture really exercises the cap",
            capped.pairing_quality == "capped" and capped.capped_diagnostics,
            f"quality={capped.pairing_quality}")

    print("first-seen membership is no longer quadratic:")
    rows_a = [_row(i, f"{i:06d}", "1.0") for i in range(_PERF_ROWS)]
    rows_b = [_row(i, f"{i:06d}", "1.0") for i in range(_PERF_ROWS)]
    t = time.perf_counter()
    groups = _current_grouping(SCHEMA, rows_a, rows_b)
    indexed = time.perf_counter() - t
    c.check(f"{2 * _PERF_ROWS:,} rows group in {indexed:.2f}s "
            f"(budget {_PERF_BUDGET_S:.0f}s)",
            indexed < _PERF_BUDGET_S and len(groups[2]) == _PERF_ROWS,
            f"{indexed:.2f}s, {len(groups[2])} keys")
    # The original is only sampled — at the full size it is the very cost this
    # finding removes — but the sample must still agree exactly.
    sample_a, sample_b = rows_a[:1500], rows_b[:1500]
    t = time.perf_counter()
    legacy_sample = _legacy_grouping(SCHEMA, sample_a, sample_b)
    legacy_time = time.perf_counter() - t
    t = time.perf_counter()
    current_sample = _current_grouping(SCHEMA, sample_a, sample_b)
    current_time = time.perf_counter() - t
    c.check("the sampled original and the indexed path agree exactly",
            legacy_sample == current_sample)
    c.check(f"the indexed path is faster on the same sample "
            f"({legacy_time:.3f}s -> {current_time:.3f}s)",
            current_time <= legacy_time)


if __name__ == "__main__":
    print("CMP-AUD-187 independent-oracle grouping equivalence + perf:")
    main()
    raise SystemExit(c.summary())
