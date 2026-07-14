#!/usr/bin/env python3
"""Run exactly one current Highway Sequence production comparison witness.

This runner is intentionally one-shot and one-leg.  It binds the accepted
current source workbooks before creating a previously absent output root,
runs the selected production comparator in ``both`` mode, then validates the
returned and persisted typed generation.  It never removes, replaces, or
resumes an earlier artifact.
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
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_sequence_product_sources_r2"
EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
TSN_INPUT = (
    VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
    / "highway_sequence" / "consolidated"
    / "tsn_highway_sequence_normalized.xlsx"
)

LEG_CHOICES = (
    "excel_vs_normalized_tsn",
    "pdf_vs_normalized_tsn",
    "pdf_vs_excel",
)
INPUT_BINDINGS = {
    "excel": (
        EXCEL_INPUT,
        2_424_212,
        "cf5905332db3d3eb5a49a87d603f6e36f209cad9a84173b381dace6600168b20",
    ),
    "pdf": (
        PDF_INPUT,
        2_371_547,
        "070afe51ea3bf84c9704d0a36a02702b65189941badab6374b03461db8ef6ccc",
    ),
    "tsn": (
        TSN_INPUT,
        2_536_901,
        "9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041",
    ),
}

PUBLICATION_LEASE_NAME = ".tsmis-comparison-publication.lock"
PAYLOAD_BASENAME_RE = re.compile(
    r"^\.cmpv3-[0-9a-f]{64}-[0-9]{6}-[0-9a-f]{64}"
    r"(?:-f-(?:0[0-7]|[0-9a-f]{64}-[0-9a-f]{16}))?"
    r"\.comparison-payload\.zlib$")
LEASE_CONSTANT_SOURCE = (
    '_COMPARISON_PUBLICATION_LOCK_NAME = "'
    '.tsmis-comparison-publication.lock"'
)
LEASE_POLICY_SOURCE = "The permanent lock file is never unlinked."
RESULT_NAME = "result.json"
ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"
PRODUCT_CODE_MANIFEST_NAME = "product-code-manifest.json"


class WitnessError(RuntimeError):
    """The product run did not satisfy the witness contract."""


class _SingleValue(argparse.Action):
    """Reject repeated spellings instead of silently accepting the last one."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} must be supplied exactly once")
        setattr(namespace, self.dest, values)


def _canonical_bytes(value: object, *, newline: bool = False) -> bytes:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stat_token(value: os.stat_result) -> tuple[object, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        value.st_size,
        value.st_mtime_ns,
    )


def _stable_identity(path: Path) -> dict[str, object]:
    """Hash one ordinary file and reject a mid-read identity/content change."""
    path = Path(path)
    try:
        before = path.stat(follow_symlinks=False)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise WitnessError(f"required file is absent or unreadable: {path}") from exc
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (not stat.S_ISREG(before.st_mode)
            or bool(getattr(before, "st_file_attributes", 0) & reparse)):
        raise WitnessError(f"required path is not an ordinary file: {path}")
    digest = _sha(path)
    try:
        after = path.stat(follow_symlinks=False)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise WitnessError(f"file vanished while it was hashed: {path}") from exc
    if _stat_token(before) != _stat_token(after):
        raise WitnessError(f"file changed while it was hashed: {path}")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise WitnessError(f"file identity cannot be resolved: {path}") from exc
    return {
        "path": str(resolved),
        "bytes": after.st_size,
        "sha256": digest,
    }


def _bind_inputs() -> dict[str, dict[str, object]]:
    observed = {}
    for label, (path, expected_size, expected_sha) in INPUT_BINDINGS.items():
        identity = _stable_identity(path)
        if (identity["bytes"], identity["sha256"]) != (
                expected_size, expected_sha):
            raise WitnessError(f"{label} input identity drift: {identity}")
        observed[label] = identity
    return observed


def _source_backed_lease_policy() -> dict[str, object]:
    """Prove why the exact fixed publication lease is not transient residue."""
    source = SCRIPTS_ROOT / "consolidation_meta.py"
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise WitnessError("cannot read publication-lease product source") from exc

    def locate(needle: str) -> int:
        matches = [index + 1 for index, line in enumerate(lines)
                   if needle in line]
        if len(matches) != 1:
            raise WitnessError(
                f"publication-lease source assertion is not unique: {needle!r}")
        return matches[0]

    return {
        "exception": "permanent product publication lease; not a temp residue",
        "relative_path": PUBLICATION_LEASE_NAME,
        "required_bytes": 0,
        "source": _stable_identity(source),
        "constant": {
            "line": locate(LEASE_CONSTANT_SOURCE),
            "assertion": LEASE_CONSTANT_SOURCE,
        },
        "policy": {
            "line": locate(LEASE_POLICY_SOURCE),
            "assertion": LEASE_POLICY_SOURCE,
        },
    }


