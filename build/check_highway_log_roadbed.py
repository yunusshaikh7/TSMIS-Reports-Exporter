"""Golden check for the roadbed-aware comparison key (highway_log_columns +
compare_core.keys_for).

Locks the validated unification of the two sources' roadbed encodings: TSMIS
(PDF + Excel) suffix a divided segment's Location with 'R'/'L'; TSN omits the
suffix and dittos the non-subject 8-col block instead. The key derives the
roadbed from the suffix when present, else from which block is dittoed, so the
SAME physical roadbed row keys identically across sources (see
docs/highway_log/comparison-study.md §7b).

Guards:
  * roadbed_tag: Left-block-dittoed -> 'R' (right roadbed), Right -> 'L', neither
    or BOTH -> '' (safe fallback), with the leading-Route offset.
  * roadbed_canonical_location: an explicit R/L suffix is authoritative; a
    suffix-less Location gets the block tag appended; the equation 'E' marker and
    the leading alignment prefix are PRESERVED (so 'R000.000' never collapses into
    '000.000', and 'E' variants stay distinct); None/blank handled; lowercase r/l
    is NOT a roadbed suffix.
  * keys_for: key_normalizer=None is byte-identical to the raw-Location key (the
    regression-locked default); the normalizer changes ONLY suffix-less dittoed
    rows and STRICTLY REFINES the keyspace (can split, never merge).

Runnable with the plain build venv python (no login, no third-party libs):
  build\\.venv\\Scripts\\python.exe build\\check_highway_log_roadbed.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import highway_log_columns as hlc      # noqa: E402
import compare_core as cc              # noqa: E402

FAILS = []


def check(name, cond):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAILS.append(name)


W = len(hlc.HEADER)
L = hlc.LEFT_BLOCK_IDX
R = hlc.RIGHT_BLOCK_IDX


def row(loc, left=None, right=None, off=0):
    """A HEADER-aligned row (optionally with `off` leading Route cells) with the
    Location set and each 8-col block filled with `left`/`right` (a single token
    broadcast across the block, or None = blank)."""
    r = [""] * (W + off)
    if off:
        r[0] = "1"
    r[off] = loc
    for c in L:
        r[off + c] = left if left is not None else ""
    for c in R:
        r[off + c] = right if right is not None else ""
    return r


# --- roadbed_tag ----------------------------------------------------------
check("tag: Left block dittoed -> 'R'", hlc.roadbed_tag(row("x", left="++", right="C")) == "R")
check("tag: Right block dittoed -> 'L'", hlc.roadbed_tag(row("x", left="C", right="+++")) == "L")
check("tag: neither dittoed -> ''", hlc.roadbed_tag(row("x", left="C", right="C")) == "")
check("tag: BOTH dittoed -> '' (safe fallback)", hlc.roadbed_tag(row("x", left="+", right="++")) == "")
check("tag: blank blocks -> ''", hlc.roadbed_tag(row("x")) == "")
check("tag: honors the leading-Route offset (off=1)",
      hlc.roadbed_tag(row("x", left="++", right="C", off=1), off=1) == "R")

# --- roadbed_canonical_location ------------------------------------------
# Explicit suffix is authoritative (even if a block is also dittoed).
check("canon: 'R021.466R' suffix kept verbatim",
      hlc.roadbed_canonical_location(row("R021.466R", left="++", right="C")) == "R021.466R")
check("canon: '008.392L' suffix kept verbatim",
      hlc.roadbed_canonical_location(row("008.392L")) == "008.392L")
# Suffix-less + dittoed block -> base + derived tag (the TSN unification).
check("canon: suffix-less Left-dittoed -> base+'R'",
      hlc.roadbed_canonical_location(row("R021.466", left="++", right="C")) == "R021.466R")
check("canon: suffix-less Right-dittoed -> base+'L'",
      hlc.roadbed_canonical_location(row("R021.466", left="C", right="++")) == "R021.466L")
# Combined row (no suffix, no ditto) -> unchanged.
check("canon: combined row unchanged",
      hlc.roadbed_canonical_location(row("021.466", left="C", right="C")) == "021.466")
# Equation 'E' marker preserved; tag appended AFTER it when dittoed.
check("canon: 'E' marker preserved on a combined row",
      hlc.roadbed_canonical_location(row("006.526E", left="C", right="C")) == "006.526E")
check("canon: 'E' marker kept, tag appended after ('…ER')",
      hlc.roadbed_canonical_location(row("006.526E", left="++", right="C")) == "006.526ER")
# Leading alignment prefix preserved (route-start must not collapse to a bridge).
check("canon: leading 'R' prefix preserved (no false merge)",
      hlc.roadbed_canonical_location(row("R000.000", left="C", right="C")) == "R000.000")
check("canon: 'R000.000' != '000.000' (distinct tokens)",
      hlc.roadbed_canonical_location(row("R000.000", left="C", right="C"))
      != hlc.roadbed_canonical_location(row("000.000", left="C", right="C")))
# Robustness: None / blank / lowercase.
check("canon: None Location -> '' (no crash)", hlc.roadbed_canonical_location(row(None)) == "")
check("canon: blank Location -> ''", hlc.roadbed_canonical_location(row("   ")) == "")
check("canon: lowercase 'r' is NOT a roadbed suffix",
      hlc.roadbed_canonical_location(row("021.466r", left="C", right="C")) == "021.466r")
check("canon: honors off=1 (Location after the Route cell)",
      hlc.roadbed_canonical_location(row("R021.466", left="++", right="C", off=1), off=1) == "R021.466R")

# --- keys_for opt-in + refinement ----------------------------------------
# A divided segment: PDF has R-row (Left ditto) + L-row (Right ditto) with
# suffixes; TSN has the SAME two rows suffix-less (the encoding gap).
pdf_rows = [row("R021.466R", left="++", right="C"),
            row("R021.466L", left="C", right="++")]
tsn_rows = [row("R021.466", left="++", right="C"),
            row("R021.466", left="C", right="++")]

# key_normalizer=None == raw Location (byte-identical default behavior).
raw_pdf = cc.keys_for(pdf_rows, has_route=False)
raw_tsn = cc.keys_for(tsn_rows, has_route=False)
check("keys_for(None): raw PDF keys are the literal Locations",
      [k[1] for k in raw_pdf] == ["R021.466R", "R021.466L"])
check("keys_for(None): raw TSN rows collide as one key (the OLD split bug)",
      [k[1] for k in raw_tsn] == ["R021.466", "R021.466"]
      and [k[2] for k in raw_tsn] == [1, 2])

# With the roadbed normalizer, both sides key identically -> they PAIR.
kn = hlc.roadbed_canonical_location
norm_pdf = cc.keys_for(pdf_rows, has_route=False, key_normalizer=kn)
norm_tsn = cc.keys_for(tsn_rows, has_route=False, key_normalizer=kn)
check("keys_for(roadbed): PDF keys unchanged (already suffixed)",
      [k[1] for k in norm_pdf] == ["R021.466R", "R021.466L"])
check("keys_for(roadbed): TSN keys now split to R/L and MATCH the PDF",
      [k[1] for k in norm_tsn] == ["R021.466R", "R021.466L"])
check("keys_for(roadbed): every TSN roadbed row now pairs a PDF key",
      {k[:2] for k in norm_tsn} == {k[:2] for k in norm_pdf})
# Strictly refines: the normalizer never reduces the distinct-key count.
check("keys_for(roadbed): strictly refines (key count never drops)",
      len({k[1] for k in norm_tsn}) >= len({k[1] for k in raw_tsn}))

print("\nRESULT:", "ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
