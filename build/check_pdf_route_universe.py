"""CMP-AUD-050: PDF conversion enforces a route universe.

The shared convert-then-combine driver (`pdf_table_lib.run_pdf_conversion`,
all five table-PDF consolidators) and the separate Ramp Summary collection
loop must both refuse what they previously absorbed by file order:

  * two PDFs converting to the SAME route — the driver used to warn and let
    the later payload overwrite the earlier workbook while counting both;
    Ramp Summary appended both records and the vs-TSN aggregate loader
    summed them (a 5-count and a 7-count duplicate once became statewide
    count 12);
  * a populated record/conversion with NO usable route identity — Ramp
    Summary used to publish a complete workbook containing a blank Route.

Now: a duplicate route is an error naming BOTH source PDFs with nothing
published (last-good preserved); a blank route refuses in the driver and is
a named FAILED input in Ramp Summary (loud INCOMPLETE banner, PARTIAL
completion). Distinct routes still publish COMPLETE.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import consolidate_ramp_summary as rs  # noqa: E402
import outcome  # noqa: E402
from events import Events  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from pdf_table_lib import run_pdf_conversion  # noqa: E402

failures = []


def check(label, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + label
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def write_probe_workbook(rows, out_file):
    wb = Workbook()
    ws = wb.active
    ws.title = "Probe"
    ws.append(["Location", "Value"])
    for r in rows:
        ws.append(list(r))
    wb.save(out_file)
    wb.close()


def run_driver(source, out, conv, routes_by_pdf):
    def convert_one(p, _prefix, _events, _ctx):
        return "ok", routes_by_pdf[p.name], [["001.000", 1]]

    return run_pdf_conversion(
        in_dir=source, out=out, conv=conv, deps_ok=True,
        events=Events(), confirm_overwrite=lambda _p: True,
        report_name="Probe", banner_title="Probe",
        export_hint="export", unreadable_hint="unreadable",
        converted_prefix="probe",
        convert_one=convert_one,
        write_one=write_probe_workbook,
        finalize=lambda *_a: None,
        consolidate_kwargs={"sheet_name": "Probe", "report_name": "Probe",
                            "title": "Probe"})


print("shared driver (run_pdf_conversion):")
tmp = Path(tempfile.mkdtemp(prefix="tsmis_route_universe_"))
source = tmp / "inputs"
source.mkdir()
for name in ("a.pdf", "b.pdf"):
    (source / name).write_bytes(b"%PDF-1.4\n%%EOF")

out = tmp / "combined.xlsx"
out.write_bytes(b"LAST-GOOD")
res = run_driver(source, out, tmp / "conv-dup",
                 {"a.pdf": "001", "b.pdf": "001"})
check("duplicate route refuses and names BOTH source PDFs",
      res.status == "error" and "a.pdf" in res.message
      and "b.pdf" in res.message and "route 001" in res.message, res.message)
check("...the combined workbook was not written (last-good preserved)",
      out.read_bytes() == b"LAST-GOOD")

res = run_driver(source, out, tmp / "conv-blank",
                 {"a.pdf": "001", "b.pdf": "  "})
check("a blank route identity refuses and names the PDF",
      res.status == "error" and "b.pdf" in res.message
      and "route identity" in res.message, res.message)
check("...last-good still preserved", out.read_bytes() == b"LAST-GOOD")

res = run_driver(source, out, tmp / "conv-ok",
                 {"a.pdf": "001", "b.pdf": "002"})
check("distinct routes still publish", res.status == "ok", res.message)


print("Ramp Summary collection loop:")


def rs_run(records_by_pdf, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name in records_by_pdf:
        (folder / name).write_bytes(b"%PDF-1.4\n%%EOF")

    def fake_parse(path):
        return dict(records_by_pdf[Path(path).name])

    out_path = folder / "consolidated.xlsx"
    with patch.object(rs, "parse_pdf", fake_parse), \
            patch.object(rs, "_DEPS_OK", True):
        return rs.consolidate(events=Events(), confirm_overwrite=lambda _p: True,
                              input_dir=folder, out_path=out_path), out_path


res, out_path = rs_run(
    {"r1.pdf": {"route": "001", "source_file": "r1.pdf", "total_ramps": 5},
     "r2.pdf": {"route": "001", "source_file": "r2.pdf", "total_ramps": 7}},
    tmp / "rs-dup")
check("RS: two PDFs claiming one route refuse and name both",
      res.status == "error" and "r1.pdf" in res.message
      and "r2.pdf" in res.message and "route 001" in res.message, res.message)
check("...nothing was written", not out_path.exists())

res, out_path = rs_run(
    {"r1.pdf": {"route": "001", "source_file": "r1.pdf", "total_ramps": 5},
     "r2.pdf": {"route": None, "source_file": "r2.pdf", "total_ramps": 7}},
    tmp / "rs-blank")
check("RS: a populated record with no route is a named FAILED input "
      "(PARTIAL, loud banner)",
      res.status == "ok" and res.completion == outcome.PARTIAL
      and res.failed_inputs == 1
      and any("INCOMPLETE" in ln for ln in res.summary_lines), str(res.summary_lines))
check("...the workbook published without the blank-route row",
      out_path.exists())

res, out_path = rs_run(
    {"r1.pdf": {"route": "001", "source_file": "r1.pdf", "total_ramps": 5},
     "r2.pdf": {"route": "002", "source_file": "r2.pdf", "total_ramps": 7}},
    tmp / "rs-ok")
check("RS: distinct routes publish COMPLETE",
      res.status == "ok" and res.completion == outcome.COMPLETE, res.message)

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

if failures:
    print(f"\nFAILED: {len(failures)}")
    sys.exit(1)
print("\nPDF route-universe enforcement (CMP-AUD-050): PASS")
