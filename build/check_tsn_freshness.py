"""Golden check for the TSN library normalization-version freshness (D2).

The library stores ALREADY-NORMALIZED values, so a normalizer fix shipped
without a rebuild silently "looks unfixed" — it happened twice in the field
(v0.17.6, v0.18.3: 43 phantom Intrte-Postmile diffs until a manual Settings
rebuild). D2 stamps every build with the catalog's `normalization_version` and
folds it into `status()["current"]` (fail-safe: an absent/mismatched stamp is
STALE), and `ensure_current()` — called by the matrix/by-day compare paths —
auto-rebuilds a stale library from its retained raw before the comparison
reads it.

Locks:
  * an UNSTAMPED consolidated workbook reads stale (the pre-D2 upgrade case);
  * a WRONG-version stamp reads stale; the matching version reads current;
  * ensure_current rebuilds a stale library through the real build path
    (stamping it), then no-ops once current;
  * a stale consolidated workbook with deleted, unreadable, or ambiguous raw
    returns a typed ERROR and is never compared;
  * the registered not-built/no-raw state retains its existing None/UX contract;
  * the matrix + by-day compare paths consume that error and stop before their
    shared comparison boundary.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsn_freshness.py
"""
import os
import sys
import tempfile
import time
import types
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidation_meta
import day_matrix
import matrix
import matrix_build
import outcome
import tsn_library
from events import ConsolidateResult, Events
from openpyxl import Workbook

_fail = []
REPORT = "ramp_detail"          # a real registered key (statewide xlsx raw)


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


