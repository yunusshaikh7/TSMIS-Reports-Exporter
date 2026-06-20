"""Golden check for B2 — auto-consolidate on export finish (v0.12.0).

Covers reports.consolidator_for_spec (the export-subdir -> consolidate-module map,
None only for the export-only Highway Log (PDF) — every other report, incl. both
Intersection reports, has a consolidator as of v0.17.0) and ExportWorker._auto_consolidate
(runs inline with the right run-folder day + silent overwrite, skips export-only
reports and empty runs, and is non-fatal on a consolidator error).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_b2_autoconsolidate.py
"""
import queue as queue_mod
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import reports
import gui_worker
import consolidate_ramp_summary
import consolidate_ramp_detail
import consolidate_highway_sequence
import consolidate_highway_log
import consolidate_intersection_detail
import consolidate_intersection_summary
from events import Events, RunResult, ConsolidateResult

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


class _FakeSpec:
    def __init__(self, label, subdir):
        self.label, self.subdir = label, subdir


def _drain_log(q):
    out = []
    while not q.empty():
        kind, payload = q.get()
        if kind == "log":
            out.append(payload)
    return "\n".join(out)


def test_mapping():
    print("reports.consolidator_for_spec:")
    expect = {
        "ramp_summary": consolidate_ramp_summary,
        "ramp_detail": consolidate_ramp_detail,
        "highway_sequence": consolidate_highway_sequence,
        "highway_log": consolidate_highway_log,
        "intersection_detail": consolidate_intersection_detail,   # v0.17.0
        "intersection_summary": consolidate_intersection_summary,  # v0.17.0
    }
    for _label, _fmt, spec in reports.EXPORT_REPORTS:
        got = reports.consolidator_for_spec(spec)
        if spec.subdir in expect:
            check(f"{spec.subdir} -> its consolidator", got is expect[spec.subdir])
        else:
            check(f"{spec.subdir} (export-only) -> None", got is None)


def _worker():
    return gui_worker.ExportWorker([], queue_mod.Queue(), threading.Event(),
                                   threading.Event(), auto_consolidate=True)


def test_runs_with_day_and_overwrite():
    print("_auto_consolidate runs the consolidator (day + silent overwrite):")
    seen = {}

    class FakeMod:
        def consolidate(self, events=None, confirm_overwrite=None, day=None,
                        input_dir=None, out_path=None):
            seen["day"] = day
            seen["overwrite"] = confirm_overwrite("x.xlsx")
            return ConsolidateResult(status="ok",
                                     summary_lines=["FAKE: combined 5 routes"])

    orig = reports.consolidator_for_spec
    reports.consolidator_for_spec = lambda spec: FakeMod()
    try:
        w = _worker()
        out_dir = str(Path("Z:/x/output/2026-06-16 ssor-prod/ramp_summary"))
        res = RunResult(output_dir=out_dir, saved=3)
        w._auto_consolidate(_FakeSpec("Ramp Summary", "ramp_summary"), res, Events())
        logs = _drain_log(w.q)
        check("day derived from the run folder", seen.get("day") == "2026-06-16 ssor-prod")
        check("overwrites silently (confirm -> True)", seen.get("overwrite") is True)
        check("announces the report", "Auto-consolidating Ramp Summary" in logs)
        check("logs the consolidator summary", "combined 5 routes" in logs)
    finally:
        reports.consolidator_for_spec = orig


def test_skips_and_is_nonfatal():
    print("_auto_consolidate skips export-only / empty runs and survives errors:")
    orig = reports.consolidator_for_spec

    # Export-only report (no consolidator, e.g. Highway Log (PDF)): skipped, nothing run.
    reports.consolidator_for_spec = lambda spec: None
    try:
        w = _worker()
        w._auto_consolidate(_FakeSpec("Highway Log (PDF)", "highway_log_pdf"),
                            RunResult(output_dir="x", saved=4), Events())
        check("export-only report is skipped (logged)",
              "no consolidator" in _drain_log(w.q).lower())

        # Has a consolidator, but nothing was saved -> skipped.
        called = {"n": 0}

        class FakeMod:
            def consolidate(self, **k):
                called["n"] += 1
                return ConsolidateResult(status="ok")

        reports.consolidator_for_spec = lambda spec: FakeMod()
        w = _worker()
        w._auto_consolidate(_FakeSpec("Ramp Summary", "ramp_summary"),
                            RunResult(output_dir="x", saved=0), Events())
        check("empty run skips consolidation (not called)", called["n"] == 0)
        check("empty run logs the skip", "nothing to combine" in _drain_log(w.q).lower())

        # Consolidator raises -> logged, never propagated (export already succeeded).
        class BoomMod:
            def consolidate(self, **k):
                raise RuntimeError("boom")

        reports.consolidator_for_spec = lambda spec: BoomMod()
        w = _worker()
        raised = False
        try:
            w._auto_consolidate(_FakeSpec("Ramp Summary", "ramp_summary"),
                                RunResult(output_dir="x", saved=1), Events())
        except Exception:
            raised = True
        check("a consolidator error does NOT propagate", not raised)
        check("the error is logged", "failed" in _drain_log(w.q).lower())
    finally:
        reports.consolidator_for_spec = orig


def test_auto_consolidate_into_dest():
    print("_auto_consolidate targets the always-current destination (out_base):")
    seen = {}

    class FakeMod:
        FILENAME = "highway_log_consolidated.xlsx"

        def consolidate(self, events=None, confirm_overwrite=None, day=None,
                        input_dir=None, out_path=None):
            seen.update(day=day, input_dir=str(input_dir), out_path=str(out_path))
            return ConsolidateResult(status="ok", summary_lines=["ok"])

    orig = reports.consolidator_for_spec
    reports.consolidator_for_spec = lambda spec: FakeMod()
    try:
        w = gui_worker.ExportWorker([], queue_mod.Queue(), threading.Event(),
                                    threading.Event(), auto_consolidate=True,
                                    out_base="Z:/x/All Reports (current)/ssor-prod")
        w._auto_consolidate(_FakeSpec("Highway Log", "highway_log"),
                            RunResult(output_dir="", saved=2), Events())
        norm = lambda s: (s or "").replace("\\", "/")
        check("dest mode uses day=None", seen.get("day") is None)
        check("input_dir = <dest>/<src-env>/<subdir>",
              norm(seen.get("input_dir")).endswith("/ssor-prod/highway_log"))
        # The combined workbook in the always-current store is env-labeled too
        # (front-stamped with the <src-env> tag), so a file lifted out still
        # says which environment it came from — see paths.env_tagged_filename.
        check("out_path = <dest>/<src-env>/consolidated/<src-env FILENAME>",
              norm(seen.get("out_path")).endswith(
                  "/ssor-prod/consolidated/ssor-prod highway_log_consolidated.xlsx"))
    finally:
        reports.consolidator_for_spec = orig


def main():
    test_mapping()
    test_runs_with_day_and_overwrite()
    test_skips_and_is_nonfatal()
    test_auto_consolidate_into_dest()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL B2 AUTO-CONSOLIDATE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
