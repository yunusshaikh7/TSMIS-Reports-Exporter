"""CMP-AUD-129: Windows comparison component limits and long total paths.

The filesystem's per-component limit is 255 UTF-16 code units even when the
process is long-path-aware.  This gate derives every public boundary through the
production naming helpers, covers astral Unicode (two UTF-16 units), proves an
over-limit comparison stops before confirmation/production, and exercises a
real >260-character publication when the development runtime/Windows policy
permits it.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import artifact_store  # noqa: E402
import consolidation_meta as cm  # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402


_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        if detail:
            print(f"       {detail}")
        _failures.append(name)


def _units(value: str) -> int:
    return cm._windows_utf16_units(value)


def _selected_budget(mode: str) -> int:
    """Derive, rather than duplicate, the selected workbook's exact budget."""
    sample = Path("x.xlsx")
    selected_units = _units(sample.name)
    token = "0" * artifact_store._PRODUCER_TEMP_TOKEN_HEX_CHARS
    primary_temp = artifact_store._producer_temp(sample, token)
    public_names = [primary_temp.name]
    metadata_members = [sample]
    if mode == "both":
        public_names.append(artifact_store._values_twin(primary_temp).name)
        metadata_members.append(artifact_store._values_twin(sample))
    overheads = [_units(name) - selected_units for name in public_names]
    for member in metadata_members:
        for name in cm._comparison_metadata_component_names(member):
            overheads.append(_units(name) - selected_units)
    return cm._WINDOWS_COMPONENT_MAX_UTF16_UNITS - max(overheads)


def _name_at_units(target: int, *, non_bmp: bool) -> str:
    suffix = ".xlsx"
    remaining = target - _units(suffix)
    if remaining < 1:
        raise AssertionError("test filename budget is unexpectedly tiny")
    astral = min(7, remaining // 2) if non_bmp else 0
    value = "\U0001f6e3" * astral + "a" * (remaining - (astral * 2)) + suffix
    assert _units(value) == target
    assert ("\U0001f6e3" in value) == non_bmp
    return value


def _typed_result(path: Path) -> ConsolidateResult:
    typed = ComparisonOutcome(
        status="ok", completion="complete", verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=1),
        pairing_quality="exact")
    return ConsolidateResult(
        status="ok", output_path=str(path), verdict="match",
        completion="complete", skipped_inputs=0, failed_inputs=0,
        comparison_outcome=typed)


def _producer(mode: str, calls: list[Path]):
    def produce(path: Path):
        path = Path(path)
        calls.append(path)
        wb = Workbook()
        wb.active.title = "Comparison"
        wb.active["A1"] = mode
        wb.save(path)
        if mode == "both":
            values = Workbook()
            values.active.title = "Comparison"
            values.active["A1"] = "both-values"
            values.save(artifact_store._values_twin(path))
        return _typed_result(path)

    return produce


def test_exact_boundaries(root: Path) -> None:
    print("derived exact component boundaries (UTF-16 units, not code points):")
    budgets = {mode: _selected_budget(mode)
               for mode in ("formulas", "values", "both")}
    check("formulas exact selected budget is 238 including .xlsx",
          budgets["formulas"] == 238, repr(budgets))
    check("values exact selected budget is 238 including .xlsx",
          budgets["values"] == 238, repr(budgets))
    check("both exact selected budget is 229 including .xlsx",
          budgets["both"] == 229, repr(budgets))

    for mode, budget in budgets.items():
        twin = mode == "both"
        for non_bmp in (False, True):
            kind = "non-BMP" if non_bmp else "ASCII"
            exact = root / _name_at_units(budget, non_bmp=non_bmp)
            too_long = root / _name_at_units(budget + 1, non_bmp=non_bmp)
            exact_error = artifact_store._comparison_path_limit_error(exact, twin)
            over_error = artifact_store._comparison_path_limit_error(too_long, twin)
            check(f"{mode} {kind}: exact max is accepted",
                  exact_error is None, str(exact_error or ""))
            check(f"{mode} {kind}: max+1 is rejected actionably",
                  over_error is not None
                  and "UTF-16 code unit" in over_error
                  and "shorter output workbook name" in over_error
                  and "existing files were kept" in over_error,
                  str(over_error or ""))

        # Enter the real transaction at max+1.  The selected workbook itself is
        # still <=255; only a mandatory derived component is too long.  Seed old
        # bytes where the host's long-path policy permits it and prove byte-exact
        # preservation.  Even without that policy, producer/confirm must not run.
        invalid = root / _name_at_units(budget + 1, non_bmp=True)
        prior_paths = [invalid]
        if twin:
            prior_paths.append(artifact_store._values_twin(invalid))
        prior = {}
        seeded = True
        try:
            for index, path in enumerate(prior_paths):
                path.write_bytes(f"prior-{mode}-{index}".encode("ascii"))
                prior[path] = path.read_bytes()
        except OSError as e:
            seeded = False
            print(f"       [POLICY] could not seed long prior pathname: "
                  f"{type(e).__name__}: {e}")

        calls: list[Path] = []
        confirms: list[Path] = []
        result = artifact_store.commit_workbook(
            invalid, _producer(mode, calls), twin=twin,
            expect_sheet="Comparison", requested_mode=mode,
            confirm_overwrite=lambda path: confirms.append(Path(path)) or True)
        check(f"{mode}: max+1 stops before confirmation and producer",
              result.status == "error" and not calls and not confirms
              and "UTF-16 code unit" in (result.message or ""),
              result.message or "")
        if seeded:
            check(f"{mode}: max+1 leaves every prior member byte-exact",
                  all(path.read_bytes() == raw for path, raw in prior.items()))

    # One successful real publication per mode at the non-BMP exact boundary.
    # This necessarily also exceeds legacy MAX_PATH in an ordinary temp root.
    for mode, budget in budgets.items():
        exact = root / _name_at_units(budget, non_bmp=True)
        calls: list[Path] = []
        try:
            result = artifact_store.commit_workbook(
                exact, _producer(mode, calls), twin=(mode == "both"),
                expect_sheet="Comparison", requested_mode=mode)
        except OSError as e:
            if os.name == "nt":
                print(f"       [POLICY] {mode} exact publication unavailable: "
                      f"{type(e).__name__}: {e}")
                continue
            raise
        canonical = (artifact_store._values_twin(exact)
                     if mode == "both" else exact)
        strict = cm.read_comparison_outcome(canonical)
        check(f"{mode}: exact non-BMP boundary publishes trusted metadata",
              result.status == "ok" and len(calls) == 1
              and strict is not None and strict.trusted,
              result.message or "")


