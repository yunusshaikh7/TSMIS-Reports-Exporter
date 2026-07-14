"""Adversarial Matrix ownership-routing checks for CMP-AUD-090.

The Everything Matrix owns two distinct mutation roots during TSN/self cells:
``<dest>/comparisons`` for comparison artifacts and ``<dest>/<cell>`` for
persistent consolidations.  These checks prove that the worker acquires both
exact leases, routes targets to the right lease, refuses unknown/linked paths,
and fails closed when either leased directory is replaced.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidation_meta
import gui_worker_matrix
import matrix
import matrix_build
import matrix_state
import outcome
import owned_dir
import reports
from events import ConsolidateResult, Events


_failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)


def raises(fn, exc=Exception):
    try:
        fn()
    except exc:
        return True
    return False


class Queue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def _make_dir_link(link, target):
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
            link.rmdir()
    except OSError:
        pass


def _ok_result():
    return ConsolidateResult(status="ok", completion=outcome.COMPLETE,
                             verdict="same")


def worker_routing_checks(root):
    print("Everything Matrix target-aware lease routing:")
    dest = root / "routing"
    dest.mkdir()
    store = dest / "ars-test"
    owned_dir.require_owned_dir_lease(store, kind="store")
    report_dir = store / "highway_log"
    report_dir.mkdir()
    (report_dir / "route.xlsx").write_bytes(b"route")
    external = root / "external"
    external.mkdir()
    (external / "sentinel.txt").write_text("foreign", encoding="utf-8")

    original_build = matrix.build_comparison
    captured = {}

    def fake_build(_dest, _row, _cell, _mode, _baseline, **kwargs):
        guard = kwargs["commit_guard"]
        captured["guard"] = guard
        comparisons = dest / matrix.COMPARISONS_DIRNAME
        consolidated = store / "consolidated" / "combined.xlsx"
        captured["all_current"] = guard()
        captured["comparison"] = guard(comparisons / "tsn" / "cell.xlsx")
        captured["store"] = guard(consolidated)
        captured["external"] = guard(external / "escape.xlsx")

        # Exercise the real cache writer through the comparisons half.
        matrix_state.record_tsn_result(
            dest, "highway_log|tsn", "ars-test", "same", 0, 0, 1.0,
            commit_guard=guard)

        # Exercise Matrix's persistent-consolidation call site, including its
        # outcome and fingerprint sidecars, through the store half.
        class FakeConsolidator:
            @staticmethod
            def consolidate(*, input_dir, out_path, commit_guard=None, **_kwargs):
                if not commit_guard(out_path):
                    raise ValueError("guard denied fake consolidation")
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                Path(out_path).write_bytes(b"combined")
                return _ok_result()

        saved_pdf = matrix_build._pdf_store_consolidator
        saved_registry = reports.consolidator_for_subdir
        matrix_build._pdf_store_consolidator = lambda _subdir: None
        reports.consolidator_for_subdir = lambda _subdir: FakeConsolidator
        try:
            matrix_build._consolidate_store_folder(
                "test_report", report_dir, consolidated, Events(),
                commit_guard=guard)
        finally:
            matrix_build._pdf_store_consolidator = saved_pdf
            reports.consolidator_for_subdir = saved_registry
        return _ok_result()

    matrix.build_comparison = fake_build
    try:
        q = Queue()
        gui_worker_matrix.MatrixCompareWorker(
            dest, "ssor-prod", [("highway_log", "ars-test", "tsn")], q,
            threading.Event()).run()
    finally:
        matrix.build_comparison = original_build

    comparisons = dest / matrix.COMPARISONS_DIRNAME
    consolidated = store / "consolidated" / "combined.xlsx"
    check("both exact leases are current during a TSN cell",
          captured.get("all_current") is True)
    check("comparison targets route to the comparisons lease",
          captured.get("comparison") is True)
    check("persistent consolidation targets route to the store lease",
          captured.get("store") is True)
    check("an unrelated target is rejected", captured.get("external") is False)
    check("the guarded TSN cache was published under comparisons",
          (comparisons / "tsn" / "_tsn_results.json").is_file())
    check("the guarded consolidated workbook was published under the store",
          consolidated.read_bytes() == b"combined")
    check("outcome and fingerprint sidecars stayed under the store",
          consolidation_meta.meta_path(consolidated).is_file()
          and Path(str(consolidated) + ".fingerprint.json").is_file())

    guard = captured["guard"]
    anchor = comparisons / "tsn" / ".evidence-temp"
    anchor.mkdir()
    anchor_id = owned_dir.directory_identity(anchor)
    check("a bound evidence temp descendant is accepted",
          guard(anchor / "image.png", anchor_path=anchor,
                anchor_identity=anchor_id))
    check("a wrong evidence temp identity is rejected",
          not guard(anchor / "image.png", anchor_path=anchor,
                    anchor_identity=(-1, -1)))

    # A linked child must not redirect either authority to foreign content.
    linked_cmp = comparisons / "linked"
    linked_store = store / "linked"
    made_cmp = _make_dir_link(linked_cmp, external)
    made_store = _make_dir_link(linked_store, external)
    check("comparison/store descendant link fixtures are executable",
          made_cmp and made_store)
    if made_cmp and made_store:
        check("a linked comparisons descendant is rejected",
              not guard(linked_cmp / "escape.xlsx"))
        check("a linked store descendant is rejected",
              not guard(linked_store / "escape.xlsx"))
        check("foreign data behind both links is unchanged",
              (external / "sentinel.txt").read_text(encoding="utf-8") == "foreign")

        # The real cache writer must raise rather than swallow ownership loss.
        check("cache publication through a linked baseline raises fail-closed",
              raises(lambda: matrix_state.record_result(
                  dest, "linked", "row", "cell", "same", 0, 0, 1.0,
                  commit_guard=guard), ValueError))
        check("linked cache publication wrote nothing outside",
              not (external / "_results.json").exists())

        # Matrix's consolidation boundary must reject the linked destination
        # before a consolidator can touch it.
        check("persistent consolidation through a linked child raises",
              raises(lambda: matrix_build._consolidate_store_folder(
                  "test_report", report_dir, linked_store / "combined.xlsx",
                  Events(), commit_guard=guard), ValueError))
    _remove_dir_link(linked_cmp)
    _remove_dir_link(linked_store)

    # The PDF conversion driver binds its scratch identity internally. Matrix's
    # outer cleanup must preserve that same binding instead of deleting a
    # foreign ordinary-directory replacement after the driver returns.
    scratch = {}

    class ReplacingPdfConsolidator:
        @staticmethod
        def consolidate(*, out_path, converted_dir, commit_guard=None, **_kwargs):
            converted_dir = Path(converted_dir)
            moved = converted_dir.with_name(converted_dir.name + "-moved")
            converted_dir.rename(moved)
            converted_dir.mkdir()
            sentinel = converted_dir / "foreign.txt"
            sentinel.write_text("foreign", encoding="utf-8")
            scratch.update(replacement=converted_dir, moved=moved,
                           sentinel=sentinel,
                           denied=not commit_guard(Path(out_path)))
            return ConsolidateResult(status="error", message="replacement detected")

    saved_pdf = matrix_build._pdf_store_consolidator
    matrix_build._pdf_store_consolidator = lambda _subdir: ReplacingPdfConsolidator
    try:
        replaced = matrix_build._consolidate_store_folder(
            "test_pdf", report_dir, store / "consolidated" / "pdf.xlsx",
            Events(), commit_guard=guard)
    finally:
        matrix_build._pdf_store_consolidator = saved_pdf
    check("PDF scratch replacement invalidates the bound driver guard",
          replaced.status == "error" and scratch.get("denied") is True)
    check("Matrix cleanup retains an ordinary foreign scratch replacement",
          scratch["sentinel"].read_text(encoding="utf-8") == "foreign"
          and scratch["moved"].is_dir())

    linked_scratch = {}

    class LinkedScratchPdfConsolidator:
        @staticmethod
        def consolidate(*, converted_dir, **_kwargs):
            converted_dir = Path(converted_dir)
            link = converted_dir / "linked-child"
            linked_scratch.update(root=converted_dir, link=link,
                                  made=_make_dir_link(link, external))
            return ConsolidateResult(status="error", message="linked child")

    matrix_build._pdf_store_consolidator = lambda _subdir: LinkedScratchPdfConsolidator
    try:
        matrix_build._consolidate_store_folder(
            "test_pdf", report_dir, store / "consolidated" / "pdf-link.xlsx",
            Events(), commit_guard=guard)
    finally:
        matrix_build._pdf_store_consolidator = saved_pdf
    check("nested PDF scratch link fixture is executable",
          linked_scratch.get("made") is True)
    check("Matrix recursive cleanup retains scratch with a linked child",
          linked_scratch["root"].is_dir()
          and (external / "sentinel.txt").read_text(encoding="utf-8") == "foreign")
    _remove_dir_link(linked_scratch["link"])

    # Replacing either active root invalidates the whole cell publication, even
    # when a later check names a path under the other still-current root.
    moved_store = dest / "ars-test-moved"
    store.rename(moved_store)
    store.mkdir()
    decoy = store / "personal.txt"
    decoy.write_text("mine", encoding="utf-8")
    check("store replacement invalidates the combined guard",
          not guard() and not guard(comparisons / "tsn" / "late.xlsx"))
    check("the foreign replacement is untouched", decoy.read_text() == "mine")


def lazy_store_and_replacement_checks(root):
    print("lazy store lease and comparisons replacement:")
    original_build = matrix.build_comparison

    # An env-only comparison reads an unowned store but writes only comparisons;
    # it must not adopt or require a store lease.
    dest = root / "env-only"
    dest.mkdir()
    foreign_store = dest / "ars-test"
    foreign_store.mkdir()
    sentinel = foreign_store / "mine.txt"
    sentinel.write_text("foreign", encoding="utf-8")
    captured = {}

    def fake_env(_dest, _row, _cell, _mode, _baseline, **kwargs):
        guard = kwargs["commit_guard"]
        captured["guard"] = guard
        captured["comparison"] = guard(
            dest / matrix.COMPARISONS_DIRNAME / "ssor-prod" / "cell.xlsx")
        captured["foreign_store"] = guard(foreign_store / "consolidated" / "x.xlsx")
        return _ok_result()

    matrix.build_comparison = fake_env
    try:
        gui_worker_matrix.MatrixCompareWorker(
            dest, "ssor-prod", [("ramp_summary", "ars-test", "env")], Queue(),
            threading.Event()).run()
    finally:
        matrix.build_comparison = original_build
    check("env mode runs without claiming its read-only store", "guard" in captured)
    check("env mode still authorizes its comparison output",
          captured.get("comparison") is True)
    check("env mode has no authority over the unowned store",
          captured.get("foreign_store") is False
          and not owned_dir.is_owned(foreign_store, kind="store"))
    check("the read-only foreign store is unchanged", sentinel.read_text() == "foreign")

    guard = captured["guard"]
    comparisons = dest / matrix.COMPARISONS_DIRNAME
    moved = dest / "comparisons-moved"
    comparisons.rename(moved)
    comparisons.mkdir()
    replacement = comparisons / "mine.txt"
    replacement.write_text("foreign", encoding="utf-8")
    check("comparisons replacement invalidates its guard",
          not guard() and not guard(comparisons / "ssor-prod" / "late.xlsx"))
    check("the comparisons replacement is untouched",
          replacement.read_text(encoding="utf-8") == "foreign")

    # A TSN/self cell must acquire an already-owned store, never create/adopt it.
    blocked = root / "blocked-non-env"
    blocked.mkdir()
    unowned = blocked / "ars-test"
    unowned.mkdir()
    (unowned / "personal.xlsx").write_bytes(b"mine")
    calls = []
    matrix.build_comparison = lambda *_a, **_k: calls.append(True) or _ok_result()
    try:
        q = Queue()
        gui_worker_matrix.MatrixCompareWorker(
            blocked, "ssor-prod", [("highway_log", "ars-test", "tsn")], q,
            threading.Event()).run()
    finally:
        matrix.build_comparison = original_build
    check("non-env mode refuses an unowned existing store before build", not calls)
    check("the refused store is neither stamped nor changed",
          not owned_dir.is_owned(unowned, kind="store")
          and (unowned / "personal.xlsx").read_bytes() == b"mine")


def evidence_worker_checks(root):
    print("Everything on-demand evidence lease:")
    dest = root / "evidence"
    dest.mkdir()
    comparisons = owned_dir.require_owned_dir_lease(
        dest / matrix.COMPARISONS_DIRNAME, kind="comparisons").path
    external = root / "evidence-external"
    external.mkdir()
    observed = {}

    def resolver(_events, commit_guard=None):
        observed["called"] = True
        observed["allowed"] = commit_guard(
            comparisons / "tsn" / "cell (evidence).xlsx")
        observed["external"] = commit_guard(external / "escape.xlsx")
        return _ok_result()

    gui_worker_matrix.MatrixEvidenceWorker(
        resolver, "highway_log", "ars-test", Queue(), threading.Event(),
        comparisons_dest=dest).run()
    check("Everything evidence resolver receives a live comparisons guard",
          observed.get("called") and observed.get("allowed") is True)
    check("Everything evidence guard rejects an external target",
          observed.get("external") is False)

    missing = root / "evidence-missing"
    missing.mkdir()
    called = []
    q = Queue()
    gui_worker_matrix.MatrixEvidenceWorker(
        lambda *_a, **_k: called.append(True) or _ok_result(),
        "highway_log", "ars-test", q, threading.Event(),
        comparisons_dest=missing).run()
    check("on-demand evidence refuses a missing/unowned comparisons root",
          not called and any(item[0] == "matrix_done"
                             and item[1]["errors"] == 1 for item in q.items))

    # Day evidence remains app-private and keeps its legacy resolver shape.
    day_called = []
    gui_worker_matrix.MatrixEvidenceWorker(
        lambda _events: day_called.append(True) or _ok_result(),
        "highway_log", "2026-07-11", Queue(), threading.Event()).run()
    check("Day evidence remains app-private and does not require a batch lease",
          day_called == [True])


def main():
    root = Path(tempfile.mkdtemp(prefix="tsmis_matrix_ownership_"))
    try:
        worker_routing_checks(root)
        lazy_store_and_replacement_checks(root)
        evidence_worker_checks(root)
    finally:
        # Link fixtures are explicitly removed in their test before recursive cleanup.
        shutil.rmtree(root, ignore_errors=True)
    if _failures:
        print("\nFAILED:")
        for name in _failures:
            print(" -", name)
        raise SystemExit(1)
    print("\nALL MATRIX OWNERSHIP CHECKS PASSED")


if __name__ == "__main__":
    main()
