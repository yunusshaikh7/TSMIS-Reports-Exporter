"""Golden check (CT-9 + stable-ID uniqueness, R1-T05) for the P3 four-tier
stable-ID taxonomy and the batch-manifest v1/v2 migration.

Proves selection/resume no longer depends on registry list position (F7):
- every tier's keys are unique and 1:1 with its registry list; the export-op key
  IS the spec subdir; key<->index round-trips; unknown keys reject to None;
- a v1 (integer-index) manifest migrates to export-op KEYS via the FROZEN v0.17
  order 1:1 (length-preserving); a malformed/out-of-range entry is poisoned and
  DUPLICATES are kept, so resolution rejects the whole saved set all-or-nothing;
- a v2 manifest whose REGISTRY ORDER has since changed still resolves the saved
  KEYS to the SAME reports (the F7 re-order proof) — an index scheme would not;
- the REAL BatchWorker resolves manifest keys to specs on resume and marks NO
  environment done when nothing resolves (no false-complete on empty resolution).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_stable_ids.py
"""
import sys
import threading
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import batch_manifest
import reports

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_uniqueness_and_roundtrip():
    print("stable-ID uniqueness + key<->index round-trip (R1-T05):")
    check("EXPORT_KEYS unique + 1:1 with EXPORT_REPORTS",
          len(reports.EXPORT_KEYS) == len(reports.EXPORT_REPORTS)
          == len(set(reports.EXPORT_KEYS)))
    check("CONSOLIDATE_KEYS unique + 1:1 with CONSOLIDATE_REPORTS",
          len(reports.CONSOLIDATE_KEYS) == len(reports.CONSOLIDATE_REPORTS)
          == len(set(reports.CONSOLIDATE_KEYS)))
    check("COMPARE_KEYS unique + 1:1 with COMPARE_REPORTS",
          len(reports.COMPARE_KEYS) == len(reports.COMPARE_REPORTS)
          == len(set(reports.COMPARE_KEYS)))
    check("export-op key == the spec's subdir (family key)",
          all(reports.EXPORT_KEYS[i] == s.subdir
              for i, (_l, _f, s) in enumerate(reports.EXPORT_REPORTS)))
    check("export key<->index round-trips for every row",
          all(reports.export_index_for_key(k) == i
              and reports.spec_for_export_key(k).subdir == k
              for i, k in enumerate(reports.EXPORT_KEYS)))
    check("consolidate key->index round-trips",
          all(reports.consolidate_index_for_key(k) == i
              for i, k in enumerate(reports.CONSOLIDATE_KEYS)))
    check("compare key->index round-trips",
          all(reports.compare_index_for_key(k) == i
              for i, k in enumerate(reports.COMPARE_KEYS)))
    check("unknown keys resolve to None (rejected, never mis-indexed)",
          reports.export_index_for_key("nope") is None
          and reports.spec_for_export_key("nope") is None
          and reports.consolidate_index_for_key("nope") is None
          and reports.compare_index_for_key("nope") is None)
    # The frozen v0.17 order the migration relies on must still equal today's export
    # keys (the v0.17.x report set is the same eight — the original seven plus the
    # v0.17.2 Intersection Detail (PDF), all in the same order; CR002-RM4 append-only).
    check("frozen _V017_EXPORT_ORDER == today's export keys",
          batch_manifest._V017_EXPORT_ORDER == reports.EXPORT_KEYS)


def test_resolve_export_keys():
    print("resolve_export_keys: ALL-OR-NOTHING — unknown/disabled/duplicate -> invalid:")
    specs, invalid = reports.resolve_export_keys(
        ["highway_log", "nope", "ramp_summary", "ramp_summary"])
    check("the enabled known keys resolve in order",
          [s.subdir for s in specs] == ["highway_log", "ramp_summary"])
    check("BOTH the unknown key AND the duplicate are rejected (not swallowed)",
          invalid == ["nope", "ramp_summary"])
    s2, inv2 = reports.resolve_export_keys(["ramp_summary", "highway_log"])
    check("a clean, unique, known set has NO invalid", inv2 == [] and len(s2) == 2)


