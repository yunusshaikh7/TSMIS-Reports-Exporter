"""U2 (v0.19.0): direct tests of the gui_endpoint envelope — the pieces every
js_api endpoint rides.

  * `_api_method` — an uncaught exception becomes a structured {"error": ...}
    (a windowed exe has no stderr; a dead Promise would hang the UI), the
    traceback is logged, and a failing `_emit_log` mirror can't mask the error.
  * `_task_endpoint(kind)` — claims the single-task gate BEFORE the body
    (B8's soft-busy exclusion lives in _claim_task_error), refuses when busy,
    and passes through the body's return when claimed.
  * `pick_path` / `pick_paths` — the ONE dialog-unwrap point: list/tuple/str
    returns all normalize; cancel -> None / [].

Pure Python; no window, no browser. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_gui_endpoint.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

logging.disable(logging.CRITICAL)      # the error-path test logs a traceback

from gui_endpoint import _api_method, _task_endpoint, pick_path, pick_paths

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


class _Host:
    """A minimal endpoint host: the gate + the log mirror the envelope touches."""
    def __init__(self, busy=None, emit_raises=False):
        self._busy = busy              # a claim-error dict, or None (free)
        self._emit_raises = emit_raises
        self.emitted = []
        self.claims = []

    def _emit_log(self, text):
        if self._emit_raises:
            raise RuntimeError("emit is broken")
        self.emitted.append(text)

    def _claim_task_error(self, kind):
        self.claims.append(kind)
        return self._busy

    @_api_method
    def ok_endpoint(self, x):
        return {"ok": True, "x": x}

    @_api_method
    def boom_endpoint(self):
        raise ValueError("kaboom")

    @_task_endpoint("export")
    def gated_endpoint(self, x):
        return {"ok": True, "x": x}


def test_api_method():
    print("_api_method — the structured-error envelope:")
    h = _Host()
    check("a healthy endpoint passes its return through",
          h.ok_endpoint(7) == {"ok": True, "x": 7})
    res = h.boom_endpoint()
    check("an uncaught exception becomes {'error': ...} (never a raise to JS)",
          isinstance(res, dict) and "ValueError: kaboom" in res.get("error", ""),
          str(res))
    check("...and the error is mirrored into the GUI log",
          any("kaboom" in e for e in h.emitted))
    h2 = _Host(emit_raises=True)
    res2 = h2.boom_endpoint()
    check("a BROKEN log mirror can't mask the structured error",
          isinstance(res2, dict) and "kaboom" in res2.get("error", ""))
    check("the wrapper keeps the endpoint's __name__ (the bridge exposes by name)",
          _Host.ok_endpoint.__name__ == "ok_endpoint")


def test_task_endpoint():
    print("_task_endpoint — claim-first gating:")
    h = _Host()
    check("free gate: claims the kind then runs the body",
          h.gated_endpoint(1) == {"ok": True, "x": 1} and h.claims == ["export"])
    busy = _Host(busy={"error": "A task is already running."})
    res = busy.gated_endpoint(1)
    check("busy gate: the claim error returns and the body never runs",
          res == {"error": "A task is already running."})
    check("...through the _api_method envelope too (name preserved)",
          _Host.gated_endpoint.__name__ == "gated_endpoint")


class _Win:
    def __init__(self, result):
        self._result = result
        self.calls = []

    def create_file_dialog(self, kind, **kw):
        self.calls.append((kind, kw))
        return self._result


def test_pickers():
    print("pick_path / pick_paths — the one dialog-unwrap point:")
    check("list result -> first path as str",
          pick_path(_Win(["C:/a.xlsx", "C:/b.xlsx"]), 1) == "C:/a.xlsx")
    check("tuple result -> first path as str",
          pick_path(_Win(("C:/a.xlsx",)), 1) == "C:/a.xlsx")
    check("bare-string result -> unchanged", pick_path(_Win("C:/a.xlsx"), 1) == "C:/a.xlsx")
    check("cancel (None) -> None", pick_path(_Win(None), 1) is None)
    check("cancel (empty tuple) -> None", pick_path(_Win(()), 1) is None)
    check("multi: list -> list of strs",
          pick_paths(_Win(["a", "b"]), 1) == ["a", "b"])
    check("multi: bare string -> one-item list", pick_paths(_Win("a"), 1) == ["a"])
    check("multi: cancel -> []", pick_paths(_Win(None), 1) == [])
    w = _Win(["x"])
    pick_path(w, 7, directory="D:/")
    check("kwargs pass through to create_file_dialog",
          w.calls == [(7, {"directory": "D:/"})])


def main():
    test_api_method()
    test_task_endpoint()
    test_pickers()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        return 1
    print("\nall good")
    return 0


if __name__ == "__main__":
    sys.exit(main())
