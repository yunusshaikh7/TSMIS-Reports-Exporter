"""CT -- batch env completion-gating (P1-B02) + fresh-staging exists anomaly (P1-B03).

Producer-path tests that run the REAL BatchWorker.run / ExportWorker._run_specs
with stubbed seams (no browser/network), proving:
  * an environment is marked DONE only when every selected report is complete; a
    partial / no_data / failed report leaves it PENDING (so a resume re-pulls it),
    and batch_done carries the aggregate completion;
  * an in-store run that reports 'exists' files in a FRESH staging dir is rejected
    (non-promotable): the swap is NOT called and last-good is preserved.

Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_batch_outcome.py
"""
import contextlib
import dataclasses
import sys
import tempfile
import threading
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import gui_worker as gw                 # noqa: E402
import gui_api as ga                    # noqa: E402
import outcome as oc                    # noqa: E402
from events import RunResult            # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


class _Q:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def _spec(label, subdir):
    return types.SimpleNamespace(label=label, subdir=subdir)


@dataclasses.dataclass
class _RealSpec:
    """A minimal dataclass spec for the REAL _run_specs path (it does
    dataclasses.replace(spec, filename=...) for the env-tagged store names)."""
    label: str
    subdir: str
    filename: object = dataclasses.field(default=lambda r: f"r{r}.xlsx")


def _rr(saved=0, empty=0, skipped=0, failed=0, exists=0):
    return RunResult(saved=saved, empty=["e"] * empty, user_skipped=["s"] * skipped,
                     failed=["f"] * failed, exists=["x"] * exists)


def _run_batch(report_results):
    """Run BatchWorker over ONE env whose reports yield `report_results`. Returns
    (marked_done_envs, batch_done_payload)."""
    q = _Q()
    manifest = {"steps": [{"src": "ssor", "env": "prod", "status": "pending"}],
                "dest": None, "fast": False, "workers": 1, "auto_consolidate": False}
    w = gw.BatchWorker(manifest, q, threading.Event(), threading.Event(), threading.Event())
    specs = [_spec(f"R{i}", f"sub{i}") for i in range(len(report_results))]
    w._specs = lambda: specs
    w._step_views = lambda *_a: []
    marked = []

    def rs(_self, _e, results):
        for s, r in zip(specs, report_results):
            results.append((s, r))

    with _patch(gw.ExportWorker, "_run_specs", rs), \
         _patch(gw, "set_site", lambda *_a: None), \
         _patch(gw, "get_site", lambda: ("ssor", "prod")), \
         _patch(gw.batch_manifest, "mark_done", lambda _m, s, e: marked.append((s, e))), \
         _patch(gw.batch_manifest, "is_complete", lambda _m: bool(marked)):
        w.run()
    bd = next((p for k, p in q.items if k == "batch_done"), {})
    return marked, bd


def _run_instore(run_result, auto=False):
    """Run ExportWorker._run_specs for ONE report into a STORE (out_base set), with
    run_export stubbed to `run_result` and the swap stubbed. With auto=True the B2
    auto-consolidate is enabled and captured (P1-B03). Returns (result, swaps, cons)
    where `cons` is the list of (completion, artifact) the auto-consolidate saw."""
    q = _Q()
    spec = _RealSpec("Ramp Summary", "ramp_summary")
    dest = Path(tempfile.mkdtemp())
    ew = gw.ExportWorker([spec], q, threading.Event(), threading.Event(),
                         out_base=dest / "ssor-prod", auto_consolidate=auto)
    swaps, cons = [], []
    ew._auto_consolidate = lambda s, r, e: cons.append((r.completion, r.artifact))
    with _patch(gw, "run_export", lambda *_a, **_k: run_result), \
         _patch(gw, "_swap_store_dir", lambda live, staged: swaps.append((live, staged))):
        results = []
        ew._run_specs(ew._build_events(), results)
    import shutil
    shutil.rmtree(dest, ignore_errors=True)
    return results[0][1], swaps, cons


