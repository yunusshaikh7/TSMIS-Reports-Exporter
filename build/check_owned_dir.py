"""Adversarial check for app-owned destination directories (CMP-AUD-090).

Ownership is authority to recursively delete a directory.  It may therefore be
created only with a directory the app itself just created; an existing unowned
directory (empty or not) must never be adopted.  Reset additionally requires a
current, purpose-matching marker in an expected direct child of the configured
Export-Everything root.

Run with the build venv:
    build\.venv\Scripts\python.exe build\check_owned_dir.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import owned_dir

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _make_dir_link(link, target):
    """Create a directory symlink, falling back to a Windows junction."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        if os.name != "nt":
            return False
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, check=False)
    return made.returncode == 0 and link.exists()


def _remove_dir_link(link):
    try:
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            link.rmdir()  # removes a Windows junction without touching its target
    except OSError:
        pass


class _Q:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def marker_checks():
    print("create-and-mark ownership primitive:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_"))
    try:
        empty = tmp / "existing-empty"
        empty.mkdir()
        check("pre-existing empty dir is refused",
              owned_dir.ensure_owned_dir(empty, kind="store") is None)
        check("pre-existing empty dir is not stamped", not owned_dir.is_owned(empty))

        nonempty = tmp / "existing-nonempty"
        nonempty.mkdir()
        sentinel = nonempty / "personal-budget.xlsx"
        sentinel.write_text("mine", encoding="utf-8")
        check("pre-existing nonempty dir is refused",
              owned_dir.ensure_owned_dir(nonempty, kind="comparisons") is None)
        check("foreign content survives and no marker appears",
              sentinel.read_text(encoding="utf-8") == "mine"
              and not (nonempty / owned_dir.OWNER_MARKER).exists())

        # The legacy public helper must no longer provide a stamp-on-sight escape.
        legacy_api = tmp / "legacy-api"
        legacy_api.mkdir()
        check("mark_owned cannot adopt an existing directory",
              owned_dir.mark_owned(legacy_api, kind="store") is False
              and not (legacy_api / owned_dir.OWNER_MARKER).exists())

        made = owned_dir.ensure_owned_dir(tmp / "made", kind="comparisons")
        check("a missing directory is created and returned", made == tmp / "made")
        check("new directory has purpose-bound ownership",
              owned_dir.is_owned(made, kind="comparisons"))
        check("same purpose can reuse an already trusted directory",
              owned_dir.ensure_owned_dir(made, kind="comparisons") == made)
        check("wrong purpose is not ownership",
              not owned_dir.is_owned(made, kind="store"))
        before = (made / owned_dir.OWNER_MARKER).read_text(encoding="utf-8")
        check("wrong purpose cannot rewrite/re-adopt the directory",
              owned_dir.ensure_owned_dir(made, kind="store") is None
              and (made / owned_dir.OWNER_MARKER).read_text(encoding="utf-8") == before)

        copied = tmp / "copied-marker"
        copied.mkdir()
        shutil.copyfile(made / owned_dir.OWNER_MARKER,
                        copied / owned_dir.OWNER_MARKER)
        check("copying a valid marker cannot transfer deletion authority",
              owned_dir.ownership_status(copied, kind="comparisons")
              == owned_dir.INVALID)

        corrupt = tmp / "corrupt"
        corrupt.mkdir()
        corrupt_marker = corrupt / owned_dir.OWNER_MARKER
        corrupt_marker.write_text("not json", encoding="utf-8")
        check("corrupt marker is refused without overwrite",
              owned_dir.ensure_owned_dir(corrupt, kind="store") is None
              and corrupt_marker.read_text(encoding="utf-8") == "not json")

        legacy = tmp / "legacy"
        legacy.mkdir()
        (legacy / owned_dir.OWNER_MARKER).write_text(json.dumps({
            "app": "TSMIS Reports Exporter", "schema": 1, "kind": "store",
        }), encoding="utf-8")
        check("legacy marker is explicitly untrusted",
              owned_dir.ownership_status(legacy, kind="store") == owned_dir.LEGACY
              and not owned_dir.is_owned(legacy, kind="store"))
        check("legacy marker is not silently migrated on use",
              owned_dir.ensure_owned_dir(legacy, kind="store") is None
              and owned_dir.ownership_status(legacy, kind="store") == owned_dir.LEGACY)

        foreign = tmp / "foreign"
        foreign.mkdir()
        (foreign / owned_dir.OWNER_MARKER).write_text(
            json.dumps({"app": "Some Other Tool"}), encoding="utf-8")
        check("foreign marker is untrusted",
              not owned_dir.is_owned(foreign, kind="store"))
        check("missing path is untrusted and never raises",
              not owned_dir.is_owned(tmp / "nope", kind="store"))

        # Deterministically replace the leaf between mkdir and marker creation.
        # The helper may leave the replacement untouched, but its marker must be
        # invalid because it carries the original directory's stable file ID.
        raced = tmp / "replacement-race"
        saved_write = owned_dir._write_creation_marker
        race_sentinel = raced / "someone-elses-file.txt"
        def _replace_then_write(path, kind, identity):
            Path(path).rmdir()
            Path(path).mkdir()
            race_sentinel.write_text("keep", encoding="utf-8")
            return saved_write(path, kind, identity)
        owned_dir._write_creation_marker = _replace_then_write
        try:
            race_result = owned_dir.ensure_owned_dir(raced, kind="store")
        finally:
            owned_dir._write_creation_marker = saved_write
        check("directory-replacement race fails without deleting replacement data",
              race_result is None and race_sentinel.read_text(encoding="utf-8") == "keep")
        check("race-written marker cannot authorize the replacement directory",
              owned_dir.ownership_status(raced, kind="store") == owned_dir.INVALID)

        # Authority reached through any reparse ancestor is ambiguous even when
        # the eventual leaf would be newly created. Creation must stop before an
        # external directory is changed.
        outside = tmp / "outside"
        outside.mkdir()
        outside_sentinel = outside / "personal.txt"
        outside_sentinel.write_text("mine", encoding="utf-8")
        alias = tmp / "aliased-parent"
        linked = _make_dir_link(alias, outside)
        check("directory symlink/junction fixture is executable", linked)
        if linked:
            alias_result = owned_dir.ensure_owned_dir(alias / "store", kind="store")
            check("reparse ancestor is refused before creating an owned leaf",
                  alias_result is None and not (outside / "store").exists())
            check("external sentinel behind the reparse ancestor is unchanged",
                  outside_sentinel.read_text(encoding="utf-8") == "mine")
            _remove_dir_link(alias)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def reset_targets_integration():
    print("Reset selection is purpose- and structure-bound:")
    import gui_worker
    import settings

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_reset_"))
    store = tmp / "store"
    store.mkdir()

    trusted_store = owned_dir.ensure_owned_dir(store / "ssor-prod", kind="store")
    trusted_comparisons = owned_dir.ensure_owned_dir(
        store / "comparisons", kind="comparisons")
    wrong_kind = owned_dir.ensure_owned_dir(store / "ars-prod", kind="comparisons")
    custom = owned_dir.ensure_owned_dir(store / "my-custom-export", kind="store")

    legacy = store / "ssor-test"
    legacy.mkdir()
    (legacy / owned_dir.OWNER_MARKER).write_text(json.dumps({
        "app": "TSMIS Reports Exporter", "schema": 1, "kind": "store",
    }), encoding="utf-8")
    corrupt = store / "ars-test"
    corrupt.mkdir()
    (corrupt / owned_dir.OWNER_MARKER).write_text("not json", encoding="utf-8")
    empty_foreign = store / "ssor-dev"
    empty_foreign.mkdir()
    nonempty_foreign = store / "ars-dev"
    nonempty_foreign.mkdir()
    sentinel = nonempty_foreign / "personal.txt"
    sentinel.write_text("keep", encoding="utf-8")

    saved = settings.get_batch_dest
    settings.get_batch_dest = lambda: str(store)
    try:
        warnings = []
        targets = gui_worker.reset_targets(warnings=warnings)
    finally:
        settings.get_batch_dest = saved

    paths = {p for _label, p in targets}
    check("current store-purpose marker on expected child is selected",
          trusted_store in paths)
    check("current comparisons-purpose marker on expected child is selected",
          trusted_comparisons in paths)
    check("wrong-kind marker is retained", wrong_kind not in paths)
    check("marked but structurally unexpected child is retained", custom not in paths)
    check("legacy marker is retained", legacy not in paths)
    check("corrupt marker is retained", corrupt not in paths)
    check("pre-existing unowned empty dir is retained", empty_foreign not in paths)
    check("pre-existing unowned nonempty dir is retained with content",
          nonempty_foreign not in paths and sentinel.read_text(encoding="utf-8") == "keep")
    check("Reset preview explains legacy retention",
          any("ssor-test" in w and "older app version" in w.lower()
              and "left untouched" in w.lower()
              for w in warnings))
    check("Reset preview explains wrong-kind retention",
          any("ars-prod" in w and "purpose" in w.lower() for w in warnings))
    check("Reset preview explains corrupt-marker retention",
          any("ars-test" in w and "marker" in w.lower() for w in warnings))
    check("Reset preview explains unexpected-structure retention",
          any("my-custom-export" in w and "left untouched" in w.lower()
              for w in warnings))
    shutil.rmtree(tmp, ignore_errors=True)


