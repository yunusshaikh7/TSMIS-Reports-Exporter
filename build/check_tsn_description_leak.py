"""Golden check for the TSN Highway Log Description-leak fix
(scripts/consolidate_tsn_highway_log.py).

City/County/District totals blocks (cumulative mileage + DVMS/DVMT volume) wrap
onto their own lines below the last data row of a group. The first line starts
with "*" (already skipped) but the wrapped continuations did not, so they were
appended to the preceding segment's Description — manufacturing false
discrepancies in the TSMIS-vs-TSN comparison (48 / 70 / 150 leaked rows in
D01 / D02 / D03; e.g. loc 015.900 got Description "(DVMS) 3,391").

_is_totals_line() recognises those continuations. This locks the predicate:
every real totals/footer fragment is caught, and real highway-feature
descriptions are kept — crucially the UNCONST family: "…UNCONSTRUCTED…" and
standalone abbreviations ("JCT UNCONST RTE 251", "CONTINUE ON UNCONST") are NOT
totals (UNCONST only marks a footer line paired with its CONST counterpart or a
mileage figure), and a lone hyphenated bridge number ("53-1075") is a real
one-token description, not a bare-numeric fragment.

NOTE: this fixture locks ONLY the _is_totals_line PATTERN. The converter also
guards descriptions structurally — an x0-gate (descriptions live at x0≈73; a
stray "TOTAL" fragment at x0≈170 and page furniture are excluded by position)
and a `*`-line that closes the open row. Those guards are verified by the
real-data audit, not this unit fixture.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsn_description_leak.py

Real-data verified (2026-06-16): across ALL 12 district PDFs (D01-D12), the
converter leaks 0 totals/furniture fragments into any Description and over-strips
0 real descriptions (60,083 rows); the TSMIS-vs-TSN Route-1 comparison holds at
969 diff cells.
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
    # "UNCONST" is a real abbreviation (UNCONSTRUCTED) in descriptions and must
    # be kept; it only marks a totals line paired with CONST / a mileage figure.
    "JCT UNCONST RTE 251/PT REYES",
    "JCT ST 84 UNC /JCT FAP 66 UNCONST RD",
    "CONTINUE ON UNCONST",
    "BEG ST 170 UNCONST RD N/LA INTER AIRPORT",
    # A lone hyphenated structure number is a legitimate one-token description,
    # not a bare-numeric totals fragment.
    "53-1075",
    "22-162",
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