def _lifecycle_api():
    """A GuiApi with the window / auth / UI seams stubbed so a batch lifecycle can run
    offline (no real auth-file touch, no window). Read terminal events from a._out."""
    a = ga.GuiApi()
    for name in ("_refresh_auth", "_push_state", "_try_start_next_matrix_job",
                 "_flash_taskbar", "_pending_batch", "_emit_log", "_set_dot",
                 "_emit_modal"):
        setattr(a, name, lambda *aa, **kk: None)
    return a


def _last_run_ended(a):
    last = None
    while not a._out.empty():
        ev = a._out.get()
        if ev.get("t") == "run_ended":
            last = ev
    return last or {}


def _b02_no_stale_leak():
    """P1-B02 (round 2): a failed batch must NOT publish a previous batch's success.
    Drives the REAL GuiApi terminal lifecycle — success, then start-clears, then a
    failed (auth) run — and asserts the second run_ended cannot reuse the first."""
    print("P1-B02 (round 2) -- a failed run cannot reuse a prior success's outcome:")
    fake_manifest = {"steps": [{"src": "ars", "env": "test", "status": "pending"}],
                     "fast": False, "workers": 1}

    class _FakeBatchWorker:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

    a = _lifecycle_api()
    # Run 1: a successful batch finishes -> run_ended complete/promoted.
    a._task = "batch"
    with _patch(ga.batch_manifest, "clear", lambda: None):
        a._on_batch_done({"complete": True, "done": 1, "total": 1, "completion": oc.COMPLETE})
    re1 = _last_run_ended(a)
    check("run 1 (success) -> run_ended completion=complete", re1.get("completion") == oc.COMPLETE)
    check("...the success outcome is retained for run_ended", a._last_batch_outcome is not None)

    # Run 2 STARTS via the real resume path -> the previous outcome MUST be cleared.
    with _patch(ga, "BatchWorker", _FakeBatchWorker), \
         _patch(ga.batch_manifest, "load", lambda: fake_manifest), \
         _patch(ga.batch_manifest, "pending", lambda _m: fake_manifest["steps"]):
        a.resume_batch()
    check("starting/resuming a new batch CLEARS the prior outcome (P1-B02)",
          a._last_batch_outcome is None)

    # Run 2 FAILS via the error terminal path (auth) -> _end_task with no current outcome.
    while not a._out.empty():
        a._out.get()
    with _patch(ga, "clear_auth", lambda: None):
        a._on_error(("auth", "session expired"))
    re2 = _last_run_ended(a)
    check("run 2 (failed) -> run_ended is NOT the prior success", re2.get("completion") != oc.COMPLETE)
    check("...it is failed / previous_preserved",
          re2.get("completion") == oc.FAILED and re2.get("artifact") == oc.PREVIOUS_PRESERVED)


