"""Golden check for the ArcGIS-tab "Reports vs layers" matrix (scripts/arcgis_matrix.py,
2026-09-02): the registry-derived rows, the layer DROP identity, the library's
per-report build state (built / trusted / from the staged drop), the snapshot's
cell states (needs build / needs export / buildable / stale), the scoped rebuild
list, build_cell's orchestration + cache recording via the SHARED primitives
(stubbed so no real report data is needed), build_report's guards + as-of default,
and the boundary validation.

openpyxl only — no browser/network. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_arcgis_matrix.py
"""
import contextlib
import datetime as dt
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from _checklib import write_comparison_stub  # noqa: E402

import arcgis_layers  # noqa: E402
import arcgis_matrix as agm  # noqa: E402
import arcgis_report_highway_detail as ah  # noqa: E402
import arcgis_report_intersection_detail as ari  # noqa: E402
import arcgis_reports  # noqa: E402
import artifact_store  # noqa: E402
import clean_road_layers as crl  # noqa: E402
import compare_highway_detail_arcgis as cmp_hd  # noqa: E402
import consolidate_clean_highway as cch  # noqa: E402
import consolidation_meta  # noqa: E402
import matrix  # noqa: E402
import outcome as oc  # noqa: E402
import paths  # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult, Events  # noqa: E402

_fail = []
DAY = "2026-08-17"
SRC = "ssor-prod"
DROP = {"fingerprint": "v2:3:feedface", "exported": "2026-08-19",
        "exported_at": "2026-08-19T12:14:14", "exported_source": "index",
        "files": 3, "index_present": True}


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


