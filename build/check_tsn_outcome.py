"""CT (P1-B05) -- TSN producer completion persistence and complete-only reuse.

Proves the contract is complete on the TSN side:
  * every incomplete-capable TSN builder SETS a producer-owned completion + structured
    counts (not just an "INCOMPLETE" warning line) -- Ramp Summary / Intersection
    Summary (missing categories) and Highway Sequence (a failed district PDF);
  * tsn_library.build_consolidated PERSISTS that outcome beside the generated workbook
    and tsn_library.resolve EXPOSES it before reuse;
  * comparison consumers never compare that PARTIAL ground truth: Everything and
    by-day drive ensure_current, rebuild from admissible raw, and proceed only after
    the persisted producer outcome is COMPLETE with zero skipped/failed inputs.

Offline: the PDF parse functions are monkeypatched (no real PDFs / pdfplumber parse);
openpyxl writes real workbooks. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_tsn_outcome.py
"""
import contextlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import outcome as oc                  # noqa: E402
import artifact_store                 # noqa: E402
import consolidation_meta as cm       # noqa: E402
import matrix                         # noqa: E402
import day_matrix as dm               # noqa: E402
import paths                          # noqa: E402
import tsn_library                    # noqa: E402
from events import ConsolidateResult, Events   # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from openpyxl import Workbook         # noqa: E402

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _partial_comparison(path):
    typed = ComparisonOutcome(
        status="ok", completion="partial", verdict="diff",
        counts=ComparisonCounts(known=True, paired_rows=1),
        warnings=("TSN source coverage was partial",), pairing_quality="exact")

    def produce(tmp):
        wb = Workbook(); wb.active.title = "Comparison"; wb.save(tmp)
        return ConsolidateResult(
            status="ok", output_path=str(tmp), verdict="diff",
            completion="partial", skipped_inputs=1, failed_inputs=0,
            comparison_outcome=typed)

    return artifact_store.commit_workbook(
        path, produce, expect_sheet="Comparison", requested_mode="values")


