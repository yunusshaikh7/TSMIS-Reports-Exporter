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
    print("start_consolidate validates the report KEY before claiming the slot:")
    a = gui_api.GuiApi()
    # A bad KEY must return an error AND leave the task slot free (not wedged).
    res = a.start_consolidate("__nope__", "")
    check("bad key returns an error", res.get("error") is not None)
    check("task slot left free after a bad key", a._try_claim_task("x") is True)
    a._release_task()


def test_compare_dialog_error_releases():
    print("start_compare releases the slot if the save dialog errors:")
    import reports
    a = gui_api.GuiApi()
    # Find a "files"-kind comparison KEY (start_compare's required kind).
    files_key = next((reports.COMPARE_KEYS[i]
                      for i, r in enumerate(reports.COMPARE_REPORTS)
                      if r[2] == "files"), None)
    if files_key is None:
        check("a files-kind comparison exists", False)
        return

    def _boom(*_a, **_k):
        raise RuntimeError("dialog blew up")

    a._save_dialog_for_compare = _boom        # claim happens, then the dialog throws
    res = a.start_compare(files_key, "a.xlsx", "b.xlsx", True, False)
    check("error surfaced to the caller", isinstance(res, dict) and res.get("error"))
    check("task slot released after a dialog error", a._try_claim_task("x") is True)
    a._release_task()


def test_tsn_library_panel():
    print("Settings TSN-library panel (v0.17.0):")
    import shutil
    import tempfile

    import tsn_library
    saved = paths.TSN_LIBRARY_ROOT
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_tsnlib_"))
    paths.TSN_LIBRARY_ROOT = tmp                  # empty -> every report has no raw
    try:
        a = gui_api.GuiApi()
        rows = a._tsn_library_status()
        reg = {r.subdir for r in tsn_library.reports()}
        check("status lists every registered TSN report",
              {r["report"] for r in rows} == reg)
        fields = {"report", "label", "raw_kind", "raw_present", "raw_count",
                  "consolidated_present", "current", "raw_dir"}
        check("status rows carry exactly the panel fields",
              all(set(r) == fields for r in rows))
        check("tsn_library_status() wraps the rows",
              {x["report"] for x in a.tsn_library_status()["reports"]} == reg)
        check("import_tsn_raw rejects an unknown report",
              a.import_tsn_raw("nope").get("error") is not None)
        check("rebuild_tsn_library rejects an unknown report",
              a.rebuild_tsn_library("nope").get("error") is not None)
        # A registered report with no raw imported: rebuild must error BEFORE
        # claiming the task slot (a no-raw rebuild can't wedge the gate).
        res = a.rebuild_tsn_library(next(iter(reg)))
        check("rebuild with no raw returns an error", res.get("error") is not None)
        check("task slot left free after a no-raw rebuild",
              a._try_claim_task("x") is True)
        a._release_task()
        # import_raw rejects a wrong-extension file (else it lands in raw/ but is
        # invisible to the glob reader — a silent import-vs-ignore mismatch).
        bad = tmp / "wrong.txt"
        bad.write_text("x")
        raised = False
        try:
            tsn_library.import_raw("ramp_detail", [str(bad)])     # expects *.xlsx
        except ValueError:
            raised = True
        check("import_raw rejects a wrong-extension file", raised)
        # ensure_layout() seeds a self-documenting skeleton so a fresh library
        # isn't just an empty folder (v0.17.1 hotfix): every report gets a raw/
        # folder + a hint file, plus a root README. GuiApi() already ran it; it's
        # idempotent, so call again and assert the shape.
        tsn_library.ensure_layout()
        check("ensure_layout creates every report's raw/ folder",
              all(tsn_library.raw_dir(r).is_dir() for r in reg))
        check("ensure_layout drops a hint into each empty raw/ folder",
              all((tsn_library.raw_dir(r) / tsn_library._RAW_HINT_NAME).is_file()
                  for r in reg))
        check("ensure_layout writes a root README",
              (tmp / tsn_library._README_NAME).is_file())
        check("the .txt hints stay invisible to the raw-file reader",
              all(tsn_library.status(r)["raw_count"] == 0 for r in reg))
        # Once real raw data is present, the hint is NOT re-seeded into that
        # folder (don't fight a user who deleted it after dropping files in).
        rd = tsn_library.raw_dir("ramp_detail")
        (rd / "statewide.xlsx").write_text("x")
        (rd / tsn_library._RAW_HINT_NAME).unlink()
        tsn_library.ensure_layout()
        check("hint not re-seeded once real raw data is present",
              not (rd / tsn_library._RAW_HINT_NAME).exists())
    finally:
        paths.TSN_LIBRARY_ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def test_env_verdict():
    print("env-scan fail-closed verdict (WS3):")
    from gui_worker import env_verdict
    ok_status, ok_detail = env_verdict(True, True)
    check("both readable -> ok", ok_status == "ok")
    uv1, d1 = env_verdict(False, True)
    check("CONFIG unreadable -> unverified (not ok)", uv1 == "unverified")
    check("CONFIG-unreadable detail names the environment",
          "environment" in d1.lower())
    uv2, d2 = env_verdict(True, False)
    check("report-list unreadable -> unverified", uv2 == "unverified")
    check("report-list-unreadable detail names the report list",
          "report-type" in d2.lower() or "report" in d2.lower())
    uv3, _ = env_verdict(False, False)
    check("both unreadable -> unverified (never silent ok)", uv3 == "unverified")


