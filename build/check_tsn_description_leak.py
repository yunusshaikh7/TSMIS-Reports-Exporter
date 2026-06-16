"""Golden check for the TSN Highway Log Description-leak fix
(scripts/consolidate_tsn_highway_log.py).

City/County/District totals blocks (cumulative mileage + DVMS/DVMT volume) wrap
onto their own lines below the last data row of a group. The first line starts
with "*" (already skipped) but the wrapped continuations did not, so they were
appended to the preceding segment's Description — manufacturing false
discrepancies in the TSMIS-vs-TSN comparison (48 / 70 / 150 leaked rows in
D01 / D02 / D03; e.g. loc 015.900 got Description "(DVMS) 3,391").

_is_totals_line() now recognises those continuations. This locks the predicate:
every real leak pattern is caught, and real highway-feature descriptions —
crucially "…UNCONSTRUCTED…", which contains the substring UNCONST — are kept.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsn_description_leak.py

Real-data verified (2026-06-16): D01-D03 catch every totals continuation and
drop no legit description; the TSMIS-vs-TSN Route-1 comparison's Description
diffs fall 12 -> 10 (the 2 leak-caused false positives removed).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from consolidate_tsn_highway_log import _is_totals_line

TOTALS = [
    "(DVMS) 3,391",
    "(within District) (DVMS) 305,169",
    "CUMULATIVE (MILEAGE) TOTAL 103.430 CONST 103.430 UNCONST 000.000",
    "TOTAL CONST UNCONST",
    "County Cumulative DVM 123,414",
    "****CITY TOTALS (MILEAGE)",
    "089.826",                 # bare cumulative-mileage fragment
    "3,391",                   # bare volume fragment
    "000.000 000.000 000.000",
]

DESCRIPTIONS = [
    "JCT 5 CAMINO L RMBLS UC, BEG IN LIEU FAP 28",
    "COUNTY BEGIN: ORA",
    "RAMP NOSE-RT(RTE 5SB)",
    "BR 55-239",
    "APPROX JCT ST 36 /UNCONSTRUCTED RD E S GRASSHOPPER RD",  # has UNCONST inside
    "EB 55-239",
    "NB ON FROM SB RTE 5-RT",
]


def main():
    for line in TOTALS:
        assert _is_totals_line(line), ("should be skipped as totals", line)
    for line in DESCRIPTIONS:
        assert not _is_totals_line(line), ("must be kept as a description", line)
    print("OK  TSN Description leak: every totals-block continuation is skipped "
          f"({len(TOTALS)} patterns) and every real description is kept "
          f"({len(DESCRIPTIONS)}, incl. UNCONSTRUCTED).")


if __name__ == "__main__":
    main()
