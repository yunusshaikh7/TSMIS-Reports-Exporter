"""Golden check for W1 one-click validation (scripts/validation.py + the
evidence-bundle integration).

Locks the automated work-PC ride-along: run_validation processes the on-disk
samples through the REAL matrix comparison path, records COUNTS/OUTCOMES/folder
NAMES only (never report data — RM05), degrades instead of crashing on a bad
family, honors should_cancel between cells, and evidence.collect ships the
manifest as validation.txt + validation.json in the credential-safe bundle.

Stdlib + openpyxl; no browser, no network. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_validation.py
"""
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_ROOT, "scripts"), _ROOT]   # scripts + repo root (version.py)

import evidence
import outcome
import validation
from events import ConsolidateResult, Events

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


class _Patch:
    def __init__(self, obj, name, value):
        self.obj, self.name, self.value = obj, name, value

    def __enter__(self):
        self.old = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *a):
        setattr(self.obj, self.name, self.old)


def _store(root, rows_per_env):
    """A fake Export-Everything store: {env: [subdir, ...]} -> files on disk."""
    for env, subs in rows_per_env.items():
        for sub in subs:
            d = root / env / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / "route_001.xlsx").write_bytes(b"PK\x03\x04data")


def test_manifest_and_cancel():
    print("validation manifest — real pipeline, counts only, cancellable:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_val_"))
    dest = tmp / "store"
    _store(dest, {"ssor-prod": ["highway_log"], "ssor-dev": ["highway_log"]})

    calls = []

    def fake_build(dest_, row, env, mode, baseline, events, **kw):
        calls.append((row, env, mode))
        return ConsolidateResult(status="ok", completion=outcome.COMPLETE,
                                 output_path=str(dest / "cmp.xlsx"))

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", fake_build), \
         _Patch(_matrix, "read_counts", lambda p: (969, 0)), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())

    ran = man["comparisons"]["cells"]
    check("both envs' comparisons ran through matrix.build_comparison",
          [(c["row"], c["env"]) for c in ran]
          == [("highway_log", "ssor-dev"), ("highway_log", "ssor-prod")]
          or sorted((c["row"], c["env"]) for c in ran)
          == [("highway_log", "ssor-dev"), ("highway_log", "ssor-prod")])
    check("counts recorded (969 diff cells), status ok",
          all(c.get("diff_cells") == 969 and c["status"] == "ok" for c in ran))
    check("totals tally", man["totals"]["comparisons_ok"] == 2
          and man["totals"]["comparisons_run"] == 2)

    # a manifest carries NO report data — only counts / names / outcomes
    blob = json.dumps(man)
    check("manifest is credential-safe (no route payload, only counts/names)",
          "route_001" not in blob and "PK" not in blob)

    # cancel after the first cell
    seen = {"n": 0}

    def cancel_after_one():
        seen["n"] += 1
        return seen["n"] > 1

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", fake_build), \
         _Patch(_matrix, "read_counts", lambda p: (1, 0)), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man2 = validation.run_validation(events=Events(),
                                         should_cancel=cancel_after_one)
    check("should_cancel stops the run early",
          man2["totals"]["cancelled"] is True
          and any(c.get("skipped") == "cancelled" for c in man2["comparisons"]["cells"]))


def test_degrades_on_family_error():
    print("validation degrades (records) a failing family, never crashes:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_valerr_"))
    dest = tmp / "store"
    _store(dest, {"ssor-prod": ["highway_log"]})

    def boom(*a, **k):
        raise RuntimeError("adapter exploded")

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports
    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", boom), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())
    cell = man["comparisons"]["cells"][0]
    check("a raising adapter is recorded as an error cell (not a crash)",
          cell["status"] == "error" and "RuntimeError" in cell["message"])
    check("totals count the failure", man["totals"]["comparisons_failed"] == 1)


def test_evidence_carries_manifest():
    print("evidence.collect ships validation.txt + validation.json:")
    man = {
        "generated": "now",
        "environment": {"app_version": "0.19.0", "build": "dev", "python": "3.11",
                        "platform": "x", "site": "ssor-prod", "playwright_pin": "1.60.0"},
        "tsn_library": [{"report": "highway_log", "raw_count": 3,
                         "consolidated_present": True, "current_before": True,
                         "healed": None, "current_after": True,
                         "normalization_version": 2}],
        "comparisons": {"dest_name": "store", "baseline": "ssor-prod",
                        "cells": [{"row": "highway_log", "env": "ssor-prod",
                                   "status": "ok", "completion": "complete",
                                   "diff_cells": 969, "one_sided": 0, "seconds": 4.2}]},
        "totals": {"comparisons_run": 1, "comparisons_ok": 1, "comparisons_failed": 0,
                   "cancelled": False, "seconds": 5.0},
    }
    out = Path(tempfile.mkdtemp(prefix="tsmis_valev_")) / "ev.zip"
    res = evidence.collect(out_path=out, emit=lambda l: None,
                           run_self_test=False, validation=man)
    check("bundle built ok", res.get("ok"))
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        check("validation.txt + validation.json in the bundle",
              "validation.txt" in names and "validation.json" in names)
        digest = z.read("validation.txt").decode()
        check("digest is human-readable (names/counts, no raw data)",
              "app v0.19.0" in digest and "969" in digest and "route_001" not in digest)
        rt = json.loads(z.read("validation.json"))
        check("json round-trips the manifest", rt["totals"]["comparisons_ok"] == 1)


def test_worker_always_posts_terminal():
    """The ValidationWorker MUST post exactly one validate_done no matter what
    fails — an un-posted terminal wedges the single-task gate. Drive it with an
    evidence.collect that RAISES (the path outside the old try/except)."""
    print("ValidationWorker guarantees a terminal (gate-safety):")
    import queue as _queue
    import gui_worker
    import validation as _val
    import evidence as _ev

    q = _queue.Queue()
    with _Patch(_val, "run_validation", lambda events=None, should_cancel=None: {"totals": {}}), \
         _Patch(_ev, "collect", lambda **k: (_ for _ in ()).throw(RuntimeError("bundle boom"))):
        w = gui_worker.ValidationWorker(q)
        w.run()   # synchronous run (no .start()) so the queue is fully drained
    kinds = []
    while not q.empty():
        kinds.append(q.get_nowait()[0])
    terminals = [k for k in kinds if k == "validate_done"]
    check("a raising evidence.collect still posts exactly one validate_done",
          len(terminals) == 1, f"terminals={terminals} all={kinds}")


if __name__ == "__main__":
    print("W1 one-click validation:")
    test_manifest_and_cancel()
    test_degrades_on_family_error()
    test_evidence_carries_manifest()
    test_worker_always_posts_terminal()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")