def _wb(path):
    wb = Workbook()
    wb.active.title = "x"
    wb.active.append(["h"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_tsnfresh_"))
    rawd = tmp / "raw"
    cons = tmp / "consolidated" / "tsn_ramp_detail_normalized.xlsx"
    saved = (tsn_library.raw_dir, tsn_library.consolidated_path,
             tsn_library.importlib.import_module)
    tsn_library.raw_dir = lambda r: rawd
    tsn_library.consolidated_path = lambda r: cons
    spec_version = tsn_library.get(REPORT).normalization_version
    builds = []

    def _stub_build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
        builds.append(str(out_path))
        _wb(Path(out_path))
        result = ConsolidateResult(status="ok", message="stub built",
                                   output_path=str(out_path))
        # Production TSN builders must bind the exact raw member names + bytes.
        # The freshness stub models that same mandatory certificate; a bare
        # success result is intentionally non-reusable.
        result.tsn_raw_manifest = tsn_library._raw_manifest(REPORT)
        return result

    stub_mod = types.SimpleNamespace(build_into=_stub_build_into)
    tsn_library.importlib = types.SimpleNamespace(
        import_module=lambda name: stub_mod)
    try:
        # raw present + consolidated FRESHER by mtime, but NO stamp -> stale
        rawd.mkdir(parents=True)
        raw = rawd / "TSN export.xlsx"
        _wb(raw)
        t = time.time()
        os.utime(raw, (t - 100, t - 100))
        _wb(cons)
        os.utime(cons, (t, t))
        st = tsn_library.status(REPORT)
        check("unstamped library reads STALE (fail-safe pre-D2 upgrade)",
              st["current"] is False and st["normalization_current"] is False)

        # a WRONG version stamp -> still stale
        ok_result = ConsolidateResult(status="ok", message="x",
                                      output_path=str(cons))
        assert consolidation_meta.write_outcome(
            cons, ok_result, extra={"tsn_normalization_version": spec_version - 1})
        check("wrong-version stamp reads STALE",
              tsn_library.status(REPORT)["current"] is False)

        # ensure_current: rebuilds through the real path, stamps, then no-ops
        logs = []
        res = tsn_library.ensure_current(REPORT, events=Events(on_log=logs.append))
        check("stale library auto-rebuilds (announced)",
              res is not None and res.status == "ok" and len(builds) == 1
              and any("rebuilding" in m for m in logs), f"logs={logs}")
        check("...the rebuild is STAMPED with the current version",
              consolidation_meta.read_extra(
                  cons, "tsn_normalization_version") == spec_version)
        check("...status now current",
              tsn_library.status(REPORT)["current"] is True)
        check("...ensure_current no-ops once current",
              tsn_library.ensure_current(REPORT) is None and len(builds) == 1)

        raw_bytes = raw.read_bytes()

        # A deleted raw source invalidates even a previously current workbook.
        # This used to return None (the same result as "already current"), after
        # which both matrices proceeded with the stale consolidated bytes.
        for f in rawd.glob("*"):
            f.unlink()
        stale_bytes = cons.read_bytes()
        missing = tsn_library.ensure_current(REPORT)
        check("stale consolidated with DELETED raw -> typed error",
              missing is not None and missing.status == "error"
              and missing.completion == outcome.FAILED
              and missing.failed_inputs == 1
              and "comparison was stopped" in missing.message.lower(),
              getattr(missing, "message", ""))
        check("...never rebuilds from nothing and preserves consolidated bytes",
              len(builds) == 1 and cons.read_bytes() == stale_bytes)

        # Prove both production consumers stop at the typed freshness result;
        # their shared comparator is a tripwire that must remain untouched.
        compares = []
        source = {"kind": "consolidated", "path": str(cons),
                  "mtime": cons.stat().st_mtime}
        saved_matrix_source = matrix.tsn_source
        saved_build_source = matrix_build.tsn_source
        saved_compare = matrix.consolidate_and_compare_tsn
        matrix.tsn_source = lambda *a, **k: dict(source)
        matrix_build.tsn_source = lambda *a, **k: dict(source)
        matrix.consolidate_and_compare_tsn = (
            lambda *a, **k: compares.append("called"))
        try:
            matrix_error = ""
            try:
                matrix_build.build_comparison(
                    tmp / "store", "highway_log", "ssor-prod", "tsn",
                    "ars-prod", Events(), row_defs={
                        "highway_log": (
                            "Highway Log", "highway_log", 0, object(), True)})
            except ValueError as e:
                matrix_error = str(e)
            day_error = ""
            try:
                day_matrix.build_day_cell(
                    "ssor-prod", "2026-07-12", "highway_log",
                    tmp / "store", Events())
            except ValueError as e:
                day_error = str(e)

            legacy = tmp / "legacy-tsn.xlsx"
            _wb(legacy)
            source.clear()
            source.update({"kind": "consolidated", "path": str(legacy),
                           "mtime": legacy.stat().st_mtime, "legacy": True})
            legacy_matrix_error = ""
            try:
                matrix_build.build_comparison(
                    tmp / "store", "highway_log", "ssor-prod", "tsn",
                    "ars-prod", Events(), row_defs={
                        "highway_log": (
                            "Highway Log", "highway_log", 0, object(), True)})
            except ValueError as e:
                legacy_matrix_error = str(e)
            legacy_day_error = ""
            try:
                day_matrix.build_day_cell(
                    "ssor-prod", "2026-07-12", "highway_log",
                    tmp / "store", Events())
            except ValueError as e:
                legacy_day_error = str(e)
        finally:
            matrix.tsn_source = saved_matrix_source
            matrix_build.tsn_source = saved_build_source
            matrix.consolidate_and_compare_tsn = saved_compare
        check("Everything matrix blocks stale consolidated before compare",
              "comparison was stopped" in matrix_error.lower()
              and not compares, matrix_error)
        check("by-day matrix blocks stale consolidated before compare",
              "comparison was stopped" in day_error.lower()
              and not compares, day_error)
        check("Everything matrix blocks legacy/foreign uncertified consolidated",
              "legacy or foreign" in legacy_matrix_error.lower()
              and "comparison was stopped" in legacy_matrix_error.lower()
              and not compares, legacy_matrix_error)
        check("by-day matrix blocks legacy/foreign uncertified consolidated",
              "legacy or foreign" in legacy_day_error.lower()
              and "comparison was stopped" in legacy_day_error.lower()
              and not compares, legacy_day_error)

        # An I/O failure must remain distinguishable from an empty folder.
        saved_probe = tsn_library._raw_probe
        tsn_library._raw_probe = (
            lambda _report: ([], "PermissionError: access is denied"))
        try:
            unreadable = tsn_library.ensure_current(REPORT)
        finally:
            tsn_library._raw_probe = saved_probe
        check("stale consolidated with UNREADABLE raw -> typed error naming I/O",
              unreadable is not None and unreadable.status == "error"
              and "could not be read" in unreadable.message.lower()
              and "permissionerror" in unreadable.message.lower()
              and len(builds) == 1, getattr(unreadable, "message", ""))

        # Exact-one statewide admission: two viable raw workbooks are ambiguous,
        # so no source is selected by name or mtime and the stale artifact is blocked.
        raw.write_bytes(raw_bytes)
        (rawd / "TSN second export.xlsx").write_bytes(raw_bytes)
        ambiguous = tsn_library.ensure_current(REPORT)
        check("stale consolidated with AMBIGUOUS raw -> typed exact-one error",
              ambiguous is not None and ambiguous.status == "error"
              and "found 2" in ambiguous.message.lower()
              and "exactly 1" in ambiguous.message.lower()
              and len(builds) == 1, getattr(ambiguous, "message", ""))

        # Preserve the established first-use experience: without any generated
        # artifact there are no stale bytes to guard, so Settings owns the normal
        # import-and-build guidance and ensure_current remains a no-op.
        for f in rawd.glob("*"):
            f.unlink()
        cons.unlink()
        check("registered NOT-BUILT/no-raw keeps the existing None UX",
              tsn_library.ensure_current(REPORT) is None)
        check("unregistered report -> None",
              tsn_library.ensure_current("nope") is None)
    finally:
        (tsn_library.raw_dir, tsn_library.consolidated_path,
         tsn_library.importlib) = (saved[0], saved[1],
                                   types.SimpleNamespace(import_module=saved[2]))
        import importlib as _imp
        tsn_library.importlib = _imp

    # Keep a small source tripwire in addition to the executable consumer checks.
    for mod in ("matrix_build.py", "day_matrix.py"):   # S4: the compare site moved to the build side
        src = (Path(__file__).resolve().parent.parent / "scripts" / mod
               ).read_text(encoding="utf-8")
        check(f"{mod} calls tsn_library.ensure_current before the TSN compare",
              "ensure_current(" in src)


if __name__ == "__main__":
    print("TSN library normalization-version freshness (D2):")
    main()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")