def test_metadata_and_payload_boundaries() -> None:
    print("metadata boundary + payload basename compatibility:")
    exact = _name_at_units(_selected_budget("values"), non_bmp=True)
    over = _name_at_units(_selected_budget("values") + 1, non_bmp=True)
    check("strict member parser accepts the exact sidecar/sentinel boundary",
          cm._safe_relative_member(exact) == exact)
    try:
        cm._safe_relative_member(over)
    except ValueError as e:
        rejected = "fixed publication sentinel" in str(e)
    else:
        rejected = False
    check("strict member parser rejects a derived max+1 sidecar boundary", rejected)

    primary = cm._payload_primary_basename("a" * 64, 0, "b" * 64)
    slot = cm._payload_slot_basename("a" * 64, 0, "b" * 64, 7)
    legacy = (primary[:-len(cm._COMPARISON_PAYLOAD_SUFFIX)]
              + "-f-" + "c" * 64 + "-" + "d" * 16
              + cm._COMPARISON_PAYLOAD_SUFFIX)
    check("new primary/slot payload names retain >=64 UTF-16 units headroom",
          _units(primary) == 167 and _units(slot) == 172
          and max(_units(primary), _units(slot))
              <= cm._WINDOWS_COMPONENT_MAX_UTF16_UNITS - 64)
    manifest = cm._strict_payload_manifest({
        "schema_version": cm._COMPARISON_PAYLOAD_SCHEMA_VERSION,
        "encoding": cm._COMPARISON_PAYLOAD_ENCODING,
        "decoded_size": 32,
        "decoded_sha256": "a" * 64,
        "binding_sha256": "c" * 64,
        "chunks": [{
            "relative_path": legacy,
            "size": 1,
            "sha256": "b" * 64,
            "decoded_size": 32,
        }],
    })
    check("legacy binding+nonce payload name remains read-compatible only",
          _units(legacy) == 251
          and manifest["chunks"][0]["relative_path"] == legacy
          and legacy not in (primary, slot))


def test_long_total_path(root: Path) -> None:
    print("long total path under the development runtime:")
    parent = root / "long-total"
    index = 0
    while len(str(parent / "comparison.xlsx")) <= 320:
        parent /= f"segment-{index:02d}-" + "x" * 24
        index += 1
    try:
        parent.mkdir(parents=True)
        final = parent / "comparison.xlsx"
        calls: list[Path] = []
        result = artifact_store.commit_workbook(
            final, _producer("values", calls), expect_sheet="Comparison",
            requested_mode="values")
        record = cm.read_comparison_outcome(final)
    except OSError as e:
        if os.name == "nt":
            print("       [POLICY] Windows rejected a >260-character path despite "
                  f"the development runtime: {type(e).__name__}: {e}")
            print("       Packaged longPathAware still requires enabled OS/registry policy.")
            return
        raise
    check("ordinary >260-character path publishes without an extended-path prefix",
          len(str(final)) > 260 and not str(final).startswith("\\\\?\\")
          and result.status == "ok" and len(calls) == 1
          and record is not None and record.trusted,
          f"length={len(str(final))}; {result.message or ''}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tsmis-cmp-path-") as tmp:
        root = Path(tmp)
        test_exact_boundaries(root)
        test_metadata_and_payload_boundaries()
        test_long_total_path(root)


if __name__ == "__main__":
    print("CMP-AUD-129 comparison Windows path-limit gate:")
    main()
    if _failures:
        print(f"\n{len(_failures)} check(s) FAILED")
        raise SystemExit(1)
    print("all good")
