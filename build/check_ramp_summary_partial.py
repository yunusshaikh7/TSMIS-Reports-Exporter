"""Golden check for RAMP-SUMMARY-FAILURES-OK + RAMP-SUMMARY-SHORT-PDF-BLANK
(scripts/consolidate_ramp_summary.py).

Before: parse failures were logged but the consolidator still returned
status="ok" and ALWAYS wrote the workbook — so an all-fail run (or a folder of
one-page/truncated PDFs, which parse without error but carry no ramp figures)
would overwrite a good prior consolidation with a blank/partial one.

After:
  * record_has_data() distinguishes a real parse (page-2 figures present) from a
    route-only record (one-page / truncated PDF).
  * consolidate() drops blank records, and when NOTHING usable parsed returns
    status="error" WITHOUT writing — the existing file is left untouched.
  * a partial run leads its summary with a loud INCOMPLETE warning.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_ramp_summary_partial.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidate_ramp_summary as rs
from events import Events


def test_record_has_data():
    assert rs.record_has_data({"source_file": "x.pdf", "route": "1",
                               "total_ramps": 5})
    # route-only (one-page PDF) → no data
    assert not rs.record_has_data({"source_file": "x.pdf", "route": "1"})
    # only audit/internal fields populated → still no real data
    assert not rs.record_has_data({"source_file": "x.pdf", "route": "1",
                                   "_chk_hwy": 0})


def _consolidate(tmp, out, fake_parse):
    """Run consolidate() against `tmp`, pointing its derived input/output dirs
    there (consolidate() takes only `day` and resolves the paths itself)."""
    saved = (rs.parse_pdf, rs.input_dir_for, rs.out_path_for)
    rs.parse_pdf = fake_parse
    rs.input_dir_for = lambda day: tmp
    rs.out_path_for = lambda day: out
    try:
        return rs.consolidate(events=Events(),
                              confirm_overwrite=lambda p: True, day="x")
    finally:
        rs.parse_pdf, rs.input_dir_for, rs.out_path_for = saved


def _run(tmp, fake_parse):
    for n in ("a_route_1.pdf", "b_route_2.pdf", "c_route_3.pdf"):
        (tmp / n).write_bytes(b"%PDF-1.4")          # glob target; content unused
    out = tmp / "out.xlsx"
    return out, _consolidate(tmp, out, fake_parse)


def test_partial_writes_only_good():
    tmp = Path(tempfile.mkdtemp())

    def fake(path):
        name = Path(path).name
        if name.startswith("a"):                    # good
            return {"source_file": name, "route": "1", "total_ramps": 7}
        if name.startswith("b"):                    # one-page / truncated → blank
            return {"source_file": name, "route": "2"}
        raise ValueError("corrupt")                 # c → parse failure

    out, res = _run(tmp, fake)
    assert res.status == "ok", res.status
    assert res.summary_lines[0].startswith("⚠ INCOMPLETE"), res.summary_lines[0]
    assert out.exists(), "the good route should still be written"


def test_all_blank_or_fail_does_not_overwrite():
    tmp = Path(tempfile.mkdtemp())
    out_existing = tmp / "out.xlsx"

    def fake(path):
        name = Path(path).name
        if name.startswith("c"):
            raise ValueError("corrupt")
        return {"source_file": name, "route": "9"}   # route-only / blank

    # Pre-existing good output must survive an all-blank/all-fail run.
    for n in ("a_route_1.pdf", "b_route_2.pdf", "c_route_3.pdf"):
        (tmp / n).write_bytes(b"%PDF-1.4")
    out_existing.write_bytes(b"PRIOR-GOOD-FILE")
    res = _consolidate(tmp, out_existing, fake)
    assert res.status == "error", ("all-blank/all-fail must be an error", res.status)
    assert out_existing.read_bytes() == b"PRIOR-GOOD-FILE", \
        "all-blank/all-fail must NOT overwrite the existing good file"


def main():
    test_record_has_data()
    test_partial_writes_only_good()
    test_all_blank_or_fail_does_not_overwrite()
    print("OK  RAMP-SUMMARY-FAILURES-OK + SHORT-PDF-BLANK: blank/one-page PDFs "
          "are dropped (not written as blank rows), partials are flagged "
          "INCOMPLETE, and an all-blank/all-fail run errors WITHOUT overwriting "
          "a good workbook.")


if __name__ == "__main__":
    main()
