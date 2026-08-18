"""Golden check: the paired-roadbed ditto convention holds for HIGHWAY DETAIL.

The Highway Log study (docs/highway_log/comparison-study.md §3) established the
domain rule: a `+`/`++` cell is a POINTER to the paired roadbed's own row, never
data, so it can never be a difference in itself. Highway Detail's TSN source uses
the very same convention -- the 2026-08-18 statewide census of the 60,083-row
extract found 1,992 rows carrying a dittoed block (1,027 LEFT, all HG='R'; 965
RIGHT, all HG='L'), zero rows dittoing both, and zero partial blocks -- while the
TSMIS export expands every one of them. Until v0.38.2 the Highway Detail schema
never switched the rule on, so all 17,928 of those cells were counted as
differences: ~10% of the reported statewide total, none of them real.

Locks, on the SHIPPED schemas (not a hand-made stand-in):
  * both vs-TSN flavors (Excel-sourced and PDF-sourced) set ditto_nonasserting
  * a dittoed block against the TSMIS values it points past is NOT a difference
  * a genuine disagreement in the same row still IS one
  * the PDF-vs-Excel self-check stays OFF (both sides expand; nothing to suppress)
  * the display resolver fills from the covering paired-roadbed SPAN, and returns
    None -- never a guess -- when no span covers it or covering spans disagree

Runs on the plain build venv python (no login, no Excel):
  build\\.venv\\Scripts\\python.exe build\\check_highway_detail_ditto.py
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001 - console encoding is best-effort
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import compare_core as cc                      # noqa: E402
import compare_highway_detail_pdf as hdp       # noqa: E402
import compare_highway_detail_tsn as hd        # noqa: E402
import highway_detail_columns as hdc           # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAILS.append(name)


H = hd.SHARED_HEADER
LB = list(range(12, 21))
RB = list(range(26, 35))


def row(pm, hg, length, lb, rb, desc="X"):
    r = [""] * len(H)
    r[0], r[2], r[4], r[10] = pm, length, hg, desc
    for i, c in enumerate(LB):
        r[c] = lb[i]
    for i, c in enumerate(RB):
        r[c] = rb[i]
    return r


# The real statewide case: route 001 MON PM 081.505 (the very record the Highway
# Log study uses). TSN prints the Right-roadbed row with its LEFT block dittoed;
# TSMIS expands the same nine cells. The paired LEFT-roadbed row carries the
# values the ditto points at.
DITTO_LB = ["++++++++", "+", "++", "+", "++", "++", "+++", "++", "++"]
REAL_LB = ["73-06-08", "C", "03", "Z", "11", "10", "36", "09", "08"]
RIGHT_BLK = ["73-06-08", "C", "03", "Z", "09", "08", "36", "11", "10"]

rows_tsmis = [row("R081.505R", "R", "000.400", REAL_LB, RIGHT_BLK)]
rows_tsn = [row("R081.505R", "R", "000.400", DITTO_LB, RIGHT_BLK)]


def diffs(sc, a, b):
    kt, kn = cc.keys_for(a, False, 0), cc.keys_for(b, False, 0)
    return cc.count_diffs(sc, a, b, kt, kn, cc.union_keys(kt, kn), False)


print("=== the shipped schemas switch the rule on ===")
check("Excel-sourced vs-TSN sets ditto_nonasserting",
      hd._SCHEMA.ditto_nonasserting is True)
check("Excel-sourced vs-TSN sets a ditto_resolver",
      hd._SCHEMA.ditto_resolver is not None)
check("PDF-sourced vs-TSN sets ditto_nonasserting",
      hdp.TSMIS_PDF_VS_TSN._schema.ditto_nonasserting is True)

print("\n=== a dittoed block is not a difference ===")
d = diffs(hd._SCHEMA, rows_tsmis, rows_tsn)
check("the 9 dittoed LEFT cells count 0 differences", d["diff_cells"] == 0)
check("the row still pairs (1 matched location)", d["both"] == 1)

# A REAL disagreement in the same row must survive untouched.
rows_tsn_real = [row("R081.505R", "R", "000.400", DITTO_LB,
                     ["73-06-08", "C", "03", "Z", "09", "08", "36", "11", "99"])]
d2 = diffs(hd._SCHEMA, rows_tsmis, rows_tsn_real)
check("a real RB disagreement still counts (1)", d2["diff_cells"] == 1)

print("\n=== the cell keeps its raw ditto, with no diff marker ===")
fv = cc._field_value(hd._SCHEMA, rows_tsmis[0], rows_tsn[0], 0, 12)
check("ditto cell carries no ' ≠ ' marker", cc._DIFF_MARK not in str(fv))

print("\n=== PDF-vs-Excel stays OFF (both sides expand) ===")
check("PDF-vs-Excel leaves ditto_nonasserting OFF",
      hdp.TSMIS_PDF_VS_EXCEL._schema.ditto_nonasserting is False)

print("\n=== the display resolver fills from the covering span ===")
# The dittoed Right-roadbed row sits inside the LEFT-roadbed row's span.
spanned = [
    row("R081.505R", "R", "000.400", DITTO_LB, RIGHT_BLK),
    row("R081.200L", "L", "001.000", REAL_LB, DITTO_LB),
]
fills = hdc.paired_roadbed_fills(spanned, False)
got = [fills.get(0, {}).get(c) for c in LB]
check("row 0's dittoed LEFT resolves to the paired row's values", got == REAL_LB)

# No covering span -> None, never a guess (and never the row above).
orphan = [
    row("R081.505R", "R", "000.400", DITTO_LB, RIGHT_BLK),
    row("R900.000L", "L", "000.100", REAL_LB, DITTO_LB),
]
of = hdc.paired_roadbed_fills(orphan, False)
check("an uncovered ditto resolves to None (not guessed)",
      all(of.get(0, {}).get(c) is None for c in LB))

# Two covering spans that DISAGREE -> None as well.
other = ["70-01-01", "H", "02", "Z", "05", "04", "24", "03", "02"]
ambig = [
    row("R081.505R", "R", "000.400", DITTO_LB, RIGHT_BLK),
    row("R081.200L", "L", "001.000", REAL_LB, DITTO_LB),
    row("R081.300L", "L", "001.000", other, DITTO_LB),
]
am = hdc.paired_roadbed_fills(ambig, False)
check("disagreeing covering spans resolve to None",
      all(am.get(0, {}).get(c) is None for c in LB))

print("\n=== the ditto predicate ===")
for t in ("+", "++", "+++", "++++++++"):
    check(f"is_ditto({t!r})", hdc.is_ditto(t))
for t in ("", "C", "0Z", "+0", None, "+ +", "73-06-08"):
    check(f"not is_ditto({t!r})", not hdc.is_ditto(t))

print("\nRESULT:", "ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
