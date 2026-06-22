"""CT-3 -- export-summary completion + cache-envelope migration.

Two P1 contracts proven offline:
  * gui_api._build_export_summary emits a producer/store-owned completion (and a
    per-report completion + run-level artifact) for every completion state -- a
    skipped/failed run is partial, an all-empty run is no_data, never a green
    complete. This is the value the mock mirrors (#mock parity) and the card keys on.
  * cache_envelope is a ONE-TIME forward migration: a pre-P1 raw cache dict reads as
    empty (rebuild), a current envelope round-trips, a future version reads empty.

No browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_export_summary_outcome.py
"""
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))             # version.py lives at the repo root

import outcome as oc                 # noqa: E402
import cache_envelope as ce          # noqa: E402
import matrix                        # noqa: E402
import gui_api                       # noqa: E402
from events import RunResult         # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _spec(label="Ramp Detail"):
    return types.SimpleNamespace(label=label, subdir="ramp_detail")


def _summary(results, cancelled=False, aborted=False):
    # _build_export_summary is pure over its args -- call it unbound.
    return gui_api.GuiApi._build_export_summary(None, results, cancelled, aborted=aborted)


def _rr(**kw):
    counts = {k: (["x"] * v if k in ("empty", "user_skipped", "failed", "exists") else v)
              for k, v in kw.items()}
    return RunResult(**counts)


def main():
    print("_build_export_summary -- run-level completion per state:")
    s = _summary([(_spec(), _rr(saved=5))])
    check("all saved -> complete", s["completion"] == oc.COMPLETE)
    check("...per-report completion present too", s["reports"][0]["completion"] == oc.COMPLETE)

    s = _summary([(_spec(), _rr(saved=4, failed=1))])
    check("a failed route -> partial", s["completion"] == oc.PARTIAL and s["failed_total"] == 1)

    s = _summary([(_spec(), _rr(saved=4, user_skipped=2))])
    check("a skipped route (no failed) -> partial (incomplete coverage)",
          s["completion"] == oc.PARTIAL)

    s = _summary([(_spec(), _rr(empty=10))])
    check("all empty -> no_data (not a green complete)", s["completion"] == oc.NO_DATA)

    s = _summary([(_spec(), _rr(saved=5))], cancelled=True)
    check("cancelled flag -> cancelled", s["completion"] == oc.CANCELLED)

    s = _summary([(_spec("A"), _rr(saved=5)), (_spec("B"), _rr(saved=2, failed=1))])
    check("multi-report: one failed makes the RUN partial", s["completion"] == oc.PARTIAL)

    # P1-B04: the run-level must REDUCE over per-report completions, not re-derive
    # from summed counts (where report A's saved>0 would mask report B's no_data).
    s = _summary([(_spec("A"), _rr(saved=5)), (_spec("B"), _rr(empty=9))])
    check("complete + no_data report -> run is PARTIAL, never green complete (the bug)",
          s["completion"] == oc.PARTIAL)
    check("...and the per-report completions are preserved (complete, no_data)",
          [r["completion"] for r in s["reports"]] == [oc.COMPLETE, oc.NO_DATA])
    s = _summary([(_spec("A"), _rr(saved=5))], aborted=True)
    check("an aborted multi-report run is non-complete even if the finished report was complete",
          s["completion"] != oc.COMPLETE and s["aborted"] is True)

    # producer/store-set fields win over derivation; run-level artifact = most telling.
    rr = _rr(saved=5)
    rr.completion, rr.artifact = oc.COMPLETE, oc.PROMOTED
    rr2 = _rr(saved=1, failed=1)
    rr2.completion, rr2.artifact = oc.PARTIAL, oc.PREVIOUS_PRESERVED
    s = _summary([(_spec("A"), rr), (_spec("B"), rr2)])
    check("store-set per-report completion/artifact are surfaced",
          s["reports"][0]["artifact"] == oc.PROMOTED and s["reports"][1]["artifact"] == oc.PREVIOUS_PRESERVED)
    check("run-level artifact = previous_preserved (a kept last-good wins)",
          s["artifact"] == oc.PREVIOUS_PRESERVED)

    print("cache_envelope -- one forward migration, never corrupt:")
    payload = {"ramp_summary": {"ars-prod": {"verdict": "diff", "diff_cells": 3}}}
    check("wrap/unwrap round-trips the payload", ce.unwrap(ce.wrap(payload)) == payload)
    check("a pre-P1 RAW dict reads as empty (rebuild)", ce.unwrap(payload) == {})
    check("a different schema_version reads as empty",
          ce.unwrap({"schema_version": ce.SCHEMA_VERSION + 1, "payload": payload}) == {})
    check("a non-dict reads as empty", ce.unwrap(["nope"]) == {})

    print("matrix results cache uses the envelope (end-to-end migration):")
    dest = Path(tempfile.mkdtemp())
    try:
        # seed a pre-P1 RAW dict at the cache path -> load reads it as empty (rebuild).
        p = matrix._results_path(dest, "ssor-prod")
        p.parent.mkdir(parents=True, exist_ok=True)
        import json
        p.write_text(json.dumps({"ramp_detail": {"ars-prod": {"verdict": "match"}}}), encoding="utf-8")
        check("a legacy raw cache file loads as empty (one-time rebuild)",
              matrix.load_results(dest, "ssor-prod") == {})
        # a write-then-read round-trips through the envelope.
        matrix.record_result(dest, "ssor-prod", "ramp_detail", "ars-prod", "diff", 7, 2, 123.0)
        loaded = matrix.load_results(dest, "ssor-prod")
        check("record_result -> load_results round-trips via the envelope",
              loaded.get("ramp_detail", {}).get("ars-prod", {}).get("diff_cells") == 7)
    finally:
        import shutil
        shutil.rmtree(dest, ignore_errors=True)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL EXPORT-SUMMARY / CACHE-ENVELOPE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
