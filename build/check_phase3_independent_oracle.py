"""Adversarial self-checks for the independent Phase-3 typed oracle."""
from __future__ import annotations

import ast
from decimal import Decimal
import itertools
from pathlib import Path
import random

import phase3_independent_oracle as oracle


ROOT = Path(__file__).resolve().parent.parent
ORACLE_SOURCE = ROOT / "build" / "phase3_independent_oracle.py"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def ordinary(name="Value", asserting=True):
    return oracle.FieldRule(name=name, kind=oracle.ORDINARY,
                            asserting=asserting)


def cell(a, b, rule=None):
    return oracle.compare_cell(a, b, rule or ordinary())


def test_forbidden_imports():
    source = ORACLE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "__import__"):
            raise AssertionError("dynamic imports are forbidden in the oracle")
    allowed = {
        "__future__", "dataclasses", "datetime", "decimal", "math", "re", "typing",
    }
    check(imports <= allowed, f"oracle imports non-independent modules: {imports - allowed}")
    forbidden_fragments = (
        "compare" + "_core", "compare" + "_env", "compare" + "_tsn_common",
        "comparison" + "_contract", "consolidation" + "_meta", "open" + "pyxl",
        "compared" + "_cell", "_xl" + "_trim", "_medwid" + "_norm",
        "keys" + "_for", "_min_cost" + "_pairs",
    )
    lowered = source.lower()
    check(not any(fragment.lower() in lowered for fragment in forbidden_fragments),
          "oracle source names a forbidden production dependency")


def test_d2_policy():
    # Case-sensitive ordinary text; only ASCII U+0020 is trimmed/collapsed.
    check(cell("ABC", "ABC").equal, "identical text must compare equal")
    check(not cell("ABC", "abc").equal, "ordinary text must be case-sensitive")
    check(cell("  A   B  ", "A B").equal, "ASCII-space runs must collapse")
    for unusual in ("A\tB", "A\rB", "A\nB", "A\u00a0B"):
        check(not cell(unusual, "A B").equal,
              "control/NBSP whitespace must not fold globally")

    # Actual Boolean typing occurs before Python's bool-as-int relationship.
    check(cell(True, "TRUE").equal, "actual True must fold to TRUE")
    check(cell(False, "FALSE").equal, "actual False must fold to FALSE")
    for other in ("true", 1):
        check(not cell(True, other).equal,
              "Boolean True must not infer truth from string/number")
    for other in ("false", 0):
        check(not cell(False, other).equal,
              "Boolean False must not infer truth from string/number")

    # Canonical numeric text is decimal-safe. None, empty text, and ASCII-space-only
    # text are the same blank; zero remains a distinct asserted value.
    check(cell(5, "5").equal and cell(5.0, "5").equal,
          "integral numeric/text values must agree")
    check(cell(Decimal("0.5000"), "0.5").equal,
          "Decimal trailing zeros must canonicalize without float rounding")
    check(not cell(0.5, ".5").equal,
          "leading-dot text is not a canonical numeric spelling")
    huge = 123456789012345678901234567890123456789
    check(cell(huge, str(huge)).equal,
          "precision reaching the oracle must remain exact")
    check(cell(None, "").equal,
          "None and empty text must normalize to the same blank")
    check(cell(None, "     ").equal,
          "None and ASCII-space-only text must normalize to the same blank")
    check(cell("", "   ").equal,
          "empty and ASCII-space-only text must normalize to the same blank")
    check(cell(None, "").normalized_a.kind == "blank"
          and cell(None, "").normalized_b.kind == "blank",
          "empty equivalents must retain explicit typed-blank state")
    check(not cell(None, 0).equal, "blank and zero must remain distinct")

    # Error tokens and the display marker are literal source content.
    for token in ("#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"):
        check(cell(token, token).equal, "literal error tokens must remain text")
        check(not cell(token, "OK").equal, "literal error token differences must count")
    marker = "North ≠ South"
    marker_cell = cell(marker, marker)
    check(marker_cell.equal and not marker_cell.counts_as_difference,
          "literal display-marker text must not become semantic state")

    med = oracle.FieldRule("Med Wid", kind=oracle.MED_WID)
    for a, b in (("0Z", "00Z"), ("06V", "6V"), ("06.00V", "6V"),
                 ("06#", "6#")):
        check(cell(a, b, med).equal, f"approved unsigned Med-Wid pair failed: {a}/{b}")
    for a, b in (("-06V", "-6V"), (".50", "0.5"), ("6v", "6V"),
                 ("6VV", "6V"), ("6.", "6"),
                 ("06\u0661", "6\u0661"), ("06\u00e9", "6\u00e9"),
                 ("06\t", "6\t")):
        check(not cell(a, b, med).equal,
              f"anomalous Med-Wid token was over-normalized: {a}/{b}")

    context = cell("different", "values", ordinary("Context", asserting=False))
    check(not context.equal and not context.counts_as_difference,
          "context equality may be observed but cannot assert a difference")


