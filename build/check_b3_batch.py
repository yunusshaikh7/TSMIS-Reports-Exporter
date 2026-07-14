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
    m = batch_manifest.build(["ramp_summary", "highway_log"],
                             [("ssor", "prod"), ("ars", "prod")],
                             fast=False, workers=1, auto_consolidate=True)
    check("build: v2 version", m["version"] == 2)
    check("build: reports kept as export-op KEYS",
          m["reports"] == ["ramp_summary", "highway_log"])
    check("build: all steps pending",
          len(m["steps"]) == 2 and all(s["status"] == "pending" for s in m["steps"]))
    batch_manifest.save(m, p)
    check("save wrote the file", p.is_file())
    check("atomic save left no .tmp behind", not p.with_name(p.name + ".tmp").exists())
    check("load round-trips", batch_manifest.load(p)["steps"] == m["steps"])
    check("load keeps the KEYS",
          batch_manifest.load(p)["reports"] == ["ramp_summary", "highway_log"])
    check("pending = both", batch_manifest.pending(batch_manifest.load(p))
          == [("ssor", "prod"), ("ars", "prod")])
    batch_manifest.mark_done(m, "ssor", "prod", p)
    check("mark_done persists (1 left)",
          batch_manifest.pending(batch_manifest.load(p)) == [("ars", "prod")])
    check("not complete with one pending", not batch_manifest.is_complete(batch_manifest.load(p)))
    batch_manifest.mark_done(m, "ars", "prod", p)
    check("complete when all done", batch_manifest.is_complete(batch_manifest.load(p)))

    # v1 (legacy) manifest: in-range integer indices migrate to export-op KEYS via
    # the FROZEN v0.17 order, and load() presents the manifest as v2 so the next save
    # rewrites it forward (F7).
    v1 = {"version": 1, "reports": [0, 3, 6], "fast": False, "workers": 1,
          "auto_consolidate": False, "dest": "", "created": "",
          "steps": [{"src": "ssor", "env": "prod", "status": "pending"}]}
    p.write_text(json.dumps(v1), encoding="utf-8")
    loaded = batch_manifest.load(p)
    check("v1 loads and is presented as v2", loaded is not None and loaded["version"] == 2)
    check("v1 in-range int indices -> keys via the frozen order",
          loaded["reports"] == ["ramp_summary", "highway_log", "intersection_detail"])
    # An out-of-range/invalid legacy index is NOT silently dropped: it maps 1:1 to the
    # poison sentinel so the all-or-nothing resolver rejects the whole saved set
    # (P3-B01) rather than running a narrower batch.
    p.write_text(json.dumps(dict(v1, reports=[0, 99])), encoding="utf-8")
    check("v1 out-of-range index -> poison kept 1:1 (not dropped)",
          batch_manifest.load(p)["reports"] == ["ramp_summary", batch_manifest._INVALID_KEY])

    p.write_text("{ this is not json", encoding="utf-8")
    check("corrupt file -> None", batch_manifest.load(p) is None)
    p.write_text(json.dumps({"version": 999, "steps": []}), encoding="utf-8")
    check("unsupported version -> None", batch_manifest.load(p) is None)
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
    import gui_export_api                       # S1: the batch endpoints' home
    bm = gui_export_api.batch_manifest
    saved = (bm.save, bm.load, bm.clear, gui_export_api.BatchWorker)
    bm.save = lambda m, path=None: store.__setitem__("m", m)
    bm.load = lambda path=None: store["m"]
    bm.clear = lambda path=None: store.__setitem__("m", None)
    gui_export_api.BatchWorker = _FakeBatchWorker
    _FakeBatchWorker.instances = []
    try:
        a = gui_api.GuiApi()
        check("env-key parse (valid, de-duped, bad dropped)",
              a._parse_env_keys(["ssor-prod", "ars-prod", "bad-x", "ssor-prod"])
              == [("ssor", "prod"), ("ars", "prod")])
        check("no reports -> error",
              a.start_batch_export([], ["ssor-prod"], False, 1).get("error"))
        check("an unknown report KEY -> error (rejected, not mis-resolved)",
              a.start_batch_export(["__nope__"], ["ssor-prod"], False, 1).get("error"))
        check("no environments -> error",
              a.start_batch_export(["ramp_summary"], [], False, 1).get("error"))

        res = a.start_batch_export(["ramp_summary", "highway_log"],
                                   ["ssor-prod", "ars-prod"], False, 1, True)
        check("valid start -> ok", res.get("ok"))
        check("manifest saved with 2 steps",
              store["m"] and len(store["m"]["steps"]) == 2)
        check("manifest persisted KEYS, not indices",
              store["m"]["reports"] == ["ramp_summary", "highway_log"])
        check("auto_consolidate recorded", store["m"]["auto_consolidate"] is True)
        check("BatchWorker launched", len(_FakeBatchWorker.instances) == 1)
        check("task claimed as 'batch'", a._task == "batch")
        check("second start refused while running",
              a.start_batch_export(["ramp_summary"], ["ssor-prod"], False, 1).get("error"))
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
        bm.save, bm.load, bm.clear, gui_export_api.BatchWorker = saved


