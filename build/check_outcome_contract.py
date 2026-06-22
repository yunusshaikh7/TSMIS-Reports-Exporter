"""CT-1 -- the orthogonal outcome contract (scripts/outcome.py).

Characterizes every row of the §C.1 export-completion table, the consolidation
completion mapping, and the promote/compare/artifact gating. Pure stdlib + the
app's outcome/events modules; no browser/openpyxl/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_outcome_contract.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import outcome as oc            # noqa: E402
from events import RunResult, ConsolidateResult   # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _rr(saved=0, empty=0, skipped=0, failed=0, exists=0):
    return RunResult(saved=saved, empty=["e"] * empty, user_skipped=["s"] * skipped,
                     failed=["f"] * failed, exists=["x"] * exists)


def main():
    print("export_completion -- every §C.1 route-status row:")
    check("failed>0 -> partial", oc.export_completion(5, 0, 0, 0, 1) == oc.PARTIAL)
    check("skipped>0 (no failed) -> partial", oc.export_completion(5, 0, 0, 2, 0) == oc.PARTIAL)
    check("saved>0, no failed/skipped -> complete", oc.export_completion(5, 0, 3, 0, 0) == oc.COMPLETE)
    check("saved=0, empty>0 -> no_data", oc.export_completion(0, 0, 4, 0, 0) == oc.NO_DATA)
    check("exists>0 only (resume, saved=0) -> complete", oc.export_completion(0, 7, 0, 0, 0) == oc.COMPLETE)
    check("nothing at all -> no_data", oc.export_completion(0, 0, 0, 0, 0) == oc.NO_DATA)
    check("cancelled overrides any counts", oc.export_completion(5, 0, 0, 0, 0, cancelled=True) == oc.CANCELLED)
    check("failed beats present (partial, not complete)", oc.export_completion(9, 0, 0, 0, 1) == oc.PARTIAL)

    print("run_completion(RunResult):")
    check("a clean save run -> complete", oc.run_completion(_rr(saved=5)) == oc.COMPLETE)
    check("a run with a failed route -> partial", oc.run_completion(_rr(saved=4, failed=1)) == oc.PARTIAL)
    check("all-empty run -> no_data", oc.run_completion(_rr(empty=10)) == oc.NO_DATA)
    check("cancelled flag honored", oc.run_completion(_rr(saved=5), cancelled=True) == oc.CANCELLED)

    print("promote / compare gating:")
    check("only complete is promotable", oc.promotable(oc.COMPLETE)
          and not any(oc.promotable(c) for c in (oc.PARTIAL, oc.NO_DATA, oc.FAILED, oc.CANCELLED)))
    check("partial is comparable; failed/no_data/cancelled are not",
          oc.comparable(oc.PARTIAL) and oc.comparable(oc.COMPLETE)
          and not oc.comparable(oc.FAILED) and not oc.comparable(oc.NO_DATA)
          and not oc.comparable(oc.CANCELLED))

    print("artifact_after_store (F1 promotion outcome):")
    check("complete + store -> promoted", oc.artifact_after_store(oc.COMPLETE, True) == oc.PROMOTED)
    check("partial + store -> previous_preserved (last-good kept)",
          oc.artifact_after_store(oc.PARTIAL, True) == oc.PREVIOUS_PRESERVED)
    check("no_data + store -> previous_preserved",
          oc.artifact_after_store(oc.NO_DATA, True) == oc.PREVIOUS_PRESERVED)
    check("cancelled + store -> previous_preserved",
          oc.artifact_after_store(oc.CANCELLED, True) == oc.PREVIOUS_PRESERVED)
    check("complete, no store -> new_unpromoted",
          oc.artifact_after_store(oc.COMPLETE, False) == oc.NEW_UNPROMOTED)

    print("consolidate_completion (producer-owned):")
    check("all inputs in -> complete", oc.consolidate_completion(wrote=True, skipped_inputs=0, failed_inputs=0) == oc.COMPLETE)
    check("some skipped -> partial", oc.consolidate_completion(wrote=True, skipped_inputs=2, failed_inputs=0) == oc.PARTIAL)
    check("some failed -> partial", oc.consolidate_completion(wrote=True, skipped_inputs=0, failed_inputs=1) == oc.PARTIAL)
    check("nothing written, not error -> no_data", oc.consolidate_completion(wrote=False, skipped_inputs=0, failed_inputs=0) == oc.NO_DATA)
    check("errored -> failed", oc.consolidate_completion(wrote=False, skipped_inputs=0, failed_inputs=3, errored=True) == oc.FAILED)
    check("cancelled -> cancelled", oc.consolidate_completion(wrote=True, skipped_inputs=0, failed_inputs=0, cancelled=True) == oc.CANCELLED)

    print("consolidate_completion_of (field, else infer from status):")
    check("producer-set completion wins",
          oc.consolidate_completion_of(ConsolidateResult(status="ok", completion=oc.PARTIAL)) == oc.PARTIAL)
    check("legacy status=ok -> complete",
          oc.consolidate_completion_of(ConsolidateResult(status="ok")) == oc.COMPLETE)
    check("legacy status=error -> failed",
          oc.consolidate_completion_of(ConsolidateResult(status="error")) == oc.FAILED)
    check("legacy status=cancelled -> cancelled",
          oc.consolidate_completion_of(ConsolidateResult(status="cancelled")) == oc.CANCELLED)

    print("reduce_completion -- run-level over per-report completions (P1-B04):")
    check("all complete -> complete", oc.reduce_completion([oc.COMPLETE, oc.COMPLETE]) == oc.COMPLETE)
    check("complete + no_data -> partial (NOT green — the bug)",
          oc.reduce_completion([oc.COMPLETE, oc.NO_DATA]) == oc.PARTIAL)
    check("complete + partial -> partial",
          oc.reduce_completion([oc.COMPLETE, oc.PARTIAL]) == oc.PARTIAL)
    check("all no_data -> no_data", oc.reduce_completion([oc.NO_DATA, oc.NO_DATA]) == oc.NO_DATA)
    check("a failed report -> partial", oc.reduce_completion([oc.COMPLETE, oc.FAILED]) == oc.PARTIAL)
    check("cancelled flag overrides", oc.reduce_completion([oc.COMPLETE], cancelled=True) == oc.CANCELLED)
    check("aborted (didn't finish all reports) is never complete",
          oc.reduce_completion([oc.COMPLETE], aborted=True) == oc.PARTIAL)
    check("aborted with a failed report -> failed",
          oc.reduce_completion([oc.COMPLETE, oc.FAILED], aborted=True) == oc.FAILED)
    check("empty -> no_data", oc.reduce_completion([]) == oc.NO_DATA)

    print("vocabulary is closed (no stray values):")
    check("all completion constants are in COMPLETIONS",
          {oc.COMPLETE, oc.PARTIAL, oc.NO_DATA, oc.CANCELLED, oc.FAILED} == set(oc.COMPLETIONS))
    check("all artifact constants are in ARTIFACTS",
          {oc.PROMOTED, oc.NEW_UNPROMOTED, oc.PREVIOUS_PRESERVED, oc.NONE} == set(oc.ARTIFACTS))

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL OUTCOME-CONTRACT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
