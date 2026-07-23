"""Golden check for the PDF-vs-Excel by-day matrix engine (scripts/pdf_excel_matrix.py,
M2-B / v0.31.0): the catalog-derived family rows, the snapshot render model (cells
need BOTH editions), the M1-C self-identifying names, available_days + the scoped
rebuild list, and build_pve_cell's orchestration + cache recording via the SHARED
self-compare primitives (stubbed so no real report data is needed).

openpyxl only — no browser/network. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_pdf_excel_matrix.py
"""
import contextlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from _checklib import write_comparison_stub  # noqa: E402

import artifact_store  # noqa: E402
import matrix  # noqa: E402
import outcome as oc  # noqa: E402
import paths  # noqa: E402
import pdf_excel_matrix as pve  # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult, Events  # noqa: E402

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def _touch_export(base, subdir, name="r001.xlsx"):
    d = base / subdir
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(b"PK export")
    return d


def test_rows_from_catalog():
    print("family rows derive from report_catalog.MATRIX (the 5 dual-edition families):")
    rows = pve._pve_rows()
    check("exactly five dual-edition families",
          {r[0] for r in rows} == {"highway_log_pdf", "intersection_detail_pdf",
                                   "highway_detail_pdf", "highway_sequence_pdf",
                                   "ramp_detail_pdf"})
    lut = pve._row_lookup()
    check("each row names its PDF + Excel edition subdirs",
          lut["highway_log_pdf"][2] == "highway_log_pdf"
          and lut["highway_log_pdf"][3] == "highway_log")
    check("labels are the family report labels",
          lut["intersection_detail_pdf"][1] == "Intersection Detail")


def test_snapshot_and_naming():
    print("snapshot shape + M1-C self-identifying names + the needs-both-editions gate:")
    out = pve.day_out_path("2026-07-22", "ssor-prod", "highway_log_pdf")
    check("workbook name embeds family + day + source (M1-C.7)",
          out.name == "highway_log_pdf_vs_excel 2026-07-22 ssor-prod.xlsx")
    check("store lives under comparisons/pdf-vs-excel-by-day/<day source>/",
          out.parent.name == "2026-07-22 ssor-prod"
          and out.parent.parent.name == "pdf-vs-excel-by-day")
    snap = pve.pve_matrix_snapshot("ssor-prod", ["2026-07-22"], today="2026-07-22")
    check("snapshot is shape-compatible with the by-day matrix (rows/days/cells, no tsn_meta)",
          set(snap) >= {"source", "days", "rows", "row_labels", "cells", "all_rows"}
          and "tsn_meta" not in snap)
    cell = snap["cells"]["highway_log_pdf"]["2026-07-22"]
    check("a day with NO exports -> cell not present (needs both editions)",
          cell["export"]["present"] is False
          and cell["export"]["pdf_present"] is False
          and cell["export"]["excel_present"] is False)


def test_export_presence_gate():
    print("the export gate requires BOTH editions present:")
    tmp = Path(tempfile.mkdtemp(prefix="pve_"))
    saved = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        day = tmp / "2026-07-22 ssor-prod"
        _touch_export(day, "highway_log_pdf")     # only the PDF edition present
        snap = pve.pve_matrix_snapshot("ssor-prod", ["2026-07-22"], today="2099-01-01")
        cell = snap["cells"]["highway_log_pdf"]["2026-07-22"]
        check("only PDF exported -> export.present False, but pdf_present True",
              cell["export"]["present"] is False and cell["export"]["pdf_present"] is True)
        check("only PDF exported -> cell NOT buildable (missing the Excel side)",
              not matrix.cell_buildable(cell["cmp"]))
        _touch_export(day, "highway_log")         # add the Excel edition
        snap = pve.pve_matrix_snapshot("ssor-prod", ["2026-07-22"], today="2099-01-01")
        cell = snap["cells"]["highway_log_pdf"]["2026-07-22"]
        check("both editions exported -> export.present True + cell buildable",
              cell["export"]["present"] is True and matrix.cell_buildable(cell["cmp"]))
        check("both exported, no comparison yet -> cell is stale (needs build)",
              cell["cmp"].get("stale") is True)
        rebuild = pve.cells_to_rebuild(snap, scope="stale")
        check("cells_to_rebuild lists the buildable stale cell",
              ("2026-07-22", "highway_log_pdf") in rebuild)
    finally:
        paths.OUTPUT_ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def _stub_self_cmp(completion=oc.COMPLETE):
    """A self comparator whose values compare() commits a real comparison-stub
    workbook through artifact_store (so it carries the typed publication state
    _published_comparison_result requires) and returns the published result — the
    same shape the real PDF-vs-Excel adapters return."""
    typed = ComparisonOutcome(
        status="ok", completion=completion,
        verdict="match" if completion == oc.COMPLETE else "diff",
        counts=ComparisonCounts(known=True, paired_rows=1),
        warnings=(() if completion == oc.COMPLETE else ("input partial",)),
        pairing_quality="exact")

    class _Cmp:
        def compare(self, a, b, out_path, events=None, confirm_overwrite=None,
                    mode="values", commit_guard=None):
            def produce(tmp):
                write_comparison_stub(Path(tmp))
                return ConsolidateResult(
                    status="ok", verdict=typed.verdict, completion=completion,
                    skipped_inputs=0 if completion == oc.COMPLETE else 1,
                    failed_inputs=0, output_path=str(tmp), comparison_outcome=typed)
            return artifact_store.commit_workbook(
                Path(out_path), produce, expect_sheet="Comparison",
                requested_mode=mode)
    return _Cmp()


