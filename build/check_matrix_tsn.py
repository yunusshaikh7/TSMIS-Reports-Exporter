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
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import day_matrix
import matrix
import matrix_state
import paths
import tsn_library
from openpyxl import Workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _touch(p, data=b"PK"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _workbook(p, value="TSN"):
    p.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.active["A1"] = value
    wb.save(p)
    wb.close()
    return p


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
    check("twelve matrix rows — every report (both HL + both Intersection + both "
          "Highway Detail + both Highway Sequence + both Ramp Detail formats, "
          "v0.26.0)",
          set(defs) == {"ramp_summary", "ramp_detail", "highway_sequence",
                        "highway_log", "highway_log_pdf", "intersection_summary",
                        "intersection_detail", "intersection_detail_pdf",
                        "highway_detail", "highway_detail_pdf",
                        "highway_sequence_pdf", "ramp_detail_pdf"})

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
    hsp = modes("highway_sequence_pdf")
    check("HSL PDF row modes: env + tsn + vs_excel, ALL supported (v0.25.0 — the HD-PDF parallel)",
          set(hsp) == {"env", "tsn", "vs_excel"}
          and hsp["env"]["supported"]
          and hsp["tsn"]["supported"] and hsp["vs_excel"]["supported"])
    check("HSL PDF tsn shares the highway_sequence TSN dataset (its Excel sibling)",
          hsp["tsn"]["fmt"] == "pdf" and hsp["tsn"]["tsn_subdir"] == "highway_sequence")
    rdpm = modes("ramp_detail_pdf")
    check("RD PDF row modes: env + tsn + vs_excel, ALL supported (v0.26.0 — the HSL-PDF parallel)",
          set(rdpm) == {"env", "tsn", "vs_excel"}
          and rdpm["env"]["supported"]
          and rdpm["tsn"]["supported"] and rdpm["vs_excel"]["supported"])
    check("RD PDF tsn shares the ramp_detail TSN dataset (its Excel sibling)",
          rdpm["tsn"]["fmt"] == "pdf" and rdpm["tsn"]["tsn_subdir"] == "ramp_detail")

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
    saved_roots = (paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT)
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
    paths.OUTPUT_ROOT = dest / "_out"
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
        picked = _workbook(dest / "elsewhere" / "my_tsn.xlsx")
        selection = tsn_library.create_explicit_selection(picked)
        check("explicit file selection wins",
              matrix.tsn_source(dest, sub, selected_file=selection)["kind"] == "file")
        legacy = matrix.tsn_source(dest, sub, selected_file=str(picked))
        check("a legacy path-only selection requires an explicit re-pick",
              legacy["kind"] == "missing_explicit"
              and legacy.get("selection_reason") == "legacy_identity")

        # Same path + restored mtime is the adversarial replacement that path/mtime
        # persistence cannot see. The content digest/file ID must still reject it.
        old_stat = picked.stat()
        picked.unlink()
        _workbook(picked, "DIFFERENT TSN DATA")
        os.utime(picked, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        replaced = matrix.tsn_source(dest, sub, selected_file=selection)
        check("same-path replacement with restored mtime fails closed",
              replaced["kind"] == "missing_explicit"
              and replaced.get("selection_reason") == "changed")

        fake_xlsx = dest / "elsewhere" / "not-a-workbook.xlsx"
        _touch(fake_xlsx, b"not an Excel workbook")
        try:
            tsn_library.create_explicit_selection(fake_xlsx)
            fake_rejected = False
        except ValueError:
            fake_rejected = True
        check("an existing non-workbook .xlsx is rejected at selection time",
              fake_rejected)
        forged_record = {
            "version": 1, "path": str(fake_xlsx),
            "identity": {"sha256": "0" * 64, "size": fake_xlsx.stat().st_size,
                         "mtime_ns": fake_xlsx.stat().st_mtime_ns,
                         "file_id": "0:0"},
        }
        fake_resolved = matrix.tsn_source(dest, sub, selected_file=forged_record)
        check("a persisted non-workbook .xlsx is rejected again at resolution",
              fake_resolved["kind"] == "missing_explicit"
              and fake_resolved.get("selection_reason") == "not_workbook")
        missing_pick = str(dest / "elsewhere" / "deleted.xlsx")
        missing = matrix.tsn_source(dest, sub, selected_file=missing_pick)
        check("a missing explicit selection fails closed instead of falling back",
              missing["kind"] == "missing_explicit"
              and missing.get("selected_path") == missing_pick
              and not missing.get("path"))
        invalid_pick = str(dest / "nope.pdf")
        invalid = matrix.tsn_source(dest, sub, selected_file=invalid_pick)
        check("an invalid explicit selection also fails closed",
              invalid["kind"] == "missing_explicit"
              and invalid.get("selected_path") == invalid_pick)
        # The canonical TSN library takes precedence over the legacy dest drop.
        lib_cons = paths.tsn_library_consolidated_path(sub, "tsn_highway_log_consolidated.xlsx")
        _touch(lib_cons)
        r = matrix.tsn_source(dest, sub)
        check("library consolidated preferred over the legacy dest drop",
              r["kind"] == "consolidated" and Path(r["path"]) == lib_cons)
    finally:
        paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT = saved_roots
        shutil.rmtree(dest, ignore_errors=True)


def test_stale_app_owned_selection_heals():
    """Field fix (2026-07-22): a MISSING explicit selection that provably named
    the app's OWN generated consolidated workbook in a previous install — the
    legacy dest drop ``…/_tsn_input/<report>/<name>`` or an old install's
    ``…/tsn_library/<report>/consolidated/<name>`` — resolves to the CURRENT
    canonical library with a ``stale_selection_ignored`` note instead of
    blocking the row. EVERYTHING ELSE keeps failing closed: foreign missing
    paths, wrong basenames, app-owned files that still EXIST, and the
    no-canonical-fallback state. Removing the heal branch turns the heal
    assertions red; weakening fail-closed turns the closed assertions red."""
    print("stale app-owned selection heals to the canonical library (field fix):")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsn_stale_"))
    saved_roots = (paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT)
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
    paths.OUTPUT_ROOT = dest / "_out"
    try:
        sub = "highway_log"
        name = "tsn_highway_log_consolidated.xlsx"
        old_install = dest / "old" / "TSMIS Exporter"
        stale_drop = old_install / "output" / "All Reports (current)" / "_tsn_input" / sub / name
        stale_lib = old_install / "tsn_library" / sub / "consolidated" / name

        def record(path):
            return {"version": 1, "path": str(path),
                    "identity": {"sha256": "0" * 64, "size": 1,
                                 "mtime_ns": 1, "file_id": "1:1"}}

        # No canonical library yet: nothing safe to fall back to — stays closed.
        r = matrix.tsn_source(dest, sub, selected_file=record(stale_drop))
        check("app-owned missing pick with NO canonical library stays closed",
              r["kind"] == "missing_explicit" and r.get("selection_reason") == "missing")

        lib_cons = paths.tsn_library_consolidated_path(sub, name)
        _workbook(lib_cons)

        # The field case: the previous install's legacy dest drop.
        r = matrix.tsn_source(dest, sub, selected_file=record(stale_drop))
        check("missing pick at a previous install's _tsn_input drop heals to the library",
              r["kind"] == "consolidated" and Path(r["path"]) == lib_cons)
        check("…and carries the stale_selection_ignored note (path + reason)",
              (r.get("stale_selection_ignored") or {}).get("path") == str(stale_drop)
              and (r.get("stale_selection_ignored") or {}).get("reason") == "missing")

        # An old install's canonical library path heals the same way.
        r = matrix.tsn_source(dest, sub, selected_file=record(stale_lib))
        check("missing pick at a previous install's tsn_library heals too",
              r["kind"] == "consolidated"
              and (r.get("stale_selection_ignored") or {}).get("path") == str(stale_lib))

        # A LEGACY v0 (path-string) record heals only when app-owned AND missing.
        r = matrix.tsn_source(dest, sub, selected_file=str(stale_drop))
        check("a legacy path-only record at the dead app-owned path heals",
              r["kind"] == "consolidated"
              and (r.get("stale_selection_ignored") or {}).get("reason") == "legacy_identity")

        # Fail-closed is untouched everywhere else:
        foreign = dest / "elsewhere" / "deleted.xlsx"
        r = matrix.tsn_source(dest, sub, selected_file=record(foreign))
        check("a foreign missing pick still fails closed",
              r["kind"] == "missing_explicit" and r.get("selection_reason") == "missing")
        odd = stale_drop.parent / "hand-edited-copy.xlsx"
        r = matrix.tsn_source(dest, sub, selected_file=record(odd))
        check("a missing pick under _tsn_input with a NON-canonical basename stays closed",
              r["kind"] == "missing_explicit")
        _workbook(stale_drop)          # the app-owned file EXISTS again…
        r = matrix.tsn_source(dest, sub, selected_file=str(stale_drop))
        check("an app-owned file that still EXISTS keeps requiring a re-pick "
              "(no heal for present-but-untrusted)",
              r["kind"] == "missing_explicit"
              and r.get("selection_reason") == "legacy_identity")
    finally:
        paths.TSN_LIBRARY_ROOT, paths.OUTPUT_ROOT = saved_roots
        shutil.rmtree(dest, ignore_errors=True)


def test_canonical_selection_keys():
    print("canonical explicit-selection keys + all PDF siblings:")
    aliases = {
        "highway_log_pdf": "highway_log",
        "intersection_detail_pdf": "intersection_detail",
        "highway_detail_pdf": "highway_detail",
        "highway_sequence_pdf": "highway_sequence",
        "ramp_detail_pdf": "ramp_detail",
    }
    check("all five PDF export keys canonicalize to their shared TSN dataset",
          all(tsn_library.canonical_dataset_key(alias) == base
              for alias, base in aliases.items()))
    sources = [
        {"name": "cell", "present": True, "mtime": 1.0},
        {"name": "tsn", "present": True, "mtime": 1.0,
         "identity": {"sha256": "a" * 64}, "identity_required": True},
    ]
    # Every record carries a CURRENT producer version (CMP-AUD-084) so the sole
    # differentiator under test is the TSN identity token, not the version gate.
    _pv = matrix.producer_identity()
    legacy_state = matrix._staleness(
        10.0, sources,
        {"built_at_mtime": 10.0, "verdict": "match", "producer_versions": _pv}, (), None)
    matching_state = matrix._staleness(
        10.0, sources,
        {"built_at_mtime": 10.0, "verdict": "match", "producer_versions": _pv,
         "source_identities": {"tsn": {"sha256": "a" * 64}}}, (), None)
    changed_state = matrix._staleness(
        10.0, sources,
        {"built_at_mtime": 10.0, "verdict": "match", "producer_versions": _pv,
         "source_identities": {"tsn": {"sha256": "b" * 64}}}, (), None)
    check("explicit identity gates cached truth (legacy/different stale; matching fresh)",
          legacy_state["stale"] and changed_state["stale"]
          and not matching_state["stale"])

    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnaliases_"))
    saved_lib = paths.TSN_LIBRARY_ROOT
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
    try:
        selections = {}
        picked_paths = {}
        for alias, base in aliases.items():
            picked = _workbook(dest / f"{base}.xlsx", base)
            selections[base] = tsn_library.create_explicit_selection(picked)
            picked_paths[base] = str(picked.resolve())
            picked.unlink()

        row_modes = {alias: "tsn" for alias in aliases}
        snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod",
                                      row_modes=row_modes, tsn_files=selections)
        check("each PDF row exposes the shared deleted explicit selection",
              all(snap["tsn_meta"][alias]["source_kind"] == "missing_explicit"
                  and snap["tsn_meta"][alias]["selection_missing"] is True
                  and snap["tsn_meta"][alias]["selected_path"] == picked_paths[base]
                  for alias, base in aliases.items()))

        # A legacy PDF-keyed setting must be migrated to the base key and block;
        # it must never be ignored in favor of an available canonical fallback.
        fallback = paths.tsn_library_consolidated_path(
            "highway_log", "tsn_highway_log_consolidated.xlsx")
        _touch(fallback)
        legacy_path = str(dest / "legacy-deleted.xlsx")
        legacy_snap = matrix.matrix_snapshot(
            dest, baseline_key="ssor-prod",
            row_modes={"highway_log_pdf": "tsn"},
            tsn_files={"highway_log_pdf": legacy_path})
        meta = legacy_snap["tsn_meta"]["highway_log_pdf"]
        check("legacy PDF-keyed explicit selection cannot silently fall back",
              meta["source_kind"] == "missing_explicit"
              and meta["selected_path"] == legacy_path
              and meta["selection_reason"] == "legacy_identity")
    finally:
        paths.TSN_LIBRARY_ROOT = saved_lib
        shutil.rmtree(dest, ignore_errors=True)


def test_snapshot_modes():
    print("snapshot per-row mode + greyed cells + scoped rebuild:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnsnap_"))
    # HERMETIC: tsn_source consults the CANONICAL library too — on a dev PC whose
    # real tsn_library/<report>/raw is stocked (e.g. the Highway Log district
    # prints, which double as its evidence source), the un-sandboxed snapshot
    # would see "pdfs" where this fixture stages a legacy-drop "consolidated".
    saved_lib = paths.TSN_LIBRARY_ROOT
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
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
        # CMP-AUD-105: a persisted explicit pick is an instruction, not a hint.
        # Even with the canonical/legacy TSN source above available, deleting the
        # picked file must block this row and keep a clearable UI state.
        missing_pick = str(dest / "deleted-explicit.xlsx")
        missing_snap = matrix.matrix_snapshot(
            dest, baseline_key="ssor-prod", row_modes={"highway_log": "tsn"},
            tsn_files={"highway_log": missing_pick})
        missing_meta = missing_snap["tsn_meta"]["highway_log"]
        missing_cell = missing_snap["cells"]["highway_log"]["ars-prod"]["cmp"]
        check("snapshot exposes a durable missing-explicit selection",
              missing_meta["source_kind"] == "missing_explicit"
              and missing_meta.get("selected_path") == missing_pick
              and missing_meta.get("selection_missing") is True)
        check("missing explicit selection blocks the TSN side and rebuild target",
              missing_cell.get("missing_side") == "tsn"
              and ("highway_log", "ars-prod", "tsn") not in
              matrix.cells_to_rebuild(missing_snap, scope="all"))
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
        paths.TSN_LIBRARY_ROOT = saved_lib
        shutil.rmtree(dest, ignore_errors=True)


