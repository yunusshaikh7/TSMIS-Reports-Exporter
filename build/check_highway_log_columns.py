"""Golden check for the corrected Highway Log column labels
(scripts/highway_log_columns.py).

The vendor TSMIS Excel export mislabeled the Highway Log columns ("N/A" is
really Non-Add Mileage; "LB T" is the Left-roadbed Surface Type; two columns
were both "RB SH"…) and those wrong labels propagated to every Highway Log
workflow. This locks the CORRECTED labels (decoded from the report's own legend
and approved by the user), the vendor→corrected mapping, and the recognize()
gate that lets the comparison still read pre-overhaul (vendor-labeled) workbooks
by POSITION.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_highway_log_columns.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import highway_log_columns as hlc

# A few load-bearing corrections (position -> expected canonical label). These
# are the columns the vendor got wrong; if any drifts, a Highway Log workflow is
# mislabeling data again.
EXPECT = {
    0: "Location",
    1: "Length (MI) [MI]",
    2: "NA [N/A]",                      # NOT "not applicable"
    10: "LB ST [LB T]",                 # Surface Type, not "T"
    12: "LB SF [LB F]",                 # Special Features, not "F"
    13: "LB OT-SH Total [LB OT]",
    14: "LB OT-SH Treated [LB TR]",
    16: "LB IN-SH Total [LB IN]",
    17: "LB IN-SH Treated [LB SH]",
    18: "Med TY/CL/BA [Med TCB]",
    19: "Med Wid/Var [Med Wid]",
    23: "RB IN-SH Total [RB IN]",
    24: "RB IN-SH Treated [RB SH]",     # vendor's first duplicate "RB SH"
    27: "RB OT-SH Treated [RB SH]",     # vendor's second duplicate "RB SH"
    28: "Description",
    29: "Date of Rec",
    30: "Sig Chg. Date",
}

VENDOR_EXACT = [
    "Location", "MI", "N/A", "Cnty Odom", "City", "R/U", "SPD", "TER", "H/G",
    "A/C", "LB T", "LB Lns", "LB F", "LB OT", "LB TR", "LB T-W", "LB IN",
    "LB SH", "Med TCB", "Med Wid", "RB T", "RB Lns", "RB F", "RB IN", "RB SH",
    "RB T-W", "RB OT", "RB SH", "Description", "Date of Rec", "Sig Chg. Date",
]


def main():
    assert len(hlc.HEADER) == 31, len(hlc.HEADER)
    assert len(hlc.VENDOR_HEADER) == 31, len(hlc.VENDOR_HEADER)
    assert hlc.DESC_IDX == 28, hlc.DESC_IDX

    for i, want in EXPECT.items():
        assert hlc.HEADER[i] == want, (i, hlc.HEADER[i], want)

    # VENDOR_HEADER must be the EXACT old labels (so a pre-overhaul workbook is
    # recognized by position) — including the vendor's duplicate "RB SH".
    assert hlc.VENDOR_HEADER == VENDOR_EXACT, hlc.VENDOR_HEADER
    assert hlc.VENDOR_HEADER.count("RB SH") == 2, "vendor had a duplicate RB SH"

    # The corrected labels must be UNIQUE (the duplicate-label bug is fixed).
    assert len(set(hlc.HEADER)) == 31, "corrected labels must be unique"

    # recognize(): accept canonical + vendor, with/without a leading Route;
    # reject anything else, and reject a wrong-width header.
    assert hlc.recognize(hlc.HEADER) is False
    assert hlc.recognize(hlc.VENDOR_HEADER) is False
    assert hlc.recognize([hlc.ROUTE_COL] + hlc.HEADER) is True
    assert hlc.recognize([hlc.ROUTE_COL] + hlc.VENDOR_HEADER) is True
    assert hlc.recognize(["totally", "different"]) is None
    assert hlc.recognize(hlc.HEADER[:-1]) is None          # wrong width
    assert hlc.recognize(hlc.HEADER + ["extra"]) is None

    # Every column has a non-empty tooltip meaning; every group is one of the
    # four bands or blank.
    groups = set()
    for grp, label, vendor, meaning in hlc.legend_rows():
        assert meaning and hlc.tooltip_for(label), label
        groups.add(grp)
    assert groups <= {"", "Location & Distance", "Left Roadbed", "Median",
                      "Right Roadbed"}, groups

    print(f"OK  Highway Log columns: {len(hlc.HEADER)} corrected labels locked "
          f"(NA/ST/SF/OT-SH/IN-SH/Median fixed; duplicate 'RB SH' disambiguated); "
          f"recognize() accepts both the corrected and the vendor layout.")


if __name__ == "__main__":
    main()