def test_v1_v2_normalization():
    print("manifest v1/v2 normalization is 1:1 + length-preserving (no coerce/drop/dedup):")
    P = batch_manifest._INVALID_KEY
    # v1: real in-range ints map; bool/float/numeric-string is NOT coerced; an
    # out-of-range index and DUPLICATES are kept (poisoned/repeated) so the resolver
    # can reject the whole set rather than silently run a narrower batch.
    v1 = {"version": 1, "reports": [3, 0, 0, 42], "steps": []}
    check("v1: in-range ok, duplicate KEPT, out-of-range 42 -> poison (1:1 length)",
          batch_manifest._normalize_reports(v1)
          == ["highway_log", "ramp_summary", "ramp_summary", P])
    v1c = {"version": 1, "reports": [True, 1.9, "3"], "steps": []}
    check("v1: bool / float / numeric-string are NOT coerced to indices -> all poison",
          batch_manifest._normalize_reports(v1c) == [P, P, P])
    # v2: strings kept (dups too); a non-string / empty entry -> poison.
    v2 = {"version": 2, "reports": ["ramp_summary", "ramp_summary", "highway_log", 9, ""]}
    check("v2: duplicate KEPT, non-string 9 + empty -> poison (1:1 length)",
          batch_manifest._normalize_reports(v2)
          == ["ramp_summary", "ramp_summary", "highway_log", P, P])


def test_v017_append_only_compat():
    print("CR002-RM4: _V017_EXPORT_ORDER is append-only; v1 manifests (pre- AND post-Int-PDF) resolve:")
    order = batch_manifest._V017_EXPORT_ORDER
    # Positions 0-6 are the ORIGINAL v0.17.1 export order and must never move.
    check("positions 0-6 unchanged (the original seven export keys)",
          order[:7] == ("ramp_summary", "ramp_detail", "highway_sequence", "highway_log",
                        "highway_log_pdf", "intersection_summary", "intersection_detail"))
    check("intersection_detail_pdf at index 7 (v0.17.8 append)",
          order[7] == "intersection_detail_pdf")
    check("Highway group appended at 8-10 (append-only): Detail/Summary v0.18.1, Detail(PDF) v0.19.2",
          order[8:11] == ("highway_detail", "highway_summary", "highway_detail_pdf"))
    check("PDF editions appended at 11-12 (v0.24.0): Highway Sequence + Ramp Detail",
          order[11:13] == ("highway_sequence_pdf", "ramp_detail_pdf"))
    check("v0.25.1 appended at 13-15: RS (Excel) + IS (PDF) + the Route History placeholder",
          order[13:16] == ("ramp_summary_excel", "intersection_summary_pdf", "route_history"))
    check("Clean Road group appended at 16-18 (2026-07-22, reserved-DISABLED)",
          order[16:] == ("clean_highway", "clean_intersection", "clean_ramp"))
    # A v1 (integer-index) manifest from the PRE-Intersection-PDF shape (v0.17.1: seven
    # reports, indices 0-6) still migrates to the seven original keys, 1:1.
    pre = {"version": 1, "reports": [0, 1, 2, 3, 4, 5, 6], "steps": []}
    check("pre-Int-PDF v1 manifest migrates to the seven original keys",
          batch_manifest._normalize_reports(pre) == list(order[:7]))
    # A v1 manifest written by a v0.17.8 user (the new 8th report, index 7) resolves
    # to intersection_detail_pdf — NOT poisoned as out-of-range (the append fixed that).
    post = {"version": 1, "reports": [6, 7], "steps": []}
    check("v0.17.8-era v1 index 7 migrates to intersection_detail_pdf",
          batch_manifest._normalize_reports(post)
          == ["intersection_detail", "intersection_detail_pdf"])
    # End-to-end: the migrated keys resolve to real, enabled specs (round-trip).
    specs, invalid = reports.resolve_export_keys(batch_manifest._normalize_reports(post))
    check("the migrated v0.17.8 keys resolve to real specs (no invalid)",
          invalid == []
          and [s.subdir for s in specs] == ["intersection_detail", "intersection_detail_pdf"])


def test_reorder_proof():
    print("F7: a re-ordered registry still resolves saved KEYS to the SAME reports:")
    saved = ["highway_log", "ramp_summary"]
    want = {k: reports.spec_for_export_key(k).subdir for k in saved}
    before_idx = reports.export_index_for_key("ramp_summary")
    # Simulate a registry re-order by reversing EXPORT_REPORTS + EXPORT_KEYS in
    # tandem (each key's list index changes; the key->spec mapping must not).
    orig_reports, orig_keys = reports.EXPORT_REPORTS, reports.EXPORT_KEYS
    try:
        reports.EXPORT_REPORTS = list(reversed(orig_reports))
        reports.EXPORT_KEYS = tuple(reversed(orig_keys))
        got = {k: reports.spec_for_export_key(k).subdir for k in saved}
        check("each saved key still resolves to its OWN report after re-order",
              got == want)
        check("the key's list index DID move (so the proof isn't vacuous)",
              reports.export_index_for_key("ramp_summary") != before_idx)
    finally:
        reports.EXPORT_REPORTS, reports.EXPORT_KEYS = orig_reports, orig_keys