def _complete_comparison(path):
    typed = ComparisonOutcome(
        status="ok", completion="complete", verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=1),
        warnings=(), pairing_quality="exact")

    def produce(tmp):
        wb = Workbook(); wb.active.title = "Comparison"; wb.save(tmp)
        return ConsolidateResult(
            status="ok", output_path=str(tmp), verdict="match",
            completion="complete", skipped_inputs=0, failed_inputs=0,
            comparison_outcome=typed)

    return artifact_store.commit_workbook(
        path, produce, expect_sheet="Comparison", requested_mode="values")


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def test_producers():
    print("TSN producers set producer-owned completion + counts:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_tsnprod_"))
    try:
        import tsn_load_ramp_summary as rs
        import compare_ramp_summary_tsn as rstsn
        raw = tmp / "raw"
        raw.mkdir()
        (raw / "tsn.pdf").write_bytes(b"%PDF-1.4")          # _find_raw needs a file
        full = {slug: 1 for _k, slug in rstsn._CATEGORIES}
        full["total_ramps"] = len(full)
        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(full)):
            r = rs.build_into(raw, tmp / "rs_full.xlsx", events=Events())
        check("ramp summary, all categories present -> complete / 0 skipped",
              r.completion == oc.COMPLETE and r.skipped_inputs == 0)
        miss = dict(full)
        miss[rstsn._CATEGORIES[0][1]] = None                 # drop one category
        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(miss)):
            r = rs.build_into(raw, tmp / "rs_part.xlsx", events=Events())
        check("ramp summary, a missing category -> partial + skipped_inputs",
              r.completion == oc.PARTIAL and r.skipped_inputs == 1)

        import tsn_load_intersection_summary as isum
        import compare_intersection_summary_tsn as istsn
        cats = istsn._SPEC.categories_for("tsn")
        ifull = {slug: 1 for _k, slug in cats}
        ifull["total_intersections"] = len(ifull)
        with _patch(istsn, "parse_tsn_pdf", lambda _p: dict(ifull)):
            r = isum.build_into(raw, tmp / "is_full.xlsx", events=Events())
        check("intersection summary, all present -> complete", r.completion == oc.COMPLETE)
        imiss = dict(ifull)
        imiss[cats[0][1]] = None
        with _patch(istsn, "parse_tsn_pdf", lambda _p: dict(imiss)):
            r = isum.build_into(raw, tmp / "is_part.xlsx", events=Events())
        check("intersection summary, a missing category -> partial + skipped_inputs",
              r.completion == oc.PARTIAL and r.skipped_inputs == 1)

        import consolidate_tsn_highway_sequence as hs
        hsraw = tmp / "hsraw"
        hsraw.mkdir()
        for district in range(1, 13):
            (hsraw / f"D{district:02d} HSL TSN.pdf").write_bytes(b"%PDF-1.4")

        def _parse_both_ok(path, events, pdf_name=None):
            district = Path(pdf_name).name[1:3]
            return district, {district: [{"row": 1}]}       # non-empty -> a route landed

        def _parse_one_fails(path, events, pdf_name=None):
            if "D02" in str(pdf_name):
                raise ValueError("unreadable district PDF")
            return _parse_both_ok(path, events, pdf_name)

        # The workbook content is irrelevant here (only the completion is) — stub the
        # writer so the test doesn't depend on the row-dict schema. The writer now takes
        # the P12 `proceed` overwrite gate and returns committed=True (mirrors
        # atomic_save_if): honor proceed, write, report success.
        def _fake_write(rows, out, proceed=None):
            if proceed is not None and not proceed():
                return False
            Path(out).write_text("wb")
            return True

        with _patch(hs, "_write_workbook", _fake_write):
            with _patch(hs, "parse_pdf", _parse_both_ok):
                r = hs.consolidate(input_dir=hsraw, out_path=tmp / "hs_full.xlsx", events=Events())
            check("highway sequence, all PDFs parse -> complete / 0 failed",
                  r.completion == oc.COMPLETE and r.failed_inputs == 0)
            with _patch(hs, "parse_pdf", _parse_one_fails):
                r = hs.consolidate(input_dir=hsraw, out_path=tmp / "hs_part.xlsx", events=Events())
            check("highway sequence, one district PDF fails -> error / no partial truth",
                  r.status == "error" and r.failed_inputs == 1
                  and not (tmp / "hs_part.xlsx").exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_library_and_matrix_end_to_end():
    print("tsn_library build -> persist -> resolve(completion) -> matrix/by-day reduce:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_tsnlib_"))
    saved = (paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT)
    paths.TSN_LIBRARY_ROOT = tmp / "_lib"
    paths.OUTPUT_ROOT = tmp / "_out"
    paths.INPUT_ROOT = tmp / "_in"
    try:
        import compare_ramp_summary_tsn as rstsn
        # land a raw .pdf in the library and build a PARTIAL consolidated (one category
        # missing), driving the REAL library builder + persistence.
        src_pdf = tmp / "ramp_summary_statewide.pdf"
        src_pdf.write_bytes(b"%PDF-1.4")
        tsn_library.import_raw("ramp_summary", [str(src_pdf)])
        full = {slug: 1 for _k, slug in rstsn._CATEGORIES}
        full["total_ramps"] = len(full)
        full[rstsn._CATEGORIES[0][1]] = None                 # one missing -> partial
        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(full)):
            br = tsn_library.build_consolidated("ramp_summary", events=Events(), force=True)
        check("build_consolidated returns the builder's partial completion",
              br.completion == oc.PARTIAL)
        cons = tsn_library.consolidated_path("ramp_summary")
        check("...and persists a sidecar beside the generated workbook",
              cm.meta_path(cons).is_file())
        src = tsn_library.resolve("ramp_summary")
        check("resolve() exposes the persisted partial completion",
              src.get("kind") == "consolidated" and src.get("completion") == oc.PARTIAL)

        # P1-R01 (round 7): build_consolidated HONORS a False write_outcome (a publication
        # failure for a partial) -> an ERROR result, not the success-shaped one.
        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(full)), \
             _patch(cm, "write_outcome", lambda *a, **k: False):
            errres = tsn_library.build_consolidated("ramp_summary", events=Events(), force=True)
        check("build_consolidated returns an ERROR result when write_outcome reports failure",
              errres.status == "error")
        # The monkeypatch above deliberately bypasses write_outcome's real
        # fail-safe cleanup. Re-certify this unchanged fixture generation before
        # testing downstream reuse; production never receives this test-only gap.
        raw_manifest = tsn_library._raw_manifest("ramp_summary")
        workbook_identity = tsn_library.normalized_workbook_identity(cons)
        cm.write_outcome(
            cons, br,
            extra={"tsn_normalization_version":
                   tsn_library.get("ramp_summary").normalization_version,
                   "tsn_raw_manifest": raw_manifest,
                   "tsn_normalized_workbook_identity": workbook_identity,
                   "tsn_artifact_identity_token":
                       tsn_library.canonical_normalized_identity_token(
                           "ramp_summary", raw_manifest, workbook_identity)})

        # Everything matrix: the identity-valid PARTIAL is not a comparison
        # source.  The real ensure_current path must rebuild it to COMPLETE from
        # the retained raw before the comparator is reached.
        dest = tmp / "store"
        (dest / "ars-prod" / "ramp_summary").mkdir(parents=True, exist_ok=True)
        healed_counts = dict(full)
        healed_counts[rstsn._CATEGORIES[0][1]] = 1

        def _ok_compare(tsmis_dir, tsn_path, out_path, *a, **k):
            return _complete_comparison(Path(out_path))

        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(healed_counts)), \
             _patch(matrix, "consolidate_and_compare_tsn", _ok_compare):
            res = matrix.build_comparison(dest, "ramp_summary", "ars-prod", "tsn",
                                          "ssor-prod", events=None)
        check("Everything matrix rebuilds PARTIAL TSN before comparison",
              res.completion == oc.COMPLETE
              and tsn_library.status("ramp_summary")["current"] is True
              and tsn_library.resolve("ramp_summary").get("completion") == oc.COMPLETE)

        # Restore a valid PARTIAL certificate over the same current workbook so
        # the independent by-day entry point must perform the same healing.
        raw_manifest = tsn_library._raw_manifest("ramp_summary")
        workbook_identity = tsn_library.normalized_workbook_identity(cons)
        assert cm.write_outcome(
            cons, br,
            extra={"tsn_normalization_version":
                   tsn_library.get("ramp_summary").normalization_version,
                   "tsn_raw_manifest": raw_manifest,
                   "tsn_normalized_workbook_identity": workbook_identity,
                   "tsn_artifact_identity_token":
                       tsn_library.canonical_normalized_identity_token(
                           "ramp_summary", raw_manifest, workbook_identity)})
        assert tsn_library.resolve("ramp_summary").get("completion") == oc.PARTIAL

        # by-day matrix: it too heals before compare and records COMPLETE.
        captured = {}

        def _rec(date, source, row_key, verdict, diff_cells, one_sided, built_at,
                 completion=None, input_fingerprint=None,
                 source_identities=None, generation_id=None,
                 commit_guard=None):
            captured["completion"] = completion

        out_file = tmp / "byday_out.xlsx"
        with _patch(rstsn, "parse_tsn_pdf", lambda _p: dict(healed_counts)), \
             _patch(matrix, "consolidate_and_compare_tsn",
                    lambda *a, **k: _complete_comparison(out_file)), \
             _patch(dm, "parse_run_folder", lambda _n: True), \
             _patch(dm, "day_out_path", lambda *a: out_file), \
             _patch(dm, "record_result", _rec):
            dres = dm.build_day_cell("ssor-prod", "2026-06-21", "ramp_summary", dest, events=None)
        check("by-day matrix rebuilds PARTIAL TSN before comparison",
              dres.completion == oc.COMPLETE
              and captured.get("completion") == oc.COMPLETE
              and tsn_library.status("ramp_summary")["current"] is True)
    finally:
        paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    test_producers()
    test_library_and_matrix_end_to_end()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL TSN-OUTCOME CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
