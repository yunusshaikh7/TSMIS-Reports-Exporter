#!/usr/bin/env python3
"""Close the Highway Log Stage-8 base audit without accepting product perfection.

This audit-only gate imports no product module.  It binds the accepted source and
Stage-6 records, the independent projection oracle, and one completed current-product
Excel/PDF leg.  It independently rehashes each publication, decodes its persisted
comparison payload, and proves that all 989 duplicate assignments and all field/count
totals match the independent oracle.  The emitted decision is intentionally limited to
the Stage-8 base audit; physical-source and evidence perfection remain false.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zlib


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / "build"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_log_product_sources_r1"
SOURCE_RESULT = SOURCE_ROOT / "result.json"
EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
TSN_INPUT = (
    VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
    / "highway_log" / "consolidated" / "tsn_highway_log_consolidated.xlsx"
)
TSN_SIDECAR = Path(str(TSN_INPUT) + ".outcome.json")
STAGE6_RESULT = (
    VISUAL_ROOT / "phase6_tsn_conservation" / "highway_log_conservation_r1.json"
)
STAGE6_ACCEPTANCE = Path(str(STAGE6_RESULT) + ".acceptance.json")
ORACLE_RESULT = VISUAL_ROOT / "phase8_highway_log_projection_oracle_r1.json"
ORACLE_CODE = BUILD_ROOT / "phase8_highway_log_projection_oracle.py"
LEG_RUNNER = BUILD_ROOT / "run_phase8_highway_log_product_comparison_leg.py"


class GateError(RuntimeError):
    """One exact closeout contract failed."""


KNOWN_FINDINGS = (
    "CMP-AUD-045", "CMP-AUD-047", "CMP-AUD-048", "CMP-AUD-049",
    "CMP-AUD-050", "CMP-AUD-066", "CMP-AUD-067", "CMP-AUD-157",
)

FILE_BINDINGS = {
    "source_result": (SOURCE_RESULT, 239_655,
        "4fc4009c5b3be05b0be3d90cab5823e8397d34d623543a6215a03a238c27b8a1"),
    "excel": (EXCEL_INPUT, 5_735_685,
        "329ccf68caf0c476d9360cb69dd28c0ab78a588d0e9bd9c816d5b484444fd660"),
    "pdf": (PDF_INPUT, 5_684_466,
        "17c04bb7400eded5c7b372d4ca87728735f8481fd37394c592e7dd0180f0333d"),
    "tsn": (TSN_INPUT, 6_663_062,
        "fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa"),
    "tsn_sidecar": (TSN_SIDECAR, 2_521,
        "6a746ce16773724954391894cbfb61dfccdb30c6c763750644deed081c533b1e"),
    "stage6_result": (STAGE6_RESULT, 10_879_397,
        "f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4"),
    "stage6_acceptance": (STAGE6_ACCEPTANCE, 6_502,
        "012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61"),
    "oracle_result": (ORACLE_RESULT, 34_203,
        "3b778c089e2070f4da9bea82aa0584b8bc4c35840dd0273fef1b2cd9f8c6a121"),
    "oracle_code": (ORACLE_CODE, 42_121,
        "5125cffceb913df8da6bf34470425fe48f58c9a2b764329b949f1a116a90f580"),
    "leg_runner": (LEG_RUNNER, 24_232,
        "1e801e91cb8e86de13843d5b4f9eca1eb13d85ef05bc0aea5a34981482dfd360"),
}

LEG_BINDINGS = {
    "excel_vs_tsn": {
        "result_bytes": 21_821,
        "result_sha256": "028c9caeedd1a080150f0dc96739b4641190af6b564ca2d5d2ab7f7195adabab",
        "trace_sha256": "435d1ab1f8909225396ba0461790c5053893dddd4152acb13b36f1566a2650a1",
        "counts": {
            "known": True, "paired_rows": 48_094, "side_a_only_rows": 3_790,
            "side_b_only_rows": 11_989, "identical_rows": 8_628,
            "differing_rows": 39_466, "differing_cells": 140_333,
            "asserted_cells": 1_430_451, "context_cells": 12_369,
        },
    },
    "pdf_vs_tsn": {
        "result_bytes": 21_819,
        "result_sha256": "5df98a2233986a7665f6cdfe181c2e22e479d5d5985ae4c5aca763755cdb3227",
        "trace_sha256": "e287bad0bea608b7adc919a602f2f3ddfb8a1562311e80b72c364e1063a4f3d0",
        "counts": {
            "known": True, "paired_rows": 48_096, "side_a_only_rows": 3_790,
            "side_b_only_rows": 11_987, "identical_rows": 8_633,
            "differing_rows": 39_463, "differing_cells": 139_786,
            "asserted_cells": 1_430_511, "context_cells": 12_369,
        },
    },
}

EXPECTED_LEG_RESULT_KEYS = {
    "accepted_chain", "audit", "comparison_end_to_end_perfect",
    "evidence_end_to_end_exact", "inputs", "inputs_after",
    "known_product_findings", "leg", "loaded_product_code", "log_lines",
    "log_sha256", "outputs", "product_code_changed_by_runner", "product_result",
    "product_universe_before_result", "schema_version", "stage8_family_accepted",
    "terminal_status",
}
EXPECTED_TRACE_KEYS = {
    "algorithm", "assignment_vector", "exact", "key_components", "matrix_cells",
    "pairs", "positional_cost", "quality", "side_a_indices", "side_a_size",
    "side_b_indices", "side_b_size", "smaller_side", "total_cost",
}
EXPECTED_PAIR_KEYS = {"cost", "side_a_index", "side_b_index"}
REPARSE_FLAG = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
EXPECTED_SCRIPTS_MANIFEST = {
    "files": 321,
    "bytes": 7_423_809,
    "manifest_bytes": 34_351,
    "manifest_sha256": "df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_bytes(value: object) -> bytes:
    return _canonical(value) + b"\n"


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _capture(path: Path) -> tuple[bytes, dict[str, object]]:
    before = path.lstat()
    _require(stat.S_ISREG(before.st_mode), f"not an ordinary file: {path}")
    _require(not path.is_symlink(), f"symlink rejected: {path}")
    _require(not (int(getattr(before, "st_file_attributes", 0)) & REPARSE_FLAG),
             f"reparse file rejected: {path}")
    payload = path.read_bytes()
    after = path.lstat()
    _require(
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
        f"file changed while read: {path}",
    )
    _require(len(payload) == after.st_size, f"short read: {path}")
    return payload, {"bytes": len(payload), "sha256": _sha_bytes(payload)}


def _read_json(path: Path, *, canonical_lf: bool = False,
               compact_canonical: bool = False) -> tuple[dict[str, object], dict[str, object]]:
    payload, identity = _capture(path)
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"invalid JSON {path.name}: {exc}") from exc
    _require(isinstance(document, dict), f"JSON root is not an object: {path}")
    if canonical_lf:
        _require(payload == _json_bytes(document), f"noncanonical JSON+LF: {path}")
    elif compact_canonical:
        _require(payload in {_canonical(document), _json_bytes(document)},
                 f"noncanonical compact JSON: {path}")
    return document, identity


def _bind_files() -> dict[str, dict[str, object]]:
    observed: dict[str, dict[str, object]] = {}
    for label, (path, size, digest) in FILE_BINDINGS.items():
        _payload, identity = _capture(path)
        _require((identity["bytes"], identity["sha256"]) == (size, digest),
                 f"{label} binding drift: {identity}")
        observed[label] = identity
    return observed


def _scripts_manifest() -> dict[str, object]:
    members = []
    for path in sorted(
            (item for item in SCRIPTS_ROOT.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(SCRIPTS_ROOT).as_posix()):
        relative = path.relative_to(SCRIPTS_ROOT).as_posix()
        _payload, identity = _capture(path)
        members.append((relative, identity))
    lines = [
        f"{relative}\t{identity['bytes']}\t{identity['sha256']}"
        for relative, identity in members
    ]
    manifest = ("\n".join(lines) + "\n").encode("utf-8")
    return {
        "files": len(members),
        "bytes": sum(int(identity["bytes"]) for _relative, identity in members),
        "manifest_bytes": len(manifest),
        "manifest_sha256": _sha_bytes(manifest),
    }


def _sequence_digest(records: object) -> dict[str, object]:
    digest = hashlib.sha256()
    count = 0
    for record in records:  # type: ignore[union-attr]
        payload = _canonical(record)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        count += 1
    return {"records": count, "sha256": digest.hexdigest()}


def _validate_source_and_oracle() -> tuple[dict[str, object], dict[str, object]]:
    source, _source_identity = _read_json(SOURCE_RESULT)
    _require(source.get("sources") == source.get("sources_after"),
             "source witness changed across its run")
    _require(all(source.get("invariants", {}).values()),
             "source witness invariants are not all true")
    excel_source = source["sources"]["excel"]  # type: ignore[index]
    pdf_source = source["sources"]["pdf"]  # type: ignore[index]
    _require(
        (excel_source["files"], excel_source["bytes"], excel_source["manifest_sha256"])
        == (252, 59_441_628,
            "f9cafb2958842550b2eeefd2117b061db45d8a02ace51428d5c97b68f8e9155e"),
        "Excel raw-source census drift",
    )
    _require(
        (pdf_source["files"], pdf_source["bytes"], pdf_source["manifest_sha256"])
        == (252, 36_545_107,
            "26fec6f7fec944681c96d7970ae6ed5c2791f173379c1e74ce050f44484c9d15"),
        "PDF raw-source census drift",
    )
    token_re = re.compile(r"_route_([^./]+)\.(?:xlsx|pdf)$", re.IGNORECASE)
    token_sets = []
    for corpus in (excel_source, pdf_source):
        tokens = []
        for member in corpus["members"]:
            match = token_re.search(member["name"])
            _require(match is not None, f"unrecognized raw route member: {member['name']}")
            tokens.append(match.group(1).casefold())
        _require(len(tokens) == len(set(tokens)) == 252, "raw route tokens repeat")
        token_sets.append(set(tokens))
    _require(token_sets[0] == token_sets[1], "Excel/PDF route-token universes differ")

    _require(
        source["excel"]["output"]["sha256"] == FILE_BINDINGS["excel"][2]
        and source["pdf"]["output"]["sha256"] == FILE_BINDINGS["pdf"][2],
        "source witness consolidated output binding drift",
    )

    stage6, _ = _read_json(STAGE6_RESULT)
    stage6_acceptance, _ = _read_json(STAGE6_ACCEPTANCE)
    _require(
        stage6.get("accepted") is True
        and stage6.get("stage6_family_audit_complete") is True
        and stage6.get("projection_exact") is True
        and stage6.get("normalized_full_conservation") is False
        and stage6.get("unexplained_projection_residue_count") == 0
        and stage6.get("failed_invariants") == [],
        "Stage-6 accepted red state drift",
    )
    _require(stage6_acceptance.get("decision") == "accepted_stage6_family_audit",
             "Stage-6 detached decision drift")

    oracle, _ = _read_json(ORACLE_RESULT, canonical_lf=True)
    _require(
        oracle.get("projection_audit_complete") is True
        and oracle.get("terminal_status") == "projection_audit_complete_not_family_acceptance"
        and all(oracle.get("invariants", {}).values())
        and oracle.get("known_product_findings") == list(KNOWN_FINDINGS)
        and oracle.get("independence", {}).get("product_modules_imported_count") == 0,
        "independent projection oracle contract drift",
    )
    for flag in (
        "stage8_family_accepted", "product_comparison_perfect",
        "product_end_to_end_perfect", "comparison_end_to_end_perfect",
        "full_physical_identity_perfect", "evidence_end_to_end_exact",
    ):
        _require(oracle.get(flag) is False, f"oracle incorrectly promotes {flag}")

    for label in ("excel", "pdf", "tsn"):
        summary = oracle["inputs"][label]  # type: ignore[index]
        rows = int(summary["loaded_nonblank_rows"])
        _require(summary["filtered_blank_rows"] == 0, f"{label} has blank row gaps")
        _require(summary["streamed_data_rows"] == rows, f"{label} row census drift")
        expected_rows = _sequence_digest(range(2, rows + 2))
        _require(summary["digests"]["loaded_source_row_numbers"] == expected_rows,
                 f"{label} source rows are not contiguous ordinal+2")
    return source, oracle


def _validate_loaded_code(manifest: dict[str, object]) -> dict[str, object]:
    members = manifest.get("members")
    _require(isinstance(members, list) and members, "loaded product code is empty")
    for member in members:
        _require(isinstance(member, dict) and set(member) == {
            "module", "relative_path", "bytes", "sha256"},
            "loaded product-code member shape drift")
        relative = member["relative_path"]
        _require(isinstance(relative, str) and relative == Path(relative).as_posix()
                 and not relative.startswith("../"), "unsafe product-code path")
        _payload, identity = _capture(SCRIPTS_ROOT / relative)
        _require((identity["bytes"], identity["sha256"])
                 == (member["bytes"], member["sha256"]),
                 f"loaded product-code drift: {relative}")
    expected_digest = _sha_bytes(_json_bytes(members))
    _require(
        manifest.get("files") == len(members)
        and manifest.get("canonical_json_sha256") == expected_digest,
        "loaded product-code manifest digest drift",
    )
    return {"files": len(members), "canonical_json_sha256": expected_digest}


def _strict_product_root(root: Path) -> list[dict[str, object]]:
    entries = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        before = path.lstat()
        _require(stat.S_ISREG(before.st_mode), f"non-file product member: {path.name}")
        _require(not path.is_symlink(), f"symlink product member: {path.name}")
        _require(not (int(getattr(before, "st_file_attributes", 0)) & REPARSE_FLAG),
                 f"reparse product member: {path.name}")
        _require(before.st_nlink == 1, f"hardlinked product member: {path.name}")
        _payload, identity = _capture(path)
        entries.append({"name": path.name, **identity})
    return entries


def _decode_payload(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    sidecars = []
    for name in ("comparison.xlsx.outcome.json", "comparison (values).xlsx.outcome.json"):
        document, _ = _read_json(root / name, compact_canonical=True)
        _require(
            document.get("record_type") == "comparison"
            and document.get("comparison_schema_version") == 3
            and document.get("completion") == "complete"
            and document.get("skipped_inputs") == 0
            and document.get("failed_inputs") == 0,
            f"sidecar contract drift: {name}",
        )
        sidecars.append(document)
    _require(
        sidecars[0]["artifact_generation"] == sidecars[1]["artifact_generation"]
        and sidecars[0]["comparison_payload"] == sidecars[1]["comparison_payload"],
        "formula/value sidecar generation or payload drift",
    )
    generation = sidecars[0]["artifact_generation"]
    _require(
        generation.get("completion") == "complete"
        and generation.get("publication_state") == "committed"
        and generation.get("requested_mode") == "both",
        "sidecar generation is not a committed twin",
    )
    manifest = sidecars[0]["comparison_payload"]
    _require(
        set(manifest) == {"schema_version", "encoding", "decoded_size",
                          "decoded_sha256", "binding_sha256", "chunks"}
        and (manifest["schema_version"], manifest["encoding"])
        == (1, "canonical-json-zlib-chunks-v1"),
        "payload manifest schema drift",
    )
    chunks = manifest["chunks"]
    _require(isinstance(chunks, list) and len(chunks) == 1,
             "Highway Log final leg must have one payload chunk")
    decoded_parts = []
    chunk_public = []
    for descriptor in chunks:
        _require(set(descriptor) == {"decoded_size", "relative_path", "sha256", "size"},
                 "payload descriptor shape drift")
        relative = descriptor["relative_path"]
        _require(isinstance(relative, str) and Path(relative).name == relative,
                 "unsafe payload chunk path")
        raw, identity = _capture(root / relative)
        _require((identity["bytes"], identity["sha256"])
                 == (descriptor["size"], descriptor["sha256"]),
                 "payload chunk identity drift")
        inflater = zlib.decompressobj()
        try:
            decoded = inflater.decompress(raw) + inflater.flush()
        except zlib.error as exc:
            raise GateError(f"payload decompression failed: {exc}") from exc
        _require(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
                 "payload framing drift")
        _require(len(decoded) == descriptor["decoded_size"], "chunk decoded-size drift")
        decoded_parts.append(decoded)
        chunk_public.append({"name": relative, **identity, "decoded_bytes": len(decoded)})
    decoded = b"".join(decoded_parts)
    _require(
        len(decoded) == manifest["decoded_size"]
        and _sha_bytes(decoded) == manifest["decoded_sha256"],
        "decoded payload identity drift",
    )
    try:
        persisted = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"decoded payload JSON failed: {exc}") from exc
    _require(isinstance(persisted, dict) and decoded == _canonical(persisted),
             "decoded payload is not canonical JSON")
    binding = _sha_bytes(_canonical({
        "decoded_sha256": manifest["decoded_sha256"], "completion": "complete",
        "skipped_inputs": 0, "failed_inputs": 0,
        "artifact_generation": generation,
    }))
    _require(binding == manifest["binding_sha256"], "payload/generation binding drift")
    return persisted, {
        "decoded_bytes": len(decoded), "decoded_sha256": _sha_bytes(decoded),
        "binding_sha256": binding, "chunks": chunk_public,
    }


def _product_trace_digest(payload: dict[str, object]) -> dict[str, object]:
    records = []
    for trace in payload["pairing_trace"]:  # type: ignore[index]
        _require(isinstance(trace, dict) and set(trace) == EXPECTED_TRACE_KEYS,
                 "product pairing trace shape drift")
        _require(trace["exact"] is True and trace["quality"] == "exact"
                 and trace["algorithm"] == "rectangular-hungarian-lex-v1",
                 "product pairing trace is not exact")
        pairs = []
        for pair in trace["pairs"]:
            _require(isinstance(pair, dict) and set(pair) == EXPECTED_PAIR_KEYS,
                     "product pairing pair shape drift")
            pairs.append({
                "side_a_ordinal": pair["side_a_index"],
                "side_a_source_row": pair["side_a_index"] + 2,
                "side_b_ordinal": pair["side_b_index"],
                "side_b_source_row": pair["side_b_index"] + 2,
                "cost": pair["cost"],
            })
        records.append({
            "key": trace["key_components"],
            "side_a_size": trace["side_a_size"],
            "side_b_size": trace["side_b_size"],
            "smaller_side": trace["smaller_side"],
            "matrix_cells": trace["matrix_cells"],
            "assignment_vector": trace["assignment_vector"],
            "pairs": pairs,
            "total_cost": trace["total_cost"],
            "positional_cost": trace["positional_cost"],
            "algorithm": trace["algorithm"],
            "quality": trace["quality"],
        })
    return _sequence_digest(records)


def _normalize_product_counts(product_counts: dict[str, object],
                              oracle_counts: dict[str, object]) -> dict[str, object]:
    field_counts = product_counts.get("per_field_counts")
    _require(isinstance(field_counts, dict), "product per-field counts missing")
    normalized_fields: dict[str, object] = {}
    observed_indices = set()
    for key, value in field_counts.items():
        _require(isinstance(key, str) and ":" in key, "malformed product field key")
        ordinal_text, name = key.split(":", 1)
        _require(ordinal_text.isdigit(), "nonnumeric product field ordinal")
        ordinal = int(ordinal_text)
        _require(ordinal not in observed_indices, "duplicate product field ordinal")
        observed_indices.add(ordinal)
        normalized_fields[name] = value
    _require(observed_indices == set(range(1, 31)), "product field ordinal universe drift")
    _require(normalized_fields == oracle_counts["per_field_counts"],
             "product per-field counts differ from oracle")
    normalized = {key: value for key, value in product_counts.items()
                  if key != "per_field_counts"}
    normalized["identical_rows"] = (
        normalized["paired_rows"] - normalized["differing_rows"])
    return normalized


def _validate_leg(leg: str, root: Path, oracle: dict[str, object]) -> dict[str, object]:
    binding = LEG_BINDINGS[leg]
    _require(root.parent == VISUAL_ROOT.resolve(), f"{leg} root is not a direct audit child")
    _require(root.is_dir() and not root.is_symlink(), f"{leg} root is not a plain directory")
    document, result_identity = _read_json(root / "result.json", canonical_lf=True)
    _require((result_identity["bytes"], result_identity["sha256"])
             == (binding["result_bytes"], binding["result_sha256"]),
             f"{leg} result binding drift")
    _require(set(document) == EXPECTED_LEG_RESULT_KEYS, f"{leg} result shape drift")
    _require(
        document.get("schema_version") == 1
        and document.get("audit") == "Stage 8 Highway Log isolated current-product comparison leg"
        and document.get("leg") == leg
        and document.get("terminal_status") == "completed_leg_not_family_acceptance"
        and document.get("known_product_findings") == list(KNOWN_FINDINGS)
        and document.get("stage8_family_accepted") is False
        and document.get("comparison_end_to_end_perfect") is False
        and document.get("evidence_end_to_end_exact") is False
        and document.get("product_code_changed_by_runner") is False,
        f"{leg} terminal/nonacceptance contract drift",
    )
    _require(document["inputs"] == document["inputs_after"], f"{leg} input drift")
    for label, (_path, size, digest) in FILE_BINDINGS.items():
        if label not in document["inputs"]:
            continue
        observed = document["inputs"][label]
        _require((observed["bytes"], observed["sha256"]) == (size, digest),
                 f"{leg} input binding drift: {label}")

    product = document["product_result"]
    _require(
        product["status"] == "ok" and product["completion"] == "complete"
        and product["verdict"] == "diff" and product["skipped_inputs"] == 0
        and product["failed_inputs"] == 0 and product["warnings"] == []
        and product["failures"] == [] and product["pairing_quality"] == "exact"
        and product["pairing_trace_count"] == 989,
        f"{leg} typed product result drift",
    )
    payload, payload_identity = _decode_payload(root)
    _require(
        payload.get("status") == "ok" and payload.get("completion") == "complete"
        and payload.get("verdict") == "diff" and payload.get("pairing_quality") == "exact"
        and payload.get("warnings") == [] and payload.get("failures") == []
        and payload.get("coverage_diagnostics") == []
        and payload.get("capped_group_diagnostics") == []
        and payload.get("duplicate_group_count") == 989
        and payload.get("counts") == product["counts"],
        f"{leg} persisted payload disagrees with typed result",
    )

    oracle_leg = oracle["comparisons"][leg]  # type: ignore[index]
    normalized_counts = _normalize_product_counts(product["counts"], oracle_leg["counts"])
    _require(normalized_counts == binding["counts"], f"{leg} expected count drift")
    oracle_counts_no_fields = {key: value for key, value in oracle_leg["counts"].items()
                               if key != "per_field_counts"}
    _require(normalized_counts == oracle_counts_no_fields, f"{leg} oracle count drift")
    trace_digest = _product_trace_digest(payload)
    oracle_trace = oracle_leg["duplicate_metrics"]["assignment_trace_manifest"]
    _require(trace_digest == oracle_trace, f"{leg} pairing trace differs from oracle")
    _require(trace_digest == {"records": 989, "sha256": binding["trace_sha256"]},
             f"{leg} frozen pairing trace drift")

    final_entries = _strict_product_root(root)
    before_entries = [entry for entry in final_entries if entry["name"] != "result.json"]
    _require(len(final_entries) == 7 and len(before_entries) == 6,
             f"{leg} artifact count drift")
    _require(document["product_universe_before_result"]["members"] == before_entries,
             f"{leg} pre-result artifact universe drift")
    before_digest = _sha_bytes(_json_bytes(before_entries))
    _require(
        document["product_universe_before_result"]["files"] == 6
        and document["product_universe_before_result"]["bytes"]
        == sum(item["bytes"] for item in before_entries)
        and document["product_universe_before_result"]["canonical_json_sha256"]
        == before_digest,
        f"{leg} pre-result artifact manifest drift",
    )
    names = {entry["name"] for entry in final_entries}
    _require({"comparison.xlsx", "comparison (values).xlsx",
              "comparison.xlsx.outcome.json", "comparison (values).xlsx.outcome.json",
              ".tsmis-comparison-publication.lock", "result.json"}.issubset(names),
             f"{leg} required publication member missing")
    _require(not any(".tmp-" in name.casefold() or name.casefold().endswith(
        (".tmp", ".partial", ".staging")) for name in names),
        f"{leg} transient residue exists")
    code = _validate_loaded_code(document["loaded_product_code"])
    return {
        "leg": leg,
        "result": result_identity,
        "counts": normalized_counts,
        "per_field_counts": oracle_leg["counts"]["per_field_counts"],
        "pairing_trace_manifest": trace_digest,
        "payload": payload_identity,
        "loaded_product_code": code,
        "artifact_universe": {
            "files": len(final_entries),
            "bytes": sum(item["bytes"] for item in final_entries),
            "canonical_json_sha256": _sha_bytes(_json_bytes(final_entries)),
            "members": final_entries,
        },
    }


def _validate_output_root(path: Path, protected: set[Path]) -> Path:
    candidate = path.expanduser().resolve(strict=False)
    _require(candidate.parent == VISUAL_ROOT.resolve(),
             "output root must be a direct visualization child")
    _require(candidate.name.startswith("phase8_highway_log_final_gate_"),
             "output root name is outside the final-gate namespace")
    _require(candidate not in protected, "output root aliases an input")
    _require(not os.path.lexists(candidate), f"output root already exists: {candidate}")
    return candidate


def _write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel-leg-root", required=True, type=Path)
    parser.add_argument("--pdf-leg-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    excel_root = args.excel_leg_root.resolve()
    pdf_root = args.pdf_leg_root.resolve()
    _require(excel_root != pdf_root, "the two product legs alias")
    protected = {excel_root, pdf_root, *(path.resolve() for path, _size, _sha in FILE_BINDINGS.values())}
    output_root = _validate_output_root(args.output_root, protected)

    scripts_before = _scripts_manifest()
    _require(scripts_before == EXPECTED_SCRIPTS_MANIFEST,
             f"product scripts freeze binding drift: {scripts_before}")
    bindings_before = _bind_files()
    source, oracle = _validate_source_and_oracle()
    excel = _validate_leg("excel_vs_tsn", excel_root, oracle)
    pdf = _validate_leg("pdf_vs_tsn", pdf_root, oracle)
    _require(excel["loaded_product_code"] == pdf["loaded_product_code"],
             "the two legs loaded different product code")
    bindings_after = _bind_files()
    _require(bindings_before == bindings_after, "bound audit inputs changed during gate")
    scripts_after = _scripts_manifest()
    _require(scripts_after == scripts_before, "product scripts changed during gate")

    gate_payload, gate_identity = _capture(Path(__file__))
    result = {
        "schema_version": 1,
        "audit": "Stage 8 Highway Log final base-family audit closeout",
        "terminal_status": "accepted_stage8_base_family_audit_only",
        "acceptance_scope": (
            "projection/current-product audit handoff; not product, physical-source, "
            "workbook-evidence, or end-to-end perfection"
        ),
        "stage8_base_family_audit_complete": True,
        "source_witness": {
            "excel": {key: source["sources"]["excel"][key]
                      for key in ("files", "bytes", "manifest_sha256")},
            "pdf": {key: source["sources"]["pdf"][key]
                    for key in ("files", "bytes", "manifest_sha256")},
            "route_token_parity": True,
        },
        "bindings": {
            **bindings_before,
            "gate_code": gate_identity,
            "product_scripts_freeze": scripts_before,
        },
        "product_legs": {"excel_vs_tsn": excel, "pdf_vs_tsn": pdf},
        "invariants": {
            "source_witness_exact": True,
            "stage6_accepted_red_state_exact": True,
            "independent_oracle_exact": True,
            "excel_product_leg_exact": True,
            "pdf_product_leg_exact": True,
            "all_per_field_counts_match_oracle": True,
            "all_989_duplicate_assignments_match_oracle_per_leg": True,
            "product_publication_universes_exact": True,
            "bound_inputs_stable": True,
            "product_code_unchanged_by_gate": True,
        },
        "known_product_findings": list(KNOWN_FINDINGS),
        "known_limitations": list(oracle["known_limitations"]),
        "stage8_family_accepted": False,
        "product_comparison_perfect": False,
        "product_end_to_end_perfect": False,
        "comparison_end_to_end_perfect": False,
        "full_physical_identity_perfect": False,
        "workbook_cell_evidence_end_to_end_exact": False,
        "evidence_end_to_end_exact": False,
        "product_code_changed_by_gate": False,
    }
    result_bytes = _json_bytes(result)
    _require(result_bytes == _json_bytes(result), "result serialization drift")
    output_root.mkdir(parents=False, exist_ok=False)
    _write_exclusive(output_root / "result.json", result_bytes)
    result_identity = {"bytes": len(result_bytes), "sha256": _sha_bytes(result_bytes)}
    acceptance = {
        "schema_version": 1,
        "decision": "accepted_stage8_base_family_audit_only",
        "result": result_identity,
        "gate_code": {"bytes": len(gate_payload), "sha256": _sha_bytes(gate_payload)},
        "required_result_flags": {
            "terminal_status": "accepted_stage8_base_family_audit_only",
            "stage8_base_family_audit_complete": True,
            "stage8_family_accepted": False,
            "product_comparison_perfect": False,
            "product_end_to_end_perfect": False,
            "comparison_end_to_end_perfect": False,
            "full_physical_identity_perfect": False,
            "workbook_cell_evidence_end_to_end_exact": False,
            "evidence_end_to_end_exact": False,
            "product_code_changed_by_gate": False,
        },
        "known_product_findings": list(KNOWN_FINDINGS),
    }
    acceptance_bytes = _json_bytes(acceptance)
    _write_exclusive(output_root / "acceptance.json", acceptance_bytes)
    final_names = sorted(path.name for path in output_root.iterdir())
    _require(final_names == ["acceptance.json", "result.json"],
             "final gate output universe drift")
    _require(_capture(output_root / "result.json")[1] == result_identity,
             "published result identity drift")
    acceptance_identity = {
        "bytes": len(acceptance_bytes), "sha256": _sha_bytes(acceptance_bytes)}
    _require(_capture(output_root / "acceptance.json")[1] == acceptance_identity,
             "published acceptance identity drift")
    print(
        "PASS Highway Log Stage-8 base audit only: "
        f"result={result_identity['bytes']}/{result_identity['sha256']}; "
        f"acceptance={acceptance_identity['bytes']}/{acceptance_identity['sha256']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GateError, OSError) as exc:
        print(f"FAIL Highway Log final base-audit gate: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
