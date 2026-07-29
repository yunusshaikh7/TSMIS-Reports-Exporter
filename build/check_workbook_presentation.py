"""Stored presentation and self-description of the comparison workbook.

The audit (PCOA-FINAL-008 / -009 / -014 / -019) found that a delivered workbook
can be internally correct and still unreadable or silent about itself:

  * a stored column width that cannot fit the identity in it, so two different
    rows read the same ("Ramp Type: C", "Highway Group: R");
  * a wholly-CONTEXT column reported as `0` differences, indistinguishable from
    a compared column that matched everywhere;
  * a values twin whose headline verdict is a formula with no cached value, so
    every consumer that does not recalculate reads the deliverable's single
    most important line as blank.

This check builds a summary-shaped and a detail-shaped comparison in BOTH
flavors and measures them with the AUDIT'S OWN gate — imported from the
committed `stage2-measure-clipping.py`, so the product check and the oracle
cannot drift apart — then asserts the two self-description contracts.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from _checklib import Checker, ROOT, scripts_path, temp_dir

scripts_path()

from compare_core import CompareSchema, run_compare  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

GATE = (ROOT / "docs" / "planning" / "post-comparison-perfection-output-audit"
        / "stage2-measure-clipping.py")

# A statewide-summary shape: the category IS the identity, and the longest of
# these are the exact labels the audit measured at 89 px of available width.
SUMMARY_SCHEMA = CompareSchema(
    report_name="Presentation Summary", header=["Category", "Count"],
    side_a="SSOR-PROD 2026-07-23", side_b="SSOR-PROD 2026-07-09",
    id_noun="category", id_noun_plural="categories")
SUMMARY_A = [
    ["Ramp Type: C - Direct or Semi-direct Connector (Left)", "1873"],
    ["RURAL/URBAN/SUBURBAN: U-O - URBAN -O OUTSIDE CITY", "441"],
    ["Population: R-RURAL -O OUTSIDE CITY", "77"],
    ["Highway Group: R - Right", "12"],
]
SUMMARY_B = [[k, v if k.startswith("Highway Group") else str(int(v) + 1)]
             for k, v in SUMMARY_A]

# A detail shape: a composite key, a wholly-context column, a compared column
# that matches everywhere (which must still report a real 0), and a compared
# column that differs.
DETAIL_SCHEMA = CompareSchema(
    report_name="Presentation Detail",
    header=["Key", "Description", "City", "PM"],
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    id_noun="location", id_noun_plural="locations",
    context_fields=("City",))
DETAIL_A = [[f"00{i} / ORA / R000.{i:03d}", f"DESCRIPTION OF LOCATION {i}",
             f"CITY {i}", f"{i}.5"] for i in range(1, 25)]
DETAIL_B = [[k, d + ("X" if i % 5 == 0 else ""), "A DIFFERENT CITY", pm]
            for i, (k, d, _c, pm) in enumerate(DETAIL_A)]

FRESHNESS_LABEL = ("Build-time source identity and duplicate pairing snapshot "
                   "is current")
CONTEXT_TEXT = "not compared (context)"
STALE_TEXT = "REGENERATE REQUIRED"


def _load_gate():
    spec = importlib.util.spec_from_file_location("stage2_clipping_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary_grid(path, data_only):
    wb = load_workbook(path, data_only=data_only, read_only=True)
    try:
        return [tuple((list(row) + [None] * 4)[:4])
                for row in wb["Summary"].iter_rows(values_only=True)]
    finally:
        wb.close()


def _per_field(rows):
    """{field label -> the DIFFERENCES BY FIELD cell} for one Summary."""
    out = {}
    seen_header = False
    for row in rows:
        if row[1] == "Field" and row[3] == "# of cells differing":
            seen_header = True
            continue
        if seen_header:
            if not row[1]:
                break
            out[row[1]] = row[3]
    return out


def main():
    c = Checker()
    gate = _load_gate()
    with temp_dir("tsmis_presentation_") as tmp:
        built = {}
        for name, sc, ra, rb in (("summary", SUMMARY_SCHEMA, SUMMARY_A, SUMMARY_B),
                                 ("detail", DETAIL_SCHEMA, DETAIL_A, DETAIL_B)):
            for mode in ("values", "formulas"):
                path = Path(tmp) / f"{name}-{mode}.xlsx"
                result = run_compare(sc, ra, rb, False, path, mode=mode,
                                     name_a="a.xlsx", name_b="b.xlsx")
                c.check(f"{name}/{mode} builds", result.status == "ok", repr(result))
                built[(name, mode)] = (path, result)

        # ---- PCOA-FINAL-008 / -009: nothing the reader needs is clipped -----
        for (name, mode), (path, _result) in built.items():
            hits = gate.audit_workbook(path)
            c.check(f"{name}/{mode} has no materially clipped cell",
                    not hits,
                    "; ".join(f"{h['sheet']}!{h['cell']} short "
                              f"{h['short_by_px']}px {h['text'][:40]!r}"
                              for h in hits[:6]))

        # The identity columns are WIDENED, never wrapped away: a key must read
        # on one line in the default view.
        wb = load_workbook(built[("summary", "values")][0], read_only=False)
        try:
            comparison = wb["Comparison"]
            key_width = comparison.column_dimensions["A"].width
            key_cell = comparison["A2"]
            c.check("the category column is widened to fit its longest identity",
                    key_width is not None and key_width >= 40,
                    repr(key_width))
            c.check("an identity cell is not wrapped instead of widened",
                    not (key_cell.alignment and key_cell.alignment.wrap_text))
        finally:
            wb.close()

        # ---- PCOA-FINAL-014: a wholly-context column says so ----------------
        for mode in ("values", "formulas"):
            fields = _per_field(_summary_grid(built[("detail", mode)][0], False))
            c.check(f"detail/{mode} renders a wholly-context column as context",
                    fields.get("City") == CONTEXT_TEXT, repr(fields))
            c.check(f"detail/{mode} still counts a compared column that differs",
                    fields.get("Description") not in (None, CONTEXT_TEXT, ""),
                    repr(fields))
            pm = fields.get("PM")
            c.check(f"detail/{mode} still reports a real 0 for a compared "
                    "column with no differences",
                    (pm == 0) if mode == "values"
                    else (isinstance(pm, str) and pm.startswith("=")),
                    repr(fields))

        # ---- PCOA-FINAL-019: the values headline is readable, and stale
        #      inputs still decertify the workbook ---------------------------
        for name in ("summary", "detail"):
            path, result = built[(name, "values")]
            cached = _summary_grid(path, True)[2][1]
            typed = result.comparison_outcome
            c.check(f"{name}: the values headline is non-empty read data_only",
                    isinstance(cached, str) and cached.strip(), repr(cached))
            c.check(f"{name}: the values headline matches the typed outcome",
                    isinstance(cached, str)
                    and (cached.startswith("✓") if typed.verdict == "match"
                         else cached.startswith("✗"))
                    and (typed.verdict == "match"
                         or f"{typed.counts.differing_cells:,}" in cached),
                    f"{cached!r} vs {typed.verdict!r} / {typed.counts!r}")

            stored = _summary_grid(path, False)
            fresh = [row[2] for row in stored if row[1] == FRESHNESS_LABEL]
            c.check(f"{name}: the values twin still fails closed when stale",
                    len(fresh) == 1 and isinstance(fresh[0], str)
                    and fresh[0].startswith("=IF(")
                    and STALE_TEXT in fresh[0]
                    and "__CMP_E2_SNAPSHOT_A" in fresh[0]
                    and "__CMP_E2_SNAPSHOT_B" in fresh[0],
                    repr(fresh))
            c.check(f"{name}: the values twin discloses its stored headline",
                    any(isinstance(row[1], str)
                        and "STORED build-time result" in row[1]
                        for row in stored),
                    "no note names the stored verdict")

            formulas_path = built[(name, "formulas")][0]
            live = _summary_grid(formulas_path, False)[2][1]
            live_fresh = [row[2] for row in _summary_grid(formulas_path, False)
                          if row[1] == FRESHNESS_LABEL]
            c.check(f"{name}: the formulas twin keeps its live guarded verdict",
                    isinstance(live, str) and live.startswith("=IF(")
                    and STALE_TEXT in live, repr(live))
            c.check(f"{name}: the formulas twin's freshness row is live too",
                    len(live_fresh) == 1 and STALE_TEXT in str(live_fresh[0]),
                    repr(live_fresh))
    return c.summary()


if __name__ == "__main__":
    raise SystemExit(main())
