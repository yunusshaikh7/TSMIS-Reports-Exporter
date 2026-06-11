"""Throwaway: post-final-pass functional check of both compare shapes."""
import sys
import tempfile
import time
from pathlib import Path

sys.path[:0] = [r"C:\Users\Yunus\Projects\TSMIS-Reports-Exporter\scripts",
                r"C:\Users\Yunus\Projects\TSMIS-Reports-Exporter"]
import compare_highway_log as cmp

DL = r"C:\Users\Yunus\Downloads"
tmp = Path(tempfile.mkdtemp())
r1 = cmp.compare(DL + r"\tsmis_highway_log_route 1.xlsx",
                 DL + r"\tsn_highway_log_route 1.xlsx", tmp / "r1.xlsx")
t0 = time.time()
r2 = cmp.compare(DL + r"\tsmis_highway_log_consolidated 1.xlsx",
                 DL + r"\tsn_highway_log_consolidated 1.xlsx", tmp / "c.xlsx")
print("route1:", r1.status, "| consolidated:", r2.status, f"({time.time()-t0:.0f}s)")
if r2.status != "ok":
    print("ERROR:", r2.message)
import zipfile
with zipfile.ZipFile(tmp / "c.xlsx") as z:
    names = z.namelist()
    wb_xml = z.read("xl/workbook.xml").decode()
print("sheets in consolidated:", sum(1 for n in names if n.startswith("xl/worksheets/sheet")),
      "| manual calc:", 'calcMode="manual"' in wb_xml)
import shutil
shutil.rmtree(tmp, ignore_errors=True)
print("FINAL CHECK OK" if r1.status == r2.status == "ok" else "FINAL CHECK FAILED")
