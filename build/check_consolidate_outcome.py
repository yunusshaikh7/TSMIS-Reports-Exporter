"""CT-2 -- producer-owned consolidation completion + F3 honoring.

Proves the consolidators SET a producer-owned completion (partial when inputs are
left out, complete when all combine, error/no-output is not comparable), and that
the matrix store-consolidation wrapper now RETURNS the ConsolidateResult instead
of discarding it (F3) so a failed/no-data consolidation can't be compared or cached
as fresh.

openpyxl only -- no browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_consolidate_outcome.py
"""
import contextlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import outcome as oc                         # noqa: E402
import consolidation_meta as cm              # noqa: E402
import matrix                                # noqa: E402
from events import ConsolidateResult, Events   # noqa: E402
from consolidate_xlsx_base import consolidate_xlsx   # noqa: E402
from openpyxl import Workbook                # noqa: E402


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)

_SHEET = "Data"
_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


class _LQ:
    """A list-backed worker queue (workers call .put((kind, payload)))."""

    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def _xlsx(path, header, n_rows=2, sheet=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet or _SHEET
    ws.append(header)
    for i in range(n_rows):
        ws.append([f"v{i}"] * len(header))
    wb.save(path)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        # all inputs share the canonical header -> COMPLETE, nothing left out.
        full = tmp / "full"
        full.mkdir()
        _xlsx(full / "r005.xlsx", ["A", "B", "C"])
        _xlsx(full / "r099.xlsx", ["A", "B", "C"])
        r = consolidate_xlsx(input_dir=full, out_path=tmp / "full.xlsx", sheet_name=_SHEET,
                             report_name="Test", title="T", events=Events())
        check("all-good consolidation -> status ok", r.status == "ok")
        check("...completion = complete (producer-owned)", r.completion == oc.COMPLETE)
        check("...no skipped/failed inputs", r.skipped_inputs == 0 and r.failed_inputs == 0)

        # an Excel owner-lock stub (~$foo.xlsx, present whenever a per-route file
        # is open in Excel) must be invisible: NOT an unreadable input, NOT a
        # false PARTIAL (a partial never promotes, so this blocked the pipeline).
        locked = tmp / "locked"
        locked.mkdir()
        _xlsx(locked / "r005.xlsx", ["A", "B", "C"])
        _xlsx(locked / "r099.xlsx", ["A", "B", "C"])
        (locked / "~$r005.xlsx").write_bytes(b"\x00" * 165)   # real stubs are tiny junk
        r = consolidate_xlsx(input_dir=locked, out_path=tmp / "locked.xlsx", sheet_name=_SHEET,
                             report_name="Test", title="T", events=Events())
        check("an Excel ~$ lock stub is ignored -> status ok", r.status == "ok")
        check("...completion stays COMPLETE (no false partial)",
              r.completion == oc.COMPLETE)
        check("...no skipped/failed inputs from the stub",
              r.skipped_inputs == 0 and r.failed_inputs == 0)

        # one file's header disagrees -> it is SKIPPED -> producer-owned PARTIAL.
        part = tmp / "part"
        part.mkdir()
        _xlsx(part / "r005.xlsx", ["A", "B", "C"])
        _xlsx(part / "r099.xlsx", ["A", "B", "C"])
        _xlsx(part / "r101.xlsx", ["A", "B", "DIFFERENT"])    # header mismatch -> skipped
        r = consolidate_xlsx(input_dir=part, out_path=tmp / "part.xlsx", sheet_name=_SHEET,
                             report_name="Test", title="T", events=Events())
        check("a left-out input -> status still ok (file produced)", r.status == "ok")
        check("...completion = partial (producer-owned, not hidden in summary text)",
              r.completion == oc.PARTIAL)
        check("...skipped_inputs counts the left-out file", r.skipped_inputs == 1)

        # empty folder -> error, no output.
        empty = tmp / "empty"
        empty.mkdir()
        r = consolidate_xlsx(input_dir=empty, out_path=tmp / "empty.xlsx", sheet_name=_SHEET,
                             report_name="Test", title="T", events=Events())
        check("empty input -> status error", r.status == "error")
        check("...consolidate_completion_of infers FAILED", oc.consolidate_completion_of(r) == oc.FAILED)
        check("...not comparable (matrix won't compare/cache it)", not oc.comparable(oc.consolidate_completion_of(r)))

        # F3: the matrix store-consolidation wrapper RETURNS the result now
        # (regression: it used to return None and silently discard it).
        store = tmp / "store"
        (store / "ramp_detail").mkdir(parents=True)
        _xlsx(store / "ramp_detail" / "r005.xlsx", ["Route", "PM"])   # 'TSAR - Ramp Detail' sheet differs -> won't read
        res = matrix._consolidate_store_folder("ramp_detail", store / "ramp_detail",
                                               tmp / "store_out.xlsx", Events())
        check("matrix._consolidate_store_folder returns a ConsolidateResult, not None (F3)",
              res is not None and hasattr(res, "status"))

        # --- F3 + R01 orchestration through consolidate_and_compare_tsn ---------
        # A stub comparator that records WHETHER it was invoked and writes a tiny
        # output workbook; a stub store-consolidator returning a chosen outcome.
        print("F3/R01 orchestration (consolidate_and_compare_tsn):")
        called = {"n": 0}

        class _Cmp:
            def compare(self, consolidated, tsn_path, out_path, events=None,
                        confirm_overwrite=None, mode="values"):
                called["n"] += 1
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                _xlsx(out_path, ["A", "B"], n_rows=1, sheet="Comparison")  # valid comparison wb
                return ConsolidateResult(status="ok", verdict="diff", output_path=str(out_path))

        def _stub_consolidate(result, write=True):
            def _f(subdir, store_dir, consolidated, events):
                if write:
                    Path(consolidated).parent.mkdir(parents=True, exist_ok=True)
                    Path(consolidated).write_text("data")     # non-empty: passes the size check
                return result
            return _f

        store_dir = tmp / "tsmis_store"
        store_dir.mkdir()
        tsn = tmp / "tsn.xlsx"; tsn.write_text("tsn")

        # PARTIAL consolidation -> still compares, but the comparison result carries partial.
        called["n"] = 0
        with _patch(matrix, "_consolidated_stale", lambda *a: True), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()), \
             _patch(matrix, "_consolidate_store_folder",
                    _stub_consolidate(ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=1))):
            r = matrix.consolidate_and_compare_tsn(store_dir, str(tsn), tmp / "out1.xlsx",
                                                   "ramp_summary", "ramp_summary", events=None)
        check("partial consolidation INVOKES the comparator", called["n"] == 1)
        check("...and the comparison result carries completion=partial (R01)",
              r.completion == oc.PARTIAL)

        # FAILED consolidation -> does NOT compare (raises), leaving any prior cache intact.
        called["n"] = 0
        with _patch(matrix, "_consolidated_stale", lambda *a: True), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()), \
             _patch(matrix, "_consolidate_store_folder",
                    _stub_consolidate(ConsolidateResult(status="error", message="all inputs failed"),
                                      write=False)):
            try:
                matrix.consolidate_and_compare_tsn(store_dir, str(tsn), tmp / "out2.xlsx",
                                                   "ramp_summary", "ramp_summary", events=None)
                raised = False
            except ValueError:
                raised = True
        check("failed consolidation RAISES (does not compare/cache — keeps stale prior)", raised)
        check("...the comparator was NEVER invoked on the failed consolidation", called["n"] == 0)

        # R01 durability: the partial flag round-trips through the TSN result cache.
        cdest = tmp / "cache_dest"
        matrix.record_tsn_result(cdest, "ramp_summary|tsn", "ars-prod", "diff", 4, 1, 100.0,
                                 completion=oc.PARTIAL)
        rec = matrix.load_tsn_results(cdest).get("ramp_summary|tsn", {}).get("ars-prod", {})
        check("a partial cell is recorded with completion=partial (durable flag)",
              rec.get("completion") == oc.PARTIAL)
        # a legacy record (no completion field) reads as complete via _cmp_state's default.
        state = matrix._cmp_state(tmp / "out1.xlsx",
                                  [{"name": "a", "present": True, "mtime": None}],
                                  {"verdict": "diff", "diff_cells": 4, "one_sided": 1,
                                   "built_at_mtime": matrix._safe_mtime(tmp / "out1.xlsx"),
                                   "completion": oc.PARTIAL})
        check("_cmp_state surfaces the partial completion for the matrix to flag",
              state.get("completion") == oc.PARTIAL)

        # --- P1-R01 round 2: durability across REUSE, self-comparison, snapshot ----
        print("P1-R01 (round 2) sidecar round-trip + mtime guard:")
        cpath = tmp / "rt" / "consolidated" / "c.xlsx"
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_bytes(b"PK")
        cm.write_outcome(
            cpath, ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=2))
        check("sidecar round-trips the partial completion",
              cm.read_completion(cpath) == oc.PARTIAL)
        st = cpath.stat()
        os.utime(cpath, (st.st_atime, st.st_mtime + 1000))    # workbook rebuilt under the meta
        check("an mtime mismatch drops the stale flag (no false partial)",
              cm.read_completion(cpath) is None)

        print("P1-R01 (round 2) REUSE keeps a partial consolidated flagged:")
        store2 = tmp / "reuse" / "store"      # unique PARENT: consolidated_store_path keys off it
        store2.mkdir(parents=True)
        tsn2 = tmp / "tsn2.xlsx"
        tsn2.write_text("tsn")

        def _consolidate_partial(subdir, store_dir, consolidated, events):
            Path(consolidated).parent.mkdir(parents=True, exist_ok=True)
            Path(consolidated).write_text("data")
            cres = ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=1)
            cm.write_outcome(consolidated, cres)                   # the REAL persistence
            return cres

        with _patch(matrix, "_consolidated_stale", lambda *a: True), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()), \
             _patch(matrix, "_consolidate_store_folder", _consolidate_partial):
            r1 = matrix.consolidate_and_compare_tsn(store2, str(tsn2), tmp / "ro1.xlsx",
                                                    "ramp_summary", "ramp_summary", events=None)
        check("first (fresh) build flags partial", r1.completion == oc.PARTIAL)
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            r2 = matrix.consolidate_and_compare_tsn(store2, str(tsn2), tmp / "ro2.xlsx",
                                                    "ramp_summary", "ramp_summary", events=None)
        check("REUSED build (no fresh result) STILL partial — recovered from sidecar",
              r2.completion == oc.PARTIAL)

        print("P1-R01 (round 2) self-comparison propagates a partial side:")
        import compare_highway_log_pdf as _chp

        class _SelfCmp:
            def compare(self, pdf_c, excel_c, out_path, events=None,
                        confirm_overwrite=None, mode="values"):
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                _xlsx(out_path, ["A", "B"], n_rows=1, sheet="Comparison")  # valid comparison wb
                return ConsolidateResult(status="ok", verdict="diff", output_path=str(out_path))

        def _sides(store_dir, subdir, events, force):
            # the PDF side is partial, the Excel side complete -> reduce to partial
            return (matrix.consolidated_store_path(store_dir, subdir),
                    oc.PARTIAL if subdir == "highway_log_pdf" else oc.COMPLETE)

        with _patch(matrix, "_ensure_consolidated", _sides), \
             _patch(_chp, "TSMIS_PDF_VS_EXCEL", _SelfCmp()):
            rself = matrix.build_comparison(tmp / "self_dest", "highway_log", "ars-prod",
                                            "vs_pdf", "ssor-prod", events=None)
        check("self comparison with ONE partial side -> result.completion=partial",
              rself.completion == oc.PARTIAL)

        print("P1-R01 (round 2) snapshot serializes the partial completion:")
        snapdest = tmp / "snapdest"
        (snapdest / "ars-prod" / "highway_log").mkdir(parents=True, exist_ok=True)
        (snapdest / "ars-prod" / "highway_log" / "r1.xlsx").write_bytes(b"PK")
        tdrop = matrix.tsn_input_root(snapdest, "highway_log")
        tdrop.mkdir(parents=True, exist_ok=True)
        (tdrop / "tsn.xlsx").write_bytes(b"PK")
        defs = matrix._row_defs()
        _l, _sub, _i, _adapter, _hr = defs["highway_log"]
        tsn_mode = {m["id"]: m for m in matrix._row_modes("highway_log", _sub, _adapter)}["tsn"]
        out_tsn = matrix.mode_out_path(snapdest, "ssor-prod", "highway_log", "ars-prod", tsn_mode)
        out_tsn.parent.mkdir(parents=True, exist_ok=True)
        out_tsn.write_bytes(b"PK")
        matrix.record_tsn_result(snapdest, "highway_log|tsn", "ars-prod", "diff", 3, 1,
                                 matrix._safe_mtime(out_tsn), completion=oc.PARTIAL)
        snap = matrix.matrix_snapshot(snapdest, baseline_key="ssor-prod",
                                      row_modes={"highway_log": "tsn"})
        cmp_cell = snap["cells"]["highway_log"]["ars-prod"]["cmp"]
        check("snapshot's tsn cell carries completion=partial (durable to the UI)",
              cmp_cell.get("completion") == oc.PARTIAL)

        # --- P1-R01 round 3: fail-safe sidecar + shared-writer persistence --------
        print("P1-R01 (round 3) read_completion degrades safely (never raises):")
        import json as _json
        check("no sidecar -> None (a legacy workbook reads complete)",
              cm.read_completion(tmp / "nope" / "absent.xlsx") is None)
        wbp = tmp / "rob" / "wb.xlsx"
        wbp.parent.mkdir(parents=True, exist_ok=True)
        wbp.write_bytes(b"PK")
        cm.meta_path(wbp).write_text("{ not valid json", encoding="utf-8")
        check("corrupt JSON sidecar -> conservative partial (no raise)",
              cm.read_completion(wbp) == oc.PARTIAL)
        cm.meta_path(wbp).write_text(_json.dumps(
            {"schema_version": cm.SCHEMA_VERSION, "completion": "complete",
             "built_at_mtime": "not-a-number"}), encoding="utf-8")
        check("malformed (non-numeric mtime) sidecar -> partial, NOT a ValueError",
              cm.read_completion(wbp) == oc.PARTIAL)
        cm.meta_path(wbp).write_text(_json.dumps(
            {"schema_version": cm.SCHEMA_VERSION + 99, "completion": "complete",
             "built_at_mtime": 1.0}), encoding="utf-8")
        check("wrong schema_version -> conservative partial (never silently complete)",
              cm.read_completion(wbp) == oc.PARTIAL)

        print("P1-R01 (round 3) write_outcome is atomic + scoped:")
        wok = tmp / "atomic" / "w.xlsx"
        wok.parent.mkdir(parents=True, exist_ok=True)
        wok.write_bytes(b"PK")
        cm.write_outcome(wok, ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=1))
        tmp_side = cm.meta_path(wok).with_name(cm.meta_path(wok).name + ".tmp")
        check("write_outcome leaves no stray .tmp (atomic publish)", not tmp_side.exists())
        check("...and the sidecar reads back partial", cm.read_completion(wok) == oc.PARTIAL)
        wfail = tmp / "atomic" / "f.xlsx"
        wfail.write_bytes(b"PK")
        cm.write_outcome(wfail, ConsolidateResult(status="error", message="x"))
        check("a failed consolidation writes NO sidecar (nothing to flag)",
              not cm.meta_path(wfail).exists())

        print("P1-R01 (round 3) shared writers persist the outcome -> matrix reuse reads it:")
        import gui_worker as _gw
        import queue as _queue
        import threading as _threading
        import types as _types
        from events import RunResult                       # noqa: E402
        # A REAL shared writer (the GUI/console Consolidate tab) writes the SAME reusable
        # workbook the matrix reuses; persisting at write time means the matrix reads its
        # partial on reuse (the bypass Codex reproduced is closed).
        store3 = tmp / "cw" / "store"         # unique PARENT (see store2) so no sidecar collision
        store3.mkdir(parents=True)
        cpath = matrix.consolidated_store_path(store3, "ramp_summary")
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text("data")

        def _fake_consolidate(events=None, confirm_overwrite=None, day=None):
            return ConsolidateResult(status="ok", output_path=str(cpath),
                                     completion=oc.PARTIAL, skipped_inputs=2)

        _gw.ConsolidateWorker(_fake_consolidate, _queue.Queue(),
                              _threading.Event(), lambda _p: True).run()
        check("ConsolidateWorker.run persists the producer outcome beside its workbook",
              cm.read_completion(cpath) == oc.PARTIAL)
        tsn3 = tmp / "tsn3.xlsx"
        tsn3.write_text("tsn")
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            r3 = matrix.consolidate_and_compare_tsn(store3, str(tsn3), tmp / "cw_out.xlsx",
                                                    "ramp_summary", "ramp_summary", events=None)
        check("matrix REUSE of a GUI-Consolidate-written partial reads partial (bypass closed)",
              r3.completion == oc.PARTIAL)

        # ExportWorker._auto_consolidate (the post-export store consolidation) likewise.
        import reports as _reports
        from paths import env_tagged_filename                # noqa: E402
        ac_base = tmp / "ac" / "ssor-prod"
        (ac_base / "consolidated").mkdir(parents=True, exist_ok=True)

        class _ACMod:
            FILENAME = "ramp_summary_consolidated.xlsx"

            def consolidate(self, events=None, confirm_overwrite=None, day=None,
                            input_dir=None, out_path=None):
                Path(out_path).write_text("data")            # a real file -> a real mtime
                return ConsolidateResult(status="ok", output_path=str(out_path),
                                         completion=oc.PARTIAL, skipped_inputs=1)

        ew_ac = _gw.ExportWorker([], _queue.Queue(), _threading.Event(), _threading.Event(),
                                 auto_consolidate=True, out_base=str(ac_base))
        with _patch(_reports, "consolidator_for_spec", lambda s: _ACMod()):
            ew_ac._auto_consolidate(_types.SimpleNamespace(label="Ramp Summary", subdir="ramp_summary"),
                                    RunResult(saved=3), Events())
        ac_file = ac_base / "consolidated" / env_tagged_filename("ramp_summary_consolidated.xlsx", "ssor-prod")
        check("_auto_consolidate persists the producer outcome beside its workbook",
              cm.read_completion(ac_file) == oc.PARTIAL)

        # --- P1-B05 (round 5): the legacy TSN-PDF worker honors a failed producer ----
        print("P1-B05 (round 5) legacy TSN-PDF worker honors a failed producer:")
        import consolidate_tsn_highway_log as _ctsn_mod
        wdest = tmp / "tsnpdf"
        prior = matrix.tsn_input_root(wdest, "highway_log") / "tsn_highway_log_consolidated.xlsx"
        prior.parent.mkdir(parents=True, exist_ok=True)
        prior.write_bytes(b"PRIOR-GOOD")
        lq = _LQ()
        with _patch(_ctsn_mod, "consolidate",
                    lambda **k: ConsolidateResult(status="error", message="parse failed")):
            _gw.MatrixTsnConsolidateWorker(str(wdest), "highway_log", lq, _threading.Event()).run()
        logs = [p for k, p in lq.items if k == "log"]
        md = next(p for k, p in lq.items if k == "matrix_done")
        check("a failed TSN consolidation -> matrix_done errors=1 (not a success terminal)",
              md.get("errors") == 1)
        check("...no 'TSN workbook ready' success log", not any("ready" in str(l) for l in logs))
        check("...the prior consolidated workbook is left UNCHANGED",
              prior.read_bytes() == b"PRIOR-GOOD")

        # --- P1-R01 (round 5): the CONSOLE consolidate routes through the boundary ---
        print("P1-R01 (round 5) console run_consolidate_cli persists the outcome:")
        import cli as _cli
        cc_out = tmp / "cli" / "combined.xlsx"
        cc_out.parent.mkdir(parents=True, exist_ok=True)

        def _cli_consolidate(events=None, confirm_overwrite=None, day=None):
            Path(cc_out).write_text("data")
            return ConsolidateResult(status="ok", output_path=str(cc_out), summary_lines=["x"],
                                     completion=oc.PARTIAL, skipped_inputs=1)

        with _patch(_cli, "_resolve_day_console", lambda: None), \
             _patch(_cli, "setup_logging", lambda: None):
            _cli.run_consolidate_cli(_cli_consolidate)
        check("run_consolidate_cli persists the producer outcome (console bypass closed)",
              cm.read_completion(cc_out) == oc.PARTIAL)

        # --- P1-R01 (round 5): metadata publication failure is fail-safe -------------
        print("P1-R01 (round 5) metadata publication failure / unreadable sidecar fail-safe:")

        def _raise_replace(*_a, **_k):
            raise PermissionError("sidecar locked")

        pf = tmp / "pubfail" / "wb.xlsx"
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text("data")
        with _patch(cm.os, "replace", _raise_replace):
            cm.write_outcome(pf, ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=1))
        pf_tmp = cm.meta_path(pf).with_name(cm.meta_path(pf).name + ".tmp")
        check("publication failure leaves no stray .tmp", not pf_tmp.exists())
        check("...a partial workbook whose flag couldn't publish is NOT reusable-as-complete",
              not pf.exists())                          # removed -> next access rebuilds

        pc = tmp / "pubok" / "wb.xlsx"
        pc.parent.mkdir(parents=True, exist_ok=True)
        pc.write_text("data")
        with _patch(cm.os, "replace", _raise_replace):
            cm.write_outcome(pc, ConsolidateResult(status="ok", completion=oc.COMPLETE))
        check("a COMPLETE workbook survives a publication failure (kept; reads complete)",
              pc.exists() and cm.read_completion(pc) is None)

        ur = tmp / "unread" / "wb.xlsx"
        ur.parent.mkdir(parents=True, exist_ok=True)
        ur.write_bytes(b"PK")
        cm.meta_path(ur).mkdir()                        # a dir at the sidecar path -> open() OSError
        check("present-but-unreadable sidecar -> conservative partial (not None/legacy)",
              cm.read_completion(ur) == oc.PARTIAL)

        # --- P1-R01 (round 6): publication failure OBSERVABLE + durable when unlink fails ---
        print("P1-R01 (round 6) write_outcome reports success/failure to callers:")
        wok = tmp / "ret_ok" / "wb.xlsx"
        wok.parent.mkdir(parents=True, exist_ok=True)
        wok.write_text("d")
        check("a normal partial publish returns True (observable success)",
              cm.write_outcome(wok, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                      skipped_inputs=1)) is True)
        check("a non-ok / falsy-path result returns True (nothing to persist)",
              cm.write_outcome(wok, ConsolidateResult(status="error", message="x")) is True
              and cm.write_outcome(None, ConsolidateResult(status="ok")) is True)

        print("P1-R01 (round 6) publication FAILURE is observable + fail-safe (Windows-lock variant):")

        def _raise_replace2(*_a, **_k):
            raise PermissionError("sidecar locked")

        rf = tmp / "ret_fail" / "wb.xlsx"
        rf.parent.mkdir(parents=True, exist_ok=True)
        rf.write_text("d")
        with _patch(cm.os, "replace", _raise_replace2):
            ok = cm.write_outcome(rf, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                       skipped_inputs=1))
        check("partial publish failure -> write_outcome returns False (observable)", ok is False)

        # publication fails AND the workbook itself can't be removed (the exact Windows lock)
        lk = tmp / "locked" / "wb.xlsx"
        lk.parent.mkdir(parents=True, exist_ok=True)
        lk.write_text("d")
        with _patch(cm.os, "replace", _raise_replace2), _patch(cm, "_silent_unlink", lambda _p: False):
            ok = cm.write_outcome(lk, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                       skipped_inputs=1))
        check("publication+unlink failure -> returns False (observable)", ok is False)
        check("...the workbook is preserved (unlink failed)", lk.exists())
        check("...a durable conservative marker keeps matrix reuse PARTIAL (no false green)",
              cm.read_completion(lk) == oc.PARTIAL)

        ck = tmp / "comp_fail" / "wb.xlsx"
        ck.parent.mkdir(parents=True, exist_ok=True)
        ck.write_text("d")
        with _patch(cm.os, "replace", _raise_replace2):
            ok = cm.write_outcome(ck, ConsolidateResult(status="ok", completion=oc.COMPLETE))
        check("COMPLETE publish failure -> returns True (kept; absent sidecar reads complete)",
              ok is True and ck.exists() and cm.read_completion(ck) is None)

        print("P1-R01 (round 6) CLI + GUI honor the failure (no misleading success):")
        import io as _io
        import contextlib as _ctxlib
        import cli as _cli2
        cli_wb = tmp / "cli6" / "combined.xlsx"
        cli_wb.parent.mkdir(parents=True, exist_ok=True)

        def _cli_part(events=None, confirm_overwrite=None, day=None):
            Path(cli_wb).write_text("data")
            return ConsolidateResult(status="ok", output_path=str(cli_wb),
                                     summary_lines=["FAKE-SUCCESS-SUMMARY 5 routes"],
                                     completion=oc.PARTIAL, skipped_inputs=1)

        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf), \
             _patch(_cli2, "_resolve_day_console", lambda: None), \
             _patch(_cli2, "setup_logging", lambda: None), \
             _patch(cm.os, "replace", _raise_replace2):
            try:
                _cli2.run_consolidate_cli(_cli_part)
                exited = 0
            except SystemExit as se:
                exited = se.code
        out = buf.getvalue()
        check("CLI publication failure -> non-zero exit", exited == 1)
        check("...and does NOT print the success summary", "FAKE-SUCCESS-SUMMARY" not in out)

        gq = _LQ()
        gw_wb = tmp / "gui6" / "combined.xlsx"
        gw_wb.parent.mkdir(parents=True, exist_ok=True)

        def _gui_part(events=None, confirm_overwrite=None, day=None):
            Path(gw_wb).write_text("data")
            return ConsolidateResult(status="ok", output_path=str(gw_wb),
                                     completion=oc.PARTIAL, skipped_inputs=1)

        with _patch(cm.os, "replace", _raise_replace2):
            _gw.ConsolidateWorker(_gui_part, gq, _threading.Event(), lambda _p: True).run()
        gkinds = [k for k, _p in gq.items]
        check("ConsolidateWorker publication failure -> NO success consolidate_done",
              "consolidate_done" not in gkinds)
        check("...emits a degraded error terminal instead", "error" in gkinds)

        # --- P1-R01 (round 7): THREE-WAY failure + ignored-return callers -----------
        print("P1-R01 (round 7) THREE-WAY failure (publish + marker + unlink) stays conservative:")
        tw = tmp / "threeway" / "wb.xlsx"
        tw.parent.mkdir(parents=True, exist_ok=True)
        tw.write_text("data")
        with _patch(cm.os, "replace", _raise_replace2), \
             _patch(cm, "_mark_untrusted", lambda *_a: False), \
             _patch(cm, "_silent_unlink", lambda _p: False):
            ok = cm.write_outcome(tw, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                       skipped_inputs=1))
        tw_tmp = cm.meta_path(tw).with_name(cm.meta_path(tw).name + ".tmp")
        check("three-way failure -> write_outcome returns False (observable)", ok is False)
        check("...the workbook is preserved (unlink failed)", tw.exists())
        check("...no final sidecar was published", not cm.meta_path(tw).is_file())
        check("...the .tmp sentinel is RETAINED (last-resort durable signal)", tw_tmp.is_file())
        check("...read_completion stays PARTIAL (no sidecar-less false green)",
              cm.read_completion(tw) == oc.PARTIAL)

        # subsequent MATRIX reuse of a three-way-failed partial -> the cell records partial
        st7 = tmp / "tw_store" / "store"      # unique PARENT (consolidated_store_path keys off it)
        st7.mkdir(parents=True)
        cp7 = matrix.consolidated_store_path(st7, "ramp_summary")
        cp7.parent.mkdir(parents=True, exist_ok=True)
        cp7.write_text("data")
        with _patch(cm.os, "replace", _raise_replace2), \
             _patch(cm, "_mark_untrusted", lambda *_a: False), \
             _patch(cm, "_silent_unlink", lambda _p: False):
            cm.write_outcome(cp7, ConsolidateResult(status="ok", completion=oc.PARTIAL, skipped_inputs=1))
        tsn7 = tmp / "tsn7.xlsx"
        tsn7.write_text("tsn")
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            r7 = matrix.consolidate_and_compare_tsn(st7, str(tsn7), tmp / "tw_out.xlsx",
                                                    "ramp_summary", "ramp_summary", events=None)
        check("matrix REUSE of a three-way-failed partial -> cell records partial (no false green)",
              r7.completion == oc.PARTIAL)

        print("P1-R01 (round 7) the remaining persistent writers honor a False return:")
        import reports as _reports7
        sf = tmp / "sf_store"
        sf.mkdir()

        class _OKMod7:
            FILENAME = "x.xlsx"

            def consolidate(self, events=None, confirm_overwrite=None, input_dir=None, out_path=None):
                Path(out_path).write_text("data")
                return ConsolidateResult(status="ok", output_path=str(out_path),
                                         completion=oc.PARTIAL, skipped_inputs=1)

        raised_sf = False
        with _patch(_reports7, "consolidator_for_subdir", lambda s: _OKMod7()), \
             _patch(cm, "write_outcome", lambda *a, **k: False):
            try:
                matrix._consolidate_store_folder("ramp_summary", sf, tmp / "sf_out.xlsx", Events())
            except ValueError:
                raised_sf = True
        check("matrix._consolidate_store_folder RAISES when write_outcome returns False", raised_sf)

        # --- P1-R01 (round 8): WRITE-STAGE failure (no valid .tmp) -> quarantine ------
        print("P1-R01 (round 8) write-stage failure (open(tmp) fails -> NO sentinel) -> quarantine:")
        import builtins as _builtins
        st8 = tmp / "ws_store" / "store"      # unique PARENT (consolidated_store_path keys off it)
        st8.mkdir(parents=True)
        cp8 = matrix.consolidated_store_path(st8, "ramp_summary")
        cp8.parent.mkdir(parents=True, exist_ok=True)
        cp8.write_text("data")
        _orig_open = _builtins.open

        def _open_fail(file, *a, **k):        # deny writing THIS workbook's sidecar + .tmp
            if str(file).startswith(str(cp8)):
                raise PermissionError("sidecar dir locked")
            return _orig_open(file, *a, **k)

        with _patch(_builtins, "open", _open_fail), _patch(cm, "_silent_unlink", lambda _p: False):
            ok = cm.write_outcome(cp8, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                        skipped_inputs=1))
        cp8_tmp = cm.meta_path(cp8).with_name(cm.meta_path(cp8).name + ".tmp")
        check("write-stage failure -> write_outcome returns False (observable)", ok is False)
        check("...no .tmp sentinel exists (open(tmp) failed)", not cp8_tmp.exists())
        check("...the workbook is QUARANTINED — canonical path now MISSING (resolver rebuilds)",
              not cp8.exists())
        check("...the data is preserved at the .unverified quarantine name",
              cp8.with_name(cp8.name + ".unverified").is_file())
        # subsequent MATRIX reuse of the (now-missing) canonical workbook -> NOT green:
        tsn8 = tmp / "tsn8.xlsx"
        tsn8.write_text("tsn")
        raised8 = False
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            try:
                matrix.consolidate_and_compare_tsn(st8, str(tsn8), tmp / "ws_out.xlsx",
                                                   "ramp_summary", "ramp_summary", events=None)
            except ValueError:
                raised8 = True
        check("matrix REUSE of a quarantined partial -> not-refreshed (never green)", raised8)

        # --- P1-A01 (round 8): a STALE .tmp sentinel is ignored (mtime-validated) -----
        print("P1-A01 (round 8) a stale .tmp sentinel is mtime-validated, not forced partial:")
        sta = tmp / "stale" / "wb.xlsx"
        sta.parent.mkdir(parents=True, exist_ok=True)
        sta.write_text("newer-data")
        sta_tmp = cm.meta_path(sta).with_name(cm.meta_path(sta).name + ".tmp")
        with open(sta_tmp, "w", encoding="utf-8") as _f:
            _json.dump({"schema_version": cm.SCHEMA_VERSION, "completion": "partial",
                        "built_at_mtime": cm._safe_mtime(sta) - 1000.0}, _f)   # 1000s stale
        check("a valid but demonstrably-stale .tmp sentinel -> ignored (None, not partial)",
              cm.read_completion(sta) is None)
        cur = tmp / "cur" / "wb.xlsx"
        cur.parent.mkdir(parents=True, exist_ok=True)
        cur.write_text("data")
        cur_tmp = cm.meta_path(cur).with_name(cm.meta_path(cur).name + ".tmp")
        with open(cur_tmp, "w", encoding="utf-8") as _f:
            _json.dump({"schema_version": cm.SCHEMA_VERSION, "completion": "partial",
                        "built_at_mtime": cm._safe_mtime(cur)}, _f)            # current
        check("a valid CURRENT .tmp sentinel -> partial", cm.read_completion(cur) == oc.PARTIAL)

        # --- P1-R01 (round 9): an incompatible current 'complete' .tmp must NOT certify a
        #     failed PARTIAL write — it is rejected and the ladder quarantines instead. ---
        print("P1-R01 (round 9) a current 'complete' .tmp cannot certify a failed partial write:")
        import builtins as _b9
        st9 = tmp / "c9_store" / "store"      # unique PARENT (consolidated_store_path keys off it)
        st9.mkdir(parents=True)
        c9 = matrix.consolidated_store_path(st9, "ramp_summary")
        c9.parent.mkdir(parents=True, exist_ok=True)
        c9.write_text("data")
        c9_tmp = cm.meta_path(c9).with_name(cm.meta_path(c9).name + ".tmp")
        with open(c9_tmp, "w", encoding="utf-8") as _f:          # PLANT a valid CURRENT 'complete' tmp
            _json.dump({"schema_version": cm.SCHEMA_VERSION, "completion": "complete",
                        "built_at_mtime": cm._safe_mtime(c9)}, _f)
        _orig_open9 = _b9.open

        def _deny_writes9(file, mode="r", *a, **k):     # deny WRITES to c9's sidecar/tmp; allow READS
            if str(file).startswith(str(c9)) and any(m in mode for m in ("w", "a", "x", "+")):
                raise PermissionError("sidecar dir locked")
            return _orig_open9(file, mode, *a, **k)

        with _patch(_b9, "open", _deny_writes9), _patch(cm, "_silent_unlink", lambda _p: False):
            ok = cm.write_outcome(c9, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                       skipped_inputs=1))
        check("failed partial write -> write_outcome returns False (observable)", ok is False)
        check("...the incompatible 'complete' tmp did NOT certify it — workbook QUARANTINED (missing)",
              not c9.exists())
        check("...the data is preserved at the .unverified quarantine name",
              c9.with_name(c9.name + ".unverified").is_file())
        check("...read_completion never returns the false 'complete'", cm.read_completion(c9) != oc.COMPLETE)
        # the SHARED matrix consumer (Everything build_comparison AND by-day build_day_cell both
        # call consolidate_and_compare_tsn) cannot produce a green match on the quarantined cell:
        tsn9 = tmp / "tsn9.xlsx"
        tsn9.write_text("tsn")
        raised9 = False
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            try:
                matrix.consolidate_and_compare_tsn(st9, str(tsn9), tmp / "c9_out.xlsx",
                                                   "ramp_summary", "ramp_summary", events=None)
            except ValueError:
                raised9 = True
        check("matrix REUSE (Everything + by-day shared path) -> not-refreshed (no green match)", raised9)

        # --- P1-R01 (round 10): a retained partial .tmp DOMINATES a stale 'complete' final ---
        print("P1-R01 (round 10) a partial .tmp dominates a (stale-yet-valid) 'complete' final:")
        import builtins as _b10
        st10 = tmp / "c10_store" / "store"    # unique PARENT (consolidated_store_path keys off it)
        st10.mkdir(parents=True)
        c10 = matrix.consolidated_store_path(st10, "ramp_summary")
        c10.parent.mkdir(parents=True, exist_ok=True)
        c10.write_text("data")
        c10_final = cm.meta_path(c10)
        with open(c10_final, "w", encoding="utf-8") as _f:      # PLANT a valid CURRENT 'complete' FINAL
            _json.dump({"schema_version": cm.SCHEMA_VERSION, "completion": "complete",
                        "built_at_mtime": cm._safe_mtime(c10)}, _f)
        _orig_open10 = _b10.open

        def _deny_final10(file, mode="r", *a, **k):    # deny overwriting the FINAL; allow tmp write + reads
            if str(file) == str(c10_final) and any(m in mode for m in ("w", "a", "x", "+")):
                raise PermissionError("final sidecar locked")
            return _orig_open10(file, mode, *a, **k)

        with _patch(_b10, "open", _deny_final10), \
             _patch(cm.os, "replace", lambda *a, **k: (_ for _ in ()).throw(PermissionError("locked"))), \
             _patch(cm, "_silent_unlink", lambda _p: False):
            ok = cm.write_outcome(c10, ConsolidateResult(status="ok", completion=oc.PARTIAL,
                                                        skipped_inputs=1))
        c10_tmp = c10_final.with_name(c10_final.name + ".tmp")
        check("failed partial write -> write_outcome returns False (observable)", ok is False)
        check("...the conflicting state persists: final 'complete' + tmp 'partial' both present",
              c10_final.is_file() and c10_tmp.is_file())
        check("...read_completion lets the partial .tmp DOMINATE the stale 'complete' final",
              cm.read_completion(c10) == oc.PARTIAL)
        # the SHARED matrix consumer (Everything + by-day) records partial, never a green match:
        tsn10 = tmp / "tsn10.xlsx"
        tsn10.write_text("tsn")
        with _patch(matrix, "_consolidated_stale", lambda *a: False), \
             _patch(matrix, "tsn_comparator_for", lambda rk: _Cmp()):
            r10 = matrix.consolidate_and_compare_tsn(st10, str(tsn10), tmp / "c10_out.xlsx",
                                                     "ramp_summary", "ramp_summary", events=None)
        check("matrix REUSE -> cell records partial (never a green match)", r10.completion == oc.PARTIAL)

        print()
        if _failures:
            print(f"FAILED: {len(_failures)} check(s): {_failures}")
            return 1
        print("ALL CONSOLIDATE-OUTCOME CHECKS PASSED")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