class _Q:
    def __init__(self):
        self.items = []

    def put(self, x):
        self.items.append(x)


def _run_batch_worker(manifest):
    """Run the REAL BatchWorker.run with collaborators stubbed (no export, no
    site change). Returns (marked_done, queue_items)."""
    import gui_worker as gw
    q, marked = _Q(), []
    w = gw.BatchWorker(manifest, q, threading.Event(), threading.Event(),
                       threading.Event())
    import gui_worker_export as gwx
    saved = (gwx.set_site, gwx.get_site, gw.batch_manifest.mark_done,
             gw.batch_manifest.is_complete, gw.ExportWorker._run_specs)
    gwx.set_site = lambda *_a: None
    gwx.get_site = lambda: ("ssor", "prod")
    gw.batch_manifest.mark_done = lambda _m, s, e: marked.append((s, e))
    gw.batch_manifest.is_complete = lambda _m: bool(marked)

    def rs(_self, _e, results):
        # one COMPLETE+PROMOTED result per resolved spec (a successful env)
        for s in w._specs():
            results.append((s, types.SimpleNamespace(
                saved=5, exists=[], empty=[], user_skipped=[], failed=[],
                completion=gw.outcome.COMPLETE, artifact=gw.outcome.PROMOTED)))
    gw.ExportWorker._run_specs = rs
    try:
        w.run()
    finally:
        (gwx.set_site, gwx.get_site, gw.batch_manifest.mark_done,
         gw.batch_manifest.is_complete, gw.ExportWorker._run_specs) = saved
    return marked, q.items


def test_resume_resolution():
    print("CT-9: BatchWorker resolves manifest KEYS to specs on resume:")
    import gui_worker as gw
    m = {"version": 2, "reports": ["ramp_summary", "highway_log"],
         "steps": [{"src": "ssor", "env": "prod", "status": "pending"}],
         "fast": False, "workers": 1, "auto_consolidate": False, "dest": None}
    w = gw.BatchWorker(m, _Q(), threading.Event(), threading.Event(),
                       threading.Event())
    check("_specs resolves the saved keys to the right specs",
          [s.subdir for s in w._specs()] == ["ramp_summary", "highway_log"])
    marked, _items = _run_batch_worker(m)
    check("a fully-resolved env is marked done", marked == [("ssor", "prod")])


_TERMINAL_KINDS = {"batch_done", "error", "login_saved", "login_device_ok",
                   "login_failed", "cancelled", "export_done", "consolidate_done",
                   "reset_done", "chromium_done", "matrix_done", "matrix_export_done",
                   "env_shot", "env_access_done"}


def _terminals_of(items):
    return [k for k, _p in items if k in _TERMINAL_KINDS]


def test_invalid_or_empty_aborts_single_terminal():
    print("CT-9 + P3-B01/B02: an invalid/empty saved selection aborts ALL-OR-NOTHING:")

    def run(reports_list):
        m = {"version": 2, "reports": reports_list,
             "steps": [{"src": "ssor", "env": "prod", "status": "pending"}],
             "fast": False, "workers": 1, "auto_consolidate": False, "dest": None}
        return _run_batch_worker(m)

    # (a) the Codex false-complete repro: a PARTIALLY-resolvable set must NOT run a
    #     narrower batch — abort, mark no env done, keep the manifest.
    marked, items = run(["ramp_summary", "__removed__"])
    check("partial-resolve: NO environment marked done (no narrower false-complete)",
          marked == [])
    check("partial-resolve: exactly ONE terminal, and it is `error` (CT-10)",
          _terminals_of(items) == ["error"])
    check("partial-resolve: NO batch_done emitted",
          not any(k == "batch_done" for k, _p in items))
    # (b) all-unknown, (c) duplicate, (d) empty — same all-or-nothing single terminal.
    m2, i2 = run(["__gone__", "__also_gone__"])
    check("all-unknown: no env done + exactly one `error` terminal",
          m2 == [] and _terminals_of(i2) == ["error"])
    m3, i3 = run(["ramp_summary", "ramp_summary"])
    check("duplicate: no env done + exactly one `error` terminal",
          m3 == [] and _terminals_of(i3) == ["error"])
    m4, i4 = run([])
    check("empty: no env done + exactly one `error` terminal",
          m4 == [] and _terminals_of(i4) == ["error"])


def main():
    test_uniqueness_and_roundtrip()
    test_resolve_export_keys()
    test_v1_v2_normalization()
    test_v017_append_only_compat()
    test_reorder_proof()
    test_resume_resolution()
    test_invalid_or_empty_aborts_single_terminal()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL STABLE-ID / CT-9 CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
