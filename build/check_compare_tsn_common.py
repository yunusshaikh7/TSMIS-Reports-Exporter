"""Golden check for the shared vs-TSN file-comparator substrate (P5b / S04):
scripts/compare_tsn_common.py + the five thin compare_*_tsn modules that delegate to it.

Two halves:
  * SUBSTRATE — locks compare_tsn_common's exact behavior: the run_files_compare branch
    order + strings (deps gate, per-side missing-file message, the 6-line banner, loader
    ValueError wrap, warnings None -> the run_compare () default), the norm_pm / iso_date
    canon (incl. Intersection Detail's 2-digit TSN year), and that make_notes_writer emits
    one "Notes" sheet with the title + body lines.
  * DELEGATION — proves the five comparators were actually collapsed onto it (this is the
    half that is RED before the refactor): each imports compare_tsn_common and routes
    compare() through run_files_compare; Ramp/Intersection Detail alias _norm_pm/_iso_date
    to the shared helpers; Highway Sequence + Intersection Detail build their Notes legend
    via make_notes_writer. compare_core is never imported here for mutation — untouched.

run_compare is monkeypatched for the happy-path branch (no Excel engine needed); the
make_notes_writer assertion writes a real in-memory workbook. Offline, CI-safe. Run:
    build\\.venv\\Scripts\\python.exe build\\check_compare_tsn_common.py
"""
import contextlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_tsn_common as ctc            # noqa: E402
from events import Events                   # noqa: E402

_fail = []
_SCRIPTS = ROOT / "scripts"
_MODULES = ["compare_ramp_detail_tsn", "compare_ramp_summary_tsn",
            "compare_highway_sequence_tsn", "compare_intersection_detail_tsn",
            "compare_intersection_summary_tsn"]


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


def _events():
    logs = []
    return Events(on_log=logs.append), logs


def _src(mod):
    return (_SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# SUBSTRATE
# --------------------------------------------------------------------------- #
def test_normalizers():
    print("compare_tsn_common normalizers:")
    check("norm_pm strips TSN zero-pad (' 000.606' == '0.606')",
          ctc.norm_pm(" 000.606") == ctc.norm_pm("0.606") == "0.606")
    check("norm_pm keeps a leading-dot decimal ('.5' -> '0.5') + sign ('-000.5' -> '-0.5')",
          ctc.norm_pm(".5") == "0.5" and ctc.norm_pm("-000.5") == "-0.5")
    check("norm_pm empty -> ''", ctc.norm_pm(None) == "" and ctc.norm_pm("   ") == "")
    check("iso_date TSMIS MM/DD/YYYY -> ISO", ctc.iso_date("02/25/1976") == "1976-02-25")
    check("iso_date TSN 'YYYY-MM-DD HH:MM:SS' -> ISO", ctc.iso_date("1992-09-28 00:00:00") == "1992-09-28")
    check("iso_date TSN 2-digit year windowed (>=30 -> 19xx, <30 -> 20xx)",
          ctc.iso_date("73-10-19") == "1973-10-19" and ctc.iso_date("29-01-02") == "2029-01-02")
    check("iso_date passthrough on unrecognized + empty",
          ctc.iso_date("n/a") == "n/a" and ctc.iso_date(None) == "")


def test_notes_writer():
    print("compare_tsn_common.make_notes_writer:")
    from openpyxl import Workbook
    writer = ctc.make_notes_writer("My Title", ("line one", "line two"))
    wb = Workbook()
    ws = writer(wb)
    check("creates a sheet named 'Notes'", ws.title == "Notes" and "Notes" in wb.sheetnames)
    _tc = ws.sheet_properties.tabColor
    _rgb = getattr(_tc, "rgb", _tc)              # openpyxl wraps the value in a Color
    check("orange tab color", isinstance(_rgb, str) and _rgb.endswith("ED7D31"))
    col = [r[0].value for r in ws.iter_rows()]
    check("row 1 = title, then one row per body line",
          col == ["My Title", "line one", "line two"])
    check("column A widened", ws.column_dimensions["A"].width == 110)


def test_driver_branches():
    print("run_files_compare branches (deps / missing file / loader error):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_ctc_"))
    a, b, out = root / "a.xlsx", root / "b.xlsx", root / "o.xlsx"
    a.write_bytes(b"x")
    b.write_bytes(b"x")

    def _loader(_t, _n):
        return [["r"]], [["r"]], None

    # deps gate -> the custom deps message, run_compare never reached.
    r = ctc.run_files_compare("SC", a, b, out, banner="B", has_route=True, loader=_loader,
                              deps_ok=False, deps_msg="Required components are missing (pdfplumber, openpyxl).",
                              events=_events()[0])
    check("deps_ok False -> error with the EXACT custom deps message",
          r.status == "error" and r.message == "Required components are missing (pdfplumber, openpyxl).")

    # per-side missing file -> names the side + the path (TSMIS first, TSN second).
    r = ctc.run_files_compare("SC", root / "missing.xlsx", b, out, banner="B",
                              has_route=True, loader=_loader, events=_events()[0])
    check("missing TSMIS -> 'The TSMIS file doesn't exist:\\n<path>'",
          r.status == "error" and r.message == f"The TSMIS file doesn't exist:\n{root / 'missing.xlsx'}")
    r = ctc.run_files_compare("SC", a, root / "missing.xlsx", out, banner="B",
                              has_route=True, loader=_loader, events=_events()[0])
    check("missing TSN -> 'The TSN file doesn't exist:\\n<path>'",
          r.status == "error" and r.message == f"The TSN file doesn't exist:\n{root / 'missing.xlsx'}")

    # loader ValueError -> wrapped to an error result (its message verbatim).
    def _bad(_t, _n):
        raise ValueError("bad shape")

    r = ctc.run_files_compare("SC", a, b, out, banner="B", has_route=True, loader=_bad,
                              events=_events()[0])
    check("loader ValueError -> error result with that message", r.status == "error" and r.message == "bad shape")