def exhaustive_assignment(matrix):
    n, m = len(matrix), len(matrix[0])
    candidates = []
    for assignment in itertools.permutations(range(m), n):
        total = sum(matrix[i][assignment[i]] for i in range(n))
        candidates.append((total, assignment))
    return min(candidates)[1]


def test_d3_exact_lexicographic_objective():
    # A minimum-cost choice that positional and row-greedy selection miss.
    trap = ((1, 2), (1, 100))
    check(oracle.exact_lexicographic_assignment(trap) == (1, 0),
          "exact solver did not escape the positional/greedy trap")

    # All assignments tie on cost; the vector itself decides the result.
    check(oracle.exact_lexicographic_assignment(((0, 0, 0), (0, 0, 0))) == (0, 1),
          "tie did not select the lexicographically smallest vector")

    # Cross-check many small rectangles against a separate exhaustive enumerator.
    rng = random.Random(0xD2D3)
    for n in range(1, 5):
        for m in range(n, 6):
            for _ in range(20):
                matrix = tuple(tuple(rng.randrange(5) for _ in range(m))
                               for _ in range(n))
                actual = oracle.exact_lexicographic_assignment(matrix)
                expected = exhaustive_assignment(matrix)
                check(actual == expected,
                      f"rectangular exact/lex mismatch for {n}x{m}: {actual}/{expected}")

    # The cap includes the asymmetric 1x100,000 boundary without square padding.
    long_row = [1] * oracle.PAIR_CAP
    long_row[-1] = 0
    assignment = oracle.exact_lexicographic_assignment((long_row,))
    check(assignment == (oracle.PAIR_CAP - 1,),
          "1x100,000 rectangular boundary was not solved exactly")


