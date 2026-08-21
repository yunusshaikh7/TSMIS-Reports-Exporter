"""The counts-only PREVIEW contract.

A preview runs the whole comparison and skips only serialization, so its numbers
must equal the build's numbers exactly. It publishes no workbook, so by the
comparison contract it has no artifact generation — and therefore must be unable
to certify a matrix cell no matter what it counted.

This holds both halves: that the numbers agree, and that they can never go green.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT)]

import compare_core as core        # noqa: E402
import matrix_state                # noqa: E402

_failures = []


def check(name, condition, detail=""):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)
        if detail:
            print(f"       {detail}")


SCHEMA = core.CompareSchema(
    report_name="Preview Contract",
    header=["Loc", "Text", "Num"],
    side_a="TSMIS", side_b="TSN",
    id_noun="row", id_noun_plural="rows",
)
LEFT = [["A", "same", "1"], ["B", "left", "2"], ["ONLY-A", "x", "3"]]
RIGHT = [["A", "same", "1"], ["B", "right", "9"], ["ONLY-B", "y", "4"]]
IDENTICAL = [["A", "same", "1"], ["B", "same", "2"]]


def _outcome(rows_t, rows_n, mode, path):
    return core.run_compare(SCHEMA, rows_t, rows_n, False, path, mode=mode)


def test_preview_equals_the_build(root):
    print("a preview reports exactly what the build reports:")
    for label, (a, b) in (("differences", (LEFT, RIGHT)),
                          ("identical", (IDENTICAL, IDENTICAL))):
        built = _outcome(a, b, "values", root / f"{label}.xlsx")
        pre = _outcome(a, b, "preview", root / f"{label}-preview.xlsx")
        bt, pt = built.comparison_outcome, pre.comparison_outcome
        check(f"{label}: counts are exact",
              bt.counts.to_dict() == pt.counts.to_dict(),
              f"built={bt.counts.to_dict()} preview={pt.counts.to_dict()}")
        check(f"{label}: verdict and completion agree",
              (bt.verdict, bt.completion) == (pt.verdict, pt.completion),
              f"built={(bt.verdict, bt.completion)} "
              f"preview={(pt.verdict, pt.completion)}")
        check(f"{label}: the preview wrote NO file",
              not (root / f"{label}-preview.xlsx").exists()
              and (root / f"{label}.xlsx").exists())
        check(f"{label}: the preview claims no artifact",
              getattr(pre, "artifact_generation", None) is None
              and pre.output_path == "",
              f"generation={getattr(pre, 'artifact_generation', None)!r} "
              f"path={pre.output_path!r}")
    # The identical fixture must really verdict as a match, or the pair above
    # proves nothing about the case that matters most (a clean preview).
    check("the identical fixture really does verdict as a match",
          _outcome(IDENTICAL, IDENTICAL, "preview",
                   root / "probe.xlsx").comparison_outcome.verdict == "match")
    check("the differing fixture really does count differences",
          _outcome(LEFT, RIGHT, "preview", root / "probe2.xlsx")
          .comparison_outcome.counts.differing_cells > 0)


def _shown(previews, key, cell, cmp_state, sources, fingerprint):
    """`_preview_for` with the folder fingerprint pinned to a known value."""
    saved = matrix_state._cell_input_fingerprint
    matrix_state._cell_input_fingerprint = lambda *a: fingerprint
    try:
        return matrix_state._preview_for(previews, key, cell, cmp_state,
                                         sources, (Path("x"),))
    finally:
        matrix_state._cell_input_fingerprint = saved


def test_preview_cannot_certify(root):
    print("a preview can never make a cell green:")
    dest = root / "store"
    comparisons = matrix_state.comparisons_common_root(dest)
    comparisons.mkdir(parents=True, exist_ok=True)
    key, cell = "highway_log|tsn", "ssor-prod"
    clean = _outcome(IDENTICAL, IDENTICAL, "preview", root / "clean.xlsx")
    record = matrix_state.preview_record(
        clean.comparison_outcome, {"tsn": "token-1"}, "fingerprint-1")
    check("even a MATCH preview is stored as a preview, not a result",
          record["verdict"] == "match" and record["diff_cells"] == 0)
    check("the preview persists to its own store",
          matrix_state.record_preview(comparisons, key, cell, record)
          and matrix_state.previews_path(comparisons).exists())
    check("it is NOT in the certifying result cache",
          matrix_state.load_tsn_results(dest) == {}
          and not matrix_state._tsn_results_path(dest).exists())

    previews = matrix_state.load_previews(comparisons)
    current = [{"name": "tsn", "mtime": 1.0, "identity": "token-1"}]
    other = [{"name": "tsn", "mtime": 1.0, "identity": "token-2"}]

    check("it shows on an unbuilt cell",
          _shown(previews, key, cell, {"built": False, "stale": True},
                 current, "fingerprint-1") is not None)
    check("a FRESH certified cell hides it (a real generation always wins)",
          _shown(previews, key, cell, {"built": True, "stale": False},
                 current, "fingerprint-1") is None)
    check("a STALE certified cell still shows it",
          _shown(previews, key, cell, {"built": True, "stale": True},
                 current, "fingerprint-1") is not None)
    check("a changed source identity drops it",
          _shown(previews, key, cell, {"built": False, "stale": True},
                 other, "fingerprint-1") is None)
    check("a changed input fingerprint drops it",
          _shown(previews, key, cell, {"built": False, "stale": True},
                 current, "fingerprint-2") is None)
    check("a later input mtime drops it (the inputs moved after it ran)",
          matrix_state._preview_for(
              previews, key, cell, {"built": False, "stale": True},
              [{"name": "tsn", "mtime": record["at"] + 60,
                "identity": "token-1"}], ()) is None)

    matrix_state.record_preview(
        comparisons, key, cell,
        dict(record, producer_versions={"app": "0.0.0-not-this"}))
    check("a preview from a superseded producer drops it",
          _shown(matrix_state.load_previews(comparisons), key, cell,
                 {"built": False, "stale": True}, current,
                 "fingerprint-1") is None)

    matrix_state.record_preview(comparisons, key, cell, record)
    check("clearing removes the entry",
          matrix_state.record_preview(comparisons, key, cell, None)
          and _shown(matrix_state.load_previews(comparisons), key, cell,
                     {"built": False, "stale": True}, current,
                     "fingerprint-1") is None)


def test_a_certified_build_clears_the_preview():
    print("a certified build supersedes the preview it made redundant:")
    import gui_worker_matrix as gwm
    import matrix
    calls = []
    saved = (matrix.record_attempt, matrix.record_preview)
    matrix.record_attempt = lambda *a, **k: calls.append(("attempt", a[3]))
    matrix.record_preview = lambda *a, **k: calls.append(("preview", a[3]))
    try:
        gwm._record_attempt("root", "row|tsn", "cell", matrix.ATTEMPT_OK, "")
        check("a succeeded BUILD clears the cell's preview",
              ("preview", None) in calls, repr(calls))
        calls.clear()
        gwm._record_attempt("root", "row|tsn", "cell", matrix.ATTEMPT_OK, "",
                            preview_run=True)
        check("a succeeded PREVIEW touches neither overlay", calls == [],
              repr(calls))
        calls.clear()
        gwm._record_attempt("root", "row|tsn", "cell", "failed", "why",
                            preview_run=True)
        check("a FAILED preview still records why", calls == [("attempt", "failed")],
              repr(calls))
    finally:
        matrix.record_attempt, matrix.record_preview = saved


def test_build_comparison_records_no_result(root):
    """The SHIPPED entry point: matrix.build_comparison(preview=True) must reach
    the preview store and never the certifying cache. Only the compare itself is
    stubbed, so the recording branch — the thing under test — stays real.

    Hermetic: TSN_LIBRARY_ROOT is sandboxed, or the resolver finds a real staged
    library and the build stops on ITS certificate instead of reaching the branch.
    """
    print("the shipped build_comparison(preview=True) records no result:")
    import matrix
    import matrix_build
    import paths
    from events import ConsolidateResult

    dest = root / "shipped"
    (dest / "ssor-prod" / "highway_log").mkdir(parents=True, exist_ok=True)
    outcome_obj = _outcome(LEFT, RIGHT, "preview",
                           root / "shipped.xlsx").comparison_outcome
    seen = {"result": 0, "preview": 0}

    def _compared(*_a, **_k):
        res = ConsolidateResult(status="ok", output_path="")
        res.comparison_outcome = outcome_obj
        return res

    saved_lib = paths.TSN_LIBRARY_ROOT
    saved = {name: getattr(matrix_build, name) for name in
             ("tsn_source", "tsn_identity_check_for",
              "tsn_expected_workbook_identity", "record_tsn_result")}
    saved_facade = (matrix.consolidate_and_compare_tsn, matrix.record_preview)
    paths.TSN_LIBRARY_ROOT = root / "_lib"
    matrix_build.tsn_source = lambda *a, **k: {
        "kind": "file", "path": str(root / "tsn.xlsx"),
        "identity_token": {"sha256": "a" * 64, "size": 1}, "selection": "pick"}
    matrix_build.tsn_identity_check_for = lambda *a, **k: ("tok", lambda: True)
    matrix_build.tsn_expected_workbook_identity = lambda *a, **k: {"sha256": "x"}
    matrix_build.record_tsn_result = (
        lambda *a, **k: seen.__setitem__("result", seen["result"] + 1))
    matrix.consolidate_and_compare_tsn = _compared
    matrix.record_preview = (
        lambda *a, **k: seen.__setitem__("preview", seen["preview"] + 1) or True)
    try:
        res = matrix.build_comparison(
            dest, "highway_log", "ssor-prod", "tsn", "ssor-prod", events=None,
            commit_guard=lambda *_a: True, preview=True)
        check("the preview build returns ok", res.status == "ok", repr(res.message))
        check("it recorded a PREVIEW and never the cache result",
              seen == {"result": 0, "preview": 1}, repr(seen))
    finally:
        for name, fn in saved.items():
            setattr(matrix_build, name, fn)
        matrix.consolidate_and_compare_tsn, matrix.record_preview = saved_facade
        paths.TSN_LIBRARY_ROOT = saved_lib


def test_the_ui_never_greens_a_preview():
    print("the renderer never paints a preview as a match:")
    js = (ROOT / "scripts" / "ui" / "ui-matrix.js").read_text(encoding="utf-8")
    start = js.index("if (cmp.preview")
    built_at = js.index("if (!cmp.built)")
    block = js[start:built_at]
    check("the preview branch runs BEFORE the built/stale/match branches",
          start < built_at)
    check("it uses its own class and never mx-match",
          'cls: "mx-preview"' in block and "mx-match" not in block)
    check("it says the cell still needs building", "build to certify" in block)
    css = (ROOT / "scripts" / "ui" / "app.css").read_text(encoding="utf-8")
    rule = css.split(".mx-cell.mx-preview")[1].split("}")[0]
    check("mx-preview is styled, and not with the success colour",
          ".mx-cell.mx-preview" in css and "--success" not in rule)


def main():
    print("counts-only comparison preview:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_preview_"))
    try:
        test_preview_equals_the_build(root)
        test_preview_cannot_certify(root)
        test_a_certified_build_clears_the_preview()
        test_build_comparison_records_no_result(root)
        test_the_ui_never_greens_a_preview()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL COMPARISON-PREVIEW CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
