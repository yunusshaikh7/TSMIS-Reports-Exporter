"""Golden checks for CMP-AUD-034: the CONSOLIDATED-TSMIS loaders bind their header
EXACTLY (scripts/compare_tsn_common.exact_consolidated_header_ok + the four
`_load_tsmis` gates in compare_{ramp_detail,highway_sequence,highway_detail,
intersection_detail}_tsn.py).

Those loaders read every field BY POSITION (the site's export labels are
column-shifted against their values). The previous gates established almost no
semantics — Highway Sequence and Highway Detail required only a leading 'Route';
Ramp Detail wanted 'PM' in the first five cells plus width >= 11; Intersection
Detail accepted any 36-cell header ending in 'Xing Line Lgth'. A block-shifted,
junk-relabelled, or wrong-report header therefore passed and was projected as the
intended schema (false differences / false one-sided rows / a false match). This
check locks the exact bind: every current export header is accepted (Excel- AND
PDF-consolidated share the identical header), and any relabel / block-shift /
insertion / deletion is refused — while proving the OLD gate accepted that junk.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_consolidated_layout.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_highway_detail_tsn as hd
import compare_highway_sequence_tsn as hsl
import compare_intersection_detail_tsn as idt
import compare_ramp_detail_tsn as rd
import compare_tsn_common as ctc
from openpyxl import Workbook

FAMILIES = [
    ("Ramp Detail", rd, rd.TSMIS_SHEET),
    ("Highway Sequence", hsl, hsl.TSMIS_SHEET),
    ("Highway Detail", hd, hd.TSMIS_SHEET),
    ("Intersection Detail", idt, idt.TSMIS_SHEET),
]


def _normed(h):
    """How load_consolidated_rows presents the header to header_ok."""
    return [("" if c is None else str(c).strip()) for c in h]


def test_predicate_accepts_exact_rejects_drift():
    for name, mod, _sheet in FAMILIES:
        H = list(mod._TSMIS_HEADER)
        pred = ctc.exact_consolidated_header_ok(H)
        assert pred(H), (name, "exact header must be accepted")
        assert pred(_normed(H)), (name, "loader-normalized header must be accepted")
        # a mid-column RELABEL (same width/first/last) — the exact class the old
        # gates let through
        junk = list(H)
        junk[len(H) // 2] = "JUNK"
        assert not pred(junk), (name, "a relabelled middle column must be refused")
        # a BLOCK SHIFT (rotate one): same cells, wrong positions
        assert not pred(H[1:] + H[:1]), (name, "a block-shifted header must be refused")
        # INSERTION / DELETION
        assert not pred(H + ["X"]), (name, "an inserted column must be refused")
        assert not pred(H[:-1]), (name, "a deleted column must be refused")
        # a truly empty / route-only header
        assert not pred(["Route"]), (name, "a route-only header must be refused")


def test_old_gates_accepted_the_junk():
    """Red proof: the PREVIOUS per-family gates accepted a junk-relabelled header
    that the exact bind now refuses."""
    # Intersection Detail: old gate = len==36 and header[-1]=='Xing Line Lgth'
    id_junk = ["Route"] + ["JUNK"] * 34 + ["Xing Line Lgth"]
    assert len(id_junk) == 36 and id_junk[-1] == "Xing Line Lgth", "old ID gate shape"
    assert not idt._header_ok(id_junk), "the exact ID bind must refuse the old-gate junk"
    # Ramp Detail: old gate = 'PM' in header[:5] and len(header) >= 11
    rd_junk = ["Route", "JUNK", "", "PM", "JUNK", "", "JUNK", "JUNK", "", "JUNK",
               "JUNK", "JUNK"]
    assert "PM" in rd_junk[:5] and len(rd_junk) >= 11, "old RD gate shape"
    assert not ctc.exact_consolidated_header_ok(rd._TSMIS_HEADER)(rd_junk), \
        "the exact RD bind must refuse the old-gate junk"


def test_load_tsmis_refuses_a_shifted_workbook_end_to_end():
    """Each `_load_tsmis` refuses a real workbook whose header is block-shifted —
    proving the exact bind is wired into the loader, not just the predicate. The
    shifted header is rejected before any row is read, so the dummy row is inert."""
    for name, mod, sheet in FAMILIES:
        H = list(mod._TSMIS_HEADER)
        shifted = H[1:] + H[:1]                 # 'Route' no longer at position 0
        wb = Workbook()
        ws = wb.active
        ws.title = sheet
        ws.append(shifted)
        ws.append(["x"] * len(H))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / f"{name}.xlsx"
            wb.save(p)
            raised = False
            try:
                mod._load_tsmis(str(p))
            except ValueError:
                raised = True
            assert raised, (name, "a block-shifted consolidated workbook must be refused")


def main():
    test_predicate_accepts_exact_rejects_drift()
    test_old_gates_accepted_the_junk()
    test_load_tsmis_refuses_a_shifted_workbook_end_to_end()
    print("OK  consolidated-layout gate (CMP-AUD-034): all four _load_tsmis loaders "
          "bind their exact documented header — relabels, block shifts, insertions, "
          "and deletions are refused (the old width/last-label/PM gates accepted "
          "them); a shifted workbook is refused end-to-end.")


if __name__ == "__main__":
    main()
