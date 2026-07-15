"""CT-6 / CT-7 — identity-based freshness in the matrix + by-day engines (P2/F5).

Proves the fingerprint beats the old newest-mtime signal end-to-end:
  * CT-6a — `matrix._consolidated_stale`: a DELETED non-newest route reads the persistent
    consolidated STALE even when the consolidated is newer than every remaining route (so
    the old newest-mtime logic would wrongly read it fresh);
  * CT-6b — `matrix._cmp_state` (TSN/self cells): a recorded input fingerprint that no
    longer matches the store reads the cell stale ("inputs_changed"); a legacy record with
    no fingerprint never reads falsely stale;
  * CT-6c — `matrix.comparison_state` (cross-env cells): same, over the two env folders;
  * CT-7 — `day_matrix.day_matrix_snapshot`: a day with one report consolidated and
    another exported-but-NOT-consolidated reads day_consolidated.fresh == False (the old
    `all(... if exists)` skipped the missing one).

Real openpyxl; no browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_p2_freshness.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import artifact_store        # noqa: E402
import consolidation_meta    # noqa: E402
import matrix                # noqa: E402
import day_matrix            # noqa: E402
import paths                 # noqa: E402
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


def _complete_consolidation(path):
    result = ConsolidateResult(
        status="ok", output_path=str(path), completion="complete",
        skipped_inputs=0, failed_inputs=0)
    if not consolidation_meta.write_outcome(path, result):
        raise AssertionError("could not publish consolidation outcome fixture")


def _comparison(path, diff_cells=0, one_sided=0):
    per_field = {"0:test": diff_cells} if diff_cells else {}
    counts = ComparisonCounts(
        known=True, paired_rows=max(diff_cells, 1),
        side_a_only_rows=one_sided, differing_rows=diff_cells,
        differing_cells=diff_cells, per_field_counts=per_field,
        asserted_cells=diff_cells)
    typed = ComparisonOutcome(
        status="ok", completion="complete",
        verdict="match" if not diff_cells and not one_sided else "diff",
        counts=counts, pairing_quality="exact")

    def produce(tmp):
        _xlsx(tmp)
        return ConsolidateResult(
            status="ok", output_path=str(tmp), verdict=typed.verdict,
            completion="complete", skipped_inputs=0, failed_inputs=0,
            comparison_outcome=typed)

    return artifact_store.commit_workbook(
        path, produce, requested_mode="values")


def _at(path, when):
    os.utime(path, (when, when))


def _newest_mtime(folder):
    return max((p.stat().st_mtime for p in Path(folder).iterdir() if p.is_file()), default=None)


# --------------------------------------------------------------------------- #
def test_consolidated_stale(tmp):                             # CT-6a
    print("CT-6a _consolidated_stale — a deleted route beats newest-mtime:")
    store = tmp / "store"; store.mkdir()
    for i, name in enumerate(("r1.xlsx", "r2.xlsx", "r3.xlsx")):
        (store / name).write_bytes(b"d" * (i + 5))
        _at(store / name, 1000 + i)                  # r1=1000, r2=1001, r3=1002 (newest)
    consolidated = tmp / "consolidated" / "combined.xlsx"
    _xlsx(consolidated)
    _at(consolidated, 2000)                          # NEWER than every route
    artifact_store.write_consolidated_fingerprint(consolidated, store)
    _complete_consolidation(consolidated)

    check("a freshly-built consolidated is not stale",
          matrix._consolidated_stale(consolidated, store) is False)

    (store / "r1.xlsx").unlink()                     # delete the OLDEST (non-newest) route
    check("the consolidated is still newer than every remaining route (old logic = fresh)",
          _newest_mtime(store) < consolidated.stat().st_mtime)
    check("...yet _consolidated_stale is TRUE (fingerprint caught the delete)",
          matrix._consolidated_stale(consolidated, store) is True)

    artifact_store.write_consolidated_fingerprint(consolidated, store)
    check("re-recording the fingerprint makes it fresh again",
          matrix._consolidated_stale(consolidated, store) is False)


def test_cmp_state_fingerprint(tmp):                          # CT-6b
    print("CT-6b _cmp_state — a recorded input fingerprint that no longer matches => stale:")
    store = tmp / "tsn_store"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"a" * 10)
    (store / "r2.xlsx").write_bytes(b"b" * 20)
    out_path = tmp / "cmp_tsn.xlsx"
    result = _comparison(out_path, diff_cells=3)
    cmp_m = out_path.stat().st_mtime
    rec = {"verdict": "diff", "diff_cells": 3, "one_sided": 0, "built_at_mtime": cmp_m,
           "completion": "complete", "input_fingerprint": artifact_store.fingerprint(store),
           "generation_id": result.artifact_generation.generation_id}
    sources = [{"name": "cell", "present": True, "mtime": cmp_m - 100},
               {"name": "tsn", "present": True, "mtime": cmp_m - 100}]

    st = matrix._cmp_state(out_path, sources, rec, fp_folders=(store,))
    check("fresh when nothing changed", st["stale"] is False and st["reason"] == "fresh")
    check("...and the cached counts are surfaced", st["verdict"] == "diff" and st["diff_cells"] == 3)

    (store / "r1.xlsx").unlink()                     # delete a route -> fingerprint differs
    st2 = matrix._cmp_state(out_path, sources, rec, fp_folders=(store,))
    check("a deleted route reads the cell STALE", st2["stale"] is True)
    check("...with reason 'inputs_changed'", st2["reason"] == "inputs_changed")

    legacy = dict(rec); legacy.pop("input_fingerprint")     # a pre-P2 record (no fingerprint)
    st3 = matrix._cmp_state(out_path, sources, legacy, fp_folders=(store,))
    check("a legacy record with no fingerprint is retryable, never false-fresh",
          st3["stale"] is True and st3["reason"] == "cache_missing_or_mismatched")


def test_comparison_state_fingerprint(tmp):                   # CT-6c
    print("CT-6c comparison_state (cross-env) — input identity over both env folders:")
    dest = tmp / "envdest"
    subdir = "highway_log"
    for env in ("ssor-prod", "ars-prod"):
        (dest / env / subdir).mkdir(parents=True)
        (dest / env / subdir / "r1.xlsx").write_bytes(b"x" * 10)
        (dest / env / subdir / "r2.xlsx").write_bytes(b"y" * 10)
    out_path = matrix.comparison_path(dest, "ssor-prod", "highway_log", "ars-prod")
    result = _comparison(out_path)
    cmp_m = out_path.stat().st_mtime
    fp = matrix._cell_input_fingerprint(dest / "ars-prod" / subdir, dest / "ssor-prod" / subdir)
    results = {"highway_log": {"ars-prod": {
        "verdict": "match", "diff_cells": 0, "one_sided": 0, "built_at_mtime": cmp_m,
        "completion": "complete", "input_fingerprint": fp,
        "generation_id": result.artifact_generation.generation_id}}}
    ages = {"ssor-prod": {subdir: {"mtime": cmp_m - 50}},
            "ars-prod": {subdir: {"mtime": cmp_m - 50}}}

    st = matrix.comparison_state(dest, "ssor-prod", "highway_log", "ars-prod", subdir, ages, results)
    check("fresh when both env folders are unchanged", st["stale"] is False)

    (dest / "ars-prod" / subdir / "r1.xlsx").unlink()
    st2 = matrix.comparison_state(dest, "ssor-prod", "highway_log", "ars-prod", subdir, ages, results)
    check("a deleted route in the cell env reads the cross-env cell STALE", st2["stale"] is True)
    check("...with reason 'inputs_changed'", st2["reason"] == "inputs_changed")


def test_midcompare_race(tmp):                                # CT-6d / CMP-AUD-098
    """A mid-comparison source mutation must NEVER render fresh. The record
    binds the PRE-comparison capture (the bytes the comparator actually read);
    after the mutation that no longer matches the folder, so the cell reads
    stale even when the new source mtime precedes the output mtime (the
    finding's exact raced-fresh setup). The same test demonstrates the RED
    mechanism: a record carrying the POST-mutation fingerprint (what the
    pre-fix code recorded) reads fresh — the documented defect."""
    print("CT-6d mid-comparison mutation (CMP-AUD-098) — raced results read STALE:")
    store = tmp / "race_store"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"OLD-BYTES")
    fp_before = matrix._cell_input_fingerprint(store)

    # The comparator "reads OLD"; the source then changes to NEW before the
    # record is written (contents AND identity change; mtime kept in the past).
    (store / "r1.xlsx").write_bytes(b"NEW-BYTES-LONGER")
    past = time.time() - 100
    os.utime(store / "r1.xlsx", (past, past))
    out_path = tmp / "cmp_race.xlsx"
    result = _comparison(out_path, diff_cells=0)
    cmp_m = out_path.stat().st_mtime

    events_lines = []
    class _Ev:
        def on_log(self, s):
            events_lines.append(s)
    recorded = matrix._fingerprint_for_record(fp_before, (store,),
                                              out_path.name, _Ev())
    check("the record binds the PRE-comparison capture", recorded == fp_before)
    check("...and the race is announced", any("recorded already-stale" in s
                                              for s in events_lines))
    check("the formulas twin is SKIPPED after a race",
          matrix._twin_inputs_unchanged(fp_before, (store,), out_path.name) is False)

    sources = [{"name": "cell", "present": True, "mtime": past},
               {"name": "tsn", "present": True, "mtime": past}]
    rec = {"verdict": "match", "diff_cells": 0, "one_sided": 0,
           "built_at_mtime": cmp_m, "completion": "complete",
           "input_fingerprint": recorded,
           "generation_id": result.artifact_generation.generation_id}
    st = matrix._cmp_state(out_path, sources, rec, fp_folders=(store,))
    check("the raced 0/0 'match' reads STALE (never fresh)",
          st["stale"] is True and st["reason"] == "inputs_changed")

    # RED demonstration: the pre-fix code fingerprinted AFTER production —
    # binding the NEW identity to the OLD-bytes workbook — and rendered fresh.
    red_rec = dict(rec, input_fingerprint=matrix._cell_input_fingerprint(store))
    red = matrix._cmp_state(out_path, sources, red_rec, fp_folders=(store,))
    check("(red mechanism) a post-mutation fingerprint would have read FRESH",
          red["stale"] is False)


def test_day_consolidated_gap(tmp):                           # CT-7
    print("CT-7 day_matrix — a missing day consolidation reads NOT fresh:")
    out = tmp / "out"; out.mkdir()
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT)
    paths.OUTPUT_ROOT = out
    day_matrix.OUTPUT_ROOT = out
    try:
        date, source = "2026-06-20", "ssor-prod"
        # Two supported vs-TSN reports both EXPORTED that day.
        for subdir in ("highway_log", "ramp_summary"):
            tdir = day_matrix.tsmis_dir(date, source, subdir)
            _xlsx(tdir / "r1.xlsx")
        # Consolidate ONLY highway_log (record its fingerprint); ramp_summary stays
        # exported-but-not-consolidated.
        hl_dir = day_matrix.tsmis_dir(date, source, "highway_log")
        hl_cons = matrix.consolidated_store_path(hl_dir, "highway_log")
        _xlsx(hl_cons)
        artifact_store.write_consolidated_fingerprint(hl_cons, hl_dir)
        _complete_consolidation(hl_cons)

        snap = day_matrix.day_matrix_snapshot(source, [date], dest=str(tmp / "nodest"))
        dc = snap["day_consolidated"][date]
        check("a consolidated workbook EXISTS for the day", dc["exists"] is True)
        check("...but the day is NOT fresh (ramp_summary export has no consolidation)",
              dc["fresh"] is False)

        # Now consolidate ramp_summary too -> the whole day reads fresh.
        rs_dir = day_matrix.tsmis_dir(date, source, "ramp_summary")
        rs_cons = matrix.consolidated_store_path(rs_dir, "ramp_summary")
        _xlsx(rs_cons)
        artifact_store.write_consolidated_fingerprint(rs_cons, rs_dir)
        _complete_consolidation(rs_cons)
        snap2 = day_matrix.day_matrix_snapshot(source, [date], dest=str(tmp / "nodest"))
        check("with every exported report consolidated, the day reads fresh",
              snap2["day_consolidated"][date]["fresh"] is True)
    finally:
        paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT = saved


def main():
    # Each test runs in its own clean temp root to avoid cross-test residue.
    for fn in (test_consolidated_stale, test_cmp_state_fingerprint,
               test_comparison_state_fingerprint, test_midcompare_race,
               test_day_consolidated_gap):
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
    print()
    if _failures:
        print(f"FAILED {len(_failures)} check(s): {_failures}")
        return 1
    print("All P2 freshness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
