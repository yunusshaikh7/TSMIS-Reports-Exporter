"""CMP-AUD-100 — Matrix cache envelopes + records are never accepted under a false
identity, and a malformed nested record degrades ONE cell, never crashes the snapshot.

The Everything (env + TSN), by-day, and baseline matrices each cache verdicts in a
versioned envelope keyed by an EXACT output identity (``baseline_key`` / ``"tsn"`` /
``"tsn-by-day"`` / ``"baseline-by-day"``). The finding reproduced two defects: a day
cache mislabelled ``baseline-by-day`` was accepted and rendered as a fresh 777-diff
result, and a current-version payload whose cell record was a LIST crashed the whole
day snapshot with ``AttributeError``. The loaders were corrected to require the exact
identity and isolate malformed nested records; this is the dedicated adversarial gate
the finding asked for — it swaps envelopes among all four identities and exhausts the
nested-record JSON shapes, proving each foreign / malformed / wrong-type case reads
empty or stale (rebuildable) rather than trusted or a whole-snapshot crash.

Real openpyxl-free; no browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_cache_adversarial.py
"""
import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_ROOT / "scripts"), str(_ROOT)]

import cache_envelope       # noqa: E402
import matrix               # noqa: E402
import matrix_state         # noqa: E402
import day_matrix           # noqa: E402
import baseline_matrix      # noqa: E402
import paths                # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


# The four distinct matrix cache output identities.
_IDENTITIES = ["ssor-prod", "tsn", "tsn-by-day", "baseline-by-day"]
_PAYLOAD = {"row|env": {"verdict": "diff", "diff_cells": 777, "one_sided": 0,
                        "built_at_mtime": 1000.0}}


def test_cross_matrix_identity():
    print("cross-matrix identity — an envelope is accepted ONLY by its own identity:")
    for wrote in _IDENTITIES:
        env = cache_envelope.wrap(_PAYLOAD, output_identity=wrote)
        for expect in _IDENTITIES:
            got = cache_envelope.unwrap(env, output_identity=expect)
            if expect == wrote:
                check(f"{wrote!r} accepted by its own identity",
                      got == _PAYLOAD)
            else:
                check(f"{wrote!r} REJECTED under {expect!r} (foreign cache -> empty)",
                      got == {})


def test_persisted_swap(tmp):
    print("persisted cache swap — a foreign envelope planted at a loader's path reads empty:")
    # Plant a baseline-by-day envelope where the by-day loader reads, and vice versa,
    # and confirm each loader rebuilds (empty) rather than rendering foreign counts.
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, baseline_matrix.OUTPUT_ROOT)
    paths.OUTPUT_ROOT = day_matrix.OUTPUT_ROOT = baseline_matrix.OUTPUT_ROOT = tmp
    try:
        def _plant(path, identity):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cache_envelope.wrap(_PAYLOAD, output_identity=identity), f)

        # by-day loader (expects "tsn-by-day") fed a baseline-by-day envelope.
        _plant(day_matrix._results_path(), "baseline-by-day")
        check("by-day loader rejects a baseline-by-day envelope (the finding's case)",
              day_matrix.load_results() == {})
        # baseline loader (expects "baseline-by-day") fed a tsn-by-day envelope.
        _plant(baseline_matrix._results_path(), "tsn-by-day")
        check("baseline loader rejects a tsn-by-day envelope",
              baseline_matrix.load_results() == {})
        # Everything env loader (expects the baseline_key) fed the wrong baseline.
        p = matrix._results_path(tmp, "ssor-prod")
        _plant(p, "ars-prod")
        check("Everything env loader rejects a different-baseline envelope",
              matrix.load_results(tmp, "ssor-prod") == {})
        # Everything TSN loader (expects "tsn") fed a tsn-by-day envelope.
        _plant(matrix._tsn_results_path(tmp), "tsn-by-day")
        check("Everything TSN loader rejects a tsn-by-day envelope",
              matrix.load_tsn_results(tmp) == {})
        # ...and each loader ACCEPTS its own identity (not a blanket reject).
        _plant(day_matrix._results_path(), "tsn-by-day")
        check("by-day loader accepts its own tsn-by-day envelope",
              day_matrix.load_results() == _PAYLOAD)
    finally:
        (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT,
         baseline_matrix.OUTPUT_ROOT) = saved


