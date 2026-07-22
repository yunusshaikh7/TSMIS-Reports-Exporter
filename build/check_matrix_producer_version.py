"""CMP-AUD-084 — a semantic producer version invalidates stale Matrix caches.

The Matrix cache envelope's schema version describes only the JSON record SHAPE.
Before this gate, neither a comparison cache record nor a persistent consolidation
recorded which comparator / parser / normalizer / consolidator produced it, so a
cell built at v0.18 kept its old ``match`` verdict fresh after years of pipeline
fixes (the finding's exact "caches introduced at v0.18 can still pass" case).

This proves the fix end to end, with EVERY other freshness signal held constant
(mtime, input fingerprint, output generation, TSN identity all match) so the
producer version is the SOLE differentiator — i.e. without the gate the record
would read fresh (the red mechanism):

  * comparison cache — a record stamped by the CURRENT pipeline reads fresh; the
    SAME record read after an app upgrade reads stale with reason
    ``producer_version_changed``; a rebuild re-stamps and reads fresh once; a
    legacy record (no ``producer_versions`` field) reads stale;
  * persistent consolidation — a workbook stamped by the current app reads not
    stale; after an upgrade it reads stale (a corrected parser must re-parse
    rather than feed pre-fix rows to the fixed comparator); a rebuild re-stamps
    and reads not stale once; a legacy sidecar (no stamp) reads stale.

A shipped comparator / parser / normalizer fix always rides a new release, so the
app version is the release-granular semantic signal for all of them — one upgrade
invalidates every affected cell/consolidation exactly once (a rebuild, never a
silent stale verdict). Record-shape migration stays the SEPARATE cache-envelope
version.

Real openpyxl; no browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_producer_version.py
"""
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_ROOT / "scripts"), str(_ROOT)]   # scripts + repo root (version.py)

from _checklib import write_comparison_stub  # noqa: E402

import artifact_store        # noqa: E402
import consolidation_meta    # noqa: E402
import matrix                # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _xlsx(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook(); wb.active["A1"] = "x"; wb.save(str(path))


@contextlib.contextmanager
def _app_upgraded_to(new_version):
    """Simulate an app upgrade: producer_app_version() is the ONE point both
    freshness gates read (the comparison cache via matrix.producer_identity and the
    consolidation stamp/read), so patching it here moves the whole running pipeline
    to `new_version` for the duration."""
    saved = consolidation_meta.producer_app_version
    consolidation_meta.producer_app_version = lambda: new_version
    try:
        yield
    finally:
        consolidation_meta.producer_app_version = saved


def _comparison(path):
    """A real committed comparison workbook + its strict generation sidecar."""
    counts = ComparisonCounts(
        known=True, paired_rows=1, side_a_only_rows=0, differing_rows=0,
        differing_cells=0, per_field_counts={}, asserted_cells=0)
    typed = ComparisonOutcome(status="ok", completion="complete", verdict="match",
                              counts=counts, pairing_quality="exact")

    def produce(tmp):
        write_comparison_stub(tmp)
        return ConsolidateResult(
            status="ok", output_path=str(tmp), verdict="match",
            completion="complete", skipped_inputs=0, failed_inputs=0,
            comparison_outcome=typed)

    return artifact_store.commit_workbook(path, produce, requested_mode="values")


def _complete_consolidation(path):
    result = ConsolidateResult(
        status="ok", output_path=str(path), completion="complete",
        skipped_inputs=0, failed_inputs=0)
    if not consolidation_meta.write_outcome(path, result):
        raise AssertionError("could not publish consolidation outcome fixture")


