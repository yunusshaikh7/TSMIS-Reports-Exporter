"""Golden check for the P7b GUI mechanical extraction: the pywebview façade surface
stays IDENTICAL, the Win32/ctypes helpers moved to gui_win32, and the two compare
endpoints share one claim->dialog->launch tail.

Two halves:
  * SURFACE IDENTITY (RM08) — GuiApi's public method set (the methods pywebview exposes
    to JS) equals a FROZEN list of 100 names (U3 deleted the dead set_batch_dest;
    v0.21.0 added the two evidence-toggle endpoints). A moved/renamed/dropped/added endpoint fails
    here; this is the invariant the mechanical move must preserve. The two touched
    endpoints (start_compare / start_compare_env) additionally have their exact source
    `def` signature asserted (the @_api_method wrapper hides arity from inspect, so the
    arity is locked at the source).
  * EXTRACTION + DELEGATION (the RED-before-refactor half) — gui_win32 exposes the four
    pure Win32 helpers; gui_api delegates to them and no longer open-codes the Win32 calls
    (no `import ctypes`, no `windll`/`EnumWindows`/`FlashWindowEx`/`MessageBoxW`/`LoadImageW`);
    `_begin_compare` exists and both compare endpoints route through it.

Class-level introspection only (constructing GuiApi would start threads + write the TSN
skeleton). Offline, CI-safe. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_gui_api_surface.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_api                                 # noqa: E402
import gui_win32                               # noqa: E402

_fail = []
_SCRIPTS = ROOT / "scripts"


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _src(mod):
    return (_SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")


# The frozen pywebview façade: every PUBLIC method GuiApi exposes to JS (plus `attach`,
# the one public non-endpoint). Captured at the P7b baseline (8eb9cc8). A mechanical
# extraction must NOT change this set — adding/removing/renaming an endpoint fails here.
FROZEN_API = {
    "add_day_matrix_day", "apply_site_preset", "attach", "build_day_cell", "cancel_login",
    "cancel_run", "check_environments", "check_updates", "clear_saved_login",
    "consolidate_info", "consolidate_matrix_tsn", "day_matrix_info", "decline_overwrite",
    "delete_chromium", "discard_batch", "download_chromium", "export_day_cell",
    "export_day_column", "export_day_row", "finish_login", "get_compare_folders",
    "get_initial_state", "get_settings", "import_tsn_raw", "log_js_error", "matrix_info",
    "matrix_queue_clear", "matrix_queue_move", "matrix_queue_remove", "matrix_stop_all",
    "open_cell_comparison", "open_comparisons_folder", "open_consolidate_input",
    "open_consolidated_folder", "open_day_cell_comparison", "open_day_comparisons_folder",
    "open_failures_folder", "open_logs_folder", "open_output_folder", "open_release_page",
    "open_run_folder", "open_tsn_library_folder", "parse_routes_preview", "pause_or_resume",
    "pick_batch_dest", "pick_compare_file", "pick_compare_folder", "pick_matrix_tsn_file",
    "rebuild_day_matrix", "rebuild_tsn_library", "recompute_matrix", "refresh_cell_comparison",
    "refresh_cell_export", "refresh_column_export", "refresh_row_export", "remove_day_matrix_day",
    "report_library_info", "request_preview", "reset_preview", "resume_batch", "retry_failed",
    "revert_to_previous", "run_validation", "save_run_report", "save_support_bundle", "set_all_matrix_modes",
    "set_day_matrix_formulas", "set_day_matrix_report",
    "set_day_matrix_row_order", "set_day_matrix_source", "set_evidence_examples",
    "set_evidence_images", "set_export_browser",
    "set_matrix_baseline", "set_matrix_env", "set_matrix_env_order", "set_matrix_fast",
    "set_matrix_formulas", "set_matrix_report", "set_matrix_row_mode", "set_matrix_row_order",
    "set_matrix_tsn_file", "set_setting", "set_site", "set_site_url", "skip_route",
    "start_batch_export", "start_checks", "start_compare", "start_compare_env",
    "start_consolidate", "start_export", "start_login", "start_reset", "tsn_library_status",
    "ui_event", "ui_ready", "update_apply", "update_start", "verify_environment",
}


def _public_methods():
    return {n for n, _f in inspect.getmembers(gui_api.GuiApi, inspect.isfunction)
            if not n.startswith("_")}


# --------------------------------------------------------------------------- #
# SURFACE IDENTITY (RM08)
# --------------------------------------------------------------------------- #
def test_surface_identity():
    print("pywebview façade surface identity (RM08):")
    cur = _public_methods()
    check(f"exactly {len(FROZEN_API)} public methods exposed (got {len(cur)})", len(cur) == len(FROZEN_API))
    missing = FROZEN_API - cur
    extra = cur - FROZEN_API
    check("no façade endpoint dropped/renamed", not missing)
    if missing:
        print(f"      MISSING: {sorted(missing)}")
    check("no unexpected new public method (group via private helpers, not new endpoints)", not extra)
    if extra:
        print(f"      EXTRA: {sorted(extra)}")


def test_touched_endpoint_signatures():
    print("the two touched endpoints keep their exact source signature (arity lock):")
    s = _src("gui_compare_api")          # S1: the compare endpoints' home
    check("start_compare(self, report_key, tsmis_path, tsn_path, want_formulas=True, want_values=False)",
          "def start_compare(self, report_key, tsmis_path, tsn_path,\n"
          "                      want_formulas=True, want_values=False):" in s)
    check("start_compare_env(self, report_key, dir_a, dir_b, want_formulas=True, want_values=False)",
          "def start_compare_env(self, report_key, dir_a, dir_b,\n"
          "                          want_formulas=True, want_values=False):" in s)


# --------------------------------------------------------------------------- #
# EXTRACTION + DELEGATION  (RED before the refactor)
# --------------------------------------------------------------------------- #
def test_gui_win32_module():
    print("gui_win32 exposes the four pure Win32 helpers:")
    for fn in ("find_own_window", "set_window_icon", "flash_taskbar", "message_box"):
        check(f"gui_win32.{fn} is callable", callable(getattr(gui_win32, fn, None)))


def test_gui_api_delegates():
    print("gui_api delegates the Win32 calls to gui_win32 (no inline ctypes left):")
    s = _src("gui_api")
    check("gui_api imports gui_win32", "import gui_win32" in s)
    for call in ("gui_win32.find_own_window", "gui_win32.set_window_icon",
                 "gui_win32.flash_taskbar", "gui_win32.message_box"):
        check(f"gui_api calls {call}", call in s)
    # The inline Win32 CODE moved out: no `import ctypes`, and none of the raw API
    # call markers remain (docstrings may still say the word "ctypes" — that's fine).
    check("gui_api no longer `import ctypes`", "\nimport ctypes\n" not in s)
    for marker in ("ctypes.windll", "windll.user32", "EnumWindows", "FlashWindowEx",
                   "MessageBoxW", "LoadImageW"):
        check(f"gui_api no longer open-codes {marker}", marker not in s)
    # ...and gui_win32 is where they now live.
    w = _src("gui_win32")
    check("gui_win32 owns the raw Win32 calls (EnumWindows/FlashWindowEx/MessageBoxW/LoadImageW)",
          all(m in w for m in ("EnumWindows", "FlashWindowEx", "MessageBoxW", "LoadImageW")))


def test_begin_compare_unify():
    print("_begin_compare unifies start_compare / start_compare_env:")
    s = _src("gui_compare_api")          # S1: the compare endpoints' home
    check("the compare mixin defines _begin_compare", "def _begin_compare(self," in s)
    check("start_compare/start_compare_env route through _begin_compare (2 call sites)",
          s.count("self._begin_compare(") == 2)
    # The duplicated claim→dialog→launch tails are gone from the two endpoints (the gate
    # claim + the dialog-cancel release now live once in _begin_compare).
    check("the duplicated 'A task is already running.' claim tail collapsed to one helper",
          s.count('self._claim_task_error("compare")') == 1)
    # P7b-A01: the default name is a LAZY callable evaluated INSIDE the claim (preserving
    # the pre-P7b claim-before-suggest_name ordering), so a suggest-name error releases the
    # gate just like the baseline rather than running before any claim.
    check("_begin_compare takes a lazy `suggest` and calls suggest() inside the claim",
          "def _begin_compare(self, label, mode, save_dir, suggest, build):" in s
          and "self._save_dialog_for_compare(save_dir, suggest())" in s)
    check("both endpoints pass the suggest-name as a lazy callable",
          "lambda: mod.suggest_name(tsmis_path)" in s
          and "lambda: adapter.suggest_name(pa, pb)" in s)


def test_matrix_grouping():
    print("the Matrix cluster lives in gui_matrix.GuiMatrixMixin (P7c):")
    import gui_matrix
    check("GuiApi inherits GuiMatrixMixin", gui_matrix.GuiMatrixMixin in gui_api.GuiApi.__mro__)
    mixin = vars(gui_matrix.GuiMatrixMixin)
    ga = vars(gui_api.GuiApi)
    # A representative cross-section of the moved cluster: public endpoints (matrix,
    # by-day, TSN-library), the dispatch/queue machinery, and the matrix _on_* handlers.
    MOVED = ["matrix_info", "set_matrix_baseline", "recompute_matrix", "refresh_cell_export",
             "refresh_cell_comparison", "open_cell_comparison", "consolidate_matrix_tsn",
             "tsn_library_status", "import_tsn_raw", "rebuild_tsn_library", "matrix_queue_clear",
             "matrix_stop_all", "set_matrix_fast", "day_matrix_info", "build_day_cell",
             "export_day_column", "rebuild_day_matrix", "open_tsn_library_folder",
             "_dispatch_matrix_job", "_try_start_next_matrix_job", "_make_job",
             "_resolve_export_steps", "_resolve_day_export_steps",
             "_on_matrix_cell", "_on_matrix_done", "_on_matrix_export_done"]
    for m in MOVED:
        check(f"{m}: defined in GuiMatrixMixin", m in mixin)
        check(f"{m}: NO LONGER defined on GuiApi (truly moved)", m not in ga)
        check(f"{m}: still resolves on GuiApi via the mixin (façade intact)",
              hasattr(gui_api.GuiApi, m))
    # the moved PUBLIC endpoints are still in the frozen 98-name façade (no rename/drop)
    moved_public = {m for m in MOVED if not m.startswith("_")}
    check("every moved public matrix endpoint stays in the frozen façade",
          moved_public <= FROZEN_API)


def main():
    test_surface_identity()
    test_touched_endpoint_signatures()
    test_gui_win32_module()
    test_gui_api_delegates()
    test_begin_compare_unify()
    test_matrix_grouping()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL GUI-API-SURFACE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
