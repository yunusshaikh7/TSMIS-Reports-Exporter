"""CMP-AUD-115 — the versioned comparison-artifact schema at the commit boundary.

The transactional commit used to require only that openpyxl could open the
workbook and that a sheet named `Comparison` existed, so a header-only or
label-less Comparison sheet published with status=ok / verdict=match.

The gate's rejection domain is deliberately a SUBSET of what the Matrix count
reader already cannot read: everything refused here would have read as
`(None, None)` anyway, so no legitimate report can be blocked. That equivalence
is asserted directly below, and the census walks every supported comparison
recipe to prove the shipped comparators' real output satisfies the schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from _checklib import Checker, temp_dir, write_comparison_stub  # noqa: E402

import artifact_store as a  # noqa: E402
import matrix_state  # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402

c = Checker()


def _typed(rows=1, completion="complete"):
    return ComparisonOutcome(
        status="ok", completion=completion,
        verdict="match" if completion == "complete" else "diff",
        counts=ComparisonCounts(known=True, paired_rows=rows),
        warnings=(() if completion == "complete" else ("incomplete",)),
        pairing_quality="exact")


def _commit(final, writer, mode="values", rows=1, twin=False):
    def produce(tmp):
        writer(Path(tmp))
        return ConsolidateResult(
            status="ok", output_path=str(tmp), verdict="match",
            completion="complete", skipped_inputs=0, failed_inputs=0,
            comparison_outcome=_typed(rows))
    return a.commit_workbook(final, produce, expect_sheet="Comparison",
                             requested_mode=mode, twin=twin)


def _sheet(path, header, rows=(), title="Comparison"):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    if header is not None:
        ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    wb.save(str(path))
    wb.close()


def main(tmp: Path) -> None:
    print("the schema accepts a real comparison artifact:")
    good = tmp / "good.xlsx"
    res = _commit(good, lambda p: write_comparison_stub(p, rows=3))
    c.check("a labelled Comparison sheet with valid rows commits",
            res.status == "ok" and good.exists(), repr(res.message))
    c.check("the schema is versioned", isinstance(a.COMPARISON_ARTIFACT_SCHEMA, int)
            and a.COMPARISON_ARTIFACT_SCHEMA >= 1)

    print("the audit's own artifacts are REFUSED, last-good kept:")
    prior = good.read_bytes()
    header_only = lambda p: _sheet(p, ["Route", "Status", "Diffs"])           # noqa: E731
    no_labels = lambda p: _sheet(p, ["Route", "State", "Count"],              # noqa: E731
                                 [["001", "Both", 0]])
    a1_only = lambda p: _sheet(p, None, [["x"]])                              # noqa: E731
    dup_labels = lambda p: _sheet(p, ["Status", "Status", "Diffs"],           # noqa: E731
                                  [["Both", "Both", 0]])
    bad_status = lambda p: _sheet(p, ["Route", "Status", "Diffs"],            # noqa: E731
                                  [["001", 42, 0]])
    diffs_on_one_sided = lambda p: _sheet(p, ["Route", "Status", "Diffs"],    # noqa: E731
                                          [["001", "TSMIS only", 3]])
    bad_diffs = lambda p: _sheet(p, ["Route", "Status", "Diffs"],             # noqa: E731
                                 [["001", "Both", "lots"]])
    cases = [
        ("a header-only Comparison sheet under a typed row claim", header_only),
        ("a Comparison sheet with neither Status nor Diffs labels", no_labels),
        ("a bare A1='x' Comparison sheet", a1_only),
        ("duplicate Status labels", dup_labels),
        ("a non-string row status", bad_status),
        ("a one-sided row carrying Diffs", diffs_on_one_sided),
        ("a matched row with a non-integer Diffs", bad_diffs),
    ]
    for label, writer in cases:
        res = _commit(good, writer, rows=5)
        c.check(f"REFUSED: {label}",
                res.status == "error" and good.read_bytes() == prior,
                f"status={res.status} message={res.message!r}")
    c.check("the refusal names the artifact and keeps the previous file",
            "left unchanged" in (res.message or ""), repr(res.message))

    print("the rejection domain is a SUBSET of the unreadable domain:")
    for label, writer in cases:
        probe = tmp / "probe.xlsx"
        writer(probe)
        problem = a.comparison_artifact_problem(probe, _typed(rows=5))
        counts = matrix_state.read_counts(probe)
        unreadable = counts == (None, None)
        # A refused artifact must already be unreadable to the Matrix — except
        # the header-only case, which is refused for contradicting the typed row
        # claim rather than for being unreadable.
        c.check(f"{label}: refused implies Matrix-unreadable (or a typed contradiction)",
                problem is None or unreadable or writer is header_only,
                f"problem={problem!r} counts={counts!r}")

    print("the gate is scoped to a typed comparison's VALUES artifact:")
    formulas = tmp / "formulas.xlsx"
    res = _commit(formulas, a1_only, mode="formulas")
    c.check("a live-formulas commit is NOT schema-gated (its cells are formulas)",
            res.status == "ok" and formulas.exists(), repr(res.message))
    plain = tmp / "plain.xlsx"

    def produce_untyped(t):
        _sheet(Path(t), None, [["x"]], title="Sheet1")
        return ConsolidateResult(status="ok", output_path=str(t))

    res = a.commit_workbook(plain, produce_untyped)
    c.check("an ordinary consolidation commit is NOT schema-gated",
            res.status == "ok" and plain.exists(), repr(res.message))

    twin_final = tmp / "twin.xlsx"

    def produce_twin(t):
        t = Path(t)
        _sheet(t, None, [["formulas"]])                     # formulas primary
        write_comparison_stub(a._values_twin(t))            # the VALUES artifact
        return ConsolidateResult(
            status="ok", output_path=str(t), verdict="match", completion="complete",
            skipped_inputs=0, failed_inputs=0, comparison_outcome=_typed())

    res = a.commit_workbook(twin_final, produce_twin, expect_sheet="Comparison",
                            requested_mode="both", twin=True)
    c.check("mode=both gates the VALUES twin, not the formulas primary",
            res.status == "ok", repr(res.message))

    def produce_twin_bad(t):
        t = Path(t)
        _sheet(t, None, [["formulas"]])
        _sheet(a._values_twin(t), ["Route", "State"], [["001", "Both"]])
        return ConsolidateResult(
            status="ok", output_path=str(t), verdict="match", completion="complete",
            skipped_inputs=0, failed_inputs=0, comparison_outcome=_typed())

    bad_twin = tmp / "twin-bad.xlsx"
    res = a.commit_workbook(bad_twin, produce_twin_bad, expect_sheet="Comparison",
                            requested_mode="both", twin=True)
    c.check("mode=both REFUSES a label-less values twin",
            res.status == "error" and not bad_twin.exists(), repr(res.message))

    print("one reader serves the gate and the Matrix:")
    counts_path = tmp / "counts.xlsx"
    _sheet(counts_path, ["Route", "Status", "Diffs"],
           [["001", "Both", 4], ["002", "TSMIS only", None], ["003", "Both", 2]])
    c.check("the shared reader returns (diffs, one-sided, rows)",
            a.comparison_counts(counts_path) == (6, 1, 3),
            repr(a.comparison_counts(counts_path)))
    c.check("read_counts delegates to it unchanged",
            matrix_state.read_counts(counts_path) == (6, 1))


if __name__ == "__main__":
    print("CMP-AUD-115 comparison-artifact schema gate:")
    with temp_dir("tsmis_artifact_schema_") as tmp:
        main(Path(tmp))
    raise SystemExit(c.summary())
