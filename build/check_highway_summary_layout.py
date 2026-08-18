"""build/check_highway_summary_layout.py — the Highway Summary layout contract.

Highway Summary's per-route export is a fixed statistics document, and
`highway_summary_columns.values_from_rows` is the ONE reader the consolidator and
the cross-environment loader both go through (the CMP-AUD-018 rule: two paths
that read differently can certify a clean match between two equally-broken
sides). This check proves the reader's TRIPWIRE actually fires — a renamed
section, a new/unknown code, a dropped or duplicated row, a missing total, or an
over-precise value must each FAIL loudly rather than silently yielding a table.

Hermetic by construction: every sheet here is synthesized from the spec itself,
so the check needs no corpus and runs anywhere CI does. The real 252-route
statewide census that produced the spec is recorded in the module docstring and
re-proved by build/check_highway_summary_real.py when the corpus is present.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_highway_summary_layout.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import highway_summary_columns as hsc

_fail = []


def check(name, cond, detail=""):
    suffix = f"  -> {detail}" if (not cond and detail) else ""
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}{suffix}")
    if not cond:
        _fail.append(name)


def canonical_rows(total="640.899", value="1.000", value_for=None):
    """The (col A, col B) pairs of a well-formed per-route sheet, built from the
    spec so the 'good' case can never drift from what the reader expects.

    `value_for(section, cat, index_in_section)` overrides the flat `value` when a
    test needs a specific distribution (e.g. a route whose sections partition the
    total exactly)."""
    rows = [(hsc.TITLE_LINE, None), (hsc.SUBTITLE_LINE, None), (None, None),
            (hsc.TOTAL_LABEL, total), (None, None)]
    for section in hsc.SECTIONS:
        rows.append((section.name, None))
        rows.append(("Code", "Miles"))
        for i, cat in enumerate(section.cats):
            rows.append((cat.label,
                         value if value_for is None else value_for(section, cat, i)))
        rows.append((None, None))
    return rows


def exactly_partitioned_rows(total="95.000"):
    """A route whose every section tabulates the total EXACTLY: the first
    category of each section carries all of it, the rest are a real source 0."""
    return canonical_rows(
        total=total,
        value_for=lambda _sec, _cat, i: (total if i == 0 else "0"))


def refuses(rows, label, *, must_mention=None):
    """The reader must reject `rows` with a ValueError (optionally naming a term)."""
    try:
        hsc.values_from_rows(rows, source="probe.xlsx")
    except ValueError as e:
        text = str(e)
        if must_mention and must_mention.lower() not in text.lower():
            check(label, False, f"raised, but did not mention {must_mention!r}: {text}")
            return
        check(label, True)
        return
    except Exception as e:                       # noqa: BLE001 - any other type is a bug
        check(label, False, f"raised {type(e).__name__}, expected ValueError: {e}")
        return
    check(label, False, "the reader ACCEPTED a layout it must refuse")


def test_spec_invariants():
    print("the spec's own invariants:")
    check("10 sections", len(hsc.SECTIONS) == 10, f"{len(hsc.SECTIONS)}")
    check("95 category rows", len(hsc.CATS) == 95, f"{len(hsc.CATS)}")
    check("category keys unique", len({c.key for c in hsc.CATS}) == len(hsc.CATS))
    check("category slugs unique", len({c.slug for c in hsc.CATS}) == len(hsc.CATS))
    check("header is Route + total + every category",
          hsc.HEADER == [hsc.ROUTE_COL, hsc.TOTAL_KEY] + [c.key for c in hsc.CATS])
    check("header width 97", len(hsc.HEADER) == 97, f"{len(hsc.HEADER)}")
    check("recognize() accepts the canonical header", hsc.recognize(list(hsc.HEADER)) is True)
    check("recognize() rejects a truncated header",
          hsc.recognize(list(hsc.HEADER)[:-1]) is None)
    check("NON-ADD is the only independent section",
          hsc.INDEPENDENT_SECTIONS == frozenset({"NON-ADD"}),
          f"{set(hsc.INDEPENDENT_SECTIONS)}")


def test_reads_a_good_sheet():
    print("a well-formed sheet reads correctly:")
    total, values = hsc.values_from_rows(canonical_rows(), source="good.xlsx")
    check("total parsed as exact thousandths", total == 640899, f"{total}")
    check("every category present", len(values) == 95, f"{len(values)}")
    check("values are exact thousandths",
          set(values.values()) == {1000}, f"{sorted(set(values.values()))[:4]}")
    check("miles() round-trips", hsc.miles(640899) == 640.899, f"{hsc.miles(640899)}")
    print("  cosmetic whitespace/case drift is tolerated (not identity):")
    rows = [((a.replace("  ", "   ").lower() if isinstance(a, str) else a), b)
            for a, b in canonical_rows()]
    try:
        t2, v2 = hsc.values_from_rows(rows, source="respaced.xlsx")
        check("re-spaced + lower-cased labels still read", t2 == 640899 and len(v2) == 95)
    except ValueError as e:
        check("re-spaced + lower-cased labels still read", False, str(e))


def test_skeleton_tripwire():
    print("the skeleton tripwire fires on every layout change:")
    # a renamed section heading
    rows = [(("HIGHWAY GROUPS" if a == "HIGHWAY GROUP" else a), b)
            for a, b in canonical_rows()]
    refuses(rows, "a RENAMED section heading is refused", must_mention="section")

    # an unknown new code inside a known section
    rows = canonical_rows()
    at = next(i for i, (a, _b) in enumerate(rows) if a == "Z- NO BARRIER")
    rows.insert(at, ("W- NEW BARRIER TYPE", "1.000"))
    refuses(rows, "an UNKNOWN new code row is refused", must_mention="category")

    # a dropped code row
    rows = [r for r in canonical_rows() if r[0] != "Z- NO BARRIER"]
    refuses(rows, "a DROPPED code row is refused")

    # a duplicated code row
    rows = canonical_rows()
    at = next(i for i, (a, _b) in enumerate(rows) if a == "Z- NO BARRIER")
    rows.insert(at + 1, ("Z- NO BARRIER", "1.000"))
    refuses(rows, "a DUPLICATED code row is refused", must_mention="twice")

    # a whole dropped section
    drop = {c.label for c in hsc.SECTIONS[-1].cats} | {hsc.SECTIONS[-1].name}
    rows = [r for r in canonical_rows() if r[0] not in drop]
    refuses(rows, "a DROPPED section is refused")

    # reordered sections
    rows = canonical_rows()
    first = next(i for i, (a, _b) in enumerate(rows) if a == hsc.SECTIONS[0].name)
    last = next(i for i, (a, _b) in enumerate(rows) if a == hsc.SECTIONS[-1].name)
    block = rows[last:]
    refuses(rows[:first] + block + rows[first:last], "REORDERED sections are refused")

    # a mileage with no label — unattributable, and invisible to the skeleton check
    rows = canonical_rows()
    rows.insert(6, (None, "12.345"))
    refuses(rows, "an UNLABELLED mileage is refused", must_mention="no category label")
    # ...while a genuinely blank spacer row stays fine
    rows = canonical_rows()
    rows.insert(6, (None, None))
    try:
        t, v = hsc.values_from_rows(rows, source="spacer.xlsx")
        check("an extra BLANK spacer row is still accepted", t == 640899 and len(v) == 95)
    except ValueError as e:
        check("an extra BLANK spacer row is still accepted", False, str(e))

    # the total line missing / duplicated
    refuses([r for r in canonical_rows() if r[0] != hsc.TOTAL_LABEL],
            "a MISSING total row is refused", must_mention="TOTAL MILES SELECTED")
    rows = canonical_rows()
    rows.insert(4, (hsc.TOTAL_LABEL, "1.000"))
    refuses(rows, "a DUPLICATED total row is refused", must_mention="twice")


def test_value_parsing_is_strict():
    print("miles parsing is strict:")
    for bad, label in ((True, "a boolean"), ("", "empty text"), ("n/a", "non-numeric text"),
                       (-1.5, "a negative mileage"), (0.12345, "an over-precise mileage"),
                       (float("nan"), "NaN"), (float("inf"), "infinity"),
                       (None, "a blank")):
        rows = [((a, bad) if a == "Z- NO BARRIER" else (a, b))
                for a, b in canonical_rows()]
        # A blank col-B turns the row into a "section heading" — still a refusal,
        # just via the skeleton arm; both are the contract.
        refuses(rows, f"{label} in a value cell is refused")
    print("  three decimals are accepted, four are not:")
    ok = True
    try:
        hsc.parse_miles("1.234", source="p", category="c")
    except ValueError:
        ok = False
    check("three decimals accepted", ok)
    try:
        hsc.parse_miles("1.2345", source="p", category="c")
        check("four decimals refused", False, "accepted 1.2345")
    except ValueError:
        check("four decimals refused", True)
    check("integer thousandths are exact",
          hsc.parse_miles("640.899", source="p", category="c") == 640899)
    check("a plain int mileage reads", hsc.parse_miles(0, source="p", category="c") == 0)


def test_partition_contract():
    print("the partition contract:")
    total, values = hsc.values_from_rows(canonical_rows(total="95.000"),
                                         source="good.xlsx")
    check("a sound route has no partition problem",
          hsc.partition_problem(total, values, source="good.xlsx") is None)

    # every non-independent section sums 1.000 * len(cats); make the total tiny so
    # a real section overshoots it.
    total_small, values_small = hsc.values_from_rows(canonical_rows(total="1.000"),
                                                     source="small.xlsx")
    problem = hsc.partition_problem(total_small, values_small, source="small.xlsx")
    check("a section summing ABOVE the total is refused", problem is not None)
    check("the refusal names the offending section and both figures",
          bool(problem) and "HIGHWAY GROUP" in problem and "1.000" in problem,
          f"{problem}")

    # NON-ADD is independent: it may exceed the total without any complaint.
    rows = [((a, "500.000") if a == "N Non-Add" else (a, b)) for a, b in
            canonical_rows(total="95.000")]
    t, v = hsc.values_from_rows(rows, source="nonadd.xlsx")
    check("NON-ADD above the total is NOT a problem (independent section)",
          hsc.partition_problem(t, v, source="nonadd.xlsx") is None)

    # bounded residuals are exposed as notes, never fabricated away
    notes = hsc.partition_notes(total * 2, values)
    check("a section summing BELOW the total is exposed as a note", len(notes) == 9,
          f"{len(notes)} notes")
    check("the note names the section and both figures",
          bool(notes) and "HIGHWAY GROUP" in notes[0] and "tabulated" in notes[0],
          f"{notes[:1]}")

    # a route whose sections each partition the total exactly: no residual at all
    t_exact, v_exact = hsc.values_from_rows(exactly_partitioned_rows(),
                                            source="exact.xlsx")
    check("an exactly-partitioned route has no partition problem",
          hsc.partition_problem(t_exact, v_exact, source="exact.xlsx") is None)
    check("an exactly-partitioned route produces no notes",
          hsc.partition_notes(t_exact, v_exact) == [],
          f"{hsc.partition_notes(t_exact, v_exact)}")


def main():
    print("=== Highway Summary layout contract ===")
    test_spec_invariants()
    test_reads_a_good_sheet()
    test_skeleton_tripwire()
    test_value_parsing_is_strict()
    test_partition_contract()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL HIGHWAY SUMMARY LAYOUT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