def test_adversarial_nested_records(tmp):
    print("adversarial nested records — each degrades ONE cell to stale, never crashes:")
    # The production reader (`_cmp_state`) always passes the workbook path as the
    # comparison output; a present workbook with no trusted sidecar reads stale
    # (outcome_missing) and never surfaces a verdict from the malformed record.
    workbook = tmp / "cell.xlsx"
    workbook.write_bytes(b"a present but un-sidecar'd comparison workbook")
    sources = [{"name": "cell", "present": True, "mtime": 900.0},
               {"name": "tsn", "present": True, "mtime": 900.0}]
    bad_recs = [
        ("a list record", [1, 2, 3]),
        ("a string record", "totally not a record"),
        ("an int record", 42),
        ("an empty dict", {}),
        ("a non-numeric built_at_mtime", {"built_at_mtime": "yesterday"}),
        ("a list built_at_mtime", {"built_at_mtime": [1, 2]}),
        ("a bool built_at_mtime", {"built_at_mtime": True}),
        ("a partial record (no mtime)", {"verdict": "match", "diff_cells": 0}),
        ("a wrong-generation record", {"built_at_mtime": workbook.stat().st_mtime,
                                       "verdict": "match", "diff_cells": 0,
                                       "generation_id": "some-foreign-generation"}),
    ]
    for label, rec in bad_recs:
        try:
            st = matrix._cmp_state(workbook, sources, rec)
            ok = (isinstance(st, dict) and st.get("stale") is True
                  and st.get("verdict") is None)      # never a trusted verdict/count
        except Exception as e:                       # noqa: BLE001 — a crash IS the defect
            ok = False
            print(f"       {label}: CRASHED {type(e).__name__}: {e}")
        check(f"{label} -> stale + no trusted verdict, no crash", ok)

    # _nested_record must not trust foreign container shapes either.
    check("_nested_record on a list outer -> None (no crash)",
          matrix_state._nested_record([1, 2, 3], "row", "env") is None)
    check("_nested_record on a list inner -> None (no crash)",
          matrix_state._nested_record({"row": [1, 2, 3]}, "row", "env") is None)
    check("_nested_record on a missing key -> None",
          matrix_state._nested_record({"row": {}}, "row", "env") is None)


def test_snapshot_survives_malformed_cache(tmp):
    print("whole-snapshot survival — a malformed persisted cache never crashes render:")
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT)
    paths.OUTPUT_ROOT = day_matrix.OUTPUT_ROOT = tmp
    try:
        # A CURRENT-version by-day envelope whose cell record is a LIST (the exact
        # AttributeError crash the finding reproduced) + one export folder present.
        date, source = "2026-06-22", "ssor-prod"
        tdir = day_matrix.tsmis_dir(date, source, "highway_log")
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "r1.xlsx").write_bytes(b"x")
        p = day_matrix._results_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cache_envelope.wrap(
                {f"{date} {source}|highway_log": ["not", "a", "record"]},
                output_identity="tsn-by-day"), f)
        try:
            snap = day_matrix.day_matrix_snapshot(source, [date], dest=None)
            ok = isinstance(snap, dict) and "cells" in snap
            cell = snap["cells"].get("highway_log", {}).get(date, {}).get("cmp", {})
            stale = cell.get("stale") is True or cell.get("missing_side") is not None
        except Exception as e:                       # noqa: BLE001
            ok = stale = False
            print(f"       day snapshot CRASHED {type(e).__name__}: {e}")
        check("a list cell record renders the day snapshot without crashing", ok)
        check("...and that cell reads stale / not-fresh (never a trusted 777)", stale)
    finally:
        paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT = saved


def main():
    test_cross_matrix_identity()
    with tempfile.TemporaryDirectory() as td:
        test_persisted_swap(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_adversarial_nested_records(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_snapshot_survives_malformed_cache(Path(td))
    print()
    if _failures:
        print(f"FAILED {len(_failures)} check(s): {_failures}")
        return 1
    print("All CMP-AUD-100 adversarial cache checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