def reset_replacement_race():
    print("Reset retains a foreign replacement selected under an owned pathname:")
    import gui_worker_maint
    import settings

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_reset_race_"))
    output = tmp / "output"
    input_root = tmp / "input"
    store = tmp / "store"
    output.mkdir()
    input_root.mkdir()
    store.mkdir()
    live = owned_dir.ensure_owned_dir(store / "ssor-prod", kind="store")
    (live / "app-report.xlsx").write_text("app", encoding="utf-8")
    moved = store / "original-owned-moved-aside"
    sentinel = live / "personal-budget.xlsx"

    saved = (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
             gui_worker_maint.INPUT_ROOT, gui_worker_maint.measure_targets,
             settings.get_batch_dest)
    calls = 0

    def _replace_during_measure(targets):
        nonlocal calls
        calls += 1
        if calls == 1:
            live.rename(moved)
            live.mkdir()
            sentinel.write_text("user-owned", encoding="utf-8")
        return saved[3](targets)

    try:
        gui_worker_maint.OUTPUT_ROOT = output
        gui_worker_maint.FAILURES_DIR = tmp / "failures"
        gui_worker_maint.INPUT_ROOT = input_root
        gui_worker_maint.measure_targets = _replace_during_measure
        settings.get_batch_dest = lambda: str(store)
        q = _Q()
        gui_worker_maint.ResetWorker(
            q, include_input=False, cancel_event=threading.Event()).run()
        check("foreign replacement survives the selection-to-delete race",
              sentinel.exists()
              and sentinel.read_text(encoding="utf-8") == "user-owned")
        terminal = [v for t, v in q.items if t == "reset_done"][-1]
        check("replacement mismatch is reported instead of claimed deleted",
              bool(terminal["errors"]))
        check("the originally selected owned directory is not followed after rename",
              (moved / "app-report.xlsx").read_text(encoding="utf-8") == "app")
    finally:
        (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
         gui_worker_maint.INPUT_ROOT, gui_worker_maint.measure_targets,
         settings.get_batch_dest) = saved
        shutil.rmtree(tmp, ignore_errors=True)


