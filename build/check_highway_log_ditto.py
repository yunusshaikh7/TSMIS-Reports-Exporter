"""Golden check for the Highway Log ditto resolver (highway_log_columns).

Locks the validated `+`/`++`/`+++` "see paired roadbed" convention:
  * is_ditto recognizes runs of '+' and nothing else
  * the two 8-column roadbed blocks are at the expected positions
  * fill_paired_roadbed fills a dittoed block from the paired roadbed (preferring
    the same base postmile) and marks exactly the dittoed cells

Runnable with the plain build venv python (no login, no third-party libs):
  build\\.venv\\Scripts\\python.exe build\\check_highway_log_ditto.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import highway_log_columns as hlc      # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAILS.append(name)


# --- is_ditto -------------------------------------------------------------
for tok in ("+", "++", "+++"):
    check(f"is_ditto({tok!r})", hlc.is_ditto(tok))
for tok in ("C", "02", "0Z", "", "  ", None, "Z", "+0", "1+", "+ +"):
    check(f"not is_ditto({tok!r})", not hlc.is_ditto(tok))

# --- block positions ------------------------------------------------------
check("LEFT block is 8 cols", len(hlc.LEFT_BLOCK_IDX) == 8)
check("RIGHT block is 8 cols", len(hlc.RIGHT_BLOCK_IDX) == 8)
check("LEFT block label[0] is LB ST", hlc.HEADER[hlc.LEFT_BLOCK_IDX[0]].startswith("LB ST"))
check("RIGHT block label[0] is RB ST", hlc.HEADER[hlc.RIGHT_BLOCK_IDX[0]].startswith("RB ST"))
check("blocks disjoint", not (set(hlc.LEFT_BLOCK_IDX) & set(hlc.RIGHT_BLOCK_IDX)))

# --- fill_paired_roadbed --------------------------------------------------
W = len(hlc.HEADER)
L = hlc.LEFT_BLOCK_IDX
R = hlc.RIGHT_BLOCK_IDX
LEFTVALS = ["LH", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
RIGHTVALS = ["RH", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
DITTO8 = ["+", "++", "+", "++", "++", "+++", "++", "++"]


def blank_row(loc):
    r = [""] * W
    r[0] = loc
    return r


def setblock(r, idx, vals):
    for k, c in enumerate(idx):
        r[c] = vals[k]


# Scenario A — route-011 style: Right row (Left ditto), Left row (Right ditto),
# combined row. Different base postmiles -> filled from the nearest concrete.
rowR = blank_row("000.000R"); setblock(rowR, L, DITTO8);  setblock(rowR, R, RIGHTVALS)
rowL = blank_row("000.199L"); setblock(rowL, L, LEFTVALS); setblock(rowL, R, DITTO8)
rowC = blank_row("000.745");  setblock(rowC, L, LEFTVALS); setblock(rowC, R, RIGHTVALS)
filled, ditto = hlc.fill_paired_roadbed([rowR, rowL, rowC])

check("A: Right row's Left block filled from paired Left",
      [filled[0][c] for c in L] == LEFTVALS)
check("A: Left row's Right block filled from paired Right",
      [filled[1][c] for c in R] == RIGHTVALS)
check("A: combined row untouched (no ditto)",
      [filled[2][c] for c in L] == LEFTVALS and [filled[2][c] for c in R] == RIGHTVALS)
check("A: ditto_cells = row0 Left (8) + row1 Right (8)",
      ditto == {(0, c) for c in L} | {(1, c) for c in R})
check("A: concrete cells NOT marked", (2, L[0]) not in ditto and (0, R[0]) not in ditto)

# Scenario B — same base postmile pairing (R081.505 R/L/combined). The Right
# row's Left ditto must take the SAME-postmile Left value, not a nearer stale one.
stale = blank_row("081.017"); setblock(stale, L, ["X"] * 8); setblock(stale, R, ["Y"] * 8)
bR = blank_row("R081.505R"); setblock(bR, L, DITTO8);  setblock(bR, R, RIGHTVALS)
bL = blank_row("R081.505L"); setblock(bL, L, LEFTVALS); setblock(bL, R, DITTO8)
filled2, _ = hlc.fill_paired_roadbed([stale, bR, bL])
check("B: same-base Left value wins over the nearer stale row",
      [filled2[1][c] for c in L] == LEFTVALS)

# --- display_fills (the comparison-data-sheet wrapper) --------------------
# Per-route grouping + the leading-Route offset. Build two routes; the dittoed
# cells must resolve from the paired roadbed WITHIN their own route.
def hl_row(loc, leftvals, rightvals):
    r = blank_row(loc); setblock(r, L, leftvals); setblock(r, R, rightvals)
    return r

# has_route=True: each row is [Route] + HEADER-aligned record.
r1R = ["1"] + hl_row("000.000R", DITTO8, RIGHTVALS)
r1L = ["1"] + hl_row("000.199L", LEFTVALS, DITTO8)
r2C = ["2"] + hl_row("000.000", ["Q"] * 8, ["W"] * 8)        # different route, no ditto
rows = [r1R, r1L, r2C]
fills = hlc.display_fills(rows, has_route=True)
# row 0 (route 1, Right row): its 8 Left cols are ditto -> resolved to LEFTVALS,
# at col_in_row = LEFT_BLOCK_IDX + 1 (the leading Route shifts every column).
exp_cols = {c + 1: LEFTVALS[k] for k, c in enumerate(L)}
check("display_fills: route-1 Right row Left block resolved (offset +1)",
      fills.get(0) == exp_cols)
check("display_fills: route-1 Left row Right block resolved",
      fills.get(1) == {c + 1: RIGHTVALS[k] for k, c in enumerate(R)})
check("display_fills: route-2 (no ditto) absent from fills", 2 not in fills)
check("display_fills: only dittoed rows present", set(fills) == {0, 1})

print("\nRESULT:", "ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
