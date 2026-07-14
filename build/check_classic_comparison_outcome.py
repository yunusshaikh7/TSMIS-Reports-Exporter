"""Classic Compare terminal UI must consume strict typed generation truth.

No browser/network. Run from the repository root:
    build\\.venv\\Scripts\\python.exe build\\check_classic_comparison_outcome.py
"""
from __future__ import annotations

from dataclasses import replace
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import artifact_store  # noqa: E402
import gui_api  # noqa: E402
from comparison_contract import ComparisonCounts, ComparisonOutcome  # noqa: E402
from compare_core import CompareSchema, run_compare  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402


failures = []


def check(name, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        failures.append(name)


def _producer(completion):
    def produce(path):
        wb = Workbook()
        wb.active.title = "Comparison"
        wb.active["A1"] = "typed comparison"
        wb.save(path)
        typed = ComparisonOutcome(
            status="ok",
            completion=completion,
            verdict="match" if completion == "complete" else "diff",
            counts=ComparisonCounts(known=True, paired_rows=1),
            warnings=(() if completion == "complete" else ("input incomplete",)),
            pairing_quality="exact",
        )
        return ConsolidateResult(
            status="ok", output_path=str(path),
            summary_lines=["engine display line"],
            verdict=typed.verdict, completion=completion,
            skipped_inputs=0 if completion == "complete" else 1,
            failed_inputs=0, comparison_outcome=typed)

    return produce


class _FakeUi:
    def __init__(self):
        self._authed = True
        self.logs = []
        self.dots = []
        self.modals = []
        self.ended = 0

    def _emit_log(self, text):
        self.logs.append(text)

    def _set_dot(self, *args):
        self.dots.append(args)

    def _emit_modal(self, *args):
        self.modals.append(args)

    def _flash_taskbar(self):
        pass

    def _end_task(self):
        self.ended += 1


def _finish(result):
    ui = _FakeUi()
    gui_api.GuiApi._finish_consolidate(ui, result)
    return ui


def main():
    with tempfile.TemporaryDirectory(prefix="tsmis_classic_outcome_") as raw:
        root = Path(raw)

        partial = artifact_store.commit_workbook(
            root / "partial.xlsx", _producer("partial"),
            expect_sheet="Comparison", requested_mode="values")
        partial.operation_kind = "comparison"
        # Deliberately contradict the typed/persisted truth. Prose remains display
        # text only and may never select a green modal.
        partial.verdict = "match"
        partial.summary_lines = ["✓ EVERYTHING MATCHES — deliberately false prose"]
        ui = _finish(partial)
        check("typed partial defeats contradictory legacy match/prose",
              ui.modals and ui.modals[-1][1] == "Comparison incomplete"
              and all(modal[1] != "Everything matches" for modal in ui.modals))
        check("partial terminal still closes the task exactly once", ui.ended == 1)

        cap_schema = CompareSchema(
            report_name="Capped UI", header=["Key", "Value"],
            side_a="A", side_b="B", id_noun="row", id_noun_plural="rows")
        cap_rows = [["K", "same"]] * 317
        capped = artifact_store.commit_workbook(
            root / "capped.xlsx",
            lambda path: run_compare(
                cap_schema, cap_rows, cap_rows, False, path, mode="values"),
            expect_sheet="Comparison", requested_mode="values")
        capped.operation_kind = "comparison"
        capped_ui = _finish(capped)
        capped_body = capped_ui.modals[-1][2] if capped_ui.modals else ""
        check("capped pairing UI explains re-scope, not missing inputs",
              capped_ui.modals
              and capped_ui.modals[-1][1] == "Comparison incomplete"
              and "exact-pairing limit" in capped_body
              and "Re-scope" in capped_body
              and "Some input coverage was incomplete" not in capped_body
              and all(modal[1] != "Everything matches"
                      for modal in capped_ui.modals))

        complete = artifact_store.commit_workbook(
            root / "complete.xlsx", _producer("complete"),
            expect_sheet="Comparison", requested_mode="values")
        complete.operation_kind = "comparison"
        complete.summary_lines = ["display text does not own state"]
        ui2 = _finish(complete)
        check("trusted complete typed match selects the match modal",
              ui2.modals and ui2.modals[-1][1] == "Everything matches")

        # Returned typed truth changed after the sidecar committed: strict reducer
        # must reject, even though every legacy field still looks successful.
        complete.comparison_outcome = replace(
            complete.comparison_outcome,
            completion="partial", verdict="diff", warnings=("mutated",))
        complete.completion = "partial"
        complete.verdict = "match"
        ui3 = _finish(complete)
        check("returned/persisted mismatch is an explicit untrusted error",
              ui3.modals and ui3.modals[-1][1] == "Comparison result untrusted"
              and ui3.dots[-1] == ("bad", "Result untrusted"))

        failed = ConsolidateResult(status="error", message="input missing")
        failed.operation_kind = "comparison"
        ui4 = _finish(failed)
        check("early comparison error is titled as a comparison",
              ui4.modals and ui4.modals[-1][1] == "Comparison failed")

        ordinary = ConsolidateResult(status="error", message="input missing")
        ui5 = _finish(ordinary)
        check("ordinary consolidation error keeps its own title",
              ui5.modals and ui5.modals[-1][1] == "Consolidation failed")

    if failures:
        print(f"\nFAILED {len(failures)} check(s): {failures}")
        raise SystemExit(1)
    print("\nALL CLASSIC COMPARISON OUTCOME CHECKS PASSED")


if __name__ == "__main__":
    main()