def reset_quarantine_positive():
    print("Reset deletes the exact previewed identity through quarantine:")
    import gui_worker_maint
    import settings

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_reset_positive_"))
    output = tmp / "output"
    input_root = tmp / "input"
    store = tmp / "store"
    output.mkdir()
    input_root.mkdir()
    store.mkdir()
    live = owned_dir.ensure_owned_dir(store / "ars-prod", kind="store")
    (live / "report.xlsx").write_text("app", encoding="utf-8")
    saved = (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
             gui_worker_maint.INPUT_ROOT, settings.get_batch_dest)
    try:
        gui_worker_maint.OUTPUT_ROOT = output
        gui_worker_maint.FAILURES_DIR = tmp / "failures"
        gui_worker_maint.INPUT_ROOT = input_root
        settings.get_batch_dest = lambda: str(store)
        previewed = gui_worker_maint.reset_targets()
        q = _Q()
        gui_worker_maint.ResetWorker(
            q, include_input=False, cancel_event=threading.Event(),
            targets=previewed).run()
        terminal = [v for t, v in q.items if t == "reset_done"][-1]
        check("the exact current owned directory is deleted", not live.exists())
        check("successful handoff reports the deleted file without errors",
              terminal["files"] >= 1 and terminal["errors"] == [])
        check("successful deletion leaves no quarantine residue",
              not list(store.glob(".*.tsmis-reset-*")))
    finally:
        (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
         gui_worker_maint.INPUT_ROOT, settings.get_batch_dest) = saved
        shutil.rmtree(tmp, ignore_errors=True)


def reset_quarantine_failure_restores():
    print("Reset restores a quarantined target when deletion is incomplete:")
    import gui_worker_maint
    import settings

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_reset_restore_"))
    output = tmp / "output"
    input_root = tmp / "input"
    store = tmp / "store"
    output.mkdir()
    input_root.mkdir()
    store.mkdir()
    live = owned_dir.ensure_owned_dir(store / "ssor-dev", kind="store")
    report = live / "locked.xlsx"
    report.write_text("app", encoding="utf-8")
    saved = (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
             gui_worker_maint.INPUT_ROOT,
             gui_worker_maint.safe_delete.scoped_rmtree,
             settings.get_batch_dest)

    def _leave_locked(path, onerror=None):
        if onerror is not None:
            onerror(None, Path(path) / "locked.xlsx", OSError("locked"))

    try:
        gui_worker_maint.OUTPUT_ROOT = output
        gui_worker_maint.FAILURES_DIR = tmp / "failures"
        gui_worker_maint.INPUT_ROOT = input_root
        gui_worker_maint.safe_delete.scoped_rmtree = _leave_locked
        settings.get_batch_dest = lambda: str(store)
        previewed = gui_worker_maint.reset_targets()
        q = _Q()
        gui_worker_maint.ResetWorker(
            q, include_input=False, cancel_event=threading.Event(),
            targets=previewed).run()
        terminal = [v for t, v in q.items if t == "reset_done"][-1]
        check("incomplete deletion restores the same owned path for retry",
              report.read_text(encoding="utf-8") == "app"
              and owned_dir.is_owned(live, kind="store"))
        check("incomplete deletion reports one retained-target error",
              len(terminal["errors"]) == 1
              and "restored to its original path" in terminal["errors"][0])
        check("restore leaves no hidden quarantine residue",
              not list(store.glob(".*.tsmis-reset-*")))
    finally:
        (gui_worker_maint.OUTPUT_ROOT, gui_worker_maint.FAILURES_DIR,
         gui_worker_maint.INPUT_ROOT,
         gui_worker_maint.safe_delete.scoped_rmtree,
         settings.get_batch_dest) = saved
        shutil.rmtree(tmp, ignore_errors=True)