def _entry_exists(path: Path) -> bool:
    try:
        path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise WitnessError(f"cannot prove output-root absence: {path}") from exc
    return True


def _create_clean_root(path: Path) -> Path:
    path = Path(path).expanduser()
    try:
        visual_root = VISUAL_ROOT.resolve(strict=True)
        candidate = path.resolve(strict=False)
        candidate.relative_to(visual_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise WitnessError(
            f"output root must be a new descendant of {VISUAL_ROOT}: {path}") from exc
    if _entry_exists(path):
        raise WitnessError(f"refusing to delete or overwrite output root: {path}")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except (FileExistsError, OSError) as exc:
        raise WitnessError(f"could not create clean output root: {path}") from exc
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise WitnessError(f"new output root cannot be resolved: {path}") from exc
    if not resolved.is_dir() or any(resolved.iterdir()):
        raise WitnessError(f"new output root is not a clean directory: {resolved}")
    return resolved


def _comparison_paths(root: Path) -> dict[str, Path]:
    formulas = root / "comparison.xlsx"
    return {
        "formulas": formulas,
        "values": formulas.with_name("comparison (values).xlsx"),
    }


def _load_product(
        leg: str,
) -> tuple[Callable[..., object], Path, Path, object, object]:
    sys.path.insert(0, str(SCRIPTS_ROOT))
    from events import Events  # type: ignore
    import consolidation_meta  # type: ignore
    import compare_highway_sequence_tsn as hsl  # type: ignore

    if leg == "excel_vs_normalized_tsn":
        compare = hsl.compare
        side_a, side_b = EXCEL_INPUT, TSN_INPUT
    else:
        import compare_highway_sequence_pdf as hsl_pdf  # type: ignore
        if leg == "pdf_vs_normalized_tsn":
            compare = hsl_pdf.TSMIS_PDF_VS_TSN.compare
            side_a, side_b = PDF_INPUT, TSN_INPUT
        elif leg == "pdf_vs_excel":
            compare = hsl_pdf.TSMIS_PDF_VS_EXCEL.compare
            side_a, side_b = PDF_INPUT, EXCEL_INPUT
        else:  # argparse choices and this independent boundary must agree.
            raise WitnessError(f"unsupported comparison leg: {leg}")
    return compare, side_a, side_b, Events(), consolidation_meta


def _counts_payload(counts: object) -> dict[str, object]:
    return {
        "known": counts.known,
        "paired_rows": counts.paired_rows,
        "side_a_only_rows": counts.side_a_only_rows,
        "side_b_only_rows": counts.side_b_only_rows,
        "differing_rows": counts.differing_rows,
        "differing_cells": counts.differing_cells,
        "asserted_cells": counts.asserted_cells,
        "context_cells": counts.context_cells,
        "per_field_counts": dict(counts.per_field_counts),
    }


def _validate_product_result(
        result: object,
        outputs: dict[str, Path],
        consolidation_meta: object,
) -> tuple[dict[str, object], dict[str, object]]:
    comparison = getattr(result, "comparison_outcome", None)
    generation = getattr(result, "artifact_generation", None)
    attempt = getattr(result, "attempt_state", None)
    counts = getattr(comparison, "counts", None)
    if comparison is None or generation is None or attempt is None or counts is None:
        raise WitnessError("product result omitted typed outcome/publication state")
    if (getattr(result, "status", None),
            getattr(result, "completion", None),
            getattr(result, "skipped_inputs", None),
            getattr(result, "failed_inputs", None)) != (
                "ok", "complete", 0, 0):
        raise WitnessError("product result is not ok/complete/0-skipped/0-failed")
    if (comparison.status, comparison.completion) != ("ok", "complete"):
        raise WitnessError("typed comparison is not ok/complete")
    if comparison.verdict not in {"match", "diff"} or counts.known is not True:
        raise WitnessError("typed comparison verdict/counts are not certifying")
    if comparison.failures:
        raise WitnessError(
            f"typed comparison reports failures: {list(comparison.failures)!r}")
    traces = tuple(comparison.pairing_trace)
    if (comparison.pairing_quality != "exact"
            or comparison.capped_group_diagnostics
            or comparison.duplicate_group_count != len(traces)
            or any(trace.exact is not True or trace.quality != "exact"
                   for trace in traces)):
        raise WitnessError("product comparison did not preserve exact pairing")
    if (generation.completion, generation.publication_state,
            generation.requested_mode) != ("complete", "committed", "both"):
        raise WitnessError("product generation is not a committed complete twin")
    if (attempt.state != "succeeded"
            or attempt.generation_id != generation.generation_id):
        raise WitnessError("product attempt and generation identities disagree")

    members = tuple(generation.members)
    if len(members) != 2:
        raise WitnessError("committed generation does not contain exactly two members")
    by_flavor = {str(member.get("flavor")): member for member in members}
    if set(by_flavor) != {"formulas", "values"}:
        raise WitnessError("committed generation omitted a formulas/values flavor")
    expected_roles = {"formulas": "best_effort", "values": "canonical"}
    workbook_identities = {}
    sidecar_identities = {}
    persisted_members = {}
    for flavor, expected_path in outputs.items():
        identity = _stable_identity(expected_path)
        workbook_identities[flavor] = identity
        member = by_flavor[flavor]
        try:
            member_path = Path(str(member["path"])).resolve(strict=True)
        except (KeyError, OSError, RuntimeError) as exc:
            raise WitnessError(f"{flavor} generation member path is invalid") from exc
        if (member_path != expected_path.resolve(strict=True)
                or member.get("relative_path") != expected_path.name
                or member.get("commit_role") != expected_roles[flavor]
                or member.get("size") != identity["bytes"]
                or member.get("sha256") != identity["sha256"]
                or generation.content_digests.get(flavor) != identity["sha256"]):
            raise WitnessError(f"{flavor} workbook disagrees with committed generation")

        sidecar = Path(str(expected_path) + ".outcome.json")
        sidecar_identities[flavor] = _stable_identity(sidecar)
        try:
            persisted = consolidation_meta.require_published_comparison(
                expected_path, result)
        except (TypeError, ValueError, OSError) as exc:
            raise WitnessError(
                f"{flavor} outcome sidecar did not validate: {exc}") from exc
        if (persisted.trusted is not True or persisted.current is not True
                or persisted.completion != "complete"
                or persisted.skipped_inputs != 0
                or persisted.failed_inputs != 0
                or persisted.self_member is None
                or persisted.self_member.get("flavor") != flavor):
            raise WitnessError(f"{flavor} persisted comparison is not trusted/current")
        persisted_members[flavor] = {
            "trusted": True,
            "current": True,
            "completion": persisted.completion,
            "source": persisted.source,
        }

    comparison_dict = comparison.to_dict()
    trace_dicts = [trace.to_dict() for trace in traces]
    summary = {
        "status": getattr(result, "status", None),
        "completion": getattr(result, "completion", None),
        "verdict": comparison.verdict,
        "skipped_inputs": getattr(result, "skipped_inputs", None),
        "failed_inputs": getattr(result, "failed_inputs", None),
        "summary_lines": list(getattr(result, "summary_lines", ()) or ()),
        "counts": _counts_payload(counts),
        "warnings": list(comparison.warnings),
        "failures": list(comparison.failures),
        "pairing_trace_count": len(traces),
        "duplicate_group_count": comparison.duplicate_group_count,
        "pairing_quality": comparison.pairing_quality,
        "pairing_trace_sha256": hashlib.sha256(
            _canonical_bytes(trace_dicts)).hexdigest(),
        "comparison_outcome_sha256": hashlib.sha256(
            _canonical_bytes(comparison_dict)).hexdigest(),
        "artifact_generation": {
            "completion": generation.completion,
            "publication_state": generation.publication_state,
            "requested_mode": generation.requested_mode,
            "members": [
                {
                    "flavor": flavor,
                    "commit_role": by_flavor[flavor]["commit_role"],
                    "path": workbook_identities[flavor]["path"],
                    "bytes": workbook_identities[flavor]["bytes"],
                    "sha256": workbook_identities[flavor]["sha256"],
                }
                for flavor in ("formulas", "values")
            ],
        },
        "persisted_members": persisted_members,
    }
    declared_outputs = {
        "workbooks": workbook_identities,
        "outcome_sidecars": sidecar_identities,
    }
    return summary, declared_outputs


def _forbidden_residue_name(name: str) -> bool:
    folded = name.casefold()
    if name == PUBLICATION_LEASE_NAME:
        return False
    return (
        folded.startswith("~$")
        or folded.startswith(".~lock.")
        or ".tmp-" in folded
        or folded.endswith(".tmp")
        or ".staging" in folded
        or folded.endswith(".lock")
        or folded.endswith(".lck")
    )


def _residue_gate(
        root: Path,
        source_policy: dict[str, object],
        *,
        allowed_audit_names: set[str],
) -> dict[str, object]:
    entries = sorted(root.iterdir(), key=lambda path: path.name.casefold())
    unexpected = []
    lease_paths = []
    payload_paths = []
    core_names = {
        "comparison.xlsx",
        "comparison (values).xlsx",
        "comparison.xlsx.outcome.json",
        "comparison (values).xlsx.outcome.json",
        PUBLICATION_LEASE_NAME,
    }
    observed_names = {path.name for path in entries}
    for path in entries:
        try:
            facts = path.stat(follow_symlinks=False)
        except OSError as exc:
            raise WitnessError(f"cannot inspect output artifact: {path}") from exc
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if (not stat.S_ISREG(facts.st_mode)
                or bool(getattr(facts, "st_file_attributes", 0) & reparse)):
            unexpected.append(f"{path.name} (not an ordinary flat file)")
            continue
        if path.name == PUBLICATION_LEASE_NAME:
            lease_paths.append(path)
        elif PAYLOAD_BASENAME_RE.fullmatch(path.name):
            payload_paths.append(path)
        elif path.name not in core_names | allowed_audit_names:
            unexpected.append(f"{path.name} (not in the exact artifact universe)")
        elif _forbidden_residue_name(path.name):
            unexpected.append(path.name)
    if unexpected:
        raise WitnessError(f"transient/lock/staging residue remains: {unexpected!r}")
    missing_core = core_names - observed_names
    missing_audit = allowed_audit_names - observed_names
    if missing_core or missing_audit:
        raise WitnessError(
            "expected comparison artifacts are absent: "
            f"core={sorted(missing_core)!r}, audit={sorted(missing_audit)!r}")
    if not payload_paths:
        raise WitnessError("comparison publication emitted no canonical payload chunks")
    if len(lease_paths) != 1:
        raise WitnessError("the exact permanent publication lease was not inventoried")
    lease_identity = _stable_identity(lease_paths[0])
    if lease_identity["bytes"] != source_policy["required_bytes"]:
        raise WitnessError("permanent publication lease is unexpectedly non-empty")
    return {
        "transient_residue": [],
        "exact_artifact_universe": {
            "core_names": sorted(core_names),
            "audit_names": sorted(allowed_audit_names),
            "payload_chunks": sorted(path.name for path in payload_paths),
        },
        "permanent_lease": lease_identity,
        "permanent_lease_exception": source_policy,
        "rejected_name_classes": [
            "Excel/LibreOffice owner locks",
            "*.tmp and *.tmp-*",
            "*.staging*",
            "all other *.lock/*.lck",
            "non-ordinary files and nested directories",
        ],
    }


def _loaded_product_manifest(leg: str) -> dict[str, object]:
    grouped: dict[str, dict[str, object]] = {}
    scripts = SCRIPTS_ROOT.resolve(strict=True)
    for module_name, module in sorted(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        try:
            path = Path(raw).resolve(strict=True)
            relative = path.relative_to(scripts).as_posix()
        except (OSError, RuntimeError, ValueError):
            continue
        if path.suffix.casefold() not in {".py", ".pyw"}:
            continue
        member = grouped.setdefault(relative, {
            "relative_path": relative,
            "modules": [],
            "identity": _stable_identity(path),
        })
        member["modules"].append(module_name)
    members = []
    for relative in sorted(grouped):
        item = grouped[relative]
        identity = item["identity"]
        members.append({
            "relative_path": relative,
            "modules": sorted(item["modules"]),
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
        })
    required = {
        "artifact_store.py", "compare_core.py",
        "compare_highway_sequence_tsn.py", "consolidation_meta.py",
    }
    if leg in {"pdf_vs_normalized_tsn", "pdf_vs_excel"}:
        required.add("compare_highway_sequence_pdf.py")
    present = {member["relative_path"] for member in members}
    if not required <= present:
        raise WitnessError(
            f"loaded product-code manifest is missing {sorted(required - present)!r}")
    return {
        "schema": "phase8-loaded-product-code-manifest/v1",
        "files": len(members),
        "bytes": sum(member["bytes"] for member in members),
        "canonical_members_sha256": hashlib.sha256(
            _canonical_bytes(members)).hexdigest(),
        "members": members,
    }


def _artifact_manifest(
        root: Path,
        *,
        excluded_names: set[str],
) -> dict[str, object]:
    members = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if path.name in excluded_names:
            continue
        identity = _stable_identity(path)
        members.append({
            "relative_path": path.name,
            "path": identity["path"],
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
        })
    return {
        "schema": "phase8-local-artifact-manifest/v1",
        "scope": "all flat files present before artifact-manifest.json/result.json",
        "excluded_names": sorted(excluded_names),
        "files": len(members),
        "bytes": sum(member["bytes"] for member in members),
        "canonical_members_sha256": hashlib.sha256(
            _canonical_bytes(members)).hexdigest(),
        "members": members,
    }


def _write_exclusive(path: Path, payload: object) -> dict[str, object]:
    raw = _canonical_bytes(payload, newline=True)
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise WitnessError(f"refusing to overwrite audit artifact: {path}") from exc
    except OSError as exc:
        raise WitnessError(f"could not write audit artifact: {path}") from exc
    return _stable_identity(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one immutable Highway Sequence product-comparison witness.")
    parser.add_argument(
        "--leg", choices=LEG_CHOICES, required=True, default=None,
        action=_SingleValue,
    )
    parser.add_argument(
        "--output-root", type=Path, required=True, default=None,
        action=_SingleValue,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = _bind_inputs()
    lease_policy = _source_backed_lease_policy()
    root = _create_clean_root(args.output_root)

    compare, side_a, side_b, events, consolidation_meta = _load_product(args.leg)
    outputs = _comparison_paths(root)
    result = compare(
        side_a,
        side_b,
        outputs["formulas"],
        events=events,
        confirm_overwrite=lambda _path: False,
        mode="both",
    )
    result_summary, declared_outputs = _validate_product_result(
        result, outputs, consolidation_meta)
    residue = _residue_gate(
        root, lease_policy, allowed_audit_names=set())

    loaded_product_code = _loaded_product_manifest(args.leg)
    product_manifest_identity = _write_exclusive(
        root / PRODUCT_CODE_MANIFEST_NAME, loaded_product_code)
    residue = _residue_gate(
        root, lease_policy,
        allowed_audit_names={PRODUCT_CODE_MANIFEST_NAME})

    artifact_manifest_before_result = _artifact_manifest(
        root,
        excluded_names={ARTIFACT_MANIFEST_NAME, RESULT_NAME},
    )
    artifact_manifest_identity = _write_exclusive(
        root / ARTIFACT_MANIFEST_NAME, artifact_manifest_before_result)
    residue = _residue_gate(
        root, lease_policy,
        allowed_audit_names={
            PRODUCT_CODE_MANIFEST_NAME, ARTIFACT_MANIFEST_NAME,
        })

    inputs_after = _bind_inputs()
    if inputs_after != inputs:
        raise WitnessError("comparison inputs changed across the product witness")

    payload = {
        "audit": "Stage 8 Highway Sequence current product comparison leg",
        "leg": args.leg,
        "output_root": str(root),
        "inputs": inputs,
        "inputs_after": inputs_after,
        "result": result_summary,
        "outputs": declared_outputs["workbooks"],
        "outcome_sidecars": declared_outputs["outcome_sidecars"],
        "publication_artifacts": {
            "payload_chunks": [
                member for member in artifact_manifest_before_result["members"]
                if member["relative_path"].endswith(
                    ".comparison-payload.zlib")
            ],
            "outcome_sidecars": declared_outputs["outcome_sidecars"],
            "permanent_lease": residue["permanent_lease"],
        },
        "residue_gate": residue,
        "loaded_product_code": loaded_product_code,
        "product_code_manifest": product_manifest_identity,
        "artifact_manifest_before_result": artifact_manifest_before_result,
        "artifact_manifest": artifact_manifest_identity,
        "invariants": {
            "one_leg": args.leg in LEG_CHOICES,
            "complete_ok_zero_zero": True,
            "pairing_exact": True,
            "committed_formula_value_twin": True,
            "two_trusted_outcome_sidecars": True,
            "inputs_unchanged": inputs_after == inputs,
            "no_transient_residue": not residue["transient_residue"],
            "permanent_lease_source_backed": True,
            "no_delete_or_overwrite": True,
        },
    }
    if not all(payload["invariants"].values()):
        raise WitnessError(f"witness invariants failed: {payload['invariants']}")
    result_identity = _write_exclusive(root / RESULT_NAME, payload)
    print(json.dumps({
        "status": "PASS",
        "leg": args.leg,
        "result": result_identity,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WitnessError as exc:
        print(f"FAIL Highway Sequence product comparison leg: {exc}")
        raise SystemExit(1)
