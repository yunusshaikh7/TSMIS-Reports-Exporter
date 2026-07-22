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
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_api  # noqa: E402
import gui_compare_api  # noqa: E402
import gui_settings_api  # noqa: E402
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

    # A matching token authorizes exactly what that preview showed. The worker
    # must not call reset_targets again and silently include a later directory.
    captured = {}

    class _FakeResetWorker:
        def __init__(self, _queue, include_input=False, cancel_event=None,
                     targets=None):
            captured["targets"] = tuple(targets or ())

        def start(self):
            captured["started"] = True

    old_targets = gui_settings_api.reset_targets
    old_worker = gui_settings_api.ResetWorker
    previewed = [("previewed target", Path("preview-A"))]
    later = [("later target", Path("preview-B"))]
    try:
        gui_settings_api.reset_targets = lambda *_a, **_k: list(previewed)
        gui_settings_api.ResetWorker = _FakeResetWorker
        prev = a.reset_preview(False)
        gui_settings_api.reset_targets = lambda *_a, **_k: list(later)
        res = a.start_reset(False, prev["token"])
        check("matching token starts Reset", res.get("ok") is True)
        check("Reset receives the exact previewed set, not a fresh expanded set",
              captured.get("started") is True
              and captured.get("targets") == tuple(previewed))
    finally:
        gui_settings_api.reset_targets = old_targets
        gui_settings_api.ResetWorker = old_worker
        a._release_task()


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
    # CMP-AUD-016: the endpoint now preflights existence + type, so the dialog-error
    # path needs REAL .xlsx inputs (otherwise the preflight rejects before the claim).
    with tempfile.TemporaryDirectory(prefix="tsmis_cmp_dlgerr_") as td:
        pa = Path(td) / "a.xlsx"; pa.write_bytes(b"a")
        pb = Path(td) / "b.xlsx"; pb.write_bytes(b"b")
        res = a.start_compare(files_key, str(pa), str(pb), True, False)
    check("error surfaced to the caller", isinstance(res, dict) and res.get("error"))
    check("task slot released after a dialog error", a._try_claim_task("x") is True)
    a._release_task()


def test_016_input_preflight():
    """CMP-AUD-016: start_compare refuses a stale (missing) or wrong-type file
    BEFORE claiming the task/opening the Save dialog — a leftover selection from
    another recipe can't launch and wedge the gate."""
    print("CMP-AUD-016: start_compare preflights existence + type before the claim:")
    import reports
    a = gui_api.GuiApi()
    files_key = next((reports.COMPARE_KEYS[i]
                      for i, r in enumerate(reports.COMPARE_REPORTS)
                      if r[2] == "files"), None)
    if files_key is None:
        check("a files-kind comparison exists", False)
        return
    dialog_calls = []
    a._save_dialog_for_compare = lambda *_a, **_k: dialog_calls.append(1)
    with tempfile.TemporaryDirectory(prefix="tsmis_cmp_pf_") as td:
        good = Path(td) / "ok.xlsx"; good.write_bytes(b"x")
        wrong = Path(td) / "note.txt"; wrong.write_bytes(b"x")
        missing = str(Path(td) / "gone.xlsx")
        # a MISSING file is refused, task NOT claimed, dialog NEVER opened
        r1 = a.start_compare(files_key, missing, str(good), True, False)
        check("a missing input is rejected before the claim",
              bool(r1.get("error")) and a._try_claim_task("x") is True)
        a._release_task()
        # a WRONG-TYPE file is refused too
        r2 = a.start_compare(files_key, str(wrong), str(good), True, False)
        check("a wrong-type input (.txt) is rejected before the claim",
              bool(r2.get("error")) and a._try_claim_task("y") is True)
        a._release_task()
        check("the Save dialog never opened for a rejected preflight", not dialog_calls)


