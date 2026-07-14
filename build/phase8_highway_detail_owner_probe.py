#!/usr/bin/env python3
"""Source-only statewide Highway Detail Excel-owner corroboration probe.

This deliberately calls the same audit-owned source and owner functions as the
Stage-8 driver but stops before any production workbook inspection.  It exists
to freeze and mutation-review CMP-AUD-191/192 ledgers without repeatedly reading
the ten multi-hundred-megabyte product workbooks.  It is diagnostic evidence;
the final Stage-8 driver independently recomputes every value.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import phase8_highway_detail_comparison as audit
import phase8_highway_detail_source_oracle as source


def run(workers: int) -> dict[str, object]:
    excel, excel_summary = source._parse_excel(
        audit.DEFAULT_TSMIS_XLSX_ROOT, None)
    pdf, pdf_summary = source._parse_pdf(
        audit.DEFAULT_TSMIS_PDF_ROOT, None, workers)
    alignment = source._source_format_alignment(excel, pdf)
    pairs, pair_map = audit._format_pairs(excel, pdf, alignment)
    current_attested, current_attestation = audit._attest_excel_county(
        excel, pdf, pairs)

    historical_excel, historical_excel_summary = source._parse_excel(
        audit.DEFAULT_HISTORICAL_OWNER_XLSX_ROOT, None)
    historical_pdf, historical_pdf_summary = source._parse_pdf(
        audit.DEFAULT_HISTORICAL_OWNER_PDF_ROOT, None, workers)
    current_owner_excel = [
        row for row in excel if row.member_route in {"005", "005S"}]
    historical_alignment = source._source_format_alignment(
        current_owner_excel, historical_pdf)
    historical_pairs, historical_pair_map = audit._format_pairs(
        current_owner_excel, historical_pdf, historical_alignment)
    same_build_pairs = [
        item for item in historical_pairs
        if (item[0].member_route == "005"
            and item[2] == "all_34_render_equal")]
    same_build_attested, same_build_attestation = (
        audit._attest_excel_county(
            current_owner_excel, historical_pdf, same_build_pairs))

    raw, raw_summary = audit._parse_tsn_raw(audit.DEFAULT_TSN_RAW)
    normalized, normalized_summary = audit._parse_tsn_normalized(
        audit.DEFAULT_TSN_NORMALIZED)
    constrained, constraint_summary = (
        audit._analyze_excel_owner_constraints(
            excel, pdf, raw, current_attested, same_build_attested))
    comparisons = {
        "snapshot_attested_excel_vs_tsn_raw": audit._comparison(
            "snapshot-attested TSMIS Excel vs TSN raw", constrained, raw),
        "snapshot_attested_excel_vs_tsn_normalized": audit._comparison(
            "snapshot-attested TSMIS Excel vs TSN normalized",
            constrained, normalized),
    }
    return {
        "schema_version": 1,
        "status": "complete-source-only-probe",
        "scope": (
            "diagnostic recomputation of current statewide sources plus the "
            "separately bound route-005/005S 7.7 owner sources; production "
            "workbooks intentionally excluded"),
        "current": {
            "excel": excel_summary,
            "pdf": pdf_summary,
            "alignment": alignment,
            "pair_map": pair_map,
            "exact_attestation": current_attestation,
        },
        "historical_owner_sources": {
            "excel": historical_excel_summary,
            "pdf": historical_pdf_summary,
            "current_excel_alignment": historical_alignment,
            "pair_map": historical_pair_map,
            "same_build_attestation": same_build_attestation,
        },
        "tsn": {
            "raw": raw_summary,
            "normalized": normalized_summary,
        },
        "owner_constraints": constraint_summary,
        "constrained_excel_rows": len(constrained),
        "comparisons": comparisons,
        "all_pairing_exact": all(
            item["pairing_quality"] == "exact"
            and not item["capped_diagnostics"]
            for item in comparisons.values()),
        "tsn_owner_promotions": constraint_summary[
            "tsn_only_owner_promotions"],
        "unresolved_owner_rows": constraint_summary[
            "unresolved_owner_rows"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.workers)
    encoded = (json.dumps(
        result, ensure_ascii=False, sort_keys=True, indent=2,
    ) + "\n").encode("utf-8")
    audit._atomic_write(args.output, encoded)
    print(json.dumps({
        "status": result["status"],
        "output": str(args.output.resolve()),
        "bytes": len(encoded),
        "sha256": audit._sha_bytes(encoded),
        "constrained_excel_rows": result["constrained_excel_rows"],
        "unresolved_owner_rows": result["unresolved_owner_rows"],
        "tsn_owner_promotions": result["tsn_owner_promotions"],
        "all_pairing_exact": result["all_pairing_exact"],
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