def test_driver_happy_path():
    print("run_files_compare happy path (banner + run_compare hand-off):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_ctc_"))
    a, b, out = root / "tsmis.xlsx", root / "tsn.xlsx", root / "o.xlsx"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    seen = {}

    def _fake_run_compare(sc, rows_t, rows_n, has_route, out_path, **kw):
        seen.update(sc=sc, rows_t=rows_t, rows_n=rows_n, has_route=has_route,
                    out_path=out_path, **kw)

        class _R:  # a stand-in result object; the driver returns it unchanged
            status = "ok"
        return _R()

    ev, logs = _events()
    with _patch(ctc, "run_compare", _fake_run_compare):
        # warnings None from the loader must reach run_compare as the () default.
        ctc.run_files_compare("SCHEMA", a, b, out, banner="Ramp Detail Comparison — TSMIS vs TSN",
                              has_route=True, loader=lambda _t, _n: ([["t"]], [["n"]], None),
                              mode="values", confirm_overwrite="CB", events=ev)
    check("banner == the 6 canonical log lines (=*60, title, =*60, TSMIS:, TSN:, '')",
          logs == ["=" * 60, "Ramp Detail Comparison — TSMIS vs TSN", "=" * 60,
                   "TSMIS: tsmis.xlsx", "TSN:   tsn.xlsx", ""])
    check("run_compare got schema/has_route/out_path/mode/name_a/name_b passed through",
          seen.get("sc") == "SCHEMA" and seen.get("has_route") is True
          and seen.get("out_path") == out and seen.get("mode") == "values"
          and seen.get("name_a") == "tsmis.xlsx" and seen.get("name_b") == "tsn.xlsx"
          and seen.get("confirm_overwrite") == "CB")
    check("loader rows reach run_compare in order", seen.get("rows_t") == [["t"]] and seen.get("rows_n") == [["n"]])
    check("warnings None normalized to the run_compare () default", seen.get("warnings") == ())

    # A list of warnings passes straight through (the AGGREGATE summaries' path).
    seen.clear()
    with _patch(ctc, "run_compare", _fake_run_compare):
        ctc.run_files_compare("SCHEMA", a, b, out, banner="B", has_route=False,
                              loader=lambda _t, _n: ([], [], ["a warning"]), events=_events()[0])
    check("explicit warnings list passes through unchanged", seen.get("warnings") == ["a warning"])


# --------------------------------------------------------------------------- #
# DELEGATION  (the RED-before-refactor half)
# --------------------------------------------------------------------------- #
def test_all_delegate():
    print("every compare_*_tsn delegates to compare_tsn_common:")
    for mod in _MODULES:
        s = _src(mod)
        check(f"{mod}: imports compare_tsn_common", "import compare_tsn_common" in s)
        check(f"{mod}: compare() routes through run_files_compare", "run_files_compare" in s)


def test_detail_aliases():
    print("the two FLAT detail comparators reuse the shared normalizers:")
    import compare_ramp_detail_tsn as rd
    import compare_intersection_detail_tsn as idt
    check("ramp_detail._norm_pm IS compare_tsn_common.norm_pm", rd._norm_pm is ctc.norm_pm)
    check("ramp_detail._iso_date IS compare_tsn_common.iso_date", rd._iso_date is ctc.iso_date)
    check("intersection_detail._norm_pm IS compare_tsn_common.norm_pm", idt._norm_pm is ctc.norm_pm)
    check("intersection_detail._iso_date IS compare_tsn_common.iso_date", idt._iso_date is ctc.iso_date)
    # the canary-pinned behavior still holds through the alias
    check("aliased _norm_pm canon intact (' 000.204' -> '0.204')", rd._norm_pm(" 000.204") == "0.204")
    check("aliased _iso_date 2-digit-year intact ('73-10-19' -> '1973-10-19')",
          idt._iso_date("73-10-19") == "1973-10-19")


def test_notes_delegation():
    print("Highway Sequence + Intersection Detail build Notes via make_notes_writer:")
    from openpyxl import Workbook
    import compare_highway_sequence_tsn as hs
    import compare_intersection_detail_tsn as idt
    for mod, label in ((hs, "highway_sequence"), (idt, "intersection_detail")):
        check(f"{label}: source uses make_notes_writer", "make_notes_writer" in _src(mod.__name__))
        check(f"{label}: schema legend_writer is wired", mod._SCHEMA.legend_writer is not None)
        wb = Workbook()
        mod._SCHEMA.legend_writer(wb)
        check(f"{label}: legend_writer emits a 'Notes' sheet", "Notes" in wb.sheetnames)


def main():
    test_normalizers()
    test_notes_writer()
    test_driver_branches()
    test_driver_happy_path()
    test_all_delegate()
    test_detail_aliases()
    test_notes_delegation()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-TSN-COMMON CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
