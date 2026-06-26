"""Golden check for the matrix multi-mode / TSN engine (scripts/matrix.py): the
per-row comparison-mode registry (cross-env / vs-TSN / cross-format), the two
Highway Log rows, TSN paths + source detection, the snapshot's per-row mode +
greyed unsupported cells, the unified scoped rebuild list, and build_comparison's
guard paths.

Pure filesystem + registry; no workbook content (the LIVE Highway-Log consolidate
-> compare paths reuse the already-golden-locked consolidate_* + compare_* and are
exercised separately / on the work PC with real TSN data).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_tsn.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import matrix
import paths

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _touch(p, data=b"PK"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def test_paths_and_modes():
    print("TSN paths + per-row mode registry:")
    d = "C:\\store"
    check("input root under _tsn_input/<subdir>",
          matrix.tsn_input_root(d, "highway_log").as_posix().endswith("_tsn_input/highway_log"))
    check("comparisons root under comparisons/tsn",
          matrix.tsn_comparisons_root(d).as_posix().endswith("comparisons/tsn"))
    check("highway_log is tsn_capable", matrix.tsn_capable("highway_log"))
    check("highway_log_pdf is tsn_capable", matrix.tsn_capable("highway_log_pdf"))
    check("intersection_detail_pdf is tsn_capable (CR-002, the HL-PDF parallel)",
          matrix.tsn_capable("intersection_detail_pdf"))
    check("ramp_summary is tsn_capable (v0.17.0 AGGREGATE)",
          matrix.tsn_capable("ramp_summary"))
    check("highway_sequence is tsn_capable (v0.17.0 FLAT, county+PM key)",
          matrix.tsn_capable("highway_sequence"))

    defs = matrix._row_defs()
    check("eight matrix rows — every report (both HL + both Intersection formats)",
          set(defs) == {"ramp_summary", "ramp_detail", "highway_sequence",
                        "highway_log", "highway_log_pdf", "intersection_summary",
                        "intersection_detail", "intersection_detail_pdf"})

    def modes(rk):
        _l, sub, _i, adapter, _hr = defs[rk]
        return {m["id"]: m for m in matrix._row_modes(rk, sub, adapter)}

    hl = modes("highway_log")
    check("HL Excel row modes: env + tsn + vs_pdf, all supported",
          set(hl) == {"env", "tsn", "vs_pdf"}
          and all(hl[k]["supported"] for k in hl))
    check("HL Excel tsn mode is the excel flavor on the highway_log TSN folder",
          hl["tsn"]["fmt"] == "excel" and hl["tsn"]["tsn_subdir"] == "highway_log")
    hp = modes("highway_log_pdf")
    check("HL PDF row modes: env + tsn + vs_excel, ALL supported (v0.17.0 — env coded)",
          set(hp) == {"env", "tsn", "vs_excel"}
          and hp["env"]["supported"]
          and hp["tsn"]["supported"] and hp["vs_excel"]["supported"])
    check("HL PDF tsn shares the highway_log TSN folder (one TSN dataset)",
          hp["tsn"]["fmt"] == "pdf" and hp["tsn"]["tsn_subdir"] == "highway_log")
    idp = modes("intersection_detail_pdf")
    check("Int-Detail PDF row modes: env + tsn + vs_excel, ALL supported (CR-002 — the HL-PDF parallel)",
          set(idp) == {"env", "tsn", "vs_excel"}
          and idp["env"]["supported"]
          and idp["tsn"]["supported"] and idp["vs_excel"]["supported"])
    check("Int-Detail PDF tsn shares the intersection_detail TSN dataset (its Excel sibling)",
          idp["tsn"]["fmt"] == "pdf" and idp["tsn"]["tsn_subdir"] == "intersection_detail")
    rs = modes("ramp_summary")
    check("ramp_summary: env + tsn supported (v0.17.0 AGGREGATE)",
          rs["env"]["supported"] and rs["tsn"]["supported"])
    hs = modes("highway_sequence")
    check("highway_sequence: env + tsn supported (v0.17.0 FLAT)",
          hs["env"]["supported"] and hs["tsn"]["supported"])

    # mode_out_path: env stays under comparisons/<baseline>/, others under tsn/
    env_p = matrix.mode_out_path(d, "ssor-prod", "highway_log", "ars-prod", hl["env"])
    tsn_p = matrix.mode_out_path(d, "ssor-prod", "highway_log", "ars-prod", hl["tsn"])
    self_p = matrix.mode_out_path(d, "ssor-prod", "highway_log", "ars-prod", hl["vs_pdf"])
    check("env out path under comparisons/<baseline>/",
          env_p.as_posix().endswith("comparisons/ssor-prod/ars-prod_highway_log.xlsx"))
    check("tsn out path under comparisons/tsn/ with mode in name",
          tsn_p.as_posix().endswith("comparisons/tsn/ars-prod_highway_log_tsn.xlsx"))
    check("self out path distinct (vs_pdf) under comparisons/tsn/",
          self_p.name == "ars-prod_highway_log_vs_pdf.xlsx")


def test_source_detection():
    print("tsn_source detection (file / consolidated / pdfs / none):")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsn_"))
    # tsn_source now resolves through the canonical TSN library (tsn_library.resolve):
    # the dest-scoped _tsn_input drop is one fallback among the library home + the
    # global legacy locations. Isolate ALL of those roots to temp dirs so the unit
    # test exercises only the dest drop it plants (no real dev-repo TSN leaks in).
    saved_roots = (paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT)
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
    paths.OUTPUT_ROOT = dest / "_out"
    paths.INPUT_ROOT = dest / "_in"
    try:
        sub = "highway_log"
        check("empty folder -> none", matrix.tsn_source(dest, sub)["kind"] == "none")
        for i in range(3):
            _touch(matrix.tsn_input_root(dest, sub) / f"D0{i}_TSN.pdf", b"%PDF-1.4")
        src = matrix.tsn_source(dest, sub)
        check("only PDFs -> pdfs with count", src["kind"] == "pdfs" and src["pdf_count"] == 3)
        _touch(matrix.tsn_input_root(dest, sub) / "tsn_highway_log_consolidated.xlsx")
        check("consolidated .xlsx present -> consolidated",
              matrix.tsn_source(dest, sub)["kind"] == "consolidated")
        picked = dest / "elsewhere" / "my_tsn.xlsx"
        _touch(picked)
        check("explicit file selection wins",
              matrix.tsn_source(dest, sub, selected_file=str(picked))["kind"] == "file")
        check("a non-xlsx selection is ignored (falls back to scan)",
              matrix.tsn_source(dest, sub, selected_file=str(dest / "nope.pdf"))["kind"]
              == "consolidated")
        # The canonical TSN library takes precedence over the legacy dest drop.
        lib_cons = paths.tsn_library_consolidated_path(sub, "tsn_highway_log_consolidated.xlsx")
        _touch(lib_cons)
        r = matrix.tsn_source(dest, sub)
        check("library consolidated preferred over the legacy dest drop",
              r["kind"] == "consolidated" and Path(r["path"]) == lib_cons)
    finally:
        paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT = saved_roots
        shutil.rmtree(dest, ignore_errors=True)


def test_snapshot_modes():
    print("snapshot per-row mode + greyed cells + scoped rebuild:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnsnap_"))
    try:
        # HL-excel in vs-TSN mode with both sides present.
        _touch(dest / "ars-prod" / "highway_log" / "r1.xlsx")
        _touch(matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx")
        snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod",
                                      row_modes={"highway_log": "tsn"})
        check("selected mode recorded", snap["modes"]["highway_log"] == "tsn"
              and snap["modes"]["ramp_detail"] == "env")
        check("row_modes lists the per-row available modes",
              {m["id"] for m in snap["row_modes"]["highway_log"]} == {"env", "tsn", "vs_pdf"})
        hl = snap["cells"]["highway_log"]["ars-prod"]
        check("tsn-mode cell carries unified 'cmp' (supported, both sides present)",
              hl["cmp"]["supported"] and hl["cmp"]["missing_side"] is None
              and not hl["cmp"]["built"])
        check("tsn_meta carries the source summary",
              snap["tsn_meta"]["highway_log"]["source_kind"] == "consolidated"
              and snap["tsn_meta"]["highway_log"]["fmt"] == "excel")
        # HL-PDF env mode is now CODED (v0.17.0) — a real cross-env cell, not greyed
        hp = snap["cells"]["highway_log_pdf"]["ars-prod"]
        check("HL-PDF cross-env cell now supported (not greyed)",
              hp["cmp"].get("supported") is not False
              and hp.get("comparison") is not None)
        # env-mode rows keep the back-compat 'comparison' alias
        rd = snap["cells"]["ramp_detail"]["ars-prod"]
        check("env-mode cell keeps comparison alias", rd.get("comparison") is not None
              and rd["cmp"] is rd["comparison"])
        # unified scoped rebuild list (entries are (row, cell, mode))
        todo = matrix.cells_to_rebuild(snap, scope="all")
        check("rebuild list includes the ready HL tsn cell as a triple",
              ("highway_log", "ars-prod", "tsn") in todo)
        check("rebuild list excludes not-ready HL-PDF env cells (no PDF export here)",
              all(rk != "highway_log_pdf" for rk, _e, _m in todo))
        check("row filter scopes to one report",
              all(rk == "highway_log"
                  for rk, _e, _m in matrix.cells_to_rebuild(snap, "all", row="highway_log")))
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_build_guards():
    print("build_comparison guard paths:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnbuild_"))
    try:
        def raises(fn):
            try:
                fn()
                return False
            except ValueError:
                return True
        check("unknown row raises",
              raises(lambda: matrix.build_comparison(dest, "nope", "ars-prod", "env",
                                                     "ssor-prod", events=None)))
        check("highway_sequence vs TSN now WIRED — reaches the no-TSN-source error (not greyed)",
              raises(lambda: matrix.build_comparison(dest, "highway_sequence", "ars-prod", "tsn",
                                                     "ssor-prod", events=None)))
        # HL-PDF cross-env is now WIRED (v0.17.0): not greyed/raised — it reaches the
        # PDF loader and returns a clean "no Highway Log (PDF) export" error result.
        _hlpdf_env = matrix.build_comparison(dest, "highway_log_pdf", "ars-prod", "env",
                                             "ssor-prod", events=None)
        check("HL-PDF cross-env wired (returns a no-export error result, not greyed)",
              _hlpdf_env is not None and getattr(_hlpdf_env, "status", "") != "ok")
        check("HL tsn with no TSN source raises",
              raises(lambda: matrix.build_comparison(dest, "highway_log", "ars-prod", "tsn",
                                                     "ssor-prod", events=None)))
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    test_paths_and_modes()
    test_source_detection()
    test_snapshot_modes()
    test_build_guards()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
