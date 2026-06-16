"""Golden check for COMPARE-VALUE-COERCION (compare_core.normalize_value +
the loaders).

The comparison compares values in text form (_xl_trim / Excel TRIM). Two risks:
  * type drift: a value stored as a number on one side and text on the other
    (e.g. 5 vs "5") would read as different;
  * real dates: a datetime cell makes the VALUES flavor (Python str(datetime))
    and the FORMULAS flavor (Excel TRIM of a live date) compute DIFFERENT text
    for the SAME cell — the two flavors would disagree (the core invariant is
    that they can't).

normalize_value() canonicalizes a loaded date/datetime to a fixed ISO string at
LOAD time, so the engine only ever sees text: both flavors agree, and an equal
date on both sides compares equal. Integer-vs-text numbers already canonicalize
via _xl_trim. This locks both.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_coercion.py
"""
import os
import sys
import tempfile
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from compare_core import (CompareSchema, _field_value, _xl_trim, count_diffs,
                          keys_for, normalize_value, run_compare, union_keys)


def test_normalize_value():
    assert normalize_value(datetime(1976, 2, 25)) == "1976-02-25"
    assert normalize_value(date(1976, 2, 25)) == "1976-02-25"
    assert normalize_value(datetime(1976, 2, 25, 13, 30, 5)) == "1976-02-25 13:30:05"
    for v in ("000.129", 0.129, 5, "5", None, "JCT 5"):
        assert normalize_value(v) == v


def test_integer_number_vs_text_matches():
    # 5 (int) vs "5" (text) and 5.0 (float) vs "5" must NOT be a difference.
    assert _xl_trim(5) == _xl_trim("5") == _xl_trim(5.0) == "5"


def test_real_date_flavor_parity():
    # A datetime present on BOTH sides, plus a date that differs by one day.
    # After loader normalization the engine sees ISO strings; the values-flavor
    # mirror (_field_value) and the run-summary counts agree, and an equal date
    # compares equal — no phantom diff, no flavor disagreement.
    sc = CompareSchema(report_name="Dt", header=["Loc", "When"], side_a="A",
                       side_b="B", id_noun="row", id_noun_plural="rows")
    norm = lambda rows: [[normalize_value(v) for v in r] for r in rows]
    a = norm([["1", datetime(1976, 2, 25)], ["2", datetime(2020, 1, 1)]])
    b = norm([["1", datetime(1976, 2, 25)], ["2", datetime(2020, 1, 2)]])
    kt, kn = keys_for(a, False), keys_for(b, False)
    u = union_keys(kt, kn)
    c = count_diffs(sc, a, b, kt, kn, u, False)
    assert c["both"] == 2 and c["diff_cells"] == 1, c   # only row 2 differs
    by_t = {k: a[i] for i, k in enumerate(kt)}
    by_n = {k: b[i] for i, k in enumerate(kn)}
    # row 1: equal date → value shown verbatim, no marker; row 2: differ marker.
    v1 = _field_value(sc, by_t[("", "1", 1)], by_n[("", "1", 1)], 0, 1)
    v2 = _field_value(sc, by_t[("", "2", 1)], by_n[("", "2", 1)], 0, 1)
    assert v1 == "1976-02-25" and " ≠ " in v2, (v1, v2)

    # End-to-end: the values workbook builds and the verdict is "diff" (1 cell).
    out = os.path.join(tempfile.gettempdir(), "_coercion.xlsx")
    res = run_compare(sc, a, b, False, out, mode="values")
    assert res.verdict == "diff", res.verdict
    os.remove(out)


def main():
    test_normalize_value()
    test_integer_number_vs_text_matches()
    test_real_date_flavor_parity()
    print("OK  COMPARE-VALUE-COERCION: dates canonicalize to ISO at load (both "
          "flavors agree; equal dates match), integer/number-vs-text compare "
          "equal.")


if __name__ == "__main__":
    main()