def test_build_records_cache():
    print("build_pve_cell orchestrates the shared self primitives + records the cache:")
    tmp = Path(tempfile.mkdtemp(prefix="pveb_"))
    saved = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        day = tmp / "2026-07-22 ssor-prod"
        _touch_export(day, "highway_log_pdf")
        _touch_export(day, "highway_log")
        consolidated = {}

        def _fake_ensure(store_dir, subdir, events, force, commit_guard=None):
            # Write to the SAME persistent location production uses (not inside the
            # fingerprinted per-route folder, which would read the cell back stale).
            p = matrix.consolidated_store_path(store_dir, subdir)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"PK cons")
            consolidated[subdir] = p
            return p, oc.COMPLETE

        with _patch(matrix, "_ensure_consolidated", _fake_ensure), \
             _patch(matrix, "_pdf_self_comparator", lambda _sub: _stub_self_cmp()):
            result = pve.build_pve_cell("ssor-prod", "2026-07-22", "highway_log_pdf",
                                        tmp, Events(), commit_guard=None)
        check("build returns an ok result", result.status == "ok")
        out = pve.day_out_path("2026-07-22", "ssor-prod", "highway_log_pdf")
        check("the VALUES workbook was written to the by-day store", out.exists())
        check("both editions were consolidated (PDF + Excel)",
              set(consolidated) == {"highway_log_pdf", "highway_log"})
        rec = pve.load_results().get("2026-07-22 ssor-prod|highway_log_pdf")
        check("the counts cache recorded the cell", rec is not None)
        check("...with a generation id + producer version (a real committed generation)",
              bool(rec and rec.get("generation_id")) and bool(rec.get("producer_versions")))
        # A snapshot now reads the cell BUILT (not stale) since inputs are unchanged.
        snap = pve.pve_matrix_snapshot("ssor-prod", ["2026-07-22"], today="2099-01-01")
        cmp = snap["cells"]["highway_log_pdf"]["2026-07-22"]["cmp"]
        check("the snapshot now reads the cell built (has a verdict, not stale)",
              cmp.get("verdict") is not None and not cmp.get("stale"))
    finally:
        paths.OUTPUT_ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def test_unknown_row_and_bad_date():
    print("build_pve_cell validates its inputs at the boundary:")
    tmp = Path(tempfile.mkdtemp(prefix="pvev_"))
    saved = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        try:
            pve.build_pve_cell("ssor-prod", "2026-07-22", "nonesuch", tmp, Events())
            check("unknown row raises ValueError", False)
        except ValueError:
            check("unknown row raises ValueError", True)
        try:
            pve.build_pve_cell("ssor-prod", "not-a-date", "highway_log_pdf", tmp, Events())
            check("invalid date raises ValueError", False)
        except ValueError:
            check("invalid date raises ValueError", True)
    finally:
        paths.OUTPUT_ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=== PDF-vs-Excel by-day matrix (M2-B) ===")
    test_rows_from_catalog()
    test_snapshot_and_naming()
    test_export_presence_gate()
    test_build_records_cache()
    test_unknown_row_and_bad_date()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL PDF-VS-EXCEL MATRIX CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