# --------------------------------------------------------------------------- #
def test_comparison_cache_version_gate(tmp):
    print("comparison cache — a superseded pipeline can never certify fresh:")
    store = tmp / "store"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"a" * 10)
    out_path = tmp / "cmp.xlsx"
    result = _comparison(out_path)
    cmp_m = out_path.stat().st_mtime
    gen = result.artifact_generation.generation_id
    # A record where EVERY legacy signal matches the workbook — only the producer
    # version can make it stale.
    rec = {"verdict": "match", "diff_cells": 0, "one_sided": 0,
           "built_at_mtime": cmp_m, "completion": "complete",
           "input_fingerprint": artifact_store.fingerprint(store),
           "generation_id": gen,
           "producer_versions": matrix.producer_identity()}
    sources = [{"name": "cell", "present": True, "mtime": cmp_m - 100},
               {"name": "tsn", "present": True, "mtime": cmp_m - 100}]

    st = matrix._cmp_state(out_path, sources, rec, fp_folders=(store,))
    check("a record stamped by the CURRENT pipeline reads fresh",
          st["stale"] is False and st["reason"] == "fresh")

    with _app_upgraded_to("99.0.0-next"):
        # The SAME otherwise-valid record now trails the running pipeline.
        st2 = matrix._cmp_state(out_path, sources, rec, fp_folders=(store,))
        check("...but after an app upgrade it reads STALE", st2["stale"] is True)
        check("...with reason 'producer_version_changed'",
              st2["reason"] == "producer_version_changed")

        # A rebuild re-stamps with the now-current version -> fresh (rebuild once).
        rebuilt = dict(rec, producer_versions=matrix.producer_identity())
        st3 = matrix._cmp_state(out_path, sources, rebuilt, fp_folders=(store,))
        check("a rebuild re-stamps and reads fresh once (rebuild-once, not looping)",
              st3["stale"] is False and st3["reason"] == "fresh")

    # A legacy record (pre-CMP-AUD-084 — no producer_versions field) reads stale.
    legacy = dict(rec); legacy.pop("producer_versions")
    st4 = matrix._cmp_state(out_path, sources, legacy, fp_folders=(store,))
    check("a legacy record with no producer version reads stale (migrate once)",
          st4["stale"] is True and st4["reason"] == "producer_version_changed")


def test_consolidation_version_gate(tmp):
    print("persistent consolidation — an older parser's workbook must re-parse:")
    store = tmp / "cstore"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"d" * 8)
    consolidated = tmp / "consolidated" / "combined.xlsx"
    _xlsx(consolidated)
    artifact_store.write_consolidated_fingerprint(consolidated, store)
    _complete_consolidation(consolidated)      # stamps the CURRENT app version

    check("a freshly-built consolidation is not stale",
          matrix._consolidated_stale(consolidated, store) is False)

    with _app_upgraded_to("99.0.0-next"):
        check("...but after an app upgrade (a shipped parser fix) it reads STALE",
              matrix._consolidated_stale(consolidated, store) is True)
        # Rebuild under the new version re-stamps the outcome sidecar.
        _complete_consolidation(consolidated)
        check("a rebuild re-stamps and reads not stale once (rebuild-once)",
              matrix._consolidated_stale(consolidated, store) is False)

    # A legacy sidecar with no producer stamp (pre-CMP-AUD-084) reads stale.
    meta = consolidation_meta.meta_path(consolidated)
    payload = json.loads(meta.read_text(encoding="utf-8"))
    payload.pop("producer_app_version", None)          # strip the stamp
    meta.write_text(json.dumps(payload), encoding="utf-8")
    os.utime(meta, None)
    # keep the sidecar mtime-coupled to the workbook so only the missing stamp matters
    os.utime(meta, (consolidated.stat().st_atime, consolidated.stat().st_mtime))
    check("a legacy consolidation with no producer stamp reads stale (migrate once)",
          matrix._consolidated_stale(consolidated, store) is True)


def main():
    for fn in (test_comparison_cache_version_gate, test_consolidation_version_gate):
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
    print()
    if _failures:
        print(f"FAILED {len(_failures)} check(s): {_failures}")
        return 1
    print("All CMP-AUD-084 producer-version checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