def _b02_two_env_partial():
    """P1-B02 (round 3, narrowed): a TWO-env batch where env1 completes (+persisted) and
    env2 hits a fatal auth error must end PARTIAL (not wholly failed), leaving env2
    resumable. Drives the REAL BatchWorker, then replays its queue through a REAL GuiApi
    terminal lifecycle — exactly the path Codex reproduced as wrongly 'failed'."""
    print("P1-B02 (round 3) -- env1 complete then env2 fatal -> partial + env2 resumable:")
    q = _Q()
    manifest = {"steps": [{"src": "ssor", "env": "prod", "status": "pending"},
                          {"src": "ars", "env": "prod", "status": "pending"}],
                "dest": None, "fast": False, "workers": 1, "auto_consolidate": False}
    w = gw.BatchWorker(manifest, q, threading.Event(), threading.Event(), threading.Event())
    spec = _spec("R1", "sub1")
    w._specs = lambda: [spec]
    w._step_views = lambda *_a: []
    calls = {"n": 0}

    def rs(_self, _e, results):
        calls["n"] += 1
        if calls["n"] == 1:
            results.append((spec, _rr(saved=5)))             # env1 complete
        else:
            raise gw.AuthError("session expired")            # env2 fatal terminal

    def _mark(m, s, e):
        for st in m["steps"]:
            if st["src"] == s and st["env"] == e:
                st["status"] = "done"

    with _patch(gw.ExportWorker, "_run_specs", rs), \
         _patch(gw, "set_site", lambda *_a: None), \
         _patch(gw, "get_site", lambda: ("ssor", "prod")), \
         _patch(gw.batch_manifest, "mark_done", _mark), \
         _patch(gw.batch_manifest, "is_complete",
                lambda m: all(s["status"] == "done" for s in m["steps"])):
        w.run()
    check("env1 marked done, env2 left PENDING (resumable)",
          manifest["steps"][0]["status"] == "done" and manifest["steps"][1]["status"] == "pending")
    kinds = [k for k, _p in q.items]
    check("the worker emitted an error terminal (no batch_done on the fatal path)",
          "error" in kinds and "batch_done" not in kinds)

    # Replay the worker's queue through a REAL GuiApi terminal lifecycle.
    a = _lifecycle_api()
    a._task = "batch"
    with _patch(ga, "clear_auth", lambda: None):
        for kind, payload in q.items:
            a._handle(kind, payload)
    re = _last_run_ended(a)
    check("the batch terminal is PARTIAL (env1's work completed), not wholly failed",
          re.get("completion") == oc.PARTIAL)
    check("...artifact = previous_preserved", re.get("artifact") == oc.PREVIOUS_PRESERVED)


def main():
    print("P1-B02 -- a batch env is DONE only when every report is complete:")
    marked, bd = _run_batch([_rr(saved=5)])
    check("one complete report -> env marked done", marked == [("ssor", "prod")])
    check("...batch_done.completion = complete", bd.get("completion") == oc.COMPLETE)

    marked, bd = _run_batch([_rr(saved=3, failed=1)])
    check("a partial report -> env NOT marked done (left pending)", marked == [])
    check("...batch_done.completion = partial", bd.get("completion") == oc.PARTIAL)

    marked, bd = _run_batch([_rr(empty=9)])
    check("a no_data report -> env NOT marked done", marked == [])

    marked, _ = _run_batch([_rr(saved=5), _rr(saved=2, failed=1)])
    check("mixed complete + partial reports -> env NOT marked done", marked == [])

    marked, _ = _run_batch([_rr(saved=5), _rr(saved=2)])
    check("all reports complete -> env marked done", marked == [("ssor", "prod")])

    print("P1-B03 -- a fresh-staging 'exists' anomaly is rejected, not promoted:")
    result, swaps, _ = _run_instore(_rr(exists=1))      # saved=0, exists=1 in fresh staging
    check("in_store + exists -> completion forced to failed (non-promotable)",
          result.completion == oc.FAILED)
    check("...the store swap was NOT called (last-good preserved)", swaps == [])
    check("...artifact = previous_preserved", result.artifact == oc.PREVIOUS_PRESERVED)

    result, swaps, _ = _run_instore(_rr(saved=5))       # a normal complete refresh
    check("control: a complete in_store run DOES promote (swap called)",
          result.completion == oc.COMPLETE and len(swaps) == 1)
    check("...artifact = promoted", result.artifact == oc.PROMOTED)

    print("P1-B03 (round 2) -- a partial store refresh does NOT auto-consolidate stale live data:")
    _r, _s, cons = _run_instore(_rr(saved=3, failed=1), auto=True)   # partial -> kept last-good
    check("partial store refresh -> auto-consolidate NOT invoked (no stale rebuild)", cons == [])
    _r, _s, cons = _run_instore(_rr(exists=1), auto=True)            # exists anomaly -> failed
    check("rejected 'exists' store refresh -> auto-consolidate NOT invoked", cons == [])
    _r, _s, cons = _run_instore(_rr(saved=5), auto=True)            # complete -> promoted
    check("complete promoted refresh -> auto-consolidate IS invoked",
          cons == [(oc.COMPLETE, oc.PROMOTED)])

    _b02_no_stale_leak()
    _b02_two_env_partial()

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL BATCH-OUTCOME / EXISTS-ANOMALY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