def test_missing_side_both():
    print("CMP-AUD-097: a comparison cell with >1 absent side reports 'both':")
    NO = "/no/such/comparison.xlsx"
    both = matrix._cmp_state(
        NO, [{"name": "cell", "present": False, "mtime": None},
             {"name": "baseline", "present": False, "mtime": None}], None)
    check("neither side present -> missing_side 'both' (reaches the UI 'both' branch)",
          both.get("missing_side") == "both")
    one = matrix._cmp_state(
        NO, [{"name": "cell", "present": True, "mtime": 1.0},
             {"name": "baseline", "present": False, "mtime": None}], None)
    check("exactly one absent side -> that side's own name (unchanged)",
          one.get("missing_side") == "baseline")
    # the actionable single-missing TSN token is preserved (renderer shows 'needs TSN')
    tsn = matrix._cmp_state(
        NO, [{"name": "cell", "present": True, "mtime": 1.0},
             {"name": "tsn", "present": False, "mtime": None}], None)
    check("single missing tsn side keeps its 'tsn' token",
          tsn.get("missing_side") == "tsn")


def test_build_guards():
    print("build_comparison guard paths:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnbuild_"))
    # HERMETIC like test_snapshot_modes: the no-TSN-source guard must not see a
    # stocked real library.
    saved_lib = paths.TSN_LIBRARY_ROOT
    paths.TSN_LIBRARY_ROOT = dest / "_lib"
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
        # Plant an automatic fallback, then point the persisted override at a
        # deleted file. The build must name the explicit selection instead of
        # silently comparing the fallback dataset.
        _touch(matrix.tsn_input_root(dest, "highway_log") / "fallback.xlsx")
        missing_pick = str(dest / "deleted-explicit.xlsx")
        try:
            matrix.build_comparison(
                dest, "highway_log", "ars-prod", "tsn", "ssor-prod", events=None,
                tsn_files={"highway_log": missing_pick})
            missing_message = ""
        except ValueError as e:
            missing_message = str(e)
        check("build names the missing explicit source with re-pick/clear guidance",
              "selected TSN" in missing_message and "re-pick" in missing_message.lower()
              and "clear" in missing_message.lower())
    finally:
        paths.TSN_LIBRARY_ROOT = saved_lib
        shutil.rmtree(dest, ignore_errors=True)


