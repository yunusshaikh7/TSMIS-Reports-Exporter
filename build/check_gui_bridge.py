"""Standalone regression checks for the WS5 GUI-bridge hardening.

Pure Python (imports the real gui_api + pywebview, but launches no window) --
run with the build venv from the repo root:

    build\\.venv\\Scripts\\python.exe build\\check_gui_bridge.py

Covers the v0.11 bridge fixes:
  * _try_claim_task single-flight (atomic check-and-set task gate)
  * _pick_report bounds-checking (out-of-range / non-numeric indices)
  * _safe_day rejects traversal / unknown run folders
  * _resolve_under_output rejects paths escaping OUTPUT_ROOT
  * start_reset server-side confirm token (no/ wrong / mismatched token refused)
  * start_consolidate validates the index BEFORE claiming the task slot
    (a bad index must not wedge the task gate)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_api  # noqa: E402
import paths  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def test_pick_report():
    print("registry bounds-check (_pick_report):")
    G = gui_api.GuiApi
    reg = [("a", 1), ("b", 2)]
    check("valid index", G._pick_report(reg, 1) == ("b", 2))
    check("float index coerced", G._pick_report(reg, 1.0) == ("b", 2))
    check("out-of-range -> None", G._pick_report(reg, 9) is None)
    check("negative -> None", G._pick_report(reg, -1) is None)
    check("non-numeric -> None", G._pick_report(reg, "x") is None)
    check("None -> None", G._pick_report(reg, None) is None)


def test_path_validation():
    print("day / folder traversal validation:")
    G = gui_api.GuiApi
    check("empty day -> None", G._safe_day("") is None)
    check("None day -> None", G._safe_day(None) is None)
    raised = False
    try:
        G._safe_day("../../Windows")
    except ValueError:
        raised = True
    check("traversal day rejected", raised)
    raised = False
    try:
        G._safe_day("not a real run folder zzz")
    except ValueError:
        raised = True
    check("unknown run folder rejected", raised)

    raised = False
    try:
        G._resolve_under_output("../../etc")
    except ValueError:
        raised = True
    check("resolve_under_output rejects escape", raised)
    p = G._resolve_under_output("2026-06-11 ssor-prod")
    check("resolve_under_output stays under OUTPUT_ROOT",
          str(p).startswith(str(paths.OUTPUT_ROOT.resolve())))


def test_single_flight():
    print("task gate single-flight:")
    a = gui_api.GuiApi()
    check("first claim wins", a._try_claim_task("export") is True)
    check("second claim rejected while busy", a._try_claim_task("compare") is False)
    a._release_task()
    check("claim succeeds after release", a._try_claim_task("consolidate") is True)
    a._release_task()


def test_reset_token():
    print("reset server-side confirm token:")
    a = gui_api.GuiApi()
    prev = a.reset_preview(False)
    check("preview issues a token", bool(prev.get("token")))
    # No token -> refused.
    check("start_reset without token refused",
          a.start_reset(False, None).get("error") is not None)
    # Token is single-use: reissue, then a mismatched include_input is refused.
    prev = a.reset_preview(False)
    check("mismatched include_input refused",
          a.start_reset(True, prev["token"]).get("error") is not None)
    # A stale (already-consumed) token is refused.
    prev = a.reset_preview(False)
    tok = prev["token"]
    a.start_reset(False, "wrong-token")          # consumes the issued token
    check("replayed/stale token refused",
          a.start_reset(False, tok).get("error") is not None)


def test_consolidate_index_before_claim():
    print("start_consolidate validates index before claiming the slot:")
    a = gui_api.GuiApi()
    # A bad index must return an error AND leave the task slot free (not wedged).
    res = a.start_consolidate(999, "")
    check("bad index returns an error", res.get("error") is not None)
    check("task slot left free after a bad index", a._try_claim_task("x") is True)
    a._release_task()


def main():
    test_pick_report()
    test_path_validation()
    test_single_flight()
    test_reset_token()
    test_consolidate_index_before_claim()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL GUI-BRIDGE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