def test_compare_derived_overwrite_token():
    print("classic both-mode derived-values overwrite confirmation:")
    import reports

    files_key = next((reports.COMPARE_KEYS[i]
                      for i, r in enumerate(reports.COMPARE_REPORTS)
                      if r[2] == "files"), None)
    if files_key is None:
        check("a files-kind comparison exists", False)
        return

    with tempfile.TemporaryDirectory(prefix="tsmis_compare_consent_") as td:
        root = Path(td)
        src_a = root / "source-a.xlsx"
        src_b = root / "source-b.xlsx"
        src_a.write_bytes(b"source-a")
        src_b.write_bytes(b"source-b")
        out = root / "chosen formulas.xlsx"
        twin = root / "chosen formulas (values).xlsx"
        twin.write_bytes(b"existing-values")

        launched = []

        def api_with_fake_launch():
            a = gui_api.GuiApi()
            a._save_dialog_for_compare = lambda *_a, **_k: out

            def fake_launch(label, mode, selected_out, run_fn, source_paths=(),
                            **kwargs):
                launched.append({
                    "label": label, "mode": mode, "out": Path(selected_out),
                    "run_fn": run_fn, "source_paths": tuple(source_paths),
                    **kwargs,
                })
                return {"ok": True}

            a._launch_compare = fake_launch
            return a

        # Existing derived twin: preview names the exact full path and does not
        # launch until the matching token is accepted.
        a = api_with_fake_launch()
        preview = a.start_compare(files_key, str(src_a), str(src_b), True, True)
        check("existing values twin requires confirmation",
              preview.get("confirm_required") is True and not launched)
        check("confirmation names the exact derived path",
              preview.get("path") == str(twin)
              and str(twin) in preview.get("message", ""))
        token = preview.get("confirm_token")
        accepted = a.confirm_compare_overwrite(token, True)
        check("accept launches the parked operation", accepted.get("ok") is True
              and len(launched) == 1)
        launch = launched[-1]
        check("accept cannot retarget output, mode, or selected inputs",
              launch["out"] == out and launch["mode"] == "both"
              and launch["source_paths"] == (str(src_a), str(src_b))
              and launch.get("confirmed_twin") == twin)
        check("matching token is single-use (replay refused)",
              a.confirm_compare_overwrite(token, True).get("error") is not None)
        a._release_task()                 # fake launch has no terminal worker

        # Decline consumes the token, preserves the twin, and releases the task.
        launched.clear()
        a = api_with_fake_launch()
        preview = a.start_compare(files_key, str(src_a), str(src_b), True, True)
        declined = a.confirm_compare_overwrite(preview["confirm_token"], False)
        check("decline does not launch and keeps the existing twin",
              declined.get("cancelled") is True and not launched
              and twin.read_bytes() == b"existing-values")
        free = a._try_claim_task("after-decline")
        check("decline does not wedge the task slot", free is True)
        if free:
            a._release_task()

        # A stale/mismatched token cannot consume or retarget the live operation;
        # its real token can still decline and release the slot.
        a = api_with_fake_launch()
        preview = a.start_compare(files_key, str(src_a), str(src_b), True, True)
        check("mismatched token refused without launch",
              a.confirm_compare_overwrite("stale-token", True).get("error") is not None
              and not launched)
        declined = a.confirm_compare_overwrite(preview["confirm_token"], False)
        check("valid decision still resolves after stale-token attempt",
              declined.get("cancelled") is True)
        free = a._try_claim_task("after-stale")
        check("stale-token path leaves no task-slot wedge after resolution", free is True)
        if free:
            a._release_task()

        # Source safety has higher precedence than consent: a selected source
        # named as the derived sibling errors before issuing any overwrite token.
        a = api_with_fake_launch()
        alias = a.start_compare(files_key, str(twin), str(src_b), True, True)
        check("source-alias precedence refuses before prompting",
              alias.get("error") is not None
              and not alias.get("confirm_required") and not launched)
        free = a._try_claim_task("after-alias")
        check("source-alias refusal releases the task slot", free is True)
        if free:
            a._release_task()

        # The selected source object is identity-bound across human think-time.
        a = api_with_fake_launch()
        preview = a.start_compare(files_key, str(src_a), str(src_b), True, True)
        original = root / "source-a-original.xlsx"
        src_a.replace(original)
        src_a.write_bytes(b"retargeted-source")
        retargeted = a.confirm_compare_overwrite(preview["confirm_token"], True)
        check("source replacement between prompt and launch is refused",
              retargeted.get("error") is not None and not launched)
        free = a._try_claim_task("after-retarget")
        check("source-retarget refusal releases the task slot", free is True)
        if free:
            a._release_task()

        # Exercise the callback passed directly into the transactional public
        # comparator. Neither an
        # absent values twin nor an absent picked formulas path may be silently
        # overwritten if it appears after the native dialog/initial decision.
        late_out = root / "late formulas.xlsx"
        late_twin = root / "late formulas (values).xlsx"
        captured = {}

        class FakeWorker:
            def __init__(self, committed, *_a, **_k):
                captured["committed"] = committed

            def start(self):
                captured["worker_started"] = True

        def fake_run(_final, events=None, confirm_overwrite=None, day=None):
            captured["run_final"] = Path(_final)
            captured["confirm"] = confirm_overwrite
            return object()

        old_worker = gui_compare_api.ConsolidateWorker
        try:
            gui_compare_api.ConsolidateWorker = FakeWorker
            a = gui_api.GuiApi()
            a._try_claim_task("compare")
            a._launch_compare("late", "both", late_out,
                              fake_run,
                              source_paths=(original, src_b),
                              captured_sources=gui_compare_api.artifact_store.capture_source_identities(
                                  (original, src_b)),
                              picked_was_existing=False)
            captured["committed"]()
            check("classic worker delegates the selected final to one transaction",
                  captured.get("run_final") == late_out)
            late_out.write_bytes(b"late-formulas-foreign")
            late_twin.write_bytes(b"late-values-foreign")
            check("values twin appearing late is denied",
                  captured["confirm"](late_twin) is False)
            check("picked formulas path appearing after native dialog is denied",
                  captured["confirm"](late_out) is False)
            approved = gui_compare_api._comparison_overwrite_authorizer(
                late_out, "both", confirmed_twin=late_twin,
                picked_was_existing=True)
            check("explicit decisions authorize only their exact two paths",
                  approved(late_out) is True and approved(late_twin) is True
                  and approved(root / "other.xlsx") is False)

            # No-confirmation path: replacement after launch but before the
            # worker actually enters the comparator must still be rejected
            # against the identity captured after the native dialog.
            worker_src = root / "worker-source.xlsx"
            worker_other = root / "worker-other.xlsx"
            worker_src.write_bytes(b"worker-source-original")
            worker_other.write_bytes(b"worker-other")
            worker_capture = gui_compare_api.artifact_store.capture_source_identities(
                (worker_src, worker_other))
            captured.pop("run_final", None)
            a._launch_compare(
                "worker-preflight", "values", root / "worker-out.xlsx",
                fake_run, source_paths=(worker_src, worker_other),
                captured_sources=worker_capture, picked_was_existing=False)
            moved_worker_src = root / "worker-source-moved.xlsx"
            worker_src.replace(moved_worker_src)
            worker_src.write_bytes(b"same-path-decoy")
            try:
                captured["committed"]()
            except ValueError:
                preflight_blocked = True
            else:
                preflight_blocked = False
            check("worker-entry preflight rejects a selected-source replacement",
                  preflight_blocked and "run_final" not in captured)
        finally:
            gui_compare_api.ConsolidateWorker = old_worker
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
        # The panel reports BOTH TSN assets per report: the raw the normalized
        # library is built from, and the TSN prints the evidence images crop from
        # (evidence_* — absent support is reported, not inferred from a zero count).
        fields = {"report", "label", "raw_kind", "raw_present", "raw_count",
                  "consolidated_present", "current", "raw_dir",
                  "evidence_supported", "evidence_pdfs", "evidence_dir",
                  "evidence_in_raw",
                  # Why a report is not current — the first failing condition,
                  # so "STALE" is actionable instead of one opaque word.
                  "stale_reason"}
        check("status rows carry exactly the panel fields",
              all(set(r) == fields for r in rows))

        # The stale reason must NAME the cause. With an empty library root every
        # report has no raw at all, so that is the reason each must give — and a
        # current report must give none.
        check("a not-current report says WHY it is not current",
              all(r["stale_reason"] for r in rows if not r["current"]))
        check("no-raw reports name the missing raw, not a generic 'stale'",
              all(r["stale_reason"] == "no raw TSN files imported yet"
                  for r in rows if not r["raw_present"]))
        # Each distinct failing condition maps to its OWN message: a rebuilt-but-
        # stale library must never read the same as a never-built one (the field
        # report this was written for).
        _reason = gui_api.GuiApi._tsn_stale_reason
        base = {"current": False, "raw_present": True, "raw_admissible": True,
                "consolidated_present": True, "metadata_current": True,
                "producer_complete": True, "normalization_current": True,
                "raw_manifest_current": True, "normalized_workbook_current": True,
                "identity_token_current": True}
        cases = {
            "normalization_current": "older normalizer",
            "raw_manifest_current": "raw TSN files changed",
            "producer_complete": "skipped or failed inputs",
            "metadata_current": "does not match the workbook",
            "identity_token_current": "identity stamp",
        }
        distinct = set()
        for field, expect in cases.items():
            reason = _reason({**base, field: False})
            distinct.add(reason)
            check(f"stale reason for {field} names its own cause ({reason!r})",
                  expect in reason)
        check("each failing condition yields a DISTINCT reason",
              len(distinct) == len(cases))
        check("a current report reports no stale reason",
              _reason({**base, "current": True}) == "")
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
        def __init__(self, q, src, env, seq, supersede=None):
            started.append((src, env, seq))
            self.supersede = supersede

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
    test_016_input_preflight()
    test_compare_derived_overwrite_token()
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
