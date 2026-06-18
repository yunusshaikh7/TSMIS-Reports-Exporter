"""Golden check: ditto (`+`-run) cells are NON-ASSERTING in a Highway Log
comparison and INERT everywhere else.

Locks compare_core's `ditto_nonasserting` behavior:
  * count_diffs / _field_value: a cell where either side is a '+'-run never
    counts as a difference (its real value is compared on the paired roadbed row)
  * the Excel formula gains the all-'+' test only when the flag is on
  * with the flag OFF (every non-Highway-Log comparison) the output is unchanged

Runs on the plain build venv python (no login, no Excel):
  build\\.venv\\Scripts\\python.exe build\\check_compare_ditto.py
"""
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import compare_core as cc       # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAILS.append(name)


# Minimal Highway-Log-shaped schema: key + a Left-roadbed and Right-roadbed col.
HEADER = ["Loc", "LB ST", "RB ST"]
SC_ON = cc.CompareSchema(report_name="HL", header=HEADER, side_a="A", side_b="B",
                         ditto_nonasserting=True)
SC_OFF = replace(SC_ON, ditto_nonasserting=False)

# A: PDF side with a ditto in LB ST; B: expanded side. RB ST agrees.
rows_a = [["L1", "++", "X"], ["L2", "+", "Y"], ["L3", "C", "Z"]]
rows_b = [["L1", "C", "X"], ["L2", "M", "Y"], ["L3", "C", "W"]]   # L3 RB differs (real)


def diffs(sc):
    kt = cc.keys_for(rows_a, False, 0)
    kn = cc.keys_for(rows_b, False, 0)
    union = cc.union_keys(kt, kn)
    return cc.count_diffs(sc, rows_a, rows_b, kt, kn, union, False)


on, off = diffs(SC_ON), diffs(SC_OFF)
# OFF: L1 LB(++≠C), L2 LB(+≠M), L3 RB(Z≠W) = 3 diff cells.
check("flag OFF counts ditto cells as diffs (3)", off["diff_cells"] == 3)
# ON: the two ditto cells drop; only the real L3 RB diff remains.
check("flag ON makes ditto non-asserting (1 real diff left)", on["diff_cells"] == 1)
check("ON/OFF agree on matched-row count", on["both"] == off["both"] == 3)

# _field_value: the ditto cell shows side A's value, no ' ≠ '; the real diff still marks.
fv_ditto = cc._field_value(SC_ON, rows_a[0], rows_b[0], 0, 1)     # L1 LB ST
fv_real = cc._field_value(SC_ON, rows_a[2], rows_b[2], 0, 2)      # L3 RB ST
check("ON: ditto cell value has no ' ≠ '", cc._DIFF_MARK not in str(fv_ditto))
check("ON: ditto cell shows side A value '++'", fv_ditto == "++")
check("ON: a real diff still shows ' ≠ '", cc._DIFF_MARK in str(fv_real))
check("OFF: ditto cell shows ' ≠ ' (unchanged)",
      cc._DIFF_MARK in str(cc._field_value(SC_OFF, rows_a[0], rows_b[0], 0, 1)))

# Formula: the all-'+' SUBSTITUTE test appears ONLY with the flag on.

class _Lay:
    def __init__(self, sc):
        self.sc = sc
        self.c_trow, self.c_nrow, self.c_status = "C", "D", "E"
        self.only_a, self.only_b = "A only", "B only"

    def data_col(self, f):
        return "G"


f_on = cc._field_formula(_Lay(SC_ON), 2, 1)
f_off = cc._field_formula(_Lay(SC_OFF), 2, 1)
check("ON formula contains the all-'+' ditto test", 'SUBSTITUTE' in f_on and '"+"' in f_on)
check("OFF formula is unchanged (no ditto test)", 'SUBSTITUTE' not in f_off)

# _is_plus_run primitive
for t in ("+", "++", "+++"):
    check(f"_is_plus_run({t!r})", cc._is_plus_run(t))
for t in ("", "C", "0Z", "+0", None, "+ +"):
    check(f"not _is_plus_run({t!r})", not cc._is_plus_run(t))

print("\nRESULT:", "ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
