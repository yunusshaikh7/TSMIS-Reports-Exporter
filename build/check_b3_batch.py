"""Golden check for B3 — Export Everything batch engine (v0.12.0).

Covers the persistent manifest (build / atomic save / load / pending / mark_done /
is_complete / clear, plus corrupt- and wrong-shape tolerance) and the GuiApi
bridge methods (start_batch_export validation + manifest write + worker launch,
resume_batch, discard_batch, env-key parsing, resumable-batch detection). The
BatchWorker is stubbed so no real export runs.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_b3_batch.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import batch_manifest
import gui_api

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_manifest_module():
    print("batch_manifest (explicit temp path):")
    p = Path(tempfile.mkdtemp(prefix="tsmis_bm_")) / "batch_job.json"
    m = batch_manifest.build([0, 3], [("ssor", "prod"), ("ars", "prod")],
                             fast=False, workers=1, auto_consolidate=True)
    check("build: reports kept", m["reports"] == [0, 3])
    check("build: all steps pending",
          len(m["steps"]) == 2 and all(s["status"] == "pending" for s in m["steps"]))
    batch_manifest.save(m, p)
    check("save wrote the file", p.is_file())
    check("atomic save left no .tmp behind", not p.with_name(p.name + ".tmp").exists())
    check("load round-trips", batch_manifest.load(p)["steps"] == m["steps"])
    check("pending = both", batch_manifest.pending(batch_manifest.load(p))
          == [("ssor", "prod"), ("ars", "prod")])
    batch_manifest.mark_done(m, "ssor", "prod", p)
    check("mark_done persists (1 left)",
          batch_manifest.pending(batch_manifest.load(p)) == [("ars", "prod")])
    check("not complete with one pending", not batch_manifest.is_complete(batch_manifest.load(p)))
    batch_manifest.mark_done(m, "ars", "prod", p)
    check("complete when all done", batch_manifest.is_complete(batch_manifest.load(p)))

    p.write_text("{ this is not json", encoding="utf-8")
    check("corrupt file -> None", batch_manifest.load(p) is None)
    p.write_text(json.dumps({"version": 999, "steps": []}), encoding="utf-8")
    check("wrong version -> None", batch_manifest.load(p) is None)
    batch_manifest.clear(p)
    check("clear removes the file", not p.exists())
    check("load when missing -> None", batch_manifest.load(p) is None)


class _FakeBatchWorker:
    instances = []

    def __init__(self, manifest, q, cancel, skip, pause):
        self.manifest = manifest
        _FakeBatchWorker.instances.append(self)

    def start(self):
        self.started = True


def test_gui_api_batch():
    print("GuiApi batch bridge (stubbed worker, in-memory manifest):")
    store = {"m": None}
    bm = gui_api.batch_manifest
    saved = (bm.save, bm.load, bm.clear, gui_api.BatchWorker)
    bm.save = lambda m, path=None: store.__setitem__("m", m)
    bm.load = lambda path=None: store["m"]
    bm.clear = lambda path=None: store.__setitem__("m", None)
    gui_api.BatchWorker = _FakeBatchWorker
    _FakeBatchWorker.instances = []
    try:
        a = gui_api.GuiApi()
        check("env-key parse (valid, de-duped, bad dropped)",
              a._parse_env_keys(["ssor-prod", "ars-prod", "bad-x", "ssor-prod"])
              == [("ssor", "prod"), ("ars", "prod")])
        check("no reports -> error",
              a.start_batch_export([], ["ssor-prod"], False, 1).get("error"))
        check("no environments -> error",
              a.start_batch_export([0], [], False, 1).get("error"))

        res = a.start_batch_export([0, 3], ["ssor-prod", "ars-prod"], False, 1, True)
        check("valid start -> ok", res.get("ok"))
        check("manifest saved with 2 steps",
              store["m"] and len(store["m"]["steps"]) == 2)
        check("auto_consolidate recorded", store["m"]["auto_consolidate"] is True)
        check("BatchWorker launched", len(_FakeBatchWorker.instances) == 1)
        check("task claimed as 'batch'", a._task == "batch")
        check("second start refused while running",
              a.start_batch_export([0], ["ssor-prod"], False, 1).get("error"))
        snap = a._state_snapshot()
        check("snapshot carries batch + batch_resume keys",
              "batch" in snap and "batch_resume" in snap)

        a._end_task()                       # simulate the run finishing
        check("a saved (still-pending) batch is resumable", a._pending_batch() is not None)
        check("resume -> ok", a.resume_batch().get("ok"))
        check("resume launched the worker again", len(_FakeBatchWorker.instances) == 2)

        a._end_task()
        a.discard_batch()
        check("discard clears the manifest", store["m"] is None)
        check("nothing resumable after discard", a._pending_batch() is None)
        check("resume with nothing -> error", a.resume_batch().get("error"))
    finally:
        bm.save, bm.load, bm.clear, gui_api.BatchWorker = saved


def main():
    test_manifest_module()
    test_gui_api_batch()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL B3 BATCH CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
