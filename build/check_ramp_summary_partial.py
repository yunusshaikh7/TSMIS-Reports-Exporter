"""Golden check for RAMP-SUMMARY-FAILURES-OK + RAMP-SUMMARY-SHORT-PDF-BLANK +
the CMP-AUD-019 audit-reconciliation contract (scripts/consolidate_ramp_summary.py).

Original scope: a folder of one-page/truncated PDFs (route-only records) must
not overwrite a good prior consolidation, and a partial run leads its summary
with a loud INCOMPLETE warning.

CMP-AUD-019 hardening:
  * record_has_data() now requires the Total AND coverage of every printed
    section — a TOTAL-ONLY record ({route, total_ramps}, every section blank) is
    no longer accepted as real data (it used to let two such sides compare as a
    phantom match).
  * reconcile_record() connects each written route's audit to the producer
    outcome: an UNEXPLAINED integrity gap (an exact block that doesn't sum to the
    route's own Total, a Ramp-Types block over the total, or an unknown/duplicate
    matcher row) makes the run PARTIAL; the EXPLAINED Ramp-Types shortfall (the
    TSN-only P/V dummy classes the Summary form doesn't tabulate) is surfaced as
    a typed note and stays COMPLETE.
  * schema_diagnostics() surfaces the ordered/case-sensitive matcher's blind
    spots (renamed = unknown, duplicated = duplicate).

Real-data census (126-route 7.9 ssor-prod pull): 0 unexplained, 0 unknown, 0
duplicate, and 9 routes / 22 ramps of P/V residual (P=2, V=20) — so the corpus
run stays COMPLETE with the residual note; none of these controls false-fire.

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


def _full_record(route="1", total=10, hwy=None, onoff=None, pop=None,
                 ramp=None, nolw=0, unknown=None, duplicate=None):
    """A fully-populated, reconciling Ramp Summary record: each section's first
    category carries the whole count so every block sums to `total`. Overrides
    let a test break one block or inject matcher diagnostics."""
    return {
        "source_file": f"r{route}.pdf", "route": route,
        "total_ramps": total, "ramp_points_no_linework": nolw,
        "hwy_right": total if hwy is None else hwy,
        "onoff_on": (total - nolw) if onoff is None else onoff,
        "pop_rural_inside": total if pop is None else pop,
        "ramp_A_frontage": (total - nolw) if ramp is None else ramp,
        "_unknown_rows": unknown or [],
        "_duplicate_rows": duplicate or [],
    }


def test_record_has_data():
    # A fully-populated route is data.
    assert rs.record_has_data(_full_record())
    # route-only (one-page PDF) → no data
    assert not rs.record_has_data({"source_file": "x.pdf", "route": "1"})
    # CMP-AUD-019 total-only CONTROL: Total present but every section blank is
    # NOT data (it used to pass on that one field and phantom-match).
    assert not rs.record_has_data({"source_file": "x.pdf", "route": "1",
                                   "total_ramps": 5})
    # a whole section blank → still not real data
    rec = _full_record()
    rec["hwy_right"] = None
    assert not rs.record_has_data(rec), "a fully-blank Highway section is not data"
    # only audit/internal fields populated → still no real data
    assert not rs.record_has_data({"source_file": "x.pdf", "route": "1",
                                   "_chk_hwy": 0})


def test_reconcile_ok():
    a = rs.reconcile_record(_full_record())
    assert a.status == rs.AUDIT_OK, a


def test_reconcile_pv_residual():
    # Ramp Types short by 2 (2 P/V ramps not printed), every exact block == Total.
    a = rs.reconcile_record(_full_record(total=10, ramp=8))
    assert a.status == rs.AUDIT_PV_RESIDUAL, a
    assert a.gap == 2, a
    assert rs.reconcile_problem(_full_record(total=10, ramp=8)) is None, \
        "an explained P/V residual is compareable, not a problem"


def test_reconcile_unexplained_exact_block():
    # Highway short by 1 with no explanation → unexplained.
    a = rs.reconcile_record(_full_record(total=10, hwy=9))
    assert a.status == rs.AUDIT_UNEXPLAINED, a
    assert "Highway" in a.detail, a.detail
    assert rs.reconcile_problem(_full_record(total=10, hwy=9))


def test_reconcile_unexplained_ramp_over():
    # Ramp Types OVER the total is impossible → unexplained (never a residual).
    a = rs.reconcile_record(_full_record(total=10, ramp=12))
    assert a.status == rs.AUDIT_UNEXPLAINED, a


def test_reconcile_no_total():
    rec = _full_record()
    rec["total_ramps"] = None
    a = rs.reconcile_record(rec)
    assert a.status == rs.AUDIT_UNEXPLAINED, a


def test_reconcile_renamed_and_duplicate_category():
    # A renamed/new category (matcher couldn't place it) → unexplained.
    a = rs.reconcile_record(_full_record(unknown=["R - RIGHT"]))
    assert a.status == rs.AUDIT_UNEXPLAINED and "unrecognized" in a.detail, a
    # A duplicate matched row (first-wins dropped the second) → unexplained.
    b = rs.reconcile_record(_full_record(duplicate=["R - Right"]))
    assert b.status == rs.AUDIT_UNEXPLAINED and "duplicate" in b.detail, b


def test_schema_diagnostics():
    schema = rs.HIGHWAY_GROUPS
    # rows: (num, label). idx0 matched R-Right (used); idx1 an unknown numbered
    # category; idx2 a duplicate of the matched R-Right; idx3 a non-category line.
    rows = [(5, "R - Right"), (3, "R - RIGHT"), (2, "R - Right"),
            (9, "NUMBER CODE")]
    unknown, dup = rs.schema_diagnostics(rows, {0}, schema)
    assert unknown == ["R - RIGHT"], unknown
    assert dup == ["R - Right"], dup


def _consolidate(tmp, out, fake_parse):
    saved = (rs.parse_pdf, rs.input_dir_for, rs.out_path_for)
    rs.parse_pdf = fake_parse
    rs.input_dir_for = lambda day: tmp
    rs.out_path_for = lambda day: out
    try:
        return rs.consolidate(events=Events(),
                              confirm_overwrite=lambda p: True, day="x")
    finally:
        rs.parse_pdf, rs.input_dir_for, rs.out_path_for = saved


def _run(tmp, fake_parse, names=("a_route_1.pdf", "b_route_2.pdf", "c_route_3.pdf")):
    for n in names:
        (tmp / n).write_bytes(b"%PDF-1.4")          # glob target; content unused
    out = tmp / "out.xlsx"
    return out, _consolidate(tmp, out, fake_parse)


def test_partial_writes_only_good():
    tmp = Path(tempfile.mkdtemp())

    def fake(path):
        name = Path(path).name
        if name.startswith("a"):                    # good, fully populated
            return _full_record(route="1")
        if name.startswith("b"):                    # one-page / truncated → blank
            return {"source_file": name, "route": "2"}
        raise ValueError("corrupt")                 # c → parse failure

    out, res = _run(tmp, fake)
    assert res.status == "ok", res.status
    assert res.summary_lines[0].startswith("⚠ INCOMPLETE"), res.summary_lines[0]
    assert res.completion == "partial", res.completion
    assert out.exists(), "the good route should still be written"


def test_pv_residual_stays_complete_with_note():
    """A route with an explained P/V Ramp-Types shortfall consolidates COMPLETE
    and surfaces the typed structural-omission note — never INCOMPLETE/PARTIAL."""
    tmp = Path(tempfile.mkdtemp())

    def fake(path):
        route = Path(path).stem.split("_")[-1]
        return _full_record(route=route, total=10, ramp=8)   # 2 P/V not printed

    out, res = _run(tmp, fake)
    assert res.status == "ok", res.status
    assert res.completion == "complete", res.completion
    assert not any(line.startswith("⚠") for line in res.summary_lines), \
        res.summary_lines
    note = [ln for ln in res.summary_lines if ln.startswith("Note:")]
    assert note and "P/V" in note[0], res.summary_lines
    # 3 routes × 2 ramps each = 6 residual ramps named in the note.
    assert "6 ramp" in note[0], note[0]


def test_unexplained_gap_makes_run_partial():
    """A written route whose own sections don't reconcile (no P/V explanation)
    escalates the run to PARTIAL and names the route (the red in-workbook Audit
    cell is no longer disconnected from the producer result)."""
    tmp = Path(tempfile.mkdtemp())

    def fake(path):
        route = Path(path).stem.split("_")[-1]
        if route == "2":
            return _full_record(route="2", total=10, hwy=9)   # unexplained
        return _full_record(route=route, total=10)

    out, res = _run(tmp, fake)
    assert res.status == "ok", res.status
    assert res.completion == "partial", res.completion
    assert any("don't reconcile" in ln for ln in res.summary_lines), res.summary_lines
    assert any("2" in ln for ln in res.summary_lines
               if "don't reconcile" in ln), res.summary_lines
    assert out.exists(), "the run still writes every parsed route"


def test_all_blank_or_fail_does_not_overwrite():
    tmp = Path(tempfile.mkdtemp())
    out_existing = tmp / "out.xlsx"

    def fake(path):
        name = Path(path).name
        if name.startswith("c"):
            raise ValueError("corrupt")
        return {"source_file": name, "route": "9"}   # route-only / blank

    for n in ("a_route_1.pdf", "b_route_2.pdf", "c_route_3.pdf"):
        (tmp / n).write_bytes(b"%PDF-1.4")
    out_existing.write_bytes(b"PRIOR-GOOD-FILE")
    res = _consolidate(tmp, out_existing, fake)
    assert res.status == "error", ("all-blank/all-fail must be an error", res.status)
    assert out_existing.read_bytes() == b"PRIOR-GOOD-FILE", \
        "all-blank/all-fail must NOT overwrite the existing good file"


def main():
    test_record_has_data()
    test_reconcile_ok()
    test_reconcile_pv_residual()
    test_reconcile_unexplained_exact_block()
    test_reconcile_unexplained_ramp_over()
    test_reconcile_no_total()
    test_reconcile_renamed_and_duplicate_category()
    test_schema_diagnostics()
    test_partial_writes_only_good()
    test_pv_residual_stays_complete_with_note()
    test_unexplained_gap_makes_run_partial()
    test_all_blank_or_fail_does_not_overwrite()
    print("OK  RAMP-SUMMARY-FAILURES-OK + SHORT-PDF-BLANK + CMP-AUD-019: "
          "total-only phantoms are rejected, a red per-route audit drives the "
          "producer outcome (unexplained -> PARTIAL, explained P/V residual -> a "
          "typed note on a COMPLETE run), and the matcher's renamed/duplicate "
          "blind spots surface as diagnostics.")


if __name__ == "__main__":
    main()