def _stub_build(path, drop_fingerprint, sidecar_key="arcgis_report_build",
                asof="2026-08-19", completion=oc.COMPLETE, payload=b"PK build"):
    """A stand-in layer build: a file + the trusted outcome sidecar a real build
    publishes, carrying the drop it came from."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    res = ConsolidateResult(status="ok", completion=completion,
                            output_path=str(path), skipped_inputs=0,
                            failed_inputs=0)
    ok = consolidation_meta.write_outcome(
        path, res, extra={sidecar_key: {
            "asof": asof, "rows": 42, "routes": 3,
            "layer_drop": {"fingerprint": drop_fingerprint,
                           "exported": "2026-08-19"}}})
    assert ok, "sidecar publish failed"
    return path


def _full_inventory(_lib_root=None):
    present = {n: Path("x") / f"{n}.xlsx" for n in crl.EXPECTED_LAYERS}
    return {"present": present, "missing": [], "unknown": [], "index": Path("x")}


# --------------------------------------------------------------------------- #
def test_rows_from_registry():
    print("rows derive from arcgis_reports (every report, buildable/comparable flagged):")
    rows = agm._ag_rows()
    check("one row per registry key, in registry order",
          [r[0] for r in rows] == list(arcgis_reports.KEYS))
    comparable = {r[0] for r in rows if r[5]}
    buildable = {r[0] for r in rows if r[4]}
    check("the two rendered reports compare",
          comparable == {"intersection_detail", "highway_detail"})
    check("Clean Road Highway builds but does not compare yet",
          buildable == comparable | {"clean_highway"})
    check("every row carries a label and a code",
          all(r[1] and r[2] for r in rows))
    check("every row that cannot compare says why",
          all(r[6] for r in rows if not r[5]) and all(not r[6] for r in rows if r[5]))
    check("comparable rows name their export editions, preferred first",
          agm._row_lookup()["highway_detail"][3] == ("highway_detail", "highway_detail_pdf"))
    check("row_keys is the registry set", agm.row_keys() == set(arcgis_reports.KEYS))
    check("the default report is comparable", arcgis_reports.can_compare(arcgis_reports.DEFAULT_KEY))


def test_drop_info():
    print("the layer drop's identity — content fingerprint + the manifest's own export date:")
    from openpyxl import Workbook
    tmp = Path(tempfile.mkdtemp(prefix="agdrop_"))
    try:
        def _wb(path, rows, created=None):
            wb = Workbook()
            ws = wb.active
            for r in rows:
                ws.append(r)
            if created is not None:
                wb.properties.created = created
            wb.save(path)

        _wb(tmp / "01_SHS Landmark.xlsx", [["a"], [1]])
        _wb(tmp / "02_City.xlsx", [["b"], [2]])
        # openpyxl stamps `created` in UTC; the drop date is the LOCAL date.
        created_utc = dt.datetime(2026, 8, 19, 19, 14, 14)
        _wb(tmp / "00_INDEX.xlsx", [crl.INDEX_HEADER], created=created_utc)
        info = arcgis_layers.drop_info(tmp)
        expected_local = (created_utc.replace(tzinfo=dt.timezone.utc)
                          .astimezone().date().isoformat())
        check("exported date comes from the INDEX's own timestamp (local date)",
              info["exported"] == expected_local and info["exported_source"] == "index")
        check("three files counted, INDEX present",
              info["files"] == 3 and info["index_present"] is True)
        check("fingerprint is the v2 content identity",
              isinstance(info["fingerprint"], str) and info["fingerprint"].startswith("v2:"))
        again = arcgis_layers.drop_info(tmp)
        check("fingerprint is stable across reads", again["fingerprint"] == info["fingerprint"])
        _wb(tmp / "02_City.xlsx", [["b"], [3]])          # a layer's bytes change
        changed = arcgis_layers.drop_info(tmp)
        check("a changed layer changes the fingerprint",
              changed["fingerprint"] != info["fingerprint"])
        (tmp / "00_INDEX.xlsx").unlink()
        no_index = arcgis_layers.drop_info(tmp)
        check("without the manifest the date falls back to the file dates and says so",
              no_index["exported_source"] == "files" and no_index["exported"]
              and no_index["index_present"] is False)
        empty = arcgis_layers.drop_info(tmp / "nothing")
        check("an absent folder reads as unknown, never raises",
              empty["fingerprint"] is None and empty["exported"] is None
              and empty["files"] == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_library_and_snapshot_states():
    print("the library's build states + the snapshot's cell states:")
    tmp = Path(tempfile.mkdtemp(prefix="agsnap_"))
    saved_root = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        day = tmp / f"{DAY} {SRC}"
        _touch_export(day, "highway_detail")
        hd_build = tmp / "builds" / "highway_detail_from_layers.xlsx"
        id_build = tmp / "builds" / "intersection_detail_from_layers.xlsx"
        cr_build = tmp / "builds" / "clean_highway_built.xlsx"
        with _patch(arcgis_layers, "drop_info", lambda lib_root=None: dict(DROP)), \
             _patch(crl, "inventory", _full_inventory), \
             _patch(ah, "OUT_PATH", hd_build), _patch(ari, "OUT_PATH", id_build), \
             _patch(cch, "OUT_PATH", cr_build):
            # nothing built yet
            lib = agm.library_snapshot()
            check("library names the drop", lib["drop"]["fingerprint"] == DROP["fingerprint"])
            bs = lib["builds"]
            check("an unbuilt buildable row: available, not built, no layers missing",
                  bs["highway_detail"]["available"] and not bs["highway_detail"]["built"]
                  and bs["highway_detail"]["missing_layers"] == [])
            check("a row with no build module: not available, says why",
                  not bs["ramp_summary"]["available"] and bs["ramp_summary"]["why"])
            check("Clean Road Highway: available but not comparable, says why",
                  bs["clean_highway"]["available"] and not bs["clean_highway"]["comparable"]
                  and bs["clean_highway"]["why"])
            snap = agm.ag_matrix_snapshot(SRC, [DAY], library=lib, today="2099-01-01")
            cells = snap["cells"]
            check("snapshot shape (rows/days/cells/library, no tsn_meta)",
                  set(snap) >= {"source", "days", "rows", "row_labels", "cells",
                                "all_rows", "library"} and "tsn_meta" not in snap)
            hd = cells["highway_detail"][DAY]
            check("export present + no build -> needs the layers side",
                  hd["export"]["present"] and hd["cmp"]["missing_side"] == "layers"
                  and not matrix.cell_buildable(hd["cmp"]))
            check("the reason the Build button gives names the layers",
                  "layers" in matrix.cell_unbuildable_reason(hd["cmp"]))
            idc = cells["intersection_detail"][DAY]
            check("no export + no build -> both sides missing",
                  idc["cmp"]["missing_side"] == "both" and not idc["export"]["present"])
            rs = cells["ramp_summary"][DAY]
            check("a row with no build renders unsupported with its reason",
                  rs["cmp"]["supported"] is False and rs["cmp"]["why"])
            check("row_supported mirrors comparability",
                  snap["row_supported"]["highway_detail"] is True
                  and snap["row_supported"]["clean_highway"] is False)
            check("available_days offers the exported day only",
                  agm.available_days(SRC) == [DAY])
            check("the add-day tag is the report's code",
                  agm.available_day_reports(SRC) == {DAY: ["HD"]})
            check("nothing to rebuild while no cell is buildable",
                  agm.cells_to_rebuild(snap, scope="all") == [])

            # a build from the CURRENT drop
            _stub_build(hd_build, DROP["fingerprint"])
            lib = agm.library_snapshot()
            b = lib["builds"]["highway_detail"]
            check("a built row from the staged drop reads current and comparable",
                  b["built"] and b["trusted"] and b["drop_current"] and b["comparable_now"]
                  and not b["stale"] and b["asof"] == "2026-08-19" and b["rows"] == 42)
            check("the build carries a content identity", bool(b.get("identity")))
            snap = agm.ag_matrix_snapshot(SRC, [DAY], library=lib, today="2099-01-01")
            hd = snap["cells"]["highway_detail"][DAY]["cmp"]
            check("build + export -> buildable, stale (no comparison yet)",
                  matrix.cell_buildable(hd) and hd["stale"] and hd["reason"] == "missing")
            check("cells_to_rebuild lists the buildable stale cell",
                  agm.cells_to_rebuild(snap, scope="stale") == [(DAY, "highway_detail")])
            check("...and the row / day filters scope it",
                  agm.cells_to_rebuild(snap, scope="all", row="intersection_detail") == []
                  and agm.cells_to_rebuild(snap, scope="all", date=DAY)
                  == [(DAY, "highway_detail")])

            # a build from ANOTHER drop: still comparable, but the row says rebuild
            _stub_build(hd_build, "v2:3:olderdrop")
            b = agm.library_snapshot()["builds"]["highway_detail"]
            check("a build from another drop reads stale with reason drop_changed, "
                  "yet stays comparable (the row header says rebuild)",
                  b["stale"] and b["stale_reason"] == "drop_changed"
                  and not b["drop_current"] and b["comparable_now"])

            # a build whose sidecar is gone: not comparable
            consolidation_meta.meta_path(hd_build).unlink()
            b = agm.library_snapshot()["builds"]["highway_detail"]
            check("a build with no trusted outcome record is not comparable",
                  b["built"] and not b["comparable_now"]
                  and b["stale_reason"] == "outcome_untrusted")
            snap = agm.ag_matrix_snapshot(SRC, [DAY], today="2099-01-01")
            check("...so its cell needs the layers side again",
                  snap["cells"]["highway_detail"][DAY]["cmp"]["missing_side"] == "layers")
    finally:
        paths.OUTPUT_ROOT = saved_root
        shutil.rmtree(tmp, ignore_errors=True)


def _stub_compare(completion=oc.COMPLETE):
    """A comparator whose values compare() commits a real comparison-stub workbook
    through artifact_store (so it carries the typed publication state
    _published_comparison_result requires) — the same shape the real
    ArcGIS-vs-TSMIS adapters return."""
    typed = ComparisonOutcome(
        status="ok", completion=completion,
        verdict="match" if completion == oc.COMPLETE else "diff",
        counts=ComparisonCounts(known=True, paired_rows=1),
        warnings=(() if completion == oc.COMPLETE else ("input partial",)),
        pairing_quality="exact")
    seen = []

    def compare(a, b, out_path, events=None, confirm_overwrite=None,
                mode="values", commit_guard=None):
        seen.append((str(a), str(b), mode))

        def produce(tmp):
            write_comparison_stub(Path(tmp))
            return ConsolidateResult(
                status="ok", verdict=typed.verdict, completion=completion,
                skipped_inputs=0 if completion == oc.COMPLETE else 1,
                failed_inputs=0, output_path=str(tmp), comparison_outcome=typed)
        return artifact_store.commit_workbook(
            Path(out_path), produce, expect_sheet="Comparison",
            requested_mode=mode)
    return compare, seen


def test_build_cell_records_cache():
    print("build_cell orchestrates the shared primitives + records the cache:")
    tmp = Path(tempfile.mkdtemp(prefix="agbuild_"))
    saved_root = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        day = tmp / f"{DAY} {SRC}"
        _touch_export(day, "highway_detail")
        hd_build = tmp / "builds" / "highway_detail_from_layers.xlsx"
        _stub_build(hd_build, DROP["fingerprint"])
        consolidated = {}

        def _fake_ensure(store_dir, subdir, events, force, commit_guard=None):
            p = matrix.consolidated_store_path(store_dir, subdir)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"PK cons")
            consolidated[subdir] = p
            return p, oc.COMPLETE

        compare, seen = _stub_compare()
        with _patch(arcgis_layers, "drop_info", lambda lib_root=None: dict(DROP)), \
             _patch(crl, "inventory", _full_inventory), \
             _patch(ah, "OUT_PATH", hd_build), \
             _patch(matrix, "_ensure_consolidated", _fake_ensure), \
             _patch(cmp_hd, "compare", compare):
            result = agm.build_cell(SRC, DAY, "highway_detail", Events())
            check("build returns an ok result", result.status == "ok")
            out = agm.day_out_path(DAY, SRC, "highway_detail")
            check("the VALUES workbook was written to the by-day store under a "
                  "self-identifying name",
                  out.exists() and out.name == f"highway_detail_vs_layers {DAY} {SRC}.xlsx"
                  and out.parent.parent.name == "arcgis-by-day")
            check("the export side was consolidated (the Excel edition, preferred)",
                  set(consolidated) == {"highway_detail"})
            check("the comparator was handed the layer build as side A and the "
                  "consolidated export as side B",
                  seen and seen[0][0] == str(hd_build)
                  and seen[0][1] == str(consolidated["highway_detail"]))
            rec = agm.load_results().get(f"{DAY} {SRC}|highway_detail")
            check("the counts cache recorded the cell", rec is not None)
            check("...with a generation id, producer version and the build's identity",
                  bool(rec and rec.get("generation_id")) and bool(rec.get("producer_versions"))
                  and rec.get("source_identities", {}).get("layers"))
            snap = agm.ag_matrix_snapshot(SRC, [DAY], today="2099-01-01")
            cmp = snap["cells"]["highway_detail"][DAY]["cmp"]
            check("the snapshot now reads the cell built and fresh",
                  cmp.get("verdict") is not None and not cmp.get("stale"))
            # A REBUILT layer build (new bytes) must read the cell stale again —
            # the build's identity is part of what the cell certified.
            _stub_build(hd_build, DROP["fingerprint"], payload=b"PK build v2")
            snap = agm.ag_matrix_snapshot(SRC, [DAY], today="2099-01-01")
            cmp = snap["cells"]["highway_detail"][DAY]["cmp"]
            check("a rebuilt layer build reads the cell stale",
                  cmp.get("stale") and cmp.get("reason") in
                  ("layers_newer", "source_identity_changed", "both_newer"))
            # HF-05: this lane writes no evidence artifact anywhere under its tree.
            tree = out.parent
            planted = tree / "highway_detail (evidence).xlsx"
            planted.write_bytes(b"PK planted positive control")
            found = [p.name for p in tree.rglob("*evidence*")]
            planted.unlink()
            check("the silence probe can SEE an evidence artifact when one exists",
                  found == [planted.name])
            check("the Reports-vs-layers lane writes ZERO evidence artifacts",
                  not list(tree.rglob("*evidence*")))
    finally:
        paths.OUTPUT_ROOT = saved_root
        shutil.rmtree(tmp, ignore_errors=True)


def test_guards():
    print("build_cell / build_report validate at the boundary:")
    tmp = Path(tempfile.mkdtemp(prefix="agguard_"))
    saved_root = paths.OUTPUT_ROOT
    try:
        paths.OUTPUT_ROOT = tmp
        hd_build = tmp / "builds" / "highway_detail_from_layers.xlsx"

        def _raises(fn, needle=None):
            try:
                fn()
                return False
            except ValueError as e:
                return needle is None or needle.lower() in str(e).lower()

        with _patch(arcgis_layers, "drop_info", lambda lib_root=None: dict(DROP)), \
             _patch(crl, "inventory", _full_inventory), \
             _patch(ah, "OUT_PATH", hd_build):
            check("build_cell: unknown row",
                  _raises(lambda: agm.build_cell(SRC, DAY, "nonesuch", Events()), "unknown"))
            check("build_cell: a row with no comparison yet refuses with its reason",
                  _raises(lambda: agm.build_cell(SRC, DAY, "ramp_summary", Events()),
                          "not rendered"))
            check("build_cell: invalid date",
                  _raises(lambda: agm.build_cell(SRC, "not-a-date", "highway_detail", Events()),
                          "invalid"))
            check("build_cell: not built yet",
                  _raises(lambda: agm.build_cell(SRC, DAY, "highway_detail", Events()),
                          "build highway detail from the layers first"))
            _stub_build(hd_build, DROP["fingerprint"])
            check("build_cell: built but no export that day",
                  _raises(lambda: agm.build_cell(SRC, DAY, "highway_detail", Events()),
                          "no highway detail export"))

            captured = {}

            def _fake_consolidate(events=None, confirm_overwrite=None, day=None, **kw):
                captured.update(kw)
                return ConsolidateResult(status="ok", completion=oc.COMPLETE,
                                         output_path=str(hd_build))
            with _patch(ah, "consolidate", _fake_consolidate):
                res = agm.build_report("highway_detail", Events())
                check("build_report defaults the as-of to the drop's export date "
                      "(never the TSN extract's)",
                      res.status == "ok" and captured.get("asof") == DROP["exported"])
                agm.build_report("highway_detail", Events(), asof=" 2026-01-02 ")
                check("an explicit as-of passes through, trimmed",
                      captured.get("asof") == "2026-01-02")
            check("build_report: unknown row",
                  _raises(lambda: agm.build_report("nonesuch", Events()), "unknown"))
            check("build_report: a row with no build yet refuses",
                  _raises(lambda: agm.build_report("ramp_summary", Events()),
                          "cannot be built"))
            with _patch(crl, "inventory", lambda lib_root=None: {"present": {}, "missing": [],
                                                                  "unknown": [], "index": None}):
                check("build_report: missing layers refuse and NAME one",
                      _raises(lambda: agm.build_report("highway_detail", Events()),
                              "SHS Landmark"))
            with _patch(arcgis_layers, "drop_info",
                        lambda lib_root=None: {**DROP, "exported": None}):
                check("build_report: an unknown drop date with no as-of refuses",
                      _raises(lambda: agm.build_report("highway_detail", Events()),
                              "export date is unknown"))
    finally:
        paths.OUTPUT_ROOT = saved_root
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=== ArcGIS Reports-vs-layers matrix ===")
    test_rows_from_registry()
    test_drop_info()
    test_library_and_snapshot_states()
    test_build_cell_records_cache()
    test_guards()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL ARCGIS-MATRIX CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