def test_reset_scopes_batch_dest():
    print("reset_targets scopes the Export Everything store to known <src-env> children:")
    import gui_worker
    import settings
    dest = Path(tempfile.mkdtemp(prefix="tsmis_store_"))
    import owned_dir
    owned_dir.ensure_owned_dir(dest / "ssor-prod", kind="store")
    owned_dir.ensure_owned_dir(dest / "ars-test", kind="store")
    owned_dir.ensure_owned_dir(dest / "comparisons", kind="comparisons")
    (dest / "ssor-prod" / "ramp_detail").mkdir()
    (dest / "ars-test" / "consolidated").mkdir()
    (dest / "comparisons" / "ssor-prod").mkdir()
    (dest / "My Personal Files").mkdir()                       # foreign — keep
    (dest / "important.txt").write_text("keep me", encoding="utf-8")  # foreign — keep
    saved = settings.get_batch_dest
    settings.get_batch_dest = lambda: str(dest)
    try:
        paths = [p for _label, p in gui_worker.reset_targets()]
    finally:
        settings.get_batch_dest = saved
    check("known ssor-prod child targeted", (dest / "ssor-prod") in paths)
    check("known ars-test child targeted", (dest / "ars-test") in paths)
    check("matrix comparisons child targeted", (dest / "comparisons") in paths)
    check("the store ROOT itself is never a target (no wholesale rmtree)",
          dest not in paths)
    check("foreign folder left untouched", (dest / "My Personal Files") not in paths)
    check("foreign file left untouched", (dest / "important.txt") not in paths)


def test_swap_store_dir():
    print("Export-Everything store stage-and-swap (clear-on-success):")
    from gui_worker import _swap_store_dir
    base = Path(tempfile.mkdtemp(prefix="tsmis_swap_"))
    # Refresh over an existing last-good copy: staged replaces live entirely.
    live = base / "ramp_detail"
    staged = base / "ramp_detail.staging"
    live.mkdir()
    (live / "old_route_001.xlsx").write_text("OLD", encoding="utf-8")
    staged.mkdir()
    (staged / "new_route_002.xlsx").write_text("NEW", encoding="utf-8")
    _swap_store_dir(live, staged)
    check("swap: fresh file present in live", (live / "new_route_002.xlsx").exists())
    check("swap: stale file removed", not (live / "old_route_001.xlsx").exists())
    check("swap: staging dir consumed", not staged.exists())

    # First refresh (no live yet): staging is promoted to live.
    live2 = base / "highway_sequence"
    staged2 = base / "highway_sequence.staging"
    staged2.mkdir()
    (staged2 / "hs_route_001.xlsx").write_text("X", encoding="utf-8")
    _swap_store_dir(live2, staged2)
    check("first refresh: staging promoted to live", (live2 / "hs_route_001.xlsx").exists())
    check("first refresh: staging dir gone", not staged2.exists())


def main():
    test_manifest_module()
    test_gui_api_batch()
    test_reset_scopes_batch_dest()
    test_swap_store_dir()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL B3 BATCH CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