def worker_checks():
    print("real ownership callers do not claim on sight or on empty work:")
    import gui_worker
    import gui_worker_export
    import gui_worker_matrix
    import reports

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_workers_"))
    try:
        # Export Everything used to stamp even an empty ExportWorker invocation.
        export_root = tmp / "ssor-prod"
        ew = gui_worker.ExportWorker([], _Q(), threading.Event(), threading.Event(),
                                     out_base=export_root)
        ew._run_specs(ew._build_events(), [])
        check("empty ExportWorker does not create/claim a store", not export_root.exists())

        cancelled_root = tmp / "cancelled-export"
        cancelled = threading.Event()
        cancelled.set()
        prep_calls = []
        ew = gui_worker.ExportWorker(
            [type("Spec", (), {"label": "Probe"})()], _Q(), cancelled,
            threading.Event(), out_base=cancelled_root)
        ew._prep_edition = lambda _s: prep_calls.append(1)
        ew._run_specs(ew._build_events(), [])
        check("already-cancelled ExportWorker neither claims nor prepares",
              not cancelled_root.exists() and prep_calls == [])

        # Everything comparison used to stamp before noticing there were no cells.
        matrix_dest = tmp / "matrix-dest"
        mw = gui_worker.MatrixCompareWorker(
            str(matrix_dest), "ssor-prod", [], _Q(), threading.Event())
        mw.run()
        check("empty Everything worker does not create comparisons",
              not (matrix_dest / "comparisons").exists())

        cancelled_dest = tmp / "cancelled-matrix"
        cancelled = threading.Event()
        cancelled.set()
        mw = gui_worker.MatrixCompareWorker(
            str(cancelled_dest), "ssor-prod",
            [("ramp_summary", "ars-prod", "env")], _Q(), cancelled)
        mw.run()
        check("already-cancelled Everything worker does not claim comparisons",
              not (cancelled_dest / "comparisons").exists())

        # Day outputs live under OUTPUT_ROOT; dest is input/store context only.
        day_dest = tmp / "day-dest"
        foreign = day_dest / "comparisons"
        foreign.mkdir(parents=True)
        sentinel = foreign / "personal-budget.xlsx"
        sentinel.write_text("mine", encoding="utf-8")
        dw = gui_worker.DayMatrixCompareWorker(
            "ssor", [], str(day_dest), _Q(), threading.Event())
        dw.run()
        check("empty Day worker neither stamps nor changes foreign comparisons",
              sentinel.read_text(encoding="utf-8") == "mine"
              and not (foreign / owned_dir.OWNER_MARKER).exists())

        # The global baseline output tree needs no user-destination ownership claim.
        baseline_root = tmp / "global-output" / "comparisons" / "baseline-by-day"
        saved_byday_root = gui_worker_matrix.baseline_matrix.byday_root
        gui_worker_matrix.baseline_matrix.byday_root = lambda: baseline_root
        try:
            bw = gui_worker.BaselineMatrixCompareWorker(
                "ssor", [], "baseline", str(tmp), _Q(), threading.Event())
            bw.run()
        finally:
            gui_worker_matrix.baseline_matrix.byday_root = saved_byday_root
        check("empty Baseline worker does not create an ownership-only root",
              not baseline_root.parent.exists())

        # Positive controls: real work can create a new purpose-bound root and
        # proceed. This prevents a superficially "safe" fix that blocks all work.
        positive_export = tmp / "positive-export"
        export_calls = []
        spec = type("Spec", (), {"label": "Probe"})()
        ew = gui_worker.ExportWorker([spec], _Q(), threading.Event(), threading.Event(),
                                     out_base=positive_export)
        ew._prep_edition = lambda _s: (None, None, None, None)
        ew._finish_edition = lambda *a: export_calls.append(1)
        saved_run_export = gui_worker_export.run_export
        gui_worker_export.run_export = lambda *a, **k: object()
        try:
            ew._run_specs(ew._build_events(), [])
        finally:
            gui_worker_export.run_export = saved_run_export
        check("non-empty Export worker creates a new trusted store and proceeds",
              export_calls == [1]
              and owned_dir.is_owned(positive_export, kind="store"))

        positive_matrix = tmp / "positive-matrix"
        matrix_calls = []
        saved_build = gui_worker_matrix.matrix.build_comparison
        def _positive_build(*_a, **_k):
            guard = _k.get("commit_guard")
            matrix_calls.append(callable(guard) and guard())
            return type("R", (), {"status": "ok"})()
        gui_worker_matrix.matrix.build_comparison = _positive_build
        try:
            q = _Q()
            w = gui_worker.MatrixCompareWorker(
                str(positive_matrix), "ssor-prod",
                [("ramp_summary", "ars-prod", "env")], q, threading.Event())
            w.run()
        finally:
            gui_worker_matrix.matrix.build_comparison = saved_build
        check("non-empty Everything worker creates a trusted comparisons root",
              matrix_calls == [True]
              and owned_dir.is_owned(positive_matrix / "comparisons",
                                     kind="comparisons"))

        # A real non-empty Everything worker must stop before its builder when the
        # configured comparisons folder is pre-existing and unowned.
        blocked_dest = tmp / "blocked-matrix"
        blocked = blocked_dest / "comparisons"
        blocked.mkdir(parents=True)
        blocked_sentinel = blocked / "mine.xlsx"
        blocked_sentinel.write_text("mine", encoding="utf-8")
        calls = []
        saved_build = gui_worker_matrix.matrix.build_comparison
        gui_worker_matrix.matrix.build_comparison = lambda *a, **k: calls.append(1)
        q = _Q()
        try:
            w = gui_worker.MatrixCompareWorker(
                str(blocked_dest), "ssor-prod", [("ramp_summary", "ars-prod", "env")],
                q, threading.Event())
            w.run()
        finally:
            gui_worker_matrix.matrix.build_comparison = saved_build
        terminal = [v for t, v in q.items if t == "matrix_done"][-1]
        check("non-empty Everything worker blocks before writing to foreign root",
              calls == [] and terminal["errors"] > 0
              and blocked_sentinel.read_text(encoding="utf-8") == "mine"
              and not (blocked / owned_dir.OWNER_MARKER).exists())

        # The Export caller must likewise stop before preparing report directories.
        blocked_export = tmp / "blocked-export"
        blocked_export.mkdir()
        (blocked_export / "mine.txt").write_text("mine", encoding="utf-8")
        prep_calls = []
        spec = type("Spec", (), {"label": "Probe"})()
        ew = gui_worker.ExportWorker([spec], _Q(), threading.Event(), threading.Event(),
                                     out_base=blocked_export)
        ew._prep_edition = lambda _s: prep_calls.append(1)
        raised = False
        try:
            ew._run_specs(ew._build_events(), [])
        except Exception:
            raised = True
        check("non-empty Export worker blocks before preparing a foreign store",
              raised and prep_calls == []
              and not (blocked_export / owned_dir.OWNER_MARKER).exists())

        # A valid claim is a lease on one directory identity, not continuing
        # authority over whatever later appears at the same pathname.
        raced_export = tmp / "raced-export"
        moved_export = tmp / "raced-export-owned-moved"
        real_spec = reports.EXPORT_REPORTS[0][2]
        foreign_stage = raced_export / f"{real_spec.subdir}.staging"
        foreign_stage_sentinel = foreign_stage / "personal-budget.xlsx"
        export_engine_calls = []
        saved_require = owned_dir.require_owned_dir_lease
        saved_run_export = gui_worker_export.run_export

        def _replace_export_after_claim(path, kind="store"):
            claimed = saved_require(path, kind=kind)
            claimed.path.rename(moved_export)
            foreign_stage.mkdir(parents=True)
            foreign_stage_sentinel.write_text("mine", encoding="utf-8")
            return claimed

        owned_dir.require_owned_dir_lease = _replace_export_after_claim
        gui_worker_export.run_export = lambda *_a, **_k: export_engine_calls.append(1)
        try:
            ew = gui_worker.ExportWorker(
                [real_spec], _Q(), threading.Event(), threading.Event(),
                out_base=raced_export)
            try:
                ew._run_specs(ew._build_events(), [])
            except Exception:
                pass
        finally:
            owned_dir.require_owned_dir_lease = saved_require
            gui_worker_export.run_export = saved_run_export
        check("Export worker rejects a root replacement before staging cleanup",
              foreign_stage_sentinel.exists()
              and foreign_stage_sentinel.read_text(encoding="utf-8") == "mine")
        check("Export engine is not entered after its owned-root lease breaks",
              export_engine_calls == [])

        raced_matrix = tmp / "raced-matrix"
        moved_comparisons = tmp / "raced-matrix-comparisons-owned-moved"
        replacement_comparisons = raced_matrix / "comparisons"
        replacement_sentinel = replacement_comparisons / "personal.xlsx"
        matrix_calls = []
        saved_require = owned_dir.require_owned_dir_lease
        saved_build = gui_worker_matrix.matrix.build_comparison

        def _replace_matrix_after_claim(path, kind="store"):
            claimed = saved_require(path, kind=kind)
            claimed.path.rename(moved_comparisons)
            replacement_comparisons.mkdir(parents=True)
            replacement_sentinel.write_text("mine", encoding="utf-8")
            return claimed

        def _raced_build(*_a, **_k):
            matrix_calls.append(1)
            (replacement_comparisons / "comparison.xlsx").write_text(
                "mutated", encoding="utf-8")
            return type("R", (), {"status": "ok"})()

        owned_dir.require_owned_dir_lease = _replace_matrix_after_claim
        gui_worker_matrix.matrix.build_comparison = _raced_build
        try:
            q = _Q()
            gui_worker.MatrixCompareWorker(
                str(raced_matrix), "ssor-prod",
                [("ramp_summary", "ars-prod", "env")], q,
                threading.Event()).run()
        finally:
            owned_dir.require_owned_dir_lease = saved_require
            gui_worker_matrix.matrix.build_comparison = saved_build
        check("Everything Matrix rejects a comparisons-root replacement before build",
              matrix_calls == [] and replacement_sentinel.exists()
              and not (replacement_comparisons / "comparison.xlsx").exists())

        # A non-empty Day compare may still run, but must never touch dest/comparisons.
        day_calls = []
        saved_day_build = gui_worker_matrix.day_matrix.build_day_cell
        def _fake_day_build(*_a, **_k):
            day_calls.append(1)
            return type("R", (), {"status": "ok"})()
        gui_worker_matrix.day_matrix.build_day_cell = _fake_day_build
        try:
            q = _Q()
            dw = gui_worker.DayMatrixCompareWorker(
                "ssor", [("2026-07-11", "ramp_summary")], str(day_dest), q,
                threading.Event())
            dw.run()
        finally:
            gui_worker_matrix.day_matrix.build_day_cell = saved_day_build
        check("non-empty Day worker leaves foreign destination content unclaimed",
              day_calls == [1] and sentinel.read_text(encoding="utf-8") == "mine"
              and not (foreign / owned_dir.OWNER_MARKER).exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def long_write_boundary_checks():
    print("Long-running export/matrix writes revalidate ownership at save/commit:")
    import artifact_store
    import exporter
    import gui_worker_export
    from events import ConsolidateResult

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_write_boundary_"))
    try:
        # Export: replace the leased root after report generation but before the
        # save strategy is entered. The Events callback must stop at _attempt_route's
        # immediate pre-save boundary.
        export_root = tmp / "export-root"
        export_lease = owned_dir.require_owned_dir_lease(export_root, kind="store")
        export_moved = tmp / "export-root-owned-moved"
        export_root.rename(export_moved)
        export_root.mkdir()
        foreign = export_root / "personal-budget.xlsx"
        foreign.write_text("mine", encoding="utf-8")
        ew = gui_worker_export.ExportWorker(
            [], _Q(), threading.Event(), threading.Event(), out_base=export_root)
        ew._owned_root_lease = export_lease
        events = ew._build_events()
        saves = []
        spec = type("Spec", (), {
            "save": lambda _self, *_a: saves.append(1),
        })()
        page = type("Page", (), {"wait_for_timeout": lambda *_a: None})()
        saved_generate = exporter._generate_route
        saved_shot = exporter.maybe_screenshot
        exporter._generate_route = lambda *_a, **_k: "ready"
        exporter.maybe_screenshot = lambda *_a, **_k: None
        stopped = False
        try:
            exporter._attempt_route(
                page, spec, "001", "Route 001:", export_root / "report.xlsx",
                events, 1_000)
        except Exception:
            stopped = True
        finally:
            exporter._generate_route = saved_generate
            exporter.maybe_screenshot = saved_shot
        check("export lease loss is detected immediately before spec.save",
              stopped and saves == [] and foreign.read_text(encoding="utf-8") == "mine")

        # Matrix: let the producer finish its temp file, then replace the owned
        # comparisons root. commit_workbook must reject the final os.replace and
        # retain the foreign replacement byte-for-byte.
        comparisons = tmp / "matrix-root" / "comparisons"
        matrix_lease = owned_dir.require_owned_dir_lease(
            comparisons, kind="comparisons")
        comparisons_moved = tmp / "comparisons-owned-moved"
        final = comparisons / "cell.xlsx"
        replacement_sentinel = comparisons / "personal.xlsx"

        def _produce_then_replace(candidate):
            Path(candidate).write_bytes(b"candidate")
            comparisons.rename(comparisons_moved)
            comparisons.mkdir()
            replacement_sentinel.write_text("mine", encoding="utf-8")
            return ConsolidateResult(status="ok", output_path=str(candidate))

        result = artifact_store.commit_workbook(
            final, _produce_then_replace, commit_guard=matrix_lease.guard)
        check("matrix commit guard rejects a root replacement after production",
              result.status == "error" and not final.exists()
              and replacement_sentinel.read_text(encoding="utf-8") == "mine")
        retained = [p for p in comparisons_moved.iterdir() if ".tmp-" in p.name]
        check("rejected matrix commit does not delete through the replacement path",
              len(retained) == 1 and retained[0].read_bytes() == b"candidate")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def staging_identity_checks():
    print("Export staging is exclusive, plain, and identity-bound:")
    import exporter
    import exporter_parallel
    import gui_worker_export
    import reports

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_stage_"))
    links = []
    try:
        spec = next(s for _label, _fmt, s in reports.EXPORT_REPORTS
                    if s.subdir == "ramp_detail")

        # A predictable stale/foreign stage is never cleared on sight.
        blocked_root = tmp / "blocked-root"
        blocked_lease = owned_dir.require_owned_dir_lease(blocked_root, kind="store")
        blocked_stage = blocked_root / f"{spec.subdir}.staging"
        blocked_stage.mkdir()
        blocked_sentinel = blocked_stage / "personal-budget.xlsx"
        blocked_sentinel.write_text("mine", encoding="utf-8")
        blocked_worker = gui_worker_export.ExportWorker(
            [], _Q(), threading.Event(), threading.Event(), out_base=blocked_root)
        blocked_worker._owned_root_lease = blocked_lease
        refused = False
        try:
            blocked_worker._prep_edition(spec)
        except owned_dir.OwnershipError:
            refused = True
        check("pre-existing normal staging is refused, not recursively cleared",
              refused and blocked_sentinel.read_text(encoding="utf-8") == "mine")

        # A stage symlink/junction cannot redirect creation or cleanup outside.
        linked_root = tmp / "linked-root"
        linked_lease = owned_dir.require_owned_dir_lease(linked_root, kind="store")
        outside = tmp / "stage-external"
        outside.mkdir()
        outside_sentinel = outside / "personal.xlsx"
        outside_sentinel.write_text("mine", encoding="utf-8")
        linked_stage = linked_root / f"{spec.subdir}.staging"
        linked = _make_dir_link(linked_stage, outside)
        check("staging symlink/junction fixture is executable", linked)
        if linked:
            links.append(linked_stage)
            linked_worker = gui_worker_export.ExportWorker(
                [], _Q(), threading.Event(), threading.Event(), out_base=linked_root)
            linked_worker._owned_root_lease = linked_lease
            refused = False
            try:
                linked_worker._prep_edition(spec)
            except owned_dir.OwnershipError:
                refused = True
            check("linked staging is refused before any external mutation",
                  refused and outside_sentinel.read_text(encoding="utf-8") == "mine")

        # Replacing a stage with an ordinary directory (not merely a link) after
        # capture must stop the immediate pre-save guard and cleanup.
        raced_root = tmp / "raced-root"
        raced_lease = owned_dir.require_owned_dir_lease(raced_root, kind="store")
        worker = gui_worker_export.ExportWorker(
            [], _Q(), threading.Event(), threading.Event(), out_base=raced_root)
        worker._owned_root_lease = raced_lease
        _live, stage, _run_spec, _run_dir = worker._prep_edition(spec)
        moved_stage = raced_root / f"{spec.subdir}.staging-original"
        stage.rename(moved_stage)
        stage.mkdir()
        replacement_sentinel = stage / "personal-budget.xlsx"
        replacement_sentinel.write_text("mine", encoding="utf-8")
        saves = []
        fake_spec = type("Spec", (), {
            "save": lambda _self, *_a: saves.append(1),
        })()
        page = type("Page", (), {"wait_for_timeout": lambda *_a: None})()
        saved_generate = exporter._generate_route
        saved_shot = exporter.maybe_screenshot
        exporter._generate_route = lambda *_a, **_k: "ready"
        exporter.maybe_screenshot = lambda *_a, **_k: None
        stopped = False
        try:
            exporter._attempt_route(
                page, fake_spec, "001", "Route 001:", stage / "route.xlsx",
                worker._build_events(), 1_000)
        except Exception:
            stopped = True
        finally:
            exporter._generate_route = saved_generate
            exporter.maybe_screenshot = saved_shot
        cleanup_refused = False
        try:
            worker._discard_stage(stage, "replacement cleanup")
        except owned_dir.OwnershipError:
            cleanup_refused = True
        check("ordinary staging replacement is rejected before every route save",
              stopped and saves == [])
        fast_events = exporter_parallel._worker_events(
            worker._build_events(), threading.Event(), 1)
        check("fast-mode worker preserves the same stage-bound destination guard",
              callable(getattr(fast_events, "destination_guard", None))
              and not fast_events.destination_guard(stage / "route.xlsx"))
        check("ordinary staging replacement is retained during cleanup",
              cleanup_refused
              and replacement_sentinel.read_text(encoding="utf-8") == "mine")

        # Even the exact stage identity is retained if a linked child appears;
        # recursive cleanup/promotion never walks it.
        tree_root = tmp / "tree-root"
        tree_lease = owned_dir.require_owned_dir_lease(tree_root, kind="store")
        tree_worker = gui_worker_export.ExportWorker(
            [], _Q(), threading.Event(), threading.Event(), out_base=tree_root)
        tree_worker._owned_root_lease = tree_lease
        _live, tree_stage, _rs, _rd = tree_worker._prep_edition(spec)
        tree_link = tree_stage / "linked-child"
        linked = _make_dir_link(tree_link, outside)
        check("nested staging junction fixture is executable", linked)
        if linked:
            links.append(tree_link)
            cleanup_refused = False
            try:
                tree_worker._discard_stage(tree_stage, "linked-tree cleanup")
            except owned_dir.OwnershipError:
                cleanup_refused = True
            check("recursive stage cleanup rejects a linked child",
                  cleanup_refused
                  and outside_sentinel.read_text(encoding="utf-8") == "mine")
    finally:
        for link in reversed(links):
            _remove_dir_link(link)
        shutil.rmtree(tmp, ignore_errors=True)


def consolidation_boundary_checks():
    print("Consolidation workbook/outcome writes stay under the leased identity:")
    import consolidation_meta
    import consolidate_ramp_detail
    import outcome
    from events import ConsolidateResult
    from openpyxl import Workbook

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_consolidation_"))
    links = []
    try:
        # Replace the normal (non-link) root only at the shared consolidator's
        # final pre-replace callback. The foreign replacement must not receive
        # the workbook or candidate cleanup.
        root = tmp / "store"
        lease = owned_dir.require_owned_dir_lease(root, kind="store")
        inputs = root / "ramp_detail"
        inputs.mkdir()
        src = inputs / "ssor-prod_route_001.xlsx"
        wb = Workbook()
        wb.active.title = consolidate_ramp_detail.SHEET_NAME
        wb.active.append(["Value"])
        wb.active.append([1])
        wb.save(src)
        out = root / "consolidated" / "combined.xlsx"
        moved = tmp / "store-original"
        replacement_sentinel = root / "personal-budget.xlsx"
        guard_calls = [0]

        def _replace_at_final(path):
            guard_calls[0] += 1
            if guard_calls[0] == 3:
                root.rename(moved)
                root.mkdir()
                replacement_sentinel.write_text("mine", encoding="utf-8")
            return lease.is_safe_descendant(path)

        res = consolidate_ramp_detail.consolidate(
            input_dir=inputs, out_path=out, commit_guard=_replace_at_final)
        check("shared consolidator rejects a normal root replacement at final commit",
              res.status != "ok" and not out.exists())
        check("final-workbook replacement sentinel is unchanged",
              replacement_sentinel.read_text(encoding="utf-8") == "mine")

        # Outcome publication revalidates before the temp write and again before
        # os.replace; losing the root between them must not publish into the
        # replacement pathname or clean through it.
        side_root = tmp / "sidecar-store"
        side_lease = owned_dir.require_owned_dir_lease(side_root, kind="store")
        side_dir = side_root / "consolidated"
        side_dir.mkdir()
        workbook = side_dir / "combined.xlsx"
        workbook.write_bytes(b"workbook")
        side_moved = tmp / "sidecar-store-original"
        side_sentinel = side_root / "personal.txt"
        side_calls = [0]

        def _replace_before_sidecar_publish(path):
            side_calls[0] += 1
            if side_calls[0] == 4:
                side_root.rename(side_moved)
                side_root.mkdir()
                side_sentinel.write_text("mine", encoding="utf-8")
            return side_lease.is_safe_descendant(path)

        ok = consolidation_meta.write_outcome(
            workbook,
            ConsolidateResult(status="ok", completion=outcome.PARTIAL,
                              skipped_inputs=1),
            commit_guard=_replace_before_sidecar_publish)
        check("outcome sidecar rejects a normal root replacement before publish",
              ok is False
              and not consolidation_meta.meta_path(workbook).exists())
        check("outcome-sidecar replacement sentinel is unchanged",
              side_sentinel.read_text(encoding="utf-8") == "mine")

        # A linked consolidated child is rejected before even opening the
        # deterministic sidecar temp path.
        link_root = tmp / "linked-sidecar-store"
        link_lease = owned_dir.require_owned_dir_lease(link_root, kind="store")
        external = tmp / "sidecar-external"
        external.mkdir()
        external_book = external / "combined.xlsx"
        external_book.write_bytes(b"external-workbook")
        external_sentinel = external / "personal.txt"
        external_sentinel.write_text("mine", encoding="utf-8")
        linked_dir = link_root / "consolidated"
        linked = _make_dir_link(linked_dir, external)
        check("outcome-sidecar junction fixture is executable", linked)
        if linked:
            links.append(linked_dir)
            linked_book = linked_dir / "combined.xlsx"
            ok = consolidation_meta.write_outcome(
                linked_book,
                ConsolidateResult(status="ok", completion=outcome.PARTIAL,
                                  skipped_inputs=1),
                commit_guard=link_lease.is_safe_descendant)
            check("linked sidecar destination is rejected before mutation",
                  ok is False
                  and not consolidation_meta.meta_path(external_book).exists()
                  and external_sentinel.read_text(encoding="utf-8") == "mine")
    finally:
        for link in reversed(links):
            _remove_dir_link(link)
        shutil.rmtree(tmp, ignore_errors=True)


def pdf_scratch_guard_checks():
    print("PDF conversion scratch deletes/saves are identity-bound:")
    from events import Events
    from pdf_table_lib import run_pdf_conversion

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_pdf_scratch_"))
    links = []
    try:
        source = tmp / "inputs"
        source.mkdir()
        (source / "route_001.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

        def _run(root, conv, out, guard, converted=None, writes=None):
            def _convert(*_args):
                if converted is not None:
                    converted.append(1)
                return "ok", "001", [[1]]

            return run_pdf_conversion(
                in_dir=source, out=out, conv=conv, deps_ok=True,
                events=Events(), confirm_overwrite=lambda _p: True,
                report_name="Probe", banner_title="Probe",
                export_hint="export", unreadable_hint="unreadable",
                converted_prefix="probe",
                convert_one=_convert,
                write_one=lambda _rows, path: (
                    writes.append(Path(path)) if writes is not None else None),
                finalize=lambda *_a: None,
                consolidate_kwargs={"sheet_name": "Probe", "report_name": "Probe",
                                    "title": "Probe"},
                commit_guard=guard)

        # Replace the ordinary scratch directory after stale names were listed,
        # immediately before the first delete.
        root = tmp / "delete-root"
        lease = owned_dir.require_owned_dir_lease(root, kind="comparisons")
        conv = root / "converted"
        conv.mkdir()
        stale = conv / "probe_route_999.xlsx"
        stale.write_bytes(b"old")
        moved = root / "converted-original"
        replacement_sentinel = conv / "personal.xlsx"
        calls = [0]

        def _replace_before_delete(path):
            calls[0] += 1
            if calls[0] == 3:
                conv.rename(moved)
                conv.mkdir()
                replacement_sentinel.write_text("mine", encoding="utf-8")
            return lease.is_safe_descendant(path)

        converted = []
        res = _run(root, conv, root / "combined.xlsx", _replace_before_delete,
                   converted=converted)
        check("normal scratch replacement blocks stale-file deletion",
              res.status == "error"
              and (moved / stale.name).exists() and converted == [])
        check("scratch-delete replacement sentinel is unchanged",
              replacement_sentinel.read_text(encoding="utf-8") == "mine")

        # Replace an empty scratch directory at the per-route save boundary.
        save_root = tmp / "save-root"
        save_lease = owned_dir.require_owned_dir_lease(
            save_root, kind="comparisons")
        save_conv = save_root / "converted"
        save_moved = save_root / "converted-original"
        save_sentinel = save_conv / "personal.xlsx"
        save_calls = [0]

        def _replace_before_save(path):
            save_calls[0] += 1
            if save_calls[0] == 4:
                save_conv.rename(save_moved)
                save_conv.mkdir()
                save_sentinel.write_text("mine", encoding="utf-8")
            return save_lease.is_safe_descendant(path)

        writes = []
        res = _run(save_root, save_conv, save_root / "combined.xlsx",
                   _replace_before_save, writes=writes)
        check("normal scratch replacement blocks the per-route workbook save",
              res.status == "error" and writes == [])
        check("scratch-save replacement sentinel is unchanged",
              save_sentinel.read_text(encoding="utf-8") == "mine")

        # A reparse scratch entry is denied before stale glob/delete or save.
        link_root = tmp / "link-root"
        link_lease = owned_dir.require_owned_dir_lease(
            link_root, kind="comparisons")
        external = tmp / "scratch-external"
        external.mkdir()
        external_sentinel = external / "personal.xlsx"
        external_sentinel.write_text("mine", encoding="utf-8")
        linked_conv = link_root / "converted"
        linked = _make_dir_link(linked_conv, external)
        check("PDF scratch junction fixture is executable", linked)
        if linked:
            links.append(linked_conv)
            res = _run(link_root, linked_conv, link_root / "combined.xlsx",
                       link_lease.is_safe_descendant)
            check("linked PDF scratch is rejected before external mutation",
                  res.status == "error"
                  and external_sentinel.read_text(encoding="utf-8") == "mine")
    finally:
        for link in reversed(links):
            _remove_dir_link(link)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("Destination ownership / Reset safety (CMP-AUD-090):")
    marker_checks()
    reset_targets_integration()
    reset_quarantine_positive()
    reset_quarantine_failure_restores()
    reset_replacement_race()
    worker_checks()
    long_write_boundary_checks()
    staging_identity_checks()
    consolidation_boundary_checks()
    pdf_scratch_guard_checks()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL OWNED-DIR CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
