#!/usr/bin/env python3
"""Permanent synthetic gate for the independent Intersection Summary oracle."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import sys

import phase6_intersection_summary_conservation as oracle


def _raw_records():
    return [
        {
            "physical_pdf_page": 3,
            "printed_report_page": 1,
            "band": band,
            "section": section,
            "code": code,
            "count": count,
            "descriptor": descriptor,
            "top": str(index),
            "bottom": str(index + 1),
            "x0": "0",
            "x1": "1",
            "parent_relation": "synthetic",
        }
        for index, (band, section, code, count, descriptor)
        in enumerate(oracle.EXPECTED_RAW_ROWS, 1)
    ]


def _valid_sidecar():
    return {
        "schema_version": 1,
        "completion": "complete",
        "skipped_inputs": 0,
        "failed_inputs": 0,
        "tsn_normalization_version": 2,
        "tsn_artifact_identity_token": oracle.SIDECAR_BINDING["artifact_identity_token"],
        "tsn_raw_manifest": {
            "member_count": 1,
            "byte_length": oracle.RAW_BINDING["bytes"],
            "sha256": oracle.SIDECAR_BINDING["raw_manifest_sha256"],
            "members": [{
                "relative_path": "Intersection Summary Statewide_TSN.pdf",
                "byte_length": oracle.RAW_BINDING["bytes"],
                "sha256": oracle.RAW_BINDING["sha256"],
            }],
        },
        "tsn_normalized_workbook_identity": {
            "byte_length": oracle.NORMALIZED_BINDING["bytes"],
            "sha256": oracle.NORMALIZED_BINDING["sha256"],
        },
    }


def _valid_r7():
    workbook_rel = "intersection_summary/consolidated/tsn_intersection_summary_normalized.xlsx"
    sidecar_rel = workbook_rel + ".outcome.json"
    status = {
        "current": True,
        "producer_complete": True,
        "coherent_snapshot_current": True,
        "identity_token_current": True,
        "identity_token": oracle.SIDECAR_BINDING["artifact_identity_token"],
    }
    return {
        "acceptance": "complete",
        "completed_family_count": 7,
        "expected_family_count": 7,
        "source_universe_stable": True,
        "generated_output_artifact_universe_exact": True,
        "families": [{
            "report": "intersection_summary",
            "normalization_version": 2,
            "output": {
                "bytes": oracle.NORMALIZED_BINDING["bytes"],
                "sha256": oracle.NORMALIZED_BINDING["sha256"],
                "sidecar_sha256": oracle.SIDECAR_BINDING["sha256"],
                "sheets": [{
                    "data_rows": 58,
                    "distinct_first_column_values": 58,
                    "header": ["Category", "Count"],
                    "name": "Intersection Summary (TSN)",
                }],
            },
            "result": {
                "status": "ok", "completion": "complete",
                "skipped_inputs": 0, "failed_inputs": 0,
            },
            "reuse": {
                "certified": True, "output_unchanged": True,
                "sidecar_unchanged": True,
            },
            "status_after_build": status,
        }],
        "generated_output_artifact_manifest": {
            "members": [
                {
                    "relative_path": workbook_rel,
                    "bytes": oracle.NORMALIZED_BINDING["bytes"],
                    "sha256": oracle.NORMALIZED_BINDING["sha256"],
                },
                {
                    "relative_path": sidecar_rel,
                    "bytes": oracle.SIDECAR_BINDING["bytes"],
                    "sha256": oracle.SIDECAR_BINDING["sha256"],
                },
            ],
        },
    }


def main() -> int:
    failed = []

    def check(name, condition):
        print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
        if not condition:
            failed.append(name)

    rows = _raw_records()
    projected, dispositions, per_category = oracle._project_records(rows, 16_626)
    expected = [(label, Decimal(count)) for label, count in oracle.EXPECTED_NORMALIZED_ROWS]
    check("62 raw rows project to 57 categories plus Total", len(rows) == 62 and len(projected) == 58)
    check("independent declared projection exact", projected == expected)
    check("every raw category disposed exactly once", len(dispositions) == 62)
    signal = next(item for item in per_category if item["normalized_category"].startswith("CONTROL TYPES: S "))
    check("J/K/L/M/N/P fold is six-to-one and exact 2648",
          signal["source_contribution_count"] == 6 and signal["projected_count"] == 2648)
    check("per-category ordered/multiset/typed-target digests cover all 58 rows",
          len(per_category) == len(expected) == 58
          and [item["normalized_category"] for item in per_category]
          == [row[0] for row in expected]
          and all(
              len(item["source_contributions_ordered_typed_sha256"]) == 64
              and len(item["source_contributions_multiset_typed_sha256"]) == 64
              and len(item["projected_typed_row_sha256"]) == 64
              for item in per_category
          )
          and all(len(item["source_category_typed_sha256"]) == 64 for item in dispositions))
    check("orphan Rural/Urban continuation fails closed", _orphan_fails())

    changed = deepcopy(rows)
    changed[28]["count"] += 1
    changed_projection, _changed_dispositions, _changed_categories = oracle._project_records(
        changed, 16_626, enforce_fixed=False
    )
    deltas = [
        (index + 1, before, after)
        for index, (before, after) in enumerate(zip(projected, changed_projection))
        if before != after
    ]
    try:
        oracle._project_records(changed, 16_626)
        mutation_failed = False
    except oracle.ConservationError:
        mutation_failed = True
    check("legacy subtype count mutation fails fixed projection with sole S delta",
          mutation_failed and deltas == [(
              29,
              ("CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)", Decimal(2648)),
              ("CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)", Decimal(2649)),
          )])

    missing = [row for row in rows if not (
        row["section"] == "CONTROL TYPES" and row["code"] == "P"
    )]
    try:
        oracle._project_records(missing, 16_626)
        missing_failed = False
    except oracle.ConservationError:
        missing_failed = True
    check("missing legacy subtype fails closed", missing_failed)

    try:
        oracle._project_records(rows, 16_627)
        total_failed = False
    except oracle.ConservationError:
        total_failed = True
    check("printed Total mutation fails fixed final row", total_failed)

    words = [{"text": "COUNT", "x0": 1.0, "x1": 2.0, "top": 3.0, "bottom": 4.0}]
    original_word_digest = oracle._word_digest(words)
    moved_words = deepcopy(words)
    moved_words[0]["x0"] = 1.125
    check("page word-coordinate mutation changes topology digest",
          oracle._word_digest(moved_words) != original_word_digest)

    blind = deepcopy(rows)
    blind[24]["descriptor"] += "#MUT"
    blind[24]["band"] = 3
    blind_projection, _blind_dispositions, _blind_categories = oracle._project_records(
        blind, 16_626, enforce_fixed=False
    )
    raw_core = [(row["band"], row["section"], row["code"], row["count"], row["descriptor"])
                for row in rows]
    blind_core = [(row["band"], row["section"], row["code"], row["count"], row["descriptor"])
                  for row in blind]
    check("descriptor/band drift changes raw digest while projection stays equal",
          oracle._ordered_digest(raw_core) != oracle._ordered_digest(blind_core)
          and blind_projection == projected)

    isolated = deepcopy(rows)
    isolated[0]["count"] += 1
    isolated_projection, _isolated_dispositions, isolated_categories = oracle._project_records(
        isolated, 16_626, enforce_fixed=False
    )
    baseline_digests = {
        item["normalized_category"]: (
            item["source_contributions_ordered_typed_sha256"],
            item["source_contributions_multiset_typed_sha256"],
            item["projected_typed_row_sha256"],
        ) for item in per_category
    }
    isolated_digests = {
        item["normalized_category"]: (
            item["source_contributions_ordered_typed_sha256"],
            item["source_contributions_multiset_typed_sha256"],
            item["projected_typed_row_sha256"],
        ) for item in isolated_categories
    }
    changed_categories = [
        key for key in baseline_digests if baseline_digests[key] != isolated_digests[key]
    ]
    changed_rows = [
        index + 1 for index, (before, after)
        in enumerate(zip(projected, isolated_projection)) if before != after
    ]
    check("one source count changes exactly one category digest and target row",
          changed_categories == ["HIGHWAY GROUP: R - RIGHT IND ALIGN"]
          and changed_rows == [1])

    sidecar = _valid_sidecar()
    check("valid synthetic sidecar accepted", all(oracle._validate_sidecar(sidecar).values()))
    changed_sidecar = deepcopy(sidecar)
    changed_sidecar["tsn_raw_manifest"]["sha256"] = "0" * 64
    try:
        oracle._validate_sidecar(changed_sidecar)
        sidecar_failed = False
    except oracle.ConservationError:
        sidecar_failed = True
    check("same-completion raw-manifest drift rejected", sidecar_failed)

    r7 = _valid_r7()
    check("valid synthetic r7 lifecycle witness accepted", all(oracle._validate_r7(r7).values()))
    changed_r7 = deepcopy(r7)
    changed_r7["families"][0]["output"]["sha256"] = "0" * 64
    try:
        oracle._validate_r7(changed_r7)
        r7_failed = False
    except oracle.ConservationError:
        r7_failed = True
    check("r7 output-hash drift rejected", r7_failed)

    check("Control F semantic label drift remains explicit",
          rows[24]["descriptor"] == "F-FOUR WAY FLASHER (RED ON ALL)"
          and projected[24][0] == "CONTROL TYPES: F - 4-WAY FLASHER (RED/MAINLINE)")

    ordered = [(row["section"], row["code"], row["count"]) for row in rows]
    swapped = list(ordered)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    check("ordered digest detects reorder",
          oracle._ordered_digest(ordered) != oracle._ordered_digest(swapped))
    check("multiset digest ignores reorder",
          oracle._multiset_digest(ordered)[0] == oracle._multiset_digest(swapped)[0])

    if failed:
        print(f"FAIL: {len(failed)} synthetic gate(s): {failed}")
        return 1
    print("OK: Intersection Summary conservation synthetic gate")
    return 0


def _orphan_fails() -> bool:
    try:
        oracle._source_code("RURAL/URBAN/SUBURBAN", "-O OUTSIDE CITY", None)
    except oracle.ConservationError:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
