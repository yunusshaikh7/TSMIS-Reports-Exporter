"""Characterization check: compare_env side-label cap keeps the distinguisher.

The two compared sides become Excel sheet/tab names, capped to fit the 31-char
sheet-name limit ("Only in <label>" = 8 + 23). The cap must trim the BASE, not
the trailing distinguisher (a run date or an (A)/(B) suffix) -- otherwise two
same-source sides collapse to the same prefix and degrade to "Side A"/"Side B",
losing their provenance. (v0.18.0 P0: the cap was an incidental s[:23]; this
locks the explicit distinguisher-preserving behavior.)

Pure Python (no openpyxl / browser). Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_compare_env_sidelabel.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_env  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def test_cap_label():
    print("_cap_label keeps the trailing distinguisher:")
    cap = compare_env._cap_label
    limit = compare_env._SIDE_LABEL_CAP
    check("cap derives from the 31-char sheet limit", limit == 31 - len("Only in "))
    check("short label unchanged", cap("SSOR-PROD") == "SSOR-PROD")
    # Long base + a run-date suffix: the date must survive the cap.
    capped = cap("VERYLONGSOURCE-ENVIRONMENT 2026-06-11")
    check("dated label fits the cap", len(capped) <= limit)
    check("date suffix preserved", capped.endswith(" 2026-06-11"))
    # Long base + (A)/(B): the suffix must survive and stay distinct.
    a = cap("VERYLONGSOURCE-ENVIRONMENT-NAME (A)")
    b = cap("VERYLONGSOURCE-ENVIRONMENT-NAME (B)")
    check("(A) suffix preserved within the cap", a.endswith(" (A)") and len(a) <= limit)
    check("(B) suffix preserved", b.endswith(" (B)"))
    check("(A)/(B) stay distinct under the cap", a != b)
    # Two same-base, different-date sides stay distinct (the regression).
    x = cap("SAME-LONG-SOURCE-ENVIRONMENT 2026-06-11")
    y = cap("SAME-LONG-SOURCE-ENVIRONMENT 2026-07-22")
    check("same base, different dates stay distinct", x != y)
    # No recognizable suffix -> plain end-truncation, still within the cap.
    plain = cap("X" * 40)
    check("no-suffix label still capped to the limit", len(plain) == limit)


def test_side_labels_integration():
    print("_side_labels preserves provenance (no needless Side A/B):")
    sl = compare_env._side_labels
    limit = compare_env._SIDE_LABEL_CAP
    # Same src-env, different run dates -> dates appended, both retained.
    la, lb = sl(Path("2026-06-11 ssor-prod"), Path("2026-07-22 ssor-prod"))
    check("same src-env, different days -> distinct dated labels",
          la != lb and "2026-06-11" in la and "2026-07-22" in lb)
    check("dated labels are not the Side A/B fallback",
          la != "Side A" and lb != "Side B")
    # Distinct src-env -> the short SRC-ENV names, unchanged.
    da, db = sl(Path("2026-06-11 ssor-prod"), Path("2026-06-11 ars-dev"))
    check("distinct src-env -> SSOR-PROD / ARS-DEV",
          da == "SSOR-PROD" and db == "ARS-DEV")
    for lbl in (la, lb, da, db):
        check(f"'{lbl}' fits the sheet-name cap", len(lbl) <= limit)


def test_labels_override():
    print("compare_folders labels override (v0.26.0, the baseline matrix):")
    # Functional: the override must reach the side machinery (labels=None keeps
    # the derived behavior the tests above lock). Two EMPTY folders make the
    # loader fail fast with a message that NAMES the side label — proving the
    # explicit labels (and the identical-override (A)/(B) fallback) apply.
    import shutil
    import tempfile
    a = Path(tempfile.mkdtemp(prefix="tsmis_lbl_a_"))
    b = Path(tempfile.mkdtemp(prefix="tsmis_lbl_b_"))
    out_dir = Path(tempfile.mkdtemp(prefix="tsmis_lbl_out_"))
    try:
        res = compare_env.RAMP_DETAIL.compare_folders(
            a, b, out_dir / "out.xlsx", labels=("MY DAY LABEL", "MY BASELINE"))
        check("explicit labels reach the side loader (error names them)",
              res.status == "error" and "MY DAY LABEL" in (res.message or ""))
        res2 = compare_env.RAMP_DETAIL.compare_folders(
            a, b, out_dir / "out.xlsx", labels=("SAME", "SAME"))
        check("identical overrides degrade to (A)/(B)",
              res2.status == "error" and "SAME (A)" in (res2.message or ""))
        res3 = compare_env.RAMP_DETAIL.compare_folders(a, b, out_dir / "out.xlsx")
        check("default (no labels) keeps the derived side names",
              res3.status == "error" and "MY DAY LABEL" not in (res3.message or ""))
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)


def test_direct_folder_driver_output_alias():
    """The public folder adapter must be safe without a Matrix/GUI wrapper."""
    print("compare_folders rejects an output inside either selected source:")
    import tempfile
    from events import ConsolidateResult
    root = Path(tempfile.mkdtemp(prefix="tsmis_env_alias_"))
    a, b = root / "side-a", root / "side-b"
    a.mkdir(); b.mkdir()
    selected = a / "selected-source.xlsx"
    selected.write_bytes(b"selected source")
    prior = selected.read_bytes()
    report_a = a / "alias_probe"; report_a.mkdir()
    report_b = b / "alias_probe"; report_b.mkdir()
    nested = report_a / "route.xlsx"
    nested.write_bytes(b"nested selected source")
    nested_prior = nested.read_bytes()
    calls = []

    adapter = compare_env.EnvCompare(
        "alias_probe", "Alias Probe", "alias_probe",
        side_loader=lambda _folder, _label, _events: ([['001', 'x']], []),
        agg_header=["Route", "Value"])

    def destructive_run_compare(_sc, _rows_a, _rows_b, _has_route, out_path, **_kw):
        calls.append(Path(out_path))
        Path(out_path).write_bytes(b"comparison replacement")
        return ConsolidateResult(status="ok", output_path=str(out_path))

    original = compare_env.run_compare
    compare_env.run_compare = destructive_run_compare
    try:
        result = adapter.compare_folders(a, b, selected, mode="values")
        check("direct folder driver rejects an output nested in selected side A",
              result.status == "error" and calls == [])
        check("...the nested source is byte-for-byte preserved",
              selected.read_bytes() == prior)

        external = root / "external-hardlink.xlsx"
        try:
            os.link(nested, external)
        except OSError:
            check("external hardlink probe skipped only when links are unavailable", True)
        else:
            calls.clear()
            hardlinked = adapter.compare_folders(a, b, external, mode="values")
            check("an external hardlink to a discovered input file is rejected",
                  hardlinked.status == "error" and calls == [])
            check("...the discovered input remains byte-for-byte intact",
                  nested.read_bytes() == nested_prior)
            external.unlink()

        moved_out = root / "moved-descendant.xlsx"
        moved = [False]

        def move_descendant(folder, _label, _events):
            if Path(folder) == a and not moved[0]:
                moved[0] = True
                os.replace(nested, moved_out)
                nested.write_bytes(b"same-path decoy")
            return ([['001', 'x']], [])

        moving_adapter = compare_env.EnvCompare(
            "alias_probe", "Alias Probe", "alias_probe",
            side_loader=move_descendant, agg_header=["Route", "Value"])
        calls.clear()
        moved_result = moving_adapter.compare_folders(a, b, moved_out, mode="values")
        check("a discovered input moved onto the output with a decoy is rejected",
              moved_result.status == "error" and calls == [])
        check("...the originally discovered file survives at its moved path",
              moved_out.read_bytes() == nested_prior)

        late_input = report_a / "late-added.xlsx"
        late_output = root / "late-added-output.xlsx"
        added = [False]

        def add_hardlinked_descendant(folder, _label, _events):
            if Path(folder) == a and not added[0]:
                added[0] = True
                late_input.write_bytes(b"late discovered source")
                os.link(late_input, late_output)
            return ([['001', 'x']], [])

        adding_adapter = compare_env.EnvCompare(
            "alias_probe", "Alias Probe", "alias_probe",
            side_loader=add_hardlinked_descendant,
            agg_header=["Route", "Value"])
        calls.clear()
        try:
            added_result = adding_adapter.compare_folders(
                a, b, late_output, mode="values")
        except OSError:
            check("late-add hardlink probe skipped only when links are unavailable", True)
        else:
            check("a source file added during discovery fails the set-equality tripwire",
                  added_result.status == "error" and calls == [])
            check("...the late-added hardlinked input is preserved",
                  late_input.read_bytes() == b"late discovered source")
    finally:
        compare_env.run_compare = original
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def test_folder_driver_target_guard():
    print("compare_folders forwards an exact target-aware commit guard:")
    import tempfile
    from events import ConsolidateResult
    from openpyxl import Workbook
    root = Path(tempfile.mkdtemp(prefix="tsmis_env_guard_"))
    a, b = root / "side-a", root / "side-b"
    a.mkdir(); b.mkdir()
    out = root / "comparison.xlsx"
    seen_paths = []
    seen_core = {}
    ran = [0]
    adapter = compare_env.EnvCompare(
        "guard_probe", "Guard Probe", "guard_probe",
        side_loader=lambda _folder, _label, _events: ([["001", "x"]], []),
        agg_header=["Route", "Value"])

    def guard(path, **binding):
        p = Path(path)
        seen_paths.append((p, dict(binding)))
        return p == root or p.parent == root

    def fake_run_compare(_sc, _rows_a, _rows_b, _has_route, temp, **kwargs):
        ran[0] += 1
        seen_core.update(temp=Path(temp), **kwargs)
        wb = Workbook(); wb.active.title = "Comparison"; wb.save(temp); wb.close()
        return ConsolidateResult(status="ok", output_path=str(temp))

    original = compare_env.run_compare
    compare_env.run_compare = fake_run_compare
    try:
        result = adapter.compare_folders(
            a, b, out, mode="values", commit_guard=guard)
        paths = [p for p, _binding in seen_paths]
        check("guarded folder comparison publishes normally",
              result.status == "ok" and out.is_file() and ran[0] == 1)
        check("guard sees the selected final and unpredictable exact temp",
              out in paths and seen_core.get("temp") in paths
              and ".tmp-" in seen_core.get("temp").name)
        check("the same callback reaches compare_core's pre-save boundary",
              seen_core.get("commit_guard") is guard)

        ran[0] = 0

        def deny_temp(path, **_binding):
            return ".tmp-" not in Path(path).name

        denied = adapter.compare_folders(
            a, b, root / "denied.xlsx", mode="values",
            commit_guard=deny_temp)
        check("temp denial blocks the folder serializer before entry",
              denied.status == "error" and ran[0] == 0
              and not (root / "denied.xlsx").exists())
        check("denied folder transaction leaves no temp",
              not list(root.glob("*.tmp-*")))
    finally:
        compare_env.run_compare = original
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def main():
    test_cap_label()
    test_side_labels_integration()
    test_labels_override()
    test_direct_folder_driver_output_alias()
    test_folder_driver_target_guard()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL SIDE-LABEL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
