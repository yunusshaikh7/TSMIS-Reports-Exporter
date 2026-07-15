"""Phase-2C: generic worker must not overwrite central comparison publication."""
import queue
import sys
import threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_worker_export as gwe  # noqa: E402
from events import ConsolidateResult  # noqa: E402


failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        failures.append(name)


def run_worker(result, writer):
    messages = queue.Queue()
    calls = []

    def consolidate_fn(**kwargs):
        calls.append(kwargs)
        return result

    worker = gwe.ConsolidateWorker(
        consolidate_fn, messages, threading.Event(), lambda _path: True,
        day="2026-07-11")
    with patch.object(gwe.consolidation_meta, "write_outcome", writer):
        worker.run()
    drained = []
    while not messages.empty():
        drained.append(messages.get_nowait())
    return drained, calls


def test_central_comparison_publication_is_not_overwritten():
    print("central comparison/generation publication ownership:")

    def must_not_write(*_args, **_kwargs):
        raise AssertionError("generic single-path writer must not run")

    for label, fields in (
            ("comparison_outcome", {"comparison_outcome": object()}),
            ("artifact_generation", {"artifact_generation": object()}),
            ("both typed fields", {"comparison_outcome": object(),
                                   "artifact_generation": object()})):
        result = ConsolidateResult(status="ok", output_path="comparison.xlsx",
                                   **fields)
        messages, calls = run_worker(result, must_not_write)
        check(f"{label}: worker invokes producer exactly once",
              len(calls) == 1 and calls[0]["day"] == "2026-07-11")
        check(f"{label}: skips generic writer and emits consolidate_done",
              messages == [("consolidate_done", result)])


def test_ordinary_consolidation_still_publishes():
    print("ordinary one-workbook consolidation remains unchanged:")
    result = ConsolidateResult(status="ok", output_path="consolidated.xlsx",
                               completion="partial", skipped_inputs=1,
                               producer_extra={"route_census": ["001"]})
    writes = []

    def write(path, observed_result, extra=None):
        writes.append((path, observed_result, extra))
        return True

    messages, _calls = run_worker(result, write)
    check("ordinary result calls generic writer exactly once with legacy "
          "path/result + the producer extra (CMP-AUD-183)",
          writes == [("consolidated.xlsx", result, {"route_census": ["001"]})])
    check("successful ordinary publication still emits consolidate_done",
          messages == [("consolidate_done", result)])


def test_ordinary_publication_failure_stays_degraded():
    print("ordinary publication failure remains the existing degraded terminal:")
    result = ConsolidateResult(status="ok", output_path="partial.xlsx",
                               completion="partial", skipped_inputs=1)
    writes = []

    def fail_write(path, observed_result, extra=None):
        writes.append((path, observed_result, extra))
        return False

    messages, _calls = run_worker(result, fail_write)
    check("failed ordinary publication still attempts the generic writer once",
          writes == [("partial.xlsx", result, None)])
    check("failed ordinary publication emits no consolidate_done",
          not any(kind == "consolidate_done" for kind, _payload in messages))
    expected = (
        "general",
        "Consolidation finished but its outcome could not be recorded; "
        "the incomplete output was discarded. Close any open copy and "
        "run it again.")
    check("failed ordinary publication retains the exact degraded error",
          messages == [("error", expected)])


if __name__ == "__main__":
    test_central_comparison_publication_is_not_overwritten()
    test_ordinary_consolidation_still_publishes()
    test_ordinary_publication_failure_stays_degraded()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {failures}")
        raise SystemExit(1)
    print("ALL CONSOLIDATE-WORKER PUBLICATION CHECKS PASSED")