def test_structured_keys_pairing_and_counts():
    schema = oracle.OracleSchema(
        key_rules=(oracle.ValueRule("Route"), oracle.ValueRule("Key")),
        field_rules=(ordinary("Asserted"), ordinary("Context", asserting=False)))

    empty = oracle.compare_rows(schema, (), ())
    check(empty.completion == "no_data" and empty.verdict == "unknown"
          and empty.counts.known and empty.counts.paired_rows == 0,
          "empty independent inputs must not certify a match")

    def row(index, key, asserted, context="ctx"):
        return oracle.OracleRow(index, tuple(key), (asserted, context))

    # Structured tuples remain injective even when flattened text would collide.
    k1 = oracle.canonical_key(row(0, ("R|X", "K"), "v"), schema)
    k2 = oracle.canonical_key(row(1, ("R", "X|K"), "v"), schema)
    check(k1 != k2, "delimiter-bearing structured keys collided")
    check(oracle.canonical_key(row(2, (5.0, "  K  "), "v"), schema)
          == oracle.canonical_key(row(3, ("5", "K"), "v"), schema),
          "key components did not use the canonical typed scalar policy")

    # Duplicate rows: cross-pairing removes two phantom differences. Context differs
    # everywhere but cannot affect assignment or counts.
    rows_a = (
        row(0, ("001", "P"), "left", "A0"),
        row(1, ("001", "P"), "right", "A1"),
        row(2, ("002", "Q"), "only-a"),
    )
    rows_b = (
        row(0, ("001", "P"), "right", "B0"),
        row(1, ("001", "P"), "left", "B1"),
        row(2, ("003", "R"), "only-b"),
    )
    result = oracle.compare_rows(schema, rows_a, rows_b)
    check(result.completion == "complete" and result.verdict == "diff",
          "one-sided rows must produce a complete diff verdict")
    check(result.counts.paired_rows == 2
          and result.counts.side_a_only_rows == 1
          and result.counts.side_b_only_rows == 1,
          "paired/one-sided typed counts are wrong")
    check(result.counts.differing_rows == 0
          and result.counts.differing_cells == 0
          and result.counts.per_field_counts == {},
          "exact duplicate assignment or context exclusion changed diff counts")
    check(result.counts.asserted_cells == 2 and result.counts.context_cells == 2,
          "asserted/context cell totals are wrong")
    trace = result.pairing_trace[0]
    check(trace.assignment_vector == (1, 0) and trace.total_cost == 0
          and trace.quality == "exact",
          "typed pairing trace does not describe the exact cross-pair")

    # Run the equal-cost rectangle in both orientations. The smaller side owns the
    # assignment vector; leftovers retain the larger side's file order.
    one_field = oracle.OracleSchema(
        key_rules=(oracle.ValueRule("K"),), field_rules=(ordinary(),))
    a2 = tuple(oracle.OracleRow(i, ("K",), ("same",)) for i in range(2))
    b3 = tuple(oracle.OracleRow(i, ("K",), ("same",)) for i in range(3))
    ab = oracle.compare_rows(one_field, a2, b3)
    ba = oracle.compare_rows(one_field, b3, a2)
    check(ab.pairing_trace[0].smaller_side == "a"
          and ab.pairing_trace[0].assignment_vector == (0, 1)
          and ab.side_b_only_indices == (2,),
          "A-small rectangle tie/leftover policy failed")
    check(ba.pairing_trace[0].smaller_side == "b"
          and ba.pairing_trace[0].assignment_vector == (0, 1)
          and ba.side_a_only_indices == (2,),
          "B-small transpose changed the declared tie/leftover policy")

    # Above-cap fallback is useful observed data but never exact or certifying.
    large_a = tuple(oracle.OracleRow(i, ("K",), (i,)) for i in range(317))
    large_b = tuple(oracle.OracleRow(i, ("K",), (i,)) for i in range(316))
    capped = oracle.compare_rows(one_field, large_a, large_b)
    check(capped.completion == "partial" and capped.verdict == "diff"
          and capped.pairing_quality == "capped",
          "above-cap pairing did not fail closed")
    check(capped.counts.paired_rows == 316
          and capped.counts.side_a_only_rows == 1
          and capped.counts.differing_cells == 0,
          "above-cap positional observed counts are wrong")
    check(len(capped.capped_diagnostics) == 1
          and capped.capped_diagnostics[0].fallback == "positional"
          and capped.pairing_trace[0].matrix_cells == 317 * 316,
          "above-cap structured diagnostic/trace is missing")


class SyntheticRawAdapter:
    """Tiny proof that corpus extraction can remain outside the oracle."""

    def adapt(self, raw_record, *, side, source_index, schema):
        prefix = "a_" if side == "a" else "b_"
        return oracle.OracleRow(
            source_index=source_index,
            key=(raw_record["route"], raw_record["key"]),
            values=(raw_record[prefix + "asserted"], raw_record["context"]),
            source_ref=f"{side}:{source_index}")


def test_raw_record_adapter_boundary():
    schema = oracle.OracleSchema(
        key_rules=(oracle.ValueRule("Route"), oracle.ValueRule("Key")),
        field_rules=(ordinary("Asserted"), ordinary("Context", asserting=False)))
    left = ({"route": "001", "key": "K", "a_asserted": "X",
             "context": "left-only-layout"},)
    right = ({"route": "001", "key": "K", "b_asserted": "X",
              "context": "right-only-layout"},)
    result = oracle.compare_raw_records(schema, left, right, SyntheticRawAdapter())
    check(result.verdict == "match" and result.counts.paired_rows == 1,
          "raw-record adapter boundary did not feed the pure oracle")
    check(result.row_results[0].source_index_a == 0
          and result.row_results[0].source_index_b == 0,
          "raw adapter did not preserve stable source indices")

    class BadAdapter:
        def adapt(self, raw_record, *, side, source_index, schema):
            return {"not": "an OracleRow"}

    try:
        oracle.adapt_raw_records(left, BadAdapter(), side="a", schema=schema)
    except TypeError:
        pass
    else:
        raise AssertionError("raw adapter output type was not enforced")


def main():
    test_forbidden_imports()
    test_d2_policy()
    test_d3_exact_lexicographic_objective()
    test_structured_keys_pairing_and_counts()
    test_raw_record_adapter_boundary()
    print("OK  independent Phase-3 oracle: approved typed D2 semantics, exact "
          "rectangular lexicographic D3 assignment, counts, cap behavior, raw-record "
          "adapter seam, and forbidden production imports")


if __name__ == "__main__":
    main()
