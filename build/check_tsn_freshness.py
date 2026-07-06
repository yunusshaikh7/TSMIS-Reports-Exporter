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
  * ensure_current never rebuilds without raw, and never touches an
    unregistered report;
  * the matrix + by-day compare paths stay WIRED to ensure_current (source
    tripwire).

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
        return ConsolidateResult(status="ok", message="stub built",
                                 output_path=str(out_path))

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

        # stale WITHOUT raw -> flagged, never rebuilt from nothing
        for f in rawd.glob("*"):
            f.unlink()
        assert consolidation_meta.write_outcome(
            cons, ok_result, extra={"tsn_normalization_version": spec_version - 1})
        check("stale with NO raw -> no rebuild attempt (None)",
              tsn_library.ensure_current(REPORT) is None and len(builds) == 1)
        check("unregistered report -> None",
              tsn_library.ensure_current("nope") is None)
    finally:
        (tsn_library.raw_dir, tsn_library.consolidated_path,
         tsn_library.importlib) = (saved[0], saved[1],
                                   types.SimpleNamespace(import_module=saved[2]))
        import importlib as _imp
        tsn_library.importlib = _imp

    # the compare paths stay WIRED to the heal (source tripwire)
    for mod in ("matrix.py", "day_matrix.py"):
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
