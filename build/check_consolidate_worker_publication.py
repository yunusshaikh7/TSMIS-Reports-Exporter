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

    # sidecar_published belongs here for the same reason: the TSN library build
    # writes an authoritative certificate (tsn_normalization_version + the raw
    # manifest + both identity bindings) and VERIFIES it through the production
    # status boundary. The worker's generic write reconstructs none of that, so
    # overwriting it dropped the normalizer version and the library then read
    # stale forever — every rebuild "succeeded" and never cleared it (field
    # report: "its build record carries no normalizer version").
    for label, fields in (
            ("comparison_outcome", {"comparison_outcome": object()}),
            ("artifact_generation", {"artifact_generation": object()}),
            ("sidecar_published (TSN library certificate)",
             {"sidecar_published": True}),
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


def test_producer_certificate_survives_on_disk():
    """END TO END, no patching: run the REAL worker with the REAL writer and then
    READ THE FILE.

    Every other test here patches write_outcome, so they assert a decision (was
    the writer called?) rather than an outcome (did the record survive?). That
    gap is exactly how the field bug shipped: the worker's second generic write
    landed on the same path and silently dropped the TSN library's binding facts,
    and no check noticed because none of them looked at the resulting bytes.
    """
    import json
    import tempfile

    import consolidation_meta as cm

    print("producer certificate survives the real worker (on-disk):")
    tsn_keys = ("tsn_normalization_version", "tsn_raw_manifest",
                "tsn_normalized_workbook_identity", "tsn_artifact_identity_token")

    def build_library_certificate(workbook):
        """What tsn_library.build_consolidated publishes before returning."""
        produced = ConsolidateResult(status="ok", output_path=str(workbook),
                                     completion="complete")
        assert cm.write_outcome(workbook, produced, extra={
            "tsn_normalization_version": 5,
            "tsn_raw_manifest": None,
            "tsn_normalized_workbook_identity": None,
            "tsn_artifact_identity_token": None})

    def stamp_after_worker(*, sidecar_published):
        with tempfile.TemporaryDirectory(prefix="tsmis_cert_") as raw:
            workbook = Path(raw) / "tsn_highway_log_consolidated.xlsx"
            workbook.write_bytes(b"PK-normalized-workbook")
            build_library_certificate(workbook)
            result = ConsolidateResult(status="ok", output_path=str(workbook),
                                       completion="complete")
            result.sidecar_published = sidecar_published
            # The REAL worker, the REAL consolidation_meta.write_outcome.
            messages = queue.Queue()
            gwe.ConsolidateWorker(lambda **_k: result, messages,
                                  threading.Event(), lambda _p: True,
                                  day="2026-07-11").run()
            payload = json.loads(cm.meta_path(workbook).read_text(encoding="utf-8"))
            return {k: payload.get(k, "<MISSING>") for k in tsn_keys}

    kept = stamp_after_worker(sidecar_published=True)
    check("a producer-published certificate keeps its normalizer version on disk",
          kept["tsn_normalization_version"] == 5)
    check("a producer-published certificate keeps every TSN binding fact",
          all(kept[k] != "<MISSING>" for k in tsn_keys))

    # Teeth: without the producer claim the generic write MUST destroy it. If this
    # ever stops failing, the test above has stopped proving anything.
    lost = stamp_after_worker(sidecar_published=False)
    check("without the producer claim the generic write still destroys it "
          "(proves this test has teeth)",
          lost["tsn_normalization_version"] == "<MISSING>")


if __name__ == "__main__":
    test_central_comparison_publication_is_not_overwritten()
    test_ordinary_consolidation_still_publishes()
    test_ordinary_publication_failure_stays_degraded()
    test_producer_certificate_survives_on_disk()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {failures}")
        raise SystemExit(1)
    print("ALL CONSOLIDATE-WORKER PUBLICATION CHECKS PASSED")
