"""Golden checks for the audit-round hardening (compare_core.py + compare_env.py).

Locks the fixes found in the ruthless multi-agent audit (all latent on real data
but real invariant/robustness gaps):
  P1  the data-sheet HELPER-KEY cell and the Routes ROUTE-ID cell are guarded —
      a "="-leading key/route no longer becomes a live formula (which broke the
      Comparison MATCH lookups AND split the two flavors). [completes injection fix]
  P2  the Summary per-field COUNTIF keys on the SPACED " ≠ " marker, like every
      other diff detector (Diffs/CF/Spot Check/Python mirror).
  P3  Ramp Summary route keys are zero-pad-normalized (PDF title "1" == filename
      "001"); internal unnamed header columns get an identifiable placeholder.
  P4  normalize_value canonicalizes datetime.time too.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_audit.py
"""
import os
import sys
import tempfile
from datetime import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_env as env
from compare_core import CompareSchema, normalize_value, run_compare
from openpyxl import Workbook, load_workbook


def _col(ws, name):
    for c in next(ws.iter_rows(max_row=1)):
        if c.value == name:
            return c.column
    raise AssertionError(f"{name!r} not in {ws.title}")


def test_p1_helper_key_and_route_id_guarded():
    sc = CompareSchema(report_name="K", header=["Loc", "V"], side_a="A", side_b="B",
                       id_noun="row", id_noun_plural="rows")
    out = os.path.join(tempfile.gettempdir(), "_audit_hk.xlsx")
    # per-route: a "="-leading KEY. The data sheet "Key (helper)" cell ("=K1|1")
    # must be TEXT, not a live formula (else its MATCH lookups break + flavors split).
    run_compare(sc, [["=K1", "x"], ["b", "y"]], [["=K1", "x"], ["b", "y"]],
                False, out, mode="formulas")
    wb = load_workbook(out, data_only=False)
    ws = wb["A"]
    hk_col = _col(ws, "Key (helper)")
    hk = ws.cell(row=2, column=hk_col)
    assert hk.data_type == "s" and hk.value == "=K1|1", (hk.data_type, hk.value)
    wb.close(); os.remove(out)

    # consolidated: a "="-leading ROUTE id on the Routes sheet must be TEXT.
    scr = CompareSchema(report_name="K", header=["Loc", "V"], side_a="A", side_b="B",
                        id_noun="row", id_noun_plural="rows")
    run_compare(scr, [["=R1", "1", "x"]], [["=R1", "1", "x"]], True, out,
                mode="formulas")
    wb = load_workbook(out, data_only=False)
    rid = wb["Routes"].cell(row=2, column=1)
    assert rid.data_type == "s" and rid.value == "=R1", (rid.data_type, rid.value)
    wb.close(); os.remove(out)


def test_p2_countif_spaced_marker():
    sc = CompareSchema(report_name="K", header=["Loc", "V"], side_a="A", side_b="B",
                       id_noun="row", id_noun_plural="rows")
    out = os.path.join(tempfile.gettempdir(), "_audit_cf.xlsx")
    run_compare(sc, [["1", "a"]], [["1", "b"]], False, out, mode="formulas")
    wb = load_workbook(out, data_only=False)
    cfs = [str(c.value) for row in wb["Summary"].iter_rows() for c in row
           if c.data_type == "f" and "COUNTIF" in str(c.value) and "Comparison!" in str(c.value)
           and "≠" in str(c.value)]
    wb.close(); os.remove(out)
    assert cfs, "no per-field COUNTIF found"
    for f in cfs:
        assert '"* ≠ *"' in f, ("per-field COUNTIF must use the spaced marker", f)


def test_p3_route_key_normalize():
    assert env._norm_route_key("1") == "001"
    assert env._norm_route_key("001") == "001"
    assert env._norm_route_key("101U") == "101U"
    assert env._norm_route_key("5s") == "005S"
    assert env._norm_route_key("1") == env._norm_route_key("001")   # the bug case


def test_p3_none_header_placeholder():
    d = Path(tempfile.mkdtemp()) / "highway_sequence"
    d.mkdir(parents=True)
    wb = Workbook(); ws = wb.active; ws.title = "Highway Locations"
    ws.append(["County", "City", None, "PM", None, "Description"])  # internal Nones
    ws.append(["ORA", None, "R", "000.1", None, "JCT"])
    wb.save(d / "highway_sequence_route_001.xlsx")
    from events import Events
    rows, header, skipped = env._load_xlsx_side(
        d.parent, "X", "highway_sequence", "Highway Locations", "Highway Sequence",
        Events())
    assert None not in header, ("internal None must be relabeled", header)
    assert header[2] == "(col C)" and header[4] == "(col E)", header
    assert header[0] == "County" and header[3] == "PM", header


def test_p4_time_normalize():
    assert normalize_value(time(8, 30)) == "08:30:00"
    assert normalize_value(time(8, 30, 5, 123456)) == "08:30:05.123456"


def test_p3_side_label_cap():
    # Same run-folder name in different parents -> date + (A)/(B) -> >23 chars
    # -> must be capped so "Only in <label>" fits Excel's 31-char sheet limit.
    base = Path(tempfile.mkdtemp())
    a = base / "x1" / "2026-06-15 ssor-prod"; a.mkdir(parents=True)
    b = base / "x2" / "2026-06-15 ssor-prod"; b.mkdir(parents=True)
    la, lb = env._side_labels(a, b)
    assert la != lb, (la, lb)
    assert len("Only in " + la) <= 31 and len("Only in " + lb) <= 31, (la, lb)


def main():
    test_p1_helper_key_and_route_id_guarded()
    test_p2_countif_spaced_marker()
    test_p3_route_key_normalize()
    test_p3_none_header_placeholder()
    test_p4_time_normalize()
    test_p3_side_label_cap()
    print("OK  audit hardening: helper-key + route-id guarded; per-field COUNTIF "
          "uses the spaced marker; route keys normalized; unnamed columns "
          "labeled; time canonicalized; side labels capped to the 31-char limit.")


if __name__ == "__main__":
    main()