def test_support_derives_from_registry():
    """CMP-AUD-013: every matrix mode's `supported` DERIVES from the comparison
    registry — the 'tsn' modes from tsn_comparator_for, the 'self' modes from
    _pdf_self_comparator — in BOTH matrix_state._row_modes and day_matrix._day_rows.
    So patching the registry flips the mode + the by-day row. A hand-written True
    (the pre-fix state, which left Highway Log + all five PDF rows supported even
    with tsn_supported False) shadows the registry and fails this guard."""
    print("CMP-AUD-013 support-parity (registry is the single source of truth):")
    HL, HDP, RDP = "highway_log", "highway_detail_pdf", "ramp_detail_pdf"

    def mode_of(row_key, subdir, kind):
        for m in matrix._row_modes(row_key, subdir, object()):
            if m["kind"] == kind:
                return m
        return None

    def day_supported(row_key):
        return {r[0]: r[4] for r in day_matrix._day_rows()}.get(row_key)

    # Baseline (no-op): every tsn + self mode and every by-day row is supported.
    check("baseline: highway_detail_pdf tsn mode supported",
          mode_of(HDP, "highway_detail", "tsn")["supported"])
    check("baseline: ramp_detail_pdf self mode supported",
          mode_of(RDP, "ramp_detail", "self")["supported"])
    check("baseline: every by-day row supported",
          all(r[4] for r in day_matrix._day_rows()))

    # Negative mutation on the TSN registry: the mode + the by-day row must flip,
    # while an unpatched row stays supported.
    saved_tsn = matrix_state.tsn_comparator_for
    try:
        matrix_state.tsn_comparator_for = lambda rk: None if rk == HDP else saved_tsn(rk)
        check("patch tsn_comparator_for(highway_detail_pdf)->None flips its tsn mode",
              mode_of(HDP, "highway_detail", "tsn")["supported"] is False)
        check("...and flips the by-day highway_detail_pdf row",
              day_supported(HDP) is False)
        check("...while highway_log stays supported (mode + by-day row)",
              mode_of(HL, "highway_log", "tsn")["supported"] and day_supported(HL) is True)
    finally:
        matrix_state.tsn_comparator_for = saved_tsn

    # Negative mutation on the self (PDF-vs-Excel) registry: the self mode must flip.
    saved_self = matrix_state._pdf_self_comparator

    def _stub_self(pdf_subdir):
        if pdf_subdir == RDP:
            raise ValueError("stubbed: no self comparator")
        return saved_self(pdf_subdir)

    try:
        matrix_state._pdf_self_comparator = _stub_self
        check("stub _pdf_self_comparator(ramp_detail_pdf)->raise flips its self mode",
              mode_of(RDP, "ramp_detail", "self")["supported"] is False)
        check("...while highway_log_pdf self mode stays supported",
              mode_of("highway_log_pdf", "highway_log_pdf", "self")["supported"])
    finally:
        matrix_state._pdf_self_comparator = saved_self

    # Registry fully restored afterward.
    check("registry restored after mutation",
          mode_of(HDP, "highway_detail", "tsn")["supported"]
          and mode_of(RDP, "ramp_detail", "self")["supported"])


def main():
    test_paths_and_modes()
    test_source_detection()
    test_stale_app_owned_selection_heals()
    test_canonical_selection_keys()
    test_snapshot_modes()
    test_missing_side_both()
    test_build_guards()
    test_support_derives_from_registry()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