def test_export_browser():
    print("export-browser setting + indicator (v0.17.0):")
    import common
    import browser_channels  # P8b: channel resolution + the _preferred_channel cache live here
    import settings
    a = gui_api.GuiApi()
    orig = settings.get_export_browser()
    orig_pref = browser_channels._preferred_channel
    try:
        check("rejects msedge as an export browser",
              a.set_export_browser("msedge").get("error") is not None)
        check("rejects an unknown channel",
              a.set_export_browser("safari").get("error") is not None)
        check("accepts chrome", a.set_export_browser("chrome").get("ok") is True)
        check("chrome persisted", settings.get_export_browser() == "chrome")
        check("accepts chromium", a.set_export_browser("chromium").get("ok") is True)
        check("chromium persisted", settings.get_export_browser() == "chromium")
        check("auto accepted", a.set_export_browser("auto").get("ok") is True)
        check("auto clears the pick (back to default)", settings.get_export_browser() == "")
        eb = a._export_browser_view()
        check("indicator carries exactly the title-bar fields",
              set(eb) == {"normal", "fast", "dot", "cls_label"})
        check("indicator dot is a known status",
              eb["dot"] in ("ok", "warn", "bad", "unknown"))
        gs = a.get_settings().get("export_browser", {})
        check("get_settings exposes the picker info",
              {"value", "chrome_ok", "chromium_present", "labels"} <= set(gs))
    finally:
        settings.set_export_browser(orig)
        common.set_preferred_channel(orig_pref)


def test_channel_order():
    print("browser channel order (Chrome-first; Edge implicit):")
    import common
    import browser_channels  # P8b: channel resolution + the _preferred_channel cache live here
    orig_pref = browser_channels._preferred_channel
    try:
        ch = list(common.BROWSER_CHANNELS)
        check("msedge is LAST in the default order", ch[-1] == "msedge")
        check("chrome comes before edge", ch.index("chrome") < ch.index("msedge"))
        common.set_preferred_channel(None)
        check("_candidate_channels() == default order with no pick",
              list(browser_channels._candidate_channels()) == ch)
        common.set_preferred_channel("msedge")
        check("set_preferred_channel('msedge') is rejected -> None",
              browser_channels._preferred_channel is None)
        common.set_preferred_channel("chrome")
        check("a chrome pick is tried first", browser_channels._candidate_channels()[0] == "chrome")
        common.set_preferred_channel("msedge")        # -> None again
        par = list(browser_channels._parallel_candidates())
        check("parallel order never STARTS with edge", par[0] != "msedge")
        if "msedge" in ch:
            check("parallel order keeps edge LAST", par[-1] == "msedge")
    finally:
        common.set_preferred_channel(orig_pref)


def test_active_env_check_gates():
    print("quiet active-env check gating:")
    import tempfile
    a = gui_api.GuiApi()
    started = []

    class _FakeWorker:
        def __init__(self, q, src, env, seq):
            started.append((src, env, seq))

        def start(self):
            pass

    orig_worker = gui_api.ActiveEnvCheckWorker
    orig_has_auth = gui_api.has_valid_auth
    orig_edge = gui_api.EDGE_LOGIN_PROFILE_DIR
    gui_api.ActiveEnvCheckWorker = _FakeWorker          # never launch a real browser
    try:
        # Credential gate: no saved login + an unprimed (empty) Edge profile dir.
        gui_api.has_valid_auth = lambda: False
        gui_api.EDGE_LOGIN_PROFILE_DIR = Path(tempfile.mkdtemp(prefix="tsmis_noedge_"))
        a._active_check = False
        a._maybe_active_env_check("startup")
        check("no credentials -> no check started",
              not started and a._active_check is False)
        # Credentials present, but a task is running -> must not touch the gate.
        gui_api.has_valid_auth = lambda: True
        a._task = "export"
        a._maybe_active_env_check("startup")
        check("a task is running -> no check started",
              not started and a._active_check is False)
        a._task = None
        # Credentials present + idle -> exactly one check, flag + seq claimed.
        a._maybe_active_env_check("startup")
        check("credentials + idle -> one check started", len(started) == 1)
        check("active-check flag set + seq bumped",
              a._active_check is True and a._active_check_seq >= 1)
        # A stale done (old seq) is ignored; the matching one clears the flag.
        a._on_active_env_done({"seq": -1, "via_device": True})
        check("stale active_env_done is ignored", a._active_check is True)
        a._on_active_env_done({"seq": a._active_check_seq, "via_device": False})
        check("matching active_env_done clears the flag", a._active_check is False)
    finally:
        gui_api.ActiveEnvCheckWorker = orig_worker
        gui_api.has_valid_auth = orig_has_auth
        gui_api.EDGE_LOGIN_PROFILE_DIR = orig_edge


def main():
    test_pick_report()
    test_env_verdict()
    test_path_validation()
    test_single_flight()
    test_reset_token()
    test_consolidate_index_before_claim()
    test_compare_dialog_error_releases()
    test_tsn_library_panel()
    test_export_browser()
    test_channel_order()
    test_active_env_check_gates()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL GUI-BRIDGE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
