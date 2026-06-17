"""Golden check for B1 — Pause/Resume (v0.12.0).

The engine holds BETWEEN routes while paused and resumes (or, if cancelled while
paused, stops cleanly). Pause is wired through Events.is_paused (default no-op),
honored by both the sequential and the parallel engines, and toggled from the GUI
via GuiApi.pause_or_resume (which also clears on cancel and at end-of-task so a
paused state never leaks across runs).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_b1_pause.py
"""
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import events as events_mod
import exporter
import exporter_parallel
import gui_api

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_events_is_paused():
    print("Events.is_paused wiring:")
    check("default is_paused() is False", events_mod.Events().is_paused() is False)
    check("custom is_paused() reflected",
          events_mod.Events(is_paused=lambda: True).is_paused() is True)
    check("parallel engine shares the one _wait_while_paused helper",
          exporter_parallel._wait_while_paused is exporter._wait_while_paused)


def _elapsed(fn):
    t0 = time.monotonic()
    fn()
    return time.monotonic() - t0


def test_wait_while_paused():
    print("_wait_while_paused holds, resumes, and yields to cancel:")
    # Not paused -> returns essentially immediately.
    e = events_mod.Events(is_paused=lambda: False)
    check("not paused -> returns at once",
          _elapsed(lambda: exporter._wait_while_paused(e)) < 0.1)

    # Paused AND cancelled -> must NOT hang (cancel wins).
    e2 = events_mod.Events(is_paused=lambda: True, is_cancelled=lambda: True)
    check("paused + cancelled -> returns at once (no hang)",
          _elapsed(lambda: exporter._wait_while_paused(e2)) < 0.2)

    # Paused, then resumed from another thread -> holds, then releases.
    state = {"paused": True}
    e3 = events_mod.Events(is_paused=lambda: state["paused"])
    threading.Timer(0.3, lambda: state.__setitem__("paused", False)).start()
    held = _elapsed(lambda: exporter._wait_while_paused(e3))
    check("held while paused then released on resume (0.2s < t < 3s)",
          0.2 < held < 3.0)


def test_gui_api_pause_toggle():
    print("GuiApi.pause_or_resume toggle + lifecycle:")
    a = gui_api.GuiApi()
    # No export running -> refused, nothing set.
    res = a.pause_or_resume()
    check("no export -> error", isinstance(res, dict) and res.get("error"))
    check("no export -> pause_event stays clear", not a.pause_event.is_set())

    a._task = "export"                       # pretend an export is running
    a.pause_or_resume()
    check("first toggle pauses", a.pause_event.is_set())
    check("snapshot reports paused=True", a._state_snapshot()["paused"] is True)
    a.pause_or_resume()
    check("second toggle resumes", not a.pause_event.is_set())
    check("snapshot reports paused=False", a._state_snapshot()["paused"] is False)

    # Cancel while paused clears the hold so the worker unblocks and stops.
    a.pause_event.set()
    a.cancel_run()
    check("cancel clears the pause hold", not a.pause_event.is_set())

    # End-of-task never leaks a paused state into the next run.
    a._task = "export"
    a.pause_event.set()
    a._end_task()
    check("_end_task clears the pause hold", not a.pause_event.is_set())


def main():
    test_events_is_paused()
    test_wait_while_paused()
    test_gui_api_pause_toggle()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL B1 PAUSE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
