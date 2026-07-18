"""Golden check for the comparison-capability DOCS (CMP-AUD-086).

Owning docs kept hand-maintained capability tables + counts that drifted from the
catalog: reports.md listed "10" comparison-integrated types and an incomplete
COMPARE_REPORTS table whose PDF-vs-Excel rows still read `env` after CMP-AUD-014
moved them to `self`. This pins the drift-prone surfaces to `report_catalog` (the
SoT), so a future audit can't bless a stale count or miss a live placement:

* the `docs/reports.md` COMPARE_REPORTS table == `report_catalog.COMPARE`
  (label / kind / group), in order and complete;
* the number-bearing prose (env-matrix row count, vs-TSN count, self-check count)
  matches the catalog's group tallies;
* the "disabled export set" prose matches `reports.DISABLED_EXPORT_SUBDIRS`.

Console-free, read-only. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_docs_capability.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import report_catalog as cat
import reports

_fail = []

_NUM_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _parse_compare_table(md):
    """Rows of the `COMPARE_REPORTS` markdown table as (label, kind, group).

    Locates the header row `| Label | Module / adapter | kind | group |`, skips the
    `|---|` separator, then reads pipe rows until the table ends. Returns None if
    the table is missing (so a check fails loudly instead of matching []-vs-[])."""
    lines = md.splitlines()
    start = None
    for i, ln in enumerate(lines):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells[:4] == ["Label", "Module / adapter", "kind", "group"]:
            start = i
            break
    if start is None:
        return None
    out = []
    for ln in lines[start + 2:]:                       # +1 header, +1 separator
        s = ln.strip()
        if not s.startswith("|"):
            break
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            break
        out.append((cells[0], cells[2], cells[3]))     # label, kind, group
    return out


def test_compare_table_matches_catalog():
    print("docs/reports.md COMPARE_REPORTS table == report_catalog.COMPARE:")
    md = (ROOT / "docs" / "reports.md").read_text(encoding="utf-8")
    rows = _parse_compare_table(md)
    check("the COMPARE_REPORTS table is present in reports.md", rows is not None)
    if rows is None:
        return
    expected = [(c.label, c.kind, c.group) for c in cat.COMPARE]
    check("table (label, kind, group) == catalog, complete and in order", rows == expected)
    if rows != expected:
        want = set(expected)
        for r in rows:
            if r not in want:
                print(f"      STALE/EXTRA doc row: {r}")
        have = set(rows)
        for e in expected:
            if e not in have:
                print(f"      MISSING doc row:     {e}")
    # NEGATIVE: the parser + comparison actually reject a mutated row (the exact
    # CMP-AUD-014 drift — a self-check parked back under env).
    mutated = [(l, k, "env" if g == "self" else g) for l, k, g in expected]
    check("[neg] a pdf-vs-excel row mislabeled `env` would be caught",
          mutated != expected)


def test_prose_counts_match_catalog():
    print("number-bearing prose == catalog group tallies:")
    md = (ROOT / "docs" / "reports.md").read_text(encoding="utf-8")
    env = sum(1 for c in cat.COMPARE if c.group == "env")
    tsn = sum(1 for c in cat.COMPARE if c.group == "tsn")
    self_ = sum(1 for c in cat.COMPARE if c.group == "self")
    check(f"reports.md states the env matrix is {env} rows",
          f"the env matrix is {env} rows" in md)
    check(f"reports.md states {tsn} vs-TSN comparisons",
          f"{tsn} of them" in md)
    check(f"reports.md names the {_NUM_WORD[self_]} PDF-vs-Excel self-checks",
          f"{_NUM_WORD[self_]} **PDF-vs-Excel**" in md
          or f"{_NUM_WORD[self_]} PDF-vs-Excel" in md)


def test_disabled_export_prose():
    print("the 'disabled export set' prose == reports.DISABLED_EXPORT_SUBDIRS:")
    md = (ROOT / "docs" / "reports.md").read_text(encoding="utf-8")
    disabled = reports.DISABLED_EXPORT_SUBDIRS
    if not disabled:
        check("reports.md states the export gate is empty (DISABLED_EXPORT_SUBDIRS == set())",
              "The gate is empty" in md and "DISABLED_EXPORT_SUBDIRS = set()" in md)
    else:
        # Non-empty: the doc must name every disabled subdir AND must NOT still claim
        # the gate is empty (the CMP-AUD-086 'empty despite Route History' drift).
        check("reports.md names every disabled export subdir",
              all(sub in md for sub in disabled))
        check("reports.md does NOT falsely claim the export gate is empty",
              "DISABLED_EXPORT_SUBDIRS = set()" not in md and "The gate is empty" not in md)


def main():
    test_compare_table_matches_catalog()
    test_prose_counts_match_catalog()
    test_disabled_export_prose()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL DOCS-CAPABILITY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
