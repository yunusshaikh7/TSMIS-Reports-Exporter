"""Golden check for the Intersection consolidators (v0.17.0).

Covers consolidate_intersection_detail (a thin wrapper over the shared
consolidate_xlsx core): the config that can't drift (subdir / sheet name /
output filename) and an end-to-end 2-route consolidation read back with openpyxl
(leading Route column, header locked, rows combined). The free-text Description
column's formula-injection guard lives in the shared consolidate_xlsx core and is
locked separately by check_compare_injection.

Also covers consolidate_intersection_summary (v0.17.0): the block-walk category
summer — a 2-route consolidation read back, verifying the per-route sheet columns
sum correctly and the Combined statewide total.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_consolidate_intersection.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidate_intersection_detail as cid
import consolidate_intersection_summary as cis
import summary_layout as sl
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# A trimmed Intersection Detail header (real sheet has 36 cols; the wrapper is
# header-agnostic — it locks whatever the first file has and prepends Route).
_HDR = ["P", "Post Mile", "Location", "Date of Record", "Description"]


def _write_route(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = cid.SHEET_NAME
    ws.append(_HDR)
    for r in rows:
        ws.append(r)
    wb.save(path)
    wb.close()


_IS_KEY = {c.slug: c.key for sec in sl.INTERSECTION_SUMMARY_SPEC.sections for c in sec.cats}


def _write_is_route(path, route, total, blocks):
    """A synthetic per-route Intersection Summary sheet (block-count layout)."""
    wb = Workbook()
    ws = wb.active
    ws.title = cis.SHEET_NAME
    ws.append(["TSAR - Intersection Summary"])
    ws.append([f"Route: {route}"])
    ws.append([f"Total Intersections = {total}"])
    ws.append([])
    for hdr, rows in blocks:
        ws.append([hdr])
        ws.append(["NUMBER", "CODE"])
        for cnt, code in rows:
            ws.append([cnt, code])
        ws.append([])
    wb.save(path)
    wb.close()


def test_summary():
    print("Intersection Summary consolidator (block-walk category summer):")
    check("subdir intersection_summary", cis.SUBDIR == "intersection_summary")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_int_sum_"))
    in_dir = tmp / "in"
    in_dir.mkdir()
    _write_is_route(in_dir / "intersection_summary_route_001.xlsx", "001", 5,
                    [("HIGHWAY GROUP", [(3, "U-UNDIVIDED"), (2, "D-DIVIDED")]),
                     ("CONTROL TYPES", [(4, "A-NO CONTROL"), (1, "S-SIGNALIZED")])])
    _write_is_route(in_dir / "intersection_summary_route_002.xlsx", "002", 5,
                    [("HIGHWAY GROUP", [(5, "U-UNDIVIDED"), (0, "D-DIVIDED")]),
                     ("CONTROL TYPES", [(5, "A-NO CONTROL"), (0, "S-SIGNALIZED")])])
    out = tmp / "out.xlsx"
    res = cis.consolidate(events=Events(), confirm_overwrite=lambda _p: True,
                          input_dir=in_dir, out_path=out)
    check("consolidate ok", res.status == "ok")
    wb = load_workbook(out, read_only=True, data_only=True)
    ws = wb[cis.SHEET_NAME]
    rows = list(ws.iter_rows(values_only=True))
    header = [("" if c is None else str(c)) for c in rows[0]]
    data = rows[1:]
    wb.close()
    check("Route + Total lead the per-route sheet",
          header[0] == "Route" and header[1] == "Total Intersections")
    check("both routes present", {str(r[0]) for r in data} == {"001", "002"})
    u_col = header.index(_IS_KEY["is_highway_group_u"])
    s_col = header.index(_IS_KEY["is_control_types_s"])
    u_sum = sum(r[u_col] for r in data)
    s_sum = sum(r[s_col] for r in data)
    check("U-UNDIVIDED column sums across routes (3+5=8)", u_sum == 8)
    check("S-SIGNALIZED column sums across routes (1+0=1)", s_sum == 1)
    cmb = load_workbook(out, data_only=True)[cis.COMBINED_SHEET]
    check("Combined statewide Total = 10", cmb["B2"].value == 10)


def main():
    print("config (no drift):")
    check("subdir intersection_detail", cid.SUBDIR == "intersection_detail")
    check("sheet name 'Intersection Detail'", cid.SHEET_NAME == "Intersection Detail")
    check("output filename", cid.FILENAME == "tsar_intersection_detail_consolidated.xlsx")

    print("end-to-end 2-route consolidation:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_int_det_"))
    in_dir = tmp / "in"
    in_dir.mkdir()
    _write_route(in_dir / "intersection_detail_route_001.xlsx",
                 [["R", "0.204", "12 ORA 001", "21-12-31", "JCT 5"],
                  ["", "4.901", "12 ORA 001", "21-12-31", "JCT FOO"]])
    _write_route(in_dir / "intersection_detail_route_002.xlsx",
                 [["R", "1.000", "12 ORA 002", "21-12-31", "BAR ST"]])
    out = tmp / "out.xlsx"
    res = cid.consolidate(events=Events(), confirm_overwrite=lambda _p: True,
                          input_dir=in_dir, out_path=out)
    check("consolidate ok", res.status == "ok")

    wb = load_workbook(out, read_only=True, data_only=True)
    ws = wb[cid.SHEET_NAME]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = [("" if c is None else str(c)) for c in rows[0]]
    data = rows[1:]
    check("leading Route column added", header[0] == "Route")
    check("original header preserved after Route", header[1:6] == _HDR)
    check("all 3 data rows combined", len(data) == 3)
    routes = {str(r[0]) for r in data}
    check("both routes present (001, 002)", routes == {"001", "002"})

    test_summary()

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL CONSOLIDATE-INTERSECTION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
