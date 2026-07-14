#!/usr/bin/env python3
"""Audit-only final-family gate scaffold for Highway Sequence.

This file is deliberately fail-closed.  It binds the completed source and
development witnesses that are already immutable, but the two direct raw-TSN
product-leg bindings remain unavailable until their corrected runners finish.
No result directory is created while either binding is absent.

One invocation is exactly one replay unit: two direct-leg roots enter and one
path-neutral ``result.json`` plus one detached ``acceptance.json`` leave.  The
required two complete replays must be separate clean processes/roots and their
result and acceptance bytes must then compare exactly.  An in-process rebuild
is only a serialization control and never substitutes for that requirement.

The gate imports no product or earlier audit module.  It independently captures
ordinary files, authenticates exact flat artifact universes and terminal
records, runs real disposable mutations, preserves every known product defect
as red, and commits the detached acceptance as the only terminal PASS file.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import sys
import tempfile
from typing import Callable, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / "build"
VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)

RESULT_NAME = "result.json"
ACCEPTANCE_NAME = "acceptance.json"
REPARSE_FLAG = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
_PINNED_WINDOWS_HANDLES: list[int] = []


class GateError(RuntimeError):
    """An exact final-family gate contract failed."""


class BindingUnavailable(GateError):
    """A required final direct-leg identity has not yet been approved."""


@dataclass(frozen=True)
class Identity:
    bytes: int
    sha256: str

    def public(self, name: str) -> dict[str, object]:
        return {"name": name, "bytes": self.bytes, "sha256": self.sha256}


@dataclass(frozen=True)
class CapturedFile:
    lexical_path: Path
    canonical_path: Path
    name: str
    identity: Identity
    token: tuple[object, ...]

    def public(self) -> dict[str, object]:
        return self.identity.public(self.name)


@dataclass(frozen=True)
class CapturedRoot:
    role: str
    lexical_path: Path
    canonical_path: Path
    token: tuple[object, ...]
    members: Mapping[str, CapturedFile]

    def public(self) -> dict[str, object]:
        members = [self.members[name].public() for name in sorted(self.members)]
        return {
            "role": self.role,
            "artifact_names": sorted(self.members),
            "files": len(members),
            "bytes": sum(int(item["bytes"]) for item in members),
            "canonical_members_sha256": _sha_bytes(_canonical_bytes(members)),
            "members": members,
        }


@dataclass(frozen=True)
class DirectLegBinding:
    leg: str
    artifacts: Mapping[str, Identity]
    completion_keys: frozenset[str]
    completion_invariant_keys: frozenset[str]
    terminal_precondition_keys: frozenset[str]
    preterminal_keys: frozenset[str]
    preterminal_invariant_keys: frozenset[str]
    audit_code_field: str
    audit_code: Mapping[str, Identity]
    audit_code_paths: Mapping[str, str]
    audit_code_schema: str
    complete_manifest_schema: str
    complete_manifest_scope: str
    preterminal_audit: str
    completion_audit: str
    expected_counts: Mapping[str, int]


@dataclass(frozen=True)
class RunContext:
    roots: Mapping[str, CapturedRoot]
    files: Mapping[str, CapturedFile]
    direct_roots: Mapping[str, CapturedRoot]
    public_summary: Mapping[str, object]


def _id(size: int, digest: str) -> Identity:
    return Identity(size, digest)


TWIN_ARTIFACTS = {
    "highway_sequence_raw_tsn_audit_twin.provenance.json": _id(
        31_368_272,
        "95c0229fc0c96eb2f1e8966c300c5916c0978a17f73c39cdf829f909a1ff441b",
    ),
    "highway_sequence_raw_tsn_audit_twin.xlsx": _id(
        2_422_010,
        "68b28921c4ca8290810c92653b4a96077d6a28bdb7954447c287cf3e78d3f67d",
    ),
    "manifest.json": _id(
        388_864,
        "97541aaa963d784dbf6537cf3e6f46d32fb161f012be0ecb3abda441708b1d91",
    ),
    "result.json": _id(
        5_183,
        "d4c0a5759b0ca9731047b0f7d57fabedb228f7a61697f0c6af3cb4ef8fc4d134",
    ),
}
TWIN_DECLARED_ARTIFACT_ORDER = [
    "manifest.json",
    "highway_sequence_raw_tsn_audit_twin.provenance.json",
    "result.json",
    "highway_sequence_raw_tsn_audit_twin.xlsx",
]

STATIC_ROOT_BINDINGS: dict[str, tuple[Path, Mapping[str, Identity]]] = {
    "direct_twin_r6": (
        VISUAL_ROOT / "phase8_highway_sequence_raw_tsn_direct_twin_r6",
        TWIN_ARTIFACTS,
    ),
    "direct_twin_r7": (
        VISUAL_ROOT / "phase8_highway_sequence_raw_tsn_direct_twin_r7",
        TWIN_ARTIFACTS,
    ),
    "source_core_r2": (
        VISUAL_ROOT / "phase8_highway_sequence_source_core_checkpoint_r2",
        {
            "source-core.json": _id(
                98_943_666,
                "a8da9a24a50bf2b1ba58a8062566c1813a6518d9bede9d6fc2dec24d7fa657ce",
            ),
        },
    ),
    "normalized_excel_vs_tsn": (
        VISUAL_ROOT
        / "phase8_highway_sequence_product_comparison_excel_vs_normalized_tsn_r2",
        {
            ".cmpv3-f3099386f64cf4bba8fc8de8d5ca5e3c2444b740a0df92ee2583c6bbb326fa29-000000-8d524d8344bdc683885188ba8e75d3bbceae13d56cb0c19b6e3a589ea9f775fc.comparison-payload.zlib": _id(
                149_660,
                "8d524d8344bdc683885188ba8e75d3bbceae13d56cb0c19b6e3a589ea9f775fc",
            ),
            ".tsmis-comparison-publication.lock": _id(
                0,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "artifact-manifest.json": _id(
                2_977,
                "f1d689251b1ae654c7df1b4b85cf2291aaf8308c31fd81e575504e66c8684271",
            ),
            "comparison (values).xlsx": _id(
                34_366_704,
                "bb2d7c911ad235649468d01e019bc5cf7c7d58c293957d6667915241caafc13b",
            ),
            "comparison (values).xlsx.outcome.json": _id(
                3_008,
                "7a7235a37a2acee41465b5b50ad6a7c69ce1473454bb1178e3b80d0e06a4f688",
            ),
            "comparison.xlsx": _id(
                52_761_743,
                "d6b306fc0cef482e6a45fd3e6d1c3b366fa8f8930de2b791b26e272b315e71ce",
            ),
            "comparison.xlsx.outcome.json": _id(
                2_985,
                "49227b80fc30e51a10219a229713bfc89df47aef0d6b03cae50c364028e5a41d",
            ),
            "product-code-manifest.json": _id(
                2_576,
                "e78fdee7818b896ffbc761ae3c6f86973148eee3fc42eea797972b48b59ba6f4",
            ),
            "result.json": _id(
                16_069,
                "b1cf6f791c18917dfb51b3f9f2d8331075091992ce3d3c3415032108ee9bec83",
            ),
        },
    ),
    "normalized_pdf_vs_tsn": (
        VISUAL_ROOT
        / "phase8_highway_sequence_product_comparison_pdf_vs_normalized_tsn_r2",
        {
            ".cmpv3-88560d15b54ebf02dc17b3726d7b2ddd9a08a26ba1ef7363b8553c564dffe1b0-000000-b4fd87a82f457910df43891ba2361d5e035bee1f92b45dad05634f65072e9a3c.comparison-payload.zlib": _id(
                149_026,
                "b4fd87a82f457910df43891ba2361d5e035bee1f92b45dad05634f65072e9a3c",
            ),
            ".tsmis-comparison-publication.lock": _id(
                0,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "artifact-manifest.json": _id(
                2_963,
                "02f0db46fce2d5fe1de65b0f428dd697a2a0a745919bbf81dbb377f14fce2a12",
            ),
            "comparison (values).xlsx": _id(
                34_331_218,
                "23e9102461f2458866ef557efd4576411063f2522a5bc1f202a629fde751f180",
            ),
            "comparison (values).xlsx.outcome.json": _id(
                2_995,
                "4a4790cff4cd9174e351c6d121a1364a0cb560e2ec46e91d180b8cb5b90a5869",
            ),
            "comparison.xlsx": _id(
                52_958_377,
                "508197c9942e196c370d5d79493891cee3ef79dcc0a84aaee0039f54542409e6",
            ),
            "comparison.xlsx.outcome.json": _id(
                2_973,
                "947282379866c65c8547083f9d789595d79cdb2436d49ac09e9b81c8bd961d2e",
            ),
            "product-code-manifest.json": _id(
                2_760,
                "e4e831da2c34adb90275e8bcd5d0b1e4d3d68cea832e2730528e89bc82570973",
            ),
            "result.json": _id(
                16_228,
                "65d79577e9dbc7dfbce22d3d12fa4b8a670edb78b439b56b2802afeaa077a59a",
            ),
        },
    ),
    "normalized_pdf_vs_excel": (
        VISUAL_ROOT
        / "phase8_highway_sequence_product_comparison_pdf_vs_excel_r2",
        {
            ".cmpv3-bad1a603808941a4b8180515014a672a1ccc8d6b89ccf7b0346fa4bdeb077e7c-000000-3b3c8ad35af3b54450b5246b671fb81387c4a54257219547744bac5f4cac4f21.comparison-payload.zlib": _id(
                141_806,
                "3b3c8ad35af3b54450b5246b671fb81387c4a54257219547744bac5f4cac4f21",
            ),
            ".tsmis-comparison-publication.lock": _id(
                0,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "artifact-manifest.json": _id(
                2_900,
                "77b51248e8574868a7655733502be4b1e5dee6b1f59b7ef7e2b63697e8d46c09",
            ),
            "comparison (values).xlsx": _id(
                30_395_310,
                "5ec82f102a10f8ccc022211e769ab83c5f14ff9d1311038d1b4193a423dd0e9f",
            ),
            "comparison (values).xlsx.outcome.json": _id(
                2_941,
                "b9c707e32dc8051bad1b3434b7460c58624b179981486c6010772de38436a0ea",
            ),
            "comparison.xlsx": _id(
                45_949_156,
                "f019396854ce29933820aadb24019ae0f935800319fa043b27309225188524d6",
            ),
            "comparison.xlsx.outcome.json": _id(
                2_918,
                "2a3d31851f8847559c064f9a9a8cc8ee042a0cd29da10c6b5805287c1b34b59a",
            ),
            "product-code-manifest.json": _id(
                2_760,
                "e4e831da2c34adb90275e8bcd5d0b1e4d3d68cea832e2730528e89bc82570973",
            ),
            "result.json": _id(
                15_896,
                "972ea8466903a27d2cc609769d6fead11aceb5e2dd8d1a4e653cc0b92309f581",
            ),
        },
    ),
    "summary_spot_oracle": (
        VISUAL_ROOT / "phase8_highway_sequence_summary_spot_audit_dev_r1",
        {
            "result.json": _id(
                35_937,
                "331d4aba8321cb8e61080678f5b71357f3da249cdf02f5ad23b18ae01b9f7395",
            ),
        },
    ),
}

STATIC_FILE_BINDINGS: dict[str, tuple[Path, Identity]] = {
    "source_core_code": (
        BUILD_ROOT / "phase8_highway_sequence_comparison.py",
        _id(
            112_009,
            "469c57d9b419b6bfbe6b0ee7a1e7171f896e3585af47cc392c00ebb2383d9dd2",
        ),
    ),
    "direct_twin_builder": (
        BUILD_ROOT / "build_phase8_highway_sequence_raw_tsn_direct_twin.py",
        _id(
            57_219,
            "86d271619f4e446590fe6edaa40e9e85d74da2ca9623f9a5bfcf7877c7101ea5",
        ),
    ),
    "residual_classifier_code": (
        BUILD_ROOT / "probe_phase8_highway_sequence_product_residuals.py",
        _id(
            95_630,
            "ca4c458b5e80faead676222ca8cada74090edaa8fb332a4a478f2173b7022cec",
        ),
    ),
    "residual_classifier_r3": (
        VISUAL_ROOT / "phase8_highway_sequence_product_residuals_hardened_replay_r3.json",
        _id(
            3_509_121,
            "f6fa06569b28cdba66d059e6e9c9f40b4464149754a2561075b02c6c0307c8cc",
        ),
    ),
    "residual_classifier_r4": (
        VISUAL_ROOT / "phase8_highway_sequence_product_residuals_hardened_replay_r4.json",
        _id(
            3_509_121,
            "f6fa06569b28cdba66d059e6e9c9f40b4464149754a2561075b02c6c0307c8cc",
        ),
    ),
    "summary_spot_checker": (
        BUILD_ROOT / "check_phase8_highway_sequence_summary_spot.py",
        _id(
            80_667,
            "374ea7f8d4994a0e07b8dece903cb1ade5362bca014e0a5a85e11c8b7fcccb96",
        ),
    ),
}


DIRECT_AUDIT_CODE_PATHS = {
    "direct_product_runner": "build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py",
    "shared_product_witness": "build/run_phase8_highway_sequence_product_comparison_leg.py",
    "raw_chunk_witness": "build/run_phase8_highway_sequence_product_raw_tsn_leg.py",
    "direct_twin_builder": "build/build_phase8_highway_sequence_raw_tsn_direct_twin.py",
}
FINAL_DIRECT_AUDIT_CODE = {
    "direct_product_runner": _id(
        199_740,
        "bcc952fb3469b0e790e72eb25e1397f4639ef78ef1427ae2ea626d22ca001e91",
    ),
    "direct_twin_builder": _id(
        57_219,
        "86d271619f4e446590fe6edaa40e9e85d74da2ca9623f9a5bfcf7877c7101ea5",
    ),
    "raw_chunk_witness": _id(
        24_746,
        "5219b65815d5738b22eb2df63d6dcbba4e05f6503c4d86af8fc8daec1e073bbf",
    ),
    "shared_product_witness": _id(
        26_668,
        "09f59581a4806caa87c33ad74a5bde9b98c3001cc34b458905b88eab0a97b15b",
    ),
}
FINAL_DIRECT_COMPLETION_KEYS = frozenset({
    "acceptance_eligible", "artifact_status", "audit", "audit_code",
    "audit_code_mutations", "complete_output_artifact_manifest",
    "expected_final_artifact_names", "invariants", "leg",
    "output_containment_mutations", "output_root", "payload_chunk_names",
    "post_result_input_revalidation", "preterminal_result",
    "publication_lifecycle_mutations", "schema_version",
    "stage8_family_accepted", "status", "terminal", "terminal_preconditions",
    "terminal_residue_gate",
})
FINAL_DIRECT_COMPLETION_INVARIANT_KEYS = frozenset({
    "complete_output_artifact_universe_exact", "complete_output_identities_exact",
    "complete_output_members_physically_disjoint", "nonterminal_result_exactly_bound",
    "not_family_acceptance", "output_root_still_disjoint",
    "post_result_input_trees_exact",
    "referenced_decoded_inventoried_final_chunks_equal",
    "terminal_completion_is_last_commit", "terminal_residue_exact",
})
FINAL_DIRECT_TERMINAL_PRECONDITION_KEYS = frozenset({
    "complete_output_artifact_universe_exact", "complete_output_identities_exact",
    "complete_output_members_physically_disjoint", "output_root_still_disjoint",
    "post_result_input_trees_exact", "terminal_residue_exact",
})
FINAL_DIRECT_PRETERMINAL_KEYS = frozenset({
    "acceptance_eligible", "artifact_manifest", "artifact_manifest_before_result",
    "artifact_status", "audit", "audit_code", "audit_code_mutations",
    "decoded_comparison_payload", "deterministic_serialization",
    "direct_twin_preimport_validation", "expected_precompletion_artifact_names",
    "input_tree_revalidation", "invariants", "leg", "loaded_product_code",
    "outcome_sidecars", "output_containment_mutations", "output_root", "outputs",
    "product_code_manifest", "publication_artifacts",
    "publication_lifecycle_mutations", "reason",
    "required_detached_terminal_completion", "residue_gate", "result",
    "schema_version", "stage8_family_accepted", "status", "terminal",
})
FINAL_DIRECT_PRETERMINAL_INVARIANT_KEYS = frozenset({
    "accepted_stage6_and_raw_pdf_bindings_exact",
    "bidirectional_998_998_zero_orphan_topology",
    "canonical_deterministic_audit_json", "committed_formula_value_twin",
    "complete_ok_zero_zero", "direct_twin_current_builder_exact",
    "direct_twin_not_family_acceptance", "direct_twin_v1_validated_before_product_import",
    "disposable_containment_mutations_passed", "exact_artifact_universe_declared",
    "input_tree_universes_frozen_through_pre_result", "loaded_product_code_manifested",
    "no_delete_or_overwrite", "no_transient_residue", "one_leg_only",
    "only_zero_byte_source_backed_permanent_lease", "pairing_exact",
    "payload_chunks_decoded_and_bound", "publication_lifecycle_mutations_passed",
    "raw_records_69804", "referenced_decoded_inventoried_chunks_equal",
    "reverse_only_topology_mutation_rejected", "this_record_is_explicitly_nonterminal",
    "tsmis_inputs_independently_exact_bound", "two_trusted_outcome_sidecars",
    "two_way_output_input_disjointness", "workbook_reopen_equals_all_provenance_rows",
})


def _final_direct_binding(
    leg: str,
    artifacts: Mapping[str, Identity],
    expected_counts: Mapping[str, int],
) -> DirectLegBinding:
    return DirectLegBinding(
        leg=leg,
        artifacts=artifacts,
        completion_keys=FINAL_DIRECT_COMPLETION_KEYS,
        completion_invariant_keys=FINAL_DIRECT_COMPLETION_INVARIANT_KEYS,
        terminal_precondition_keys=FINAL_DIRECT_TERMINAL_PRECONDITION_KEYS,
        preterminal_keys=FINAL_DIRECT_PRETERMINAL_KEYS,
        preterminal_invariant_keys=FINAL_DIRECT_PRETERMINAL_INVARIANT_KEYS,
        audit_code_field="audit_code",
        audit_code=FINAL_DIRECT_AUDIT_CODE,
        audit_code_paths=DIRECT_AUDIT_CODE_PATHS,
        audit_code_schema="phase8-direct-raw-audit-code/v1",
        complete_manifest_schema="phase8-complete-flat-output-manifest/v1",
        complete_manifest_scope=(
            "every ordinary file present before detached terminal completion"
        ),
        preterminal_audit=(
            "Stage 8 Highway Sequence direct-source raw-TSN product comparison leg "
            "preterminal record"
        ),
        completion_audit=(
            "Stage 8 Highway Sequence direct-source raw-TSN product comparison leg "
            "detached completion"
        ),
        expected_counts=expected_counts,
    )


FINAL_DIRECT_LEG_BINDINGS: dict[str, DirectLegBinding | None] = {
    "excel_vs_raw_tsn": _final_direct_binding(
        "excel_vs_raw_tsn",
        {
            ".cmpv3-5132105d1afe4b773ae4b16bc01229f0bd55cd02e08152386a6a622b6f04591e-000000-2ce830fcc3853322ab4ebc34d47a5ad606af95334da3098d4a8b621d94460abd.comparison-payload.zlib": _id(
                149_747, "2ce830fcc3853322ab4ebc34d47a5ad606af95334da3098d4a8b621d94460abd",
            ),
            ".tsmis-comparison-publication.lock": _id(
                0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "artifact-manifest.json": _id(
                2_872, "03173eb397efacdb4f43669d555d90b05079a33e939647c833ecbdf963cbae7e",
            ),
            "comparison (values).xlsx": _id(
                34_385_223, "71b84a640147a33404c2fa493b16c28796bd76ff9992313b4305b1f00ab3004c",
            ),
            "comparison (values).xlsx.outcome.json": _id(
                2_918, "fbc7066f77c8b2464442c913a091d011f6542809427fb868925f167c02ffcb55",
            ),
            "comparison.xlsx": _id(
                52_793_093, "d64d977c46ca2a50f58a97b49afd9e79b7ec6c601dfc0d501f208d38bd22448e",
            ),
            "comparison.xlsx.outcome.json": _id(
                2_895, "21cc11a182e7d8b023d06ebc5c9498035f37d5f6ac6a3d3bede19036ebad2cc6",
            ),
            "completion.json": _id(
                11_198, "6aee127601ae5caeffa85f4404f1a34c44097fa22d7214ddee87a94e15f784a0",
            ),
            "product-code-manifest.json": _id(
                2_576, "e78fdee7818b896ffbc761ae3c6f86973148eee3fc42eea797972b48b59ba6f4",
            ),
            "result.json": _id(
                37_574, "2d60f9c48b72bf109769118f193575ccb099d0f5fcb1cc1e216ff4a46301e7e5",
            ),
        },
        {
            "paired_rows": 57_072, "side_a_only_rows": 3_422,
            "side_b_only_rows": 12_732, "differing_rows": 4_822,
            "differing_cells": 5_516, "asserted_cells": 171_216,
        },
    ),
    "pdf_vs_raw_tsn": _final_direct_binding(
        "pdf_vs_raw_tsn",
        {
            ".cmpv3-f66debcbb1a9aae3bf0714fd647386c1c0dd181ee829bbf2aaf51f181780d3ca-000000-e344d06257b94416813826839dcba7aab636d5314a04ee41e31b568562306f83.comparison-payload.zlib": _id(
                149_004, "e344d06257b94416813826839dcba7aab636d5314a04ee41e31b568562306f83",
            ),
            ".tsmis-comparison-publication.lock": _id(
                0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "artifact-manifest.json": _id(
                2_858, "a8a679d2b08a2d44cf8414b1dd3ddb45817473fde949927993d2dcdf5a45dc46",
            ),
            "comparison (values).xlsx": _id(
                34_349_991, "fd75c59881d12352287ba21e0d548d26c7da027df95ae0373d7d623a0f5fc500",
            ),
            "comparison (values).xlsx.outcome.json": _id(
                2_906, "b906bdb976fa35a079d78c3e8f34adde92a7ff724842a78348dda709675e4f0f",
            ),
            "comparison.xlsx": _id(
                52_989_698, "3c4ecbbeb2d6c21b82bba4fe5ebc95a8563659a7cc38df4f95e0adfcd1d29df2",
            ),
            "comparison.xlsx.outcome.json": _id(
                2_883, "f1ec31f20a512e070c80924a9cabda59aae72d579e66841bb9f930dba833ebb4",
            ),
            "completion.json": _id(
                11_190, "2a61f7f861f6c1ce4d0736cfd849b2f5ea2309a358edac78bfec6b40d57a32b9",
            ),
            "product-code-manifest.json": _id(
                2_760, "e4e831da2c34adb90275e8bcd5d0b1e4d3d68cea832e2730528e89bc82570973",
            ),
            "result.json": _id(
                37_735, "b2b66cdaef898453e32d4f7480746b43f44b7378a5f5ba0df9031442f6081c47",
            ),
        },
        {
            "paired_rows": 57_505, "side_a_only_rows": 2_988,
            "side_b_only_rows": 12_299, "differing_rows": 4_845,
            "differing_cells": 4_929, "asserted_cells": 172_515,
        },
    ),
}
DIRECT_PRODUCT_OUTPUT_MUTATION_LABELS = {
    "comparison.xlsx": "artifact_identity_comparison_formulas_workbook",
    "comparison (values).xlsx": "artifact_identity_comparison_values_workbook",
    "comparison.xlsx.outcome.json": "artifact_identity_comparison_formulas_outcome_sidecar",
    "comparison (values).xlsx.outcome.json": "artifact_identity_comparison_values_outcome_sidecar",
}


NORMALIZED_LEG_EXPECTATIONS = {
    "normalized_excel_vs_tsn": {
        "leg": "excel_vs_normalized_tsn",
        "paired_rows": 57_072,
        "side_a_only_rows": 3_422,
        "side_b_only_rows": 12_686,
        "differing_rows": 4_823,
        "differing_cells": 5_517,
        "asserted_cells": 171_216,
    },
    "normalized_pdf_vs_tsn": {
        "leg": "pdf_vs_normalized_tsn",
        "paired_rows": 57_505,
        "side_a_only_rows": 2_988,
        "side_b_only_rows": 12_253,
        "differing_rows": 4_846,
        "differing_cells": 4_930,
        "asserted_cells": 172_515,
    },
    "normalized_pdf_vs_excel": {
        "leg": "pdf_vs_excel",
        "paired_rows": 59_946,
        "side_a_only_rows": 547,
        "side_b_only_rows": 548,
        "differing_rows": 867,
        "differing_cells": 1_725,
        "asserted_cells": 179_838,
    },
}


PRODUCT_RED_FINDINGS = (
    ("CMP-AUD-155", "normalized rows omit district/direction/report provenance"),
    ("CMP-AUD-156", "565 authoritative landmark pointer tokens are blanked"),
    ("CMP-AUD-158", "46 pre-county EQUATES annotations are absent from normalization"),
    ("CMP-AUD-159", "one wrapped Description gains invented punctuation"),
    ("CMP-AUD-193", "current-source publication must not reuse stale cross-bundle inputs"),
    ("CMP-AUD-197", "four decoded CRLF values are reported as literal escape differences"),
    ("CMP-AUD-199", "PDF-vs-Excel identity incorrectly includes the changing equation suffix"),
    ("CMP-AUD-204", "TSN numeric Description prefixes false-clean 81 rows per vs-TSN leg"),
    ("CMP-AUD-208", "visual evidence does not authenticate published Comparison cells"),
    ("CMP-AUD-209", "visual evidence excludes whole discrepancy classes before sampling"),
    ("CMP-AUD-210", "Excel and PDF-vs-Excel lack source-faithful evidence modes"),
    ("CMP-AUD-214", "Spot Check overwrites its field-by-field banner"),
    ("CMP-AUD-218", "Spot Check trusts Comparison pairing/status and can falsely say OK"),
    ("CMP-AUD-220", "product duplicate matching changes hundreds of source assignments"),
)


DIRECT_RESULT_KEYS = {
    "acceptance_eligible", "artifact_status", "artifact_universe", "artifacts",
    "audit", "bidirectional_equate_topology", "counts", "invariants",
    "ordered_rows_sha256", "output_root_embedded", "reason",
    "reverse_topology_mutation_rejected", "schema_version",
    "stage8_family_accepted", "status", "terminal",
}
DIRECT_MANIFEST_KEYS = {
    "acceptance_eligible", "accepted_stage6_chain", "artifact_status", "audit",
    "bidirectional_equate_topology", "builder_identity", "canonical_xlsx_package",
    "core_timestamp_mutation", "counts", "delayed_in_memory_determinism",
    "fresh_stage6_digests", "generated", "independence",
    "output_artifact_names", "output_root_embedded", "output_root_gate",
    "reverse_topology_mutation", "runtime", "schema_version", "source_capture",
    "stage8_family_accepted", "static_bindings", "workbook_reopen",
    "workbook_schema",
}
DIRECT_PROVENANCE_KEYS = {
    "acceptance_eligible", "accepted_stage6_chain", "artifact_status", "audit",
    "bidirectional_equate_topology", "raw_documents", "reason", "row_count", "rows",
    "schema", "schema_version", "source_capture", "stage8_family_accepted",
}
NORMALIZED_RESULT_KEYS = {
    "artifact_manifest", "artifact_manifest_before_result", "audit", "inputs",
    "inputs_after", "invariants", "leg", "loaded_product_code",
    "outcome_sidecars", "output_root", "outputs", "product_code_manifest",
    "publication_artifacts", "residue_gate", "result",
}
NORMALIZED_COMPLETION_KEYS = {
    "artifact_generation", "comparison_outcome_sha256", "completion", "counts",
    "duplicate_group_count", "failed_inputs", "failures", "pairing_quality",
    "pairing_trace_count", "pairing_trace_sha256", "persisted_members",
    "skipped_inputs", "status", "summary_lines", "verdict", "warnings",
}
NORMALIZED_INVARIANT_KEYS = {
    "committed_formula_value_twin", "complete_ok_zero_zero", "inputs_unchanged",
    "no_delete_or_overwrite", "no_transient_residue", "one_leg", "pairing_exact",
    "permanent_lease_source_backed", "two_trusted_outcome_sidecars",
}
SOURCE_CORE_KEYS = {
    "acceptance_eligible", "accepted_stage6_chain", "artifact_status", "audit",
    "bindings_after", "bindings_before", "bindings_stable", "current_source_legs",
    "description_prefix_proof", "edition_proof", "historical_regression_legs",
    "independence", "keyable_raw_semantic_contracts", "negative_mutations",
    "prior_incomplete_attempts", "raw_tsn_equate_events", "raw_vs_normalized_tsn",
    "remaining_external_layers", "same_source_equate_events",
    "same_source_unrepresented_claims", "schema_version", "single_byte_tsmis_captures",
    "source_core_invariants", "source_datasets", "stage8_family_accepted",
    "tsmis_slash_padding_artifacts", "typed_role_rename_invariance",
}
RESIDUAL_KEYS = {
    "acceptance_eligible", "artifact_status", "audit", "captured_json_identities",
    "guard_mutations", "inputs_after", "inputs_before", "invariants", "legs",
    "methodology", "not_an_acceptance_artifact", "raw_normalized_overlay",
    "source_census", "source_projection_populations", "unexplained_residuals",
}
SUMMARY_KEYS = {
    "acceptance_artifact", "audit", "checker", "legs", "negative_controls",
    "reason_not_acceptance", "status", "verified_invariants",
}


def _require(condition: object, message: str) -> None:
    if not condition:
        raise GateError(message)


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ) + "\n"
    ).encode("utf-8")


def _canonical_compact_bytes(value: object) -> bytes:
    """Producer-compatible aggregate bytes, intentionally without the file LF."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json(payload: bytes, label: str, *, canonical: bool = False) -> object:
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                GateError(f"non-finite JSON token in {label}: {token}")),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"invalid strict JSON in {label}: {exc}") from exc
    if canonical and payload != _canonical_bytes(value):
        raise GateError(f"noncanonical JSON bytes in {label}")
    return value


def _require_keys(value: object, expected: set[str] | frozenset[str], label: str) -> Mapping[str, object]:
    _require(isinstance(value, Mapping), f"{label} must be an object")
    observed = set(value)
    _require(
        observed == set(expected),
        f"{label} key universe drift: missing={sorted(set(expected) - observed)!r}; "
        f"extra={sorted(observed - set(expected))!r}",
    )
    return value


def _stat_token(value: os.stat_result) -> tuple[object, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        value.st_size,
        value.st_mtime_ns,
        getattr(value, "st_ctime_ns", None),
        getattr(value, "st_nlink", None),
        int(getattr(value, "st_file_attributes", 0)),
    )


def _physical_object_token(value: os.stat_result) -> tuple[object, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        int(getattr(value, "st_file_attributes", 0)),
    )


def _pin_windows_path(
    path: Path,
    *,
    directory: bool,
    deny_write: bool,
    rename_capable: bool = False,
) -> int:
    """Hold a no-delete Windows handle so the final path cannot be swapped.

    Raw handles are deliberately retained until process teardown.  Closing a
    successful pin after terminal publication would itself be post-commit I/O.
    """
    _require(os.name == "nt", "final publication path pinning is Windows-only")
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    file_read_attributes = 0x0080
    delete_access = 0x00010000
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    open_existing = 3
    file_flag_backup_semantics = 0x02000000
    file_flag_open_reparse_point = 0x00200000
    _require(not rename_capable or (deny_write and not directory), "rename-capable pin contract drift")
    share = file_share_read if deny_write else file_share_read | file_share_write
    flags = file_flag_open_reparse_point | (file_flag_backup_semantics if directory else 0)
    handle = create_file(
        str(path),
        file_read_attributes | (delete_access if rename_capable else 0),
        share,
        None,
        open_existing,
        flags,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    numeric = int(handle) if handle is not None else invalid
    if numeric == invalid:
        raise GateError(f"cannot pin {'directory' if directory else 'file'} against replacement")
    _PINNED_WINDOWS_HANDLES.append(numeric)
    return numeric


def _rename_pinned_windows_handle(handle: int, destination: Path) -> None:
    """Rename a write/delete-exclusive pinned file without reopening its path."""
    _require(os.name == "nt", "pinned-handle rename is Windows-only")
    import ctypes
    from ctypes import wintypes

    target = str(destination)

    class FileRenameInfo(ctypes.Structure):
        _fields_ = (
            ("ReplaceIfExists", wintypes.BOOL),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * (len(target) + 1)),
        )

    info = FileRenameInfo()
    info.ReplaceIfExists = False
    info.RootDirectory = None
    info.FileNameLength = len(target.encode("utf-16-le"))
    info.FileName = target
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    rename = kernel32.SetFileInformationByHandle
    rename.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    rename.restype = wintypes.BOOL
    file_rename_info_class = 3
    if not rename(
        wintypes.HANDLE(handle),
        file_rename_info_class,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise GateError("exclusive pinned-handle acceptance rename failed")


def _close_windows_pin_on_failure(handle: int) -> None:
    """Release a nonauthoritative pin only so failed publication can clean up."""
    _require(os.name == "nt", "Windows pin cleanup is Windows-only")
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close = kernel32.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    if not close(wintypes.HANDLE(handle)):
        raise GateError("failed to release staged acceptance pin after publication failure")
    try:
        _PINNED_WINDOWS_HANDLES.remove(handle)
    except ValueError as exc:
        raise GateError("staged acceptance pin ledger drift during failure cleanup") from exc


def _lexical_absolute(path: Path, label: str) -> Path:
    _require(path.is_absolute(), f"{label} must be absolute")
    _require(
        not any(part in {".", ".."} for part in path.parts),
        f"{label} contains a lexical alias component",
    )
    return path


def _existing_components(path: Path, label: str) -> list[tuple[Path, os.stat_result]]:
    path = _lexical_absolute(path, label)
    current = Path(path.anchor)
    candidates = [current]
    for part in path.parts[1:]:
        current = current / part
        candidates.append(current)
    observed: list[tuple[Path, os.stat_result]] = []
    for candidate in candidates:
        try:
            facts = os.lstat(candidate)
        except FileNotFoundError:
            break
        except OSError as exc:
            raise GateError(f"cannot lstat {label} component") from exc
        observed.append((candidate, facts))
    return observed


def _assert_plain_components(path: Path, label: str) -> None:
    components = _existing_components(path, label)
    _require(components, f"{label} has no existing lexical component")
    for _component, facts in components:
        _require(
            not stat.S_ISLNK(facts.st_mode)
            and not (int(getattr(facts, "st_file_attributes", 0)) & REPARSE_FLAG),
            f"{label} contains a symlink/reparse component",
        )


def _stream_identity(path: Path, label: str) -> CapturedFile:
    path = _lexical_absolute(path, label)
    _assert_plain_components(path, label)
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise GateError(f"required file is absent: {label}") from exc
    _require(stat.S_ISREG(before.st_mode), f"{label} is not an ordinary file")
    _require(
        not (int(getattr(before, "st_file_attributes", 0)) & REPARSE_FLAG),
        f"{label} is a reparse file",
    )
    digest = hashlib.sha256()
    length = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                length += len(chunk)
        after = os.lstat(path)
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GateError(f"cannot capture exact file: {label}") from exc
    _require(_stat_token(before) == _stat_token(after), f"{label} changed during capture")
    _require(length == after.st_size, f"{label} streamed length drift")
    return CapturedFile(
        lexical_path=path,
        canonical_path=canonical,
        name=path.name,
        identity=Identity(length, digest.hexdigest()),
        token=_stat_token(after),
    )


def _capture_expected_file(path: Path, expected: Identity, label: str) -> CapturedFile:
    captured = _stream_identity(path, label)
    _require(captured.identity == expected, f"{label} fixed identity drift")
    return captured


def _read_bound_bytes(captured: CapturedFile, label: str) -> bytes:
    _assert_plain_components(captured.lexical_path, label)
    before = os.lstat(captured.lexical_path)
    try:
        payload = captured.lexical_path.read_bytes()
        after = os.lstat(captured.lexical_path)
    except OSError as exc:
        raise GateError(f"cannot read bound bytes: {label}") from exc
    _require(_stat_token(before) == _stat_token(after) == captured.token, f"{label} identity token drift")
    _require(
        Identity(len(payload), _sha_bytes(payload)) == captured.identity,
        f"{label} bytes differ from captured identity",
    )
    return payload


def _capture_exact_root(
    role: str,
    path: Path,
    expected: Mapping[str, Identity],
) -> CapturedRoot:
    path = _lexical_absolute(path, role)
    _assert_plain_components(path, role)
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise GateError(f"required root is absent: {role}") from exc
    _require(stat.S_ISDIR(before.st_mode), f"{role} is not an ordinary directory")
    canonical = path.resolve(strict=True)
    try:
        names = sorted(item.name for item in os.scandir(path))
    except OSError as exc:
        raise GateError(f"cannot enumerate exact root: {role}") from exc
    _require(names == sorted(expected), f"{role} flat artifact universe drift")
    members: dict[str, CapturedFile] = {}
    for name in names:
        _require(Path(name).name == name and name not in {"", ".", ".."}, f"unsafe member name in {role}")
        member = _capture_expected_file(path / name, expected[name], f"{role}/{name}")
        _require(member.canonical_path.parent == canonical, f"{role}/{name} escaped its root")
        members[name] = member
    after = os.lstat(path)
    _require(_stat_token(before) == _stat_token(after), f"{role} root changed during capture")
    _require(sorted(item.name for item in os.scandir(path)) == names, f"{role} names changed during capture")
    return CapturedRoot(role, path, canonical, _stat_token(after), members)


def _parse_member(root: CapturedRoot, name: str, *, canonical: bool = False) -> Mapping[str, object]:
    value = _strict_json(
        _read_bound_bytes(root.members[name], f"{root.role}/{name}"),
        f"{root.role}/{name}",
        canonical=canonical,
    )
    _require(isinstance(value, Mapping), f"{root.role}/{name} is not an object")
    return value


def _parse_file(captured: CapturedFile, role: str, *, canonical: bool = False) -> Mapping[str, object]:
    value = _strict_json(_read_bound_bytes(captured, role), role, canonical=canonical)
    _require(isinstance(value, Mapping), f"{role} is not an object")
    return value


def _all_exact_true(value: object, keys: set[str] | frozenset[str], label: str) -> Mapping[str, object]:
    checked = _require_keys(value, keys, label)
    _require(all(checked[key] is True for key in keys), f"{label} is not exactly all true")
    return checked


def _require_nonacceptance(document: Mapping[str, object], label: str, *, terminal: bool) -> None:
    _require(document.get("acceptance_eligible") is False, f"{label} claims acceptance eligibility")
    _require(document.get("stage8_family_accepted") is False, f"{label} claims Stage-8 acceptance")
    if terminal:
        _require(document.get("terminal") is True, f"{label} is not terminal")
        _require(
            document.get("status") == "PASS_DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE",
            f"{label} terminal status drift",
        )


def _claim_identity(value: object, expected: Identity, label: str) -> None:
    checked = _require_keys(value, {"bytes", "sha256"}, label)
    _require(checked["bytes"] == expected.bytes, f"{label} byte count drift")
    _require(checked["sha256"] == expected.sha256, f"{label} SHA-256 drift")


def _validate_direct_twin(root: CapturedRoot) -> dict[str, object]:
    result = _require_keys(_parse_member(root, "result.json"), DIRECT_RESULT_KEYS, f"{root.role} result")
    manifest = _require_keys(_parse_member(root, "manifest.json"), DIRECT_MANIFEST_KEYS, f"{root.role} manifest")
    provenance = _require_keys(
        _parse_member(root, "highway_sequence_raw_tsn_audit_twin.provenance.json"),
        DIRECT_PROVENANCE_KEYS,
        f"{root.role} provenance",
    )
    _require_nonacceptance(result, f"{root.role} result", terminal=True)
    for label, document in (("manifest", manifest), ("provenance", provenance)):
        _require_nonacceptance(document, f"{root.role} {label}", terminal=False)
        _require(
            document.get("artifact_status") == "DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE",
            f"{root.role} {label} artifact status drift",
        )
    _require(result.get("artifact_status") == "DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE", f"{root.role} result artifact status drift")
    _require(result.get("schema_version") == manifest.get("schema_version") == provenance.get("schema_version") == 1, f"{root.role} schema drift")
    _require(result.get("output_root_embedded") is False, f"{root.role} result embeds output root")
    _require(manifest.get("output_root_embedded") is False, f"{root.role} manifest embeds output root")

    expected_counts = {
        "raw_records": 69_804,
        "data_records": 68_806,
        "equate_records": 998,
        "blank_county_equates": 46,
        "pointer_total": 565,
        "projectable_records": 69_758,
        "ordered_rows_sha256": "5ef81b31622730e8f1369d1989cc92c717be7eb4ad8f29061b3750ff78f767fc",
    }
    for label, counts in (("result", result.get("counts")), ("manifest", manifest.get("counts"))):
        _require(isinstance(counts, Mapping), f"{root.role} {label} counts absent")
        for key, expected in expected_counts.items():
            _require(counts.get(key) == expected, f"{root.role} {label} count drift: {key}")
    _require(result.get("ordered_rows_sha256") == expected_counts["ordered_rows_sha256"], f"{root.role} ordered-row digest drift")
    _require(provenance.get("row_count") == 69_804, f"{root.role} provenance row count drift")

    expected_topology = {
        "equate_rows": 998,
        "data_e_rows": 998,
        "forward_paired": 998,
        "forward_unpaired": 0,
        "reverse_paired": 998,
        "reverse_unpaired": 0,
        "pair_ledgers_exact": True,
    }
    topology_digests: set[str] = set()
    for label, document in (("result", result), ("manifest", manifest), ("provenance", provenance)):
        topology = document.get("bidirectional_equate_topology")
        _require(isinstance(topology, Mapping), f"{root.role} {label} topology absent")
        for key, expected in expected_topology.items():
            _require(topology.get(key) == expected, f"{root.role} {label} topology drift: {key}")
        _require(topology.get("forward_ledger_sha256") == topology.get("reverse_ledger_sha256"), f"{root.role} {label} topology ledger disagreement")
        topology_digests.add(str(topology.get("forward_ledger_sha256")))
    _require(len(topology_digests) == 1, f"{root.role} topology digest disagreement")
    _require(result.get("reverse_topology_mutation_rejected") is True, f"{root.role} reverse mutation not rejected")

    invariants = result.get("invariants")
    _require(isinstance(invariants, Mapping) and invariants, f"{root.role} invariants absent")
    _require(all(value is True for value in invariants.values()), f"{root.role} result invariants not all true")
    _require(result.get("artifact_universe") == TWIN_DECLARED_ARTIFACT_ORDER, f"{root.role} artifact universe/order drift")
    _require(manifest.get("output_artifact_names") == TWIN_DECLARED_ARTIFACT_ORDER, f"{root.role} manifest output names/order drift")
    artifacts = _require_keys(result.get("artifacts"), {"manifest", "provenance", "workbook"}, f"{root.role} artifact identities")
    for claim_role, name in {
        "manifest": "manifest.json",
        "provenance": "highway_sequence_raw_tsn_audit_twin.provenance.json",
        "workbook": "highway_sequence_raw_tsn_audit_twin.xlsx",
    }.items():
        _claim_identity(artifacts[claim_role], root.members[name].identity, f"{root.role} {claim_role}")
    builder = _require_keys(manifest.get("builder_identity"), {"bytes", "canonical_path", "name", "sha256"}, f"{root.role} builder identity")
    expected_builder = STATIC_FILE_BINDINGS["direct_twin_builder"][1]
    _require(builder["bytes"] == expected_builder.bytes and builder["sha256"] == expected_builder.sha256, f"{root.role} builder identity drift")
    _require(builder["name"] == "build_phase8_highway_sequence_raw_tsn_direct_twin.py", f"{root.role} builder name drift")
    return {
        "role": root.role,
        "root": root.public(),
        "raw_records": 69_804,
        "data_plus_equates": [68_806, 998],
        "blank_county_equates": 46,
        "pointer_tokens": 565,
        "ordered_rows_sha256": expected_counts["ordered_rows_sha256"],
        "bidirectional_equates": [998, 998],
        "terminal_nonacceptance": True,
    }


def _validate_source_core(root: CapturedRoot) -> dict[str, object]:
    document = _require_keys(_parse_member(root, "source-core.json"), SOURCE_CORE_KEYS, "source core")
    _require(document.get("schema_version") == 1, "source-core schema drift")
    _require(document.get("artifact_status") == "SOURCE_CORE_CHECKPOINT_NOT_FINAL_ACCEPTANCE", "source-core status drift")
    _require(document.get("acceptance_eligible") is False, "source core claims acceptance")
    _require(document.get("stage8_family_accepted") is False, "source core claims family acceptance")
    _require(document.get("bindings_stable") is True, "source-core bindings are unstable")
    invariants = document.get("source_core_invariants")
    _require(isinstance(invariants, Mapping), "source-core invariant ledger absent")
    expected = {
        "all_checks_passed": True,
        "raw_tsn_records": 69_804,
        "raw_tsn_data_plus_equates": [68_806, 998],
        "raw_tsn_unknown_county_equates": 46,
        "pointer_tokens_blanked": 565,
        "normalized_tsn_rows": 69_758,
        "current_rows_excel_pdf": [60_494, 60_493],
        "same_source_shape_pdf_excel": [60_493, 0, 1],
        "product_false_clean_rows_each_current_tsn_leg": 81,
    }
    for key, value in expected.items():
        _require(invariants.get(key) == value, f"source-core invariant drift: {key}")
    _require(
        document.get("remaining_external_layers") == [
            "product publication witness binding",
            "Comparison workbook and sidecar semantic inspection",
            "exhaustive evidence/source locator reconciliation",
            "permanent adversarial gate",
            "detached acceptance decision",
            "two byte-identical full replays",
        ],
        "source-core remaining-layer boundary drift",
    )
    return {
        "root": root.public(),
        "artifact_status": document["artifact_status"],
        "all_checks_passed": True,
        "raw_records": 69_804,
        "current_rows_excel_pdf": [60_494, 60_493],
        "remaining_external_layers": list(document["remaining_external_layers"]),
    }


def _validate_normalized_leg(root: CapturedRoot, expected: Mapping[str, object]) -> dict[str, object]:
    document = _require_keys(_parse_member(root, "result.json"), NORMALIZED_RESULT_KEYS, f"{root.role} result")
    _require(document.get("leg") == expected["leg"], f"{root.role} leg drift")
    _all_exact_true(document.get("invariants"), NORMALIZED_INVARIANT_KEYS, f"{root.role} invariants")
    completion = _require_keys(document.get("result"), NORMALIZED_COMPLETION_KEYS, f"{root.role} product result")
    _require(completion.get("status") == "ok", f"{root.role} status is not ok")
    _require(completion.get("completion") == "complete", f"{root.role} completion is not complete")
    _require(completion.get("verdict") == "diff", f"{root.role} verdict is not the expected diff")
    _require(completion.get("failed_inputs") == 0 and completion.get("skipped_inputs") == 0, f"{root.role} has skipped/failed inputs")
    _require(completion.get("pairing_quality") == "exact", f"{root.role} pairing is not exact")
    counts = completion.get("counts")
    _require(isinstance(counts, Mapping), f"{root.role} counts absent")
    for key in ("paired_rows", "side_a_only_rows", "side_b_only_rows", "differing_rows", "differing_cells", "asserted_cells"):
        _require(counts.get(key) == expected[key], f"{root.role} count drift: {key}")
    _require(document.get("inputs") == document.get("inputs_after"), f"{root.role} input identities changed")
    return {
        "root": root.public(),
        "leg": expected["leg"],
        "completion": "complete",
        "verdict": "diff",
        "counts": {key: expected[key] for key in (
            "paired_rows", "side_a_only_rows", "side_b_only_rows",
            "differing_rows", "differing_cells", "asserted_cells",
        )},
        "known_product_defects_preserved": True,
    }


RESIDUAL_INVARIANT_KEYS = {
    "all_four_aggregate_deltas_reconcile",
    "all_four_assignment_policy_attributions_executably_proven",
    "all_four_corrected_source_pair_maps_recomputed_exactly",
    "all_four_product_pair_maps_recomputed_exactly",
    "all_input_identities_stable",
    "all_residuals_classified",
    "authentic_and_arbitrary_swap_mutations_passed",
    "cmp_aud_159_normalized_false_positive_each_tsmis_form",
    "cmp_aud_204_false_clean_rows_each_leg",
    "output_alias_mutations_passed_or_truthfully_skipped",
    "raw_unknown_county_rows_explicit",
    "unexplained_residuals",
}
SUMMARY_INVARIANT_KEYS = {
    "acceptance_boundary_explicit",
    "all_declared_source_inputs_authenticated",
    "all_five_bound_witness_results_authenticated",
    "all_formula_comparison_cells_reconstructed_exactly",
    "all_source_rows_snapshots_and_backlinks_exact",
    "all_spot_cell_maps_selected_rows_and_six_fields_exact",
    "all_summary_cell_maps_semantically_exact_and_exhaustive",
    "all_ten_workbook_payloads_captured_hashed_and_inspected_from_same_bytes",
    "all_values_comparison_cells_reconstructed_from_embedded_sources",
    "audit_exact_map_negative_controls_pass",
    "cmp_aud_214_banner_overwrite_present_in_all_ten_workbooks",
    "cmp_aud_218_comparison_dependency_present_in_all_ten_workbooks",
    "cmp_aud_218_wrong_pair_and_status_mutations_falsely_say_ok_everywhere",
}
SUMMARY_NEGATIVE_KEYS = {
    "cell_type_mutation_rejected",
    "cell_value_mutation_rejected",
    "extra_cell_rejected",
    "missing_cell_rejected",
}


def _validate_residual_classifier(
    r3: CapturedFile,
    r4: CapturedFile,
    checker: CapturedFile,
) -> dict[str, object]:
    _require(r3.identity == r4.identity, "residual classifier replays are not byte-identical")
    _require(
        _read_bound_bytes(r3, "residual classifier r3")
        == _read_bound_bytes(r4, "residual classifier r4"),
        "residual classifier replay payloads differ",
    )
    document = _require_keys(_parse_file(r3, "residual classifier r3"), RESIDUAL_KEYS, "residual classifier")
    _require(document.get("artifact_status") == "NON_ACCEPTANCE_DEVELOPMENT_CLASSIFIER", "residual classifier status drift")
    _require(document.get("acceptance_eligible") is False, "residual classifier claims acceptance")
    invariants = _require_keys(document.get("invariants"), RESIDUAL_INVARIANT_KEYS, "residual invariants")
    for key in RESIDUAL_INVARIANT_KEYS - {
        "cmp_aud_159_normalized_false_positive_each_tsmis_form",
        "cmp_aud_204_false_clean_rows_each_leg",
        "raw_unknown_county_rows_explicit",
        "unexplained_residuals",
    }:
        _require(invariants[key] is True, f"residual invariant is not true: {key}")
    _require(invariants["cmp_aud_159_normalized_false_positive_each_tsmis_form"] == 1, "CMP-AUD-159 residual count drift")
    _require(invariants["cmp_aud_204_false_clean_rows_each_leg"] == 81, "CMP-AUD-204 residual count drift")
    _require(invariants["raw_unknown_county_rows_explicit"] == 46, "raw unknown-County residual count drift")
    _require(invariants["unexplained_residuals"] == 0, "residual classifier has unexplained residue")
    _require(document.get("unexplained_residuals") == [], "unexplained residual ledger is nonempty")
    _require(document.get("inputs_before") == document.get("inputs_after"), "residual classifier inputs changed")
    census = document.get("source_census")
    _require(isinstance(census, Mapping), "residual source census absent")
    for key, value in {
        "current_tsmis_excel": 60_494,
        "current_tsmis_pdf": 60_493,
        "normalized_tsn": 69_758,
        "raw_tsn_all": 69_804,
        "raw_tsn_known_county": 69_758,
        "raw_tsn_unknown_county": 46,
    }.items():
        _require(census.get(key) == value, f"residual source census drift: {key}")
    guards = document.get("guard_mutations")
    _require(isinstance(guards, Mapping), "residual guard-mutation ledger absent")
    assignment = guards.get("assignment_attribution")
    paths = guards.get("path_and_output_alias")
    _require(isinstance(assignment, Mapping) and isinstance(paths, Mapping), "residual guard mutation shape drift")
    arbitrary = assignment.get("arbitrary_swap")
    authentic = assignment.get("authentic_policy_divergence")
    _require(isinstance(arbitrary, Mapping) and arbitrary.get("status") == "rejected", "arbitrary pair swap was not rejected")
    _require(arbitrary.get("reasons") == ["PRODUCT_PAIRING_IS_NOT_RECOMPUTED_PRODUCT_OPTIMUM"], "arbitrary-swap reason drift")
    _require(isinstance(authentic, Mapping) and authentic.get("status") == "passed", "authentic assignment control failed")
    for key in (
        "directory_symlink_or_reparse_component", "file_symlink_or_reparse",
        "hardlink_output_alias", "lexical_output_alias",
    ):
        probe = paths.get(key)
        _require(isinstance(probe, Mapping) and probe.get("status") == "passed", f"residual path mutation did not execute/pass: {key}")
    return {
        "replays": [r3.public(), r4.public()],
        "checker": checker.public(),
        "byte_identical": True,
        "unexplained_residuals": 0,
        "false_clean_rows_each_vs_tsn_leg": 81,
        "raw_unknown_county_rows": 46,
        "arbitrary_swap_rejected": True,
        "real_path_and_output_mutations_passed": True,
        "artifact_status": document["artifact_status"],
    }


def _validate_summary_spot(root: CapturedRoot, checker: CapturedFile) -> dict[str, object]:
    document = _require_keys(_parse_member(root, "result.json"), SUMMARY_KEYS, "Summary/Spot oracle")
    _require(document.get("status") == "pass_with_expected_product_defects", "Summary/Spot status drift")
    _require(document.get("acceptance_artifact") is False, "Summary/Spot oracle claims acceptance")
    _all_exact_true(document.get("verified_invariants"), SUMMARY_INVARIANT_KEYS, "Summary/Spot verified invariants")
    _all_exact_true(document.get("negative_controls"), SUMMARY_NEGATIVE_KEYS, "Summary/Spot negative controls")
    legs = document.get("legs")
    _require(
        isinstance(legs, Mapping)
        and set(legs) == {
            "excel_vs_normalized_tsn", "excel_vs_raw_tsn", "pdf_vs_excel",
            "pdf_vs_normalized_tsn", "pdf_vs_raw_tsn",
        },
        "Summary/Spot five-leg universe drift",
    )
    checker_claim = _require_keys(document.get("checker"), {"bytes", "path", "sha256"}, "Summary/Spot checker identity")
    _require(checker_claim["bytes"] == checker.identity.bytes and checker_claim["sha256"] == checker.identity.sha256, "Summary/Spot checker identity drift")
    _require(Path(str(checker_claim["path"])).name == checker.name, "Summary/Spot checker filename drift")
    return {
        "root": root.public(),
        "checker": checker.public(),
        "status": document["status"],
        "acceptance_artifact": False,
        "verified_invariants": len(SUMMARY_INVARIANT_KEYS),
        "negative_controls": len(SUMMARY_NEGATIVE_KEYS),
        "cmp_aud_214_reproduced_all_ten": True,
        "cmp_aud_218_reproduced_all_ten": True,
    }


DIRECT_COMPLETION_MANDATORY_KEYS = {
    "schema_version", "audit", "status", "terminal", "artifact_status",
    "acceptance_eligible", "stage8_family_accepted", "leg", "preterminal_result",
    "complete_output_artifact_manifest", "expected_final_artifact_names",
    "terminal_preconditions", "invariants",
}
DIRECT_PRETERMINAL_MANDATORY_KEYS = {
    "schema_version", "audit", "status", "terminal", "artifact_status",
    "acceptance_eligible", "stage8_family_accepted", "leg", "invariants",
    "expected_precompletion_artifact_names", "required_detached_terminal_completion",
}
DIRECT_PRETERMINAL_REQUIRED_INVARIANTS = {
    "one_leg_only",
    "direct_twin_v1_validated_before_product_import",
    "direct_twin_not_family_acceptance",
    "raw_records_69804",
    "input_tree_universes_frozen_through_pre_result",
    "exact_artifact_universe_declared",
    "this_record_is_explicitly_nonterminal",
}
DIRECT_COMPLETION_REQUIRED_INVARIANTS = {
    "nonterminal_result_exactly_bound",
    "post_result_input_trees_exact",
    "complete_output_artifact_universe_exact",
    "complete_output_identities_exact",
    "complete_output_members_physically_disjoint",
    "terminal_residue_exact",
    "terminal_completion_is_last_commit",
    "not_family_acceptance",
}
DIRECT_TERMINAL_REQUIRED_PRECONDITIONS = {
    "post_result_input_trees_exact",
    "complete_output_artifact_universe_exact",
    "complete_output_identities_exact",
    "complete_output_members_physically_disjoint",
    "terminal_residue_exact",
    "output_root_still_disjoint",
}
DIRECT_SOURCE_EXPECTED_COUNTS = {
    "excel_vs_raw_tsn": {
        "paired_rows": 57_072,
        "side_a_only_rows": 3_422,
        "side_b_only_rows": 12_732,
        "differing_rows": 4_822,
        "differing_cells": 5_516,
        "asserted_cells": 171_216,
    },
    "pdf_vs_raw_tsn": {
        "paired_rows": 57_505,
        "side_a_only_rows": 2_988,
        "side_b_only_rows": 12_299,
        "differing_rows": 4_845,
        "differing_cells": 4_929,
        "asserted_cells": 172_515,
    },
}
AUDIT_CODE_MANIFEST_KEYS = {"schema", "roles", "canonical_members_sha256", "members"}
AUDIT_CODE_MEMBER_KEYS = {"role", "logical_path", "bytes", "sha256"}
COMPLETE_OUTPUT_MANIFEST_KEYS = {"schema", "scope", "files", "bytes", "canonical_members_sha256", "members"}
COMPLETE_OUTPUT_MEMBER_KEYS = {"relative_path", "bytes", "sha256"}


def _identity_from_claim(value: object, label: str, *, name_key: str | None = None) -> tuple[str | None, Identity]:
    keys = {"bytes", "sha256"} | ({name_key} if name_key else set())
    checked = _require_keys(value, keys, label)
    size = checked["bytes"]
    digest = checked["sha256"]
    _require(type(size) is int and size >= 0, f"{label} has invalid byte count")
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), f"{label} has invalid SHA-256")
    name: str | None = None
    if name_key:
        name = checked[name_key]
        _require(isinstance(name, str) and Path(name).name == name, f"{label} has unsafe filename")
    return name, Identity(size, digest)


def _validate_audit_code_claim(value: object, binding: DirectLegBinding, label: str) -> dict[str, object]:
    document = _require_keys(value, AUDIT_CODE_MANIFEST_KEYS, label)
    _require(set(binding.audit_code) == set(binding.audit_code_paths), f"{label} binding role/path disagreement")
    _require(document.get("schema") == binding.audit_code_schema, f"{label} schema drift")
    _require(type(document.get("roles")) is int and document.get("roles") == len(binding.audit_code), f"{label} role count drift")
    members = document.get("members")
    _require(isinstance(members, list) and len(members) == len(binding.audit_code), f"{label} member count drift")
    observed: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(members):
        member = _require_keys(raw, AUDIT_CODE_MEMBER_KEYS, f"{label} member {index}")
        role = member.get("role")
        _require(isinstance(role, str) and role in binding.audit_code and role not in observed, f"{label} invalid/duplicate role")
        _require(member.get("logical_path") == binding.audit_code_paths[role], f"{label} exact repo-relative role path drift: {role}")
        expected = binding.audit_code[role]
        _require(member.get("bytes") == expected.bytes and member.get("sha256") == expected.sha256, f"{label} role identity drift: {role}")
        observed[role] = dict(member)
    _require(set(observed) == set(binding.audit_code), f"{label} missing audit-code role")
    canonical_members = [observed[role] for role in sorted(observed)]
    _require(members == canonical_members, f"{label} member order drift")
    _require(document.get("canonical_members_sha256") == _sha_bytes(_canonical_compact_bytes(canonical_members)), f"{label} member digest drift")
    return {
        "schema": document["schema"],
        "roles": sorted(observed),
        "canonical_members_sha256": document["canonical_members_sha256"],
        "members": canonical_members,
    }


def _validate_complete_manifest(
    value: object,
    expected_members: Mapping[str, CapturedFile],
    label: str,
    *,
    schema: str,
    scope: str,
) -> dict[str, object]:
    document = _require_keys(value, COMPLETE_OUTPUT_MANIFEST_KEYS, label)
    _require(document.get("schema") == schema, f"{label} schema drift")
    _require(document.get("scope") == scope, f"{label} scope drift")
    members = document.get("members")
    _require(isinstance(members, list), f"{label} members absent")
    observed: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(members):
        member = _require_keys(raw, COMPLETE_OUTPUT_MEMBER_KEYS, f"{label} member {index}")
        name = member.get("relative_path")
        _require(isinstance(name, str) and Path(name).name == name and name not in observed, f"{label} unsafe/duplicate member")
        expected = expected_members.get(name)
        _require(expected is not None, f"{label} undeclared member: {name}")
        _require(member.get("bytes") == expected.identity.bytes and member.get("sha256") == expected.identity.sha256, f"{label} member identity drift: {name}")
        observed[name] = dict(member)
    _require(set(observed) == set(expected_members), f"{label} exact member universe drift")
    canonical_members = [observed[name] for name in sorted(observed)]
    _require(members == canonical_members, f"{label} member order drift")
    _require(document.get("files") == len(canonical_members), f"{label} file total drift")
    _require(document.get("bytes") == sum(int(member["bytes"]) for member in canonical_members), f"{label} byte total drift")
    _require(document.get("canonical_members_sha256") == _sha_bytes(_canonical_compact_bytes(canonical_members)), f"{label} canonical member digest drift")
    return {
        "schema": document["schema"],
        "scope": document["scope"],
        "files": document["files"],
        "bytes": document["bytes"],
        "canonical_members_sha256": document["canonical_members_sha256"],
        "members": canonical_members,
    }


def _path_identity_claim(value: object, expected: CapturedFile, label: str) -> None:
    claim = _require_keys(value, {"path", "bytes", "sha256"}, label)
    claimed_path = _lexical_absolute(Path(str(claim["path"])), label)
    _assert_plain_components(claimed_path, label)
    _require(claimed_path.name == expected.name, f"{label} filename drift")
    try:
        claimed_canonical = claimed_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GateError(f"{label} path cannot resolve to its bound member") from exc
    _require(claimed_canonical == expected.canonical_path, f"{label} does not resolve to the bound result member")
    _require(claim["bytes"] == expected.identity.bytes, f"{label} byte count drift")
    _require(claim["sha256"] == expected.identity.sha256, f"{label} SHA-256 drift")


def _validate_direct_leg_documents(
    root: CapturedRoot,
    binding: DirectLegBinding,
    completion: Mapping[str, object],
    preterminal: Mapping[str, object],
) -> dict[str, object]:
    _require(DIRECT_COMPLETION_MANDATORY_KEYS <= set(binding.completion_keys), f"{binding.leg} binding omits mandatory completion keys")
    _require(DIRECT_PRETERMINAL_MANDATORY_KEYS <= set(binding.preterminal_keys), f"{binding.leg} binding omits mandatory preterminal keys")
    completion = _require_keys(completion, binding.completion_keys, f"{binding.leg} completion-v1")
    preterminal = _require_keys(preterminal, binding.preterminal_keys, f"{binding.leg} preterminal-v1")
    _require(completion.get("schema_version") == preterminal.get("schema_version") == 1, f"{binding.leg} schema drift")
    _require(type(completion.get("schema_version")) is int and type(preterminal.get("schema_version")) is int, f"{binding.leg} schema type drift")
    _require(completion.get("audit") == binding.completion_audit, f"{binding.leg} completion audit identity drift")
    _require(preterminal.get("audit") == binding.preterminal_audit, f"{binding.leg} preterminal audit identity drift")
    _require(completion.get("leg") == preterminal.get("leg") == binding.leg, f"{binding.leg} leg claim drift")
    _require(completion.get("status") == "PASS_DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE", f"{binding.leg} terminal status drift")
    _require(completion.get("terminal") is True, f"{binding.leg} completion is not terminal")
    _require(preterminal.get("status") == "PRETERMINAL_AUDIT_WITNESS_PENDING_DETACHED_COMPLETION", f"{binding.leg} preterminal status drift")
    _require(preterminal.get("terminal") is False, f"{binding.leg} preterminal falsely claims terminal")
    for label, document in (("completion", completion), ("preterminal", preterminal)):
        _require(document.get("artifact_status") == "DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE", f"{binding.leg} {label} artifact status drift")
        _require(document.get("acceptance_eligible") is False, f"{binding.leg} {label} claims acceptance")
        _require(document.get("stage8_family_accepted") is False, f"{binding.leg} {label} claims family acceptance")

    for label, document in (("completion", completion), ("preterminal", preterminal)):
        if "output_root" in document:
            claimed = _lexical_absolute(Path(str(document["output_root"])), f"{binding.leg} {label} output root")
            _require(claimed.resolve(strict=True) == root.canonical_path, f"{binding.leg} {label} output-root binding drift")

    _all_exact_true(preterminal.get("invariants"), binding.preterminal_invariant_keys, f"{binding.leg} preterminal invariants")
    _all_exact_true(completion.get("invariants"), binding.completion_invariant_keys, f"{binding.leg} completion invariants")
    _all_exact_true(completion.get("terminal_preconditions"), binding.terminal_precondition_keys, f"{binding.leg} terminal preconditions")

    _require(binding.audit_code_field in completion and binding.audit_code_field in preterminal, f"{binding.leg} audit-code field absent")
    completion_code = _validate_audit_code_claim(completion[binding.audit_code_field], binding, f"{binding.leg} completion audit code")
    preterminal_code = _validate_audit_code_claim(preterminal[binding.audit_code_field], binding, f"{binding.leg} preterminal audit code")
    _require(completion_code == preterminal_code, f"{binding.leg} audit-code ledgers disagree")

    expected_final_names = sorted(root.members)
    expected_preterminal_names = sorted(set(root.members) - {"completion.json"})
    _require(completion.get("expected_final_artifact_names") == expected_final_names, f"{binding.leg} final artifact-name universe drift")
    _require(preterminal.get("expected_precompletion_artifact_names") == expected_preterminal_names, f"{binding.leg} precompletion name universe drift")
    _require(preterminal.get("required_detached_terminal_completion") == "completion.json", f"{binding.leg} required completion name drift")
    _require("completion.json" in root.members and "result.json" in root.members, f"{binding.leg} required records absent")
    manifest = _validate_complete_manifest(
        completion.get("complete_output_artifact_manifest"),
        {name: member for name, member in root.members.items() if name != "completion.json"},
        f"{binding.leg} complete output manifest",
        schema=binding.complete_manifest_schema,
        scope=binding.complete_manifest_scope,
    )
    _path_identity_claim(completion.get("preterminal_result"), root.members["result.json"], f"{binding.leg} bound preterminal result")

    result_summary = preterminal.get("result")
    _require(isinstance(result_summary, Mapping), f"{binding.leg} product-result summary absent")
    counts = result_summary.get("counts")
    _require(isinstance(counts, Mapping), f"{binding.leg} product counts absent")
    for key, expected in binding.expected_counts.items():
        _require(counts.get(key) == expected, f"{binding.leg} expected count drift: {key}")
    _require(result_summary.get("status") == "ok", f"{binding.leg} product status is not ok")
    _require(result_summary.get("completion") == "complete", f"{binding.leg} product run incomplete")
    _require(result_summary.get("verdict") == "diff", f"{binding.leg} product verdict drift")
    _require(result_summary.get("failed_inputs") == 0 and result_summary.get("skipped_inputs") == 0, f"{binding.leg} skipped/failed product inputs")
    _require(result_summary.get("pairing_quality") == "exact", f"{binding.leg} product pairing not exact")
    return {
        "leg": binding.leg,
        "root": root.public(),
        "terminal_nonacceptance": True,
        "preterminal_result": root.members["result.json"].public(),
        "completion": root.members["completion.json"].public(),
        "complete_output_manifest": manifest,
        "audit_code": completion_code,
        "counts": {key: binding.expected_counts[key] for key in sorted(binding.expected_counts)},
    }


def _validate_direct_leg(root: CapturedRoot, binding: DirectLegBinding) -> dict[str, object]:
    completion = _parse_member(root, "completion.json", canonical=True)
    preterminal = _parse_member(root, "result.json", canonical=True)
    return _validate_direct_leg_documents(root, binding, completion, preterminal)


def _require_direct_leg_bindings_ready() -> Mapping[str, DirectLegBinding]:
    missing = sorted(role for role, binding in FINAL_DIRECT_LEG_BINDINGS.items() if binding is None)
    if missing:
        raise BindingUnavailable(
            "corrected direct-leg terminal identities are unavailable: " + ", ".join(missing)
        )
    ready = {role: binding for role, binding in FINAL_DIRECT_LEG_BINDINGS.items() if binding is not None}
    _require(set(ready) == {"excel_vs_raw_tsn", "pdf_vs_raw_tsn"}, "direct-leg binding universe drift")
    for role, binding in ready.items():
        _require(binding.leg == role, f"direct-leg binding role drift: {role}")
        _require(set(binding.artifacts) >= {"result.json", "completion.json"}, f"direct-leg binding artifact universe incomplete: {role}")
        _require(set(DIRECT_PRODUCT_OUTPUT_MUTATION_LABELS) <= set(binding.artifacts), f"direct-leg real product outputs absent: {role}")
        _require(DIRECT_COMPLETION_MANDATORY_KEYS <= set(binding.completion_keys), f"direct-leg completion schema omits mandatory keys: {role}")
        _require(DIRECT_PRETERMINAL_MANDATORY_KEYS <= set(binding.preterminal_keys), f"direct-leg preterminal schema omits mandatory keys: {role}")
        _require(DIRECT_COMPLETION_REQUIRED_INVARIANTS <= set(binding.completion_invariant_keys), f"direct-leg completion invariant schema incomplete: {role}")
        _require(DIRECT_PRETERMINAL_REQUIRED_INVARIANTS <= set(binding.preterminal_invariant_keys), f"direct-leg preterminal invariant schema incomplete: {role}")
        _require(DIRECT_TERMINAL_REQUIRED_PRECONDITIONS <= set(binding.terminal_precondition_keys), f"direct-leg terminal precondition schema incomplete: {role}")
        _require(dict(binding.expected_counts) == DIRECT_SOURCE_EXPECTED_COUNTS[role], f"direct-leg source-derived expected count ledger drift: {role}")
        _require(len(binding.audit_code) == 4, f"direct-leg audit-code role count is not four: {role}")
        _require(dict(binding.audit_code_paths) == DIRECT_AUDIT_CODE_PATHS, f"direct-leg exact audit-code role/path ledger drift: {role}")
        _require(binding.audit_code_field == "audit_code", f"direct-leg audit-code field drift: {role}")
        for label, value in (
            ("audit-code schema", binding.audit_code_schema),
            ("complete-manifest schema", binding.complete_manifest_schema),
            ("complete-manifest scope", binding.complete_manifest_scope),
            ("preterminal audit identity", binding.preterminal_audit),
            ("completion audit identity", binding.completion_audit),
        ):
            _require(isinstance(value, str) and value, f"direct-leg {label} unavailable: {role}")
    excel = ready["excel_vs_raw_tsn"]
    pdf = ready["pdf_vs_raw_tsn"]
    _require(dict(excel.audit_code) == dict(pdf.audit_code), "direct-leg audit-code identities disagree across legs")
    return ready


def _all_captured_files(context: RunContext) -> list[CapturedFile]:
    result = list(context.files.values())
    for root in [*context.roots.values(), *context.direct_roots.values()]:
        result.extend(root.members.values())
    return result


def _assert_physical_independence(context: RunContext) -> None:
    captures = _all_captured_files(context)
    direct_members = [member for root in context.direct_roots.values() for member in root.members.values()]
    for member in direct_members:
        nlink = member.token[6]
        _require(nlink == 1, f"direct-leg final member has unexpected link count: {member.name}")
    for index, first in enumerate(captures):
        for second in captures[index + 1:]:
            try:
                aliased = os.path.samefile(first.lexical_path, second.lexical_path)
            except OSError as exc:
                raise GateError("cannot prove captured-file physical distinctness") from exc
            _require(not aliased, f"captured files are physical aliases: {first.name}, {second.name}")


def _semantic_summary(
    roots: Mapping[str, CapturedRoot],
    files: Mapping[str, CapturedFile],
    direct_roots: Mapping[str, CapturedRoot],
    bindings: Mapping[str, DirectLegBinding],
) -> dict[str, object]:
    twin_r6 = _validate_direct_twin(roots["direct_twin_r6"])
    twin_r7 = _validate_direct_twin(roots["direct_twin_r7"])
    for name in TWIN_ARTIFACTS:
        _require(
            roots["direct_twin_r6"].members[name].identity
            == roots["direct_twin_r7"].members[name].identity,
            f"direct twin r6/r7 bytes differ: {name}",
        )
    normalized = {
        role: _validate_normalized_leg(roots[role], expected)
        for role, expected in sorted(NORMALIZED_LEG_EXPECTATIONS.items())
    }
    source_core = _validate_source_core(roots["source_core_r2"])
    residual = _validate_residual_classifier(
        files["residual_classifier_r3"],
        files["residual_classifier_r4"],
        files["residual_classifier_code"],
    )
    summary_spot = _validate_summary_spot(
        roots["summary_spot_oracle"], files["summary_spot_checker"],
    )
    direct = {
        role: _validate_direct_leg(direct_roots[role], bindings[role])
        for role in sorted(bindings)
    }
    return {
        "direct_raw_tsn_twin": {
            "r6": twin_r6,
            "r7": twin_r7,
            "all_four_artifacts_byte_identical": True,
        },
        "source_core": source_core,
        "normalized_product_legs": normalized,
        "residual_classifier": residual,
        "summary_spot_oracle": summary_spot,
        "direct_raw_product_legs": direct,
    }


def _capture_context(
    direct_paths: Mapping[str, Path],
    bindings: Mapping[str, DirectLegBinding],
) -> RunContext:
    _require(set(direct_paths) == set(bindings), "direct-leg CLI/binding role disagreement")
    roots = {
        role: _capture_exact_root(role, path, expected)
        for role, (path, expected) in sorted(STATIC_ROOT_BINDINGS.items())
    }
    files = {
        role: _capture_expected_file(path, expected, role)
        for role, (path, expected) in sorted(STATIC_FILE_BINDINGS.items())
    }
    audit_code_by_logical_path: dict[str, Identity] = {}
    for leg, binding in sorted(bindings.items()):
        for audit_role in sorted(binding.audit_code):
            logical_path = binding.audit_code_paths[audit_role]
            parsed = PurePosixPath(logical_path)
            _require(
                not parsed.is_absolute()
                and parsed.parts
                and parsed.parts[0] == "build"
                and all(part not in {"", ".", ".."} for part in parsed.parts),
                f"unsafe direct audit-code logical path: {leg}/{audit_role}",
            )
            expected = binding.audit_code[audit_role]
            prior = audit_code_by_logical_path.get(logical_path)
            _require(prior is None or prior == expected, f"direct-leg audit-code binding disagreement: {logical_path}")
            audit_code_by_logical_path[logical_path] = expected
    for logical_path, expected in sorted(audit_code_by_logical_path.items()):
        actual = REPO_ROOT.joinpath(*PurePosixPath(logical_path).parts)
        existing = [captured for captured in files.values() if captured.lexical_path == actual]
        if existing:
            _require(len(existing) == 1 and existing[0].identity == expected, f"shared direct audit-code binding drift: {logical_path}")
        else:
            files[f"direct_audit_code::{logical_path}"] = _capture_expected_file(
                actual,
                expected,
                f"direct audit code {logical_path}",
            )
    self_path = _lexical_absolute(Path(__file__).absolute(), "final-family gate code")
    _require(self_path == BUILD_ROOT / "phase8_highway_sequence_final_family_gate.py", "final-family gate physical repo-relative role drift")
    files["final_family_gate_code"] = _stream_identity(self_path, "final-family gate code")
    direct_roots = {
        role: _capture_exact_root(role, direct_paths[role], bindings[role].artifacts)
        for role in sorted(bindings)
    }
    provisional = RunContext(roots, files, direct_roots, {})
    _assert_physical_independence(provisional)
    public_summary = _semantic_summary(roots, files, direct_roots, bindings)
    return RunContext(roots, files, direct_roots, public_summary)


def _recapture_context(context: RunContext, bindings: Mapping[str, DirectLegBinding]) -> RunContext:
    roots: dict[str, CapturedRoot] = {}
    for role, original in sorted(context.roots.items()):
        roots[role] = _capture_exact_root(
            role,
            original.lexical_path,
            {name: member.identity for name, member in original.members.items()},
        )
        _require(roots[role].token == original.token, f"frozen root identity token drift: {role}")
    files: dict[str, CapturedFile] = {}
    for role, original in sorted(context.files.items()):
        files[role] = _capture_expected_file(original.lexical_path, original.identity, role)
        _require(files[role].token == original.token, f"frozen file identity token drift: {role}")
    direct_roots: dict[str, CapturedRoot] = {}
    for role, original in sorted(context.direct_roots.items()):
        direct_roots[role] = _capture_exact_root(
            role,
            original.lexical_path,
            {name: member.identity for name, member in original.members.items()},
        )
        _require(direct_roots[role].token == original.token, f"frozen direct root token drift: {role}")
    recaptured = RunContext(roots, files, direct_roots, {})
    _assert_physical_independence(recaptured)
    summary = _semantic_summary(roots, files, direct_roots, bindings)
    _require(summary == context.public_summary, "semantic input summary changed during final revalidation")
    return RunContext(roots, files, direct_roots, summary)


def _path_text(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _paths_overlap(first: Path, second: Path) -> bool:
    left = _path_text(first)
    right = _path_text(second)
    try:
        common = os.path.commonpath([left, right])
    except ValueError:
        return False
    return common == left or common == right


def _validate_new_output_root(
    candidate: Path,
    private_root: Path,
    protected_paths: Iterable[Path],
) -> Path:
    candidate = _lexical_absolute(candidate, "output root")
    private_root = _lexical_absolute(private_root, "private output parent")
    _assert_plain_components(private_root, "private output parent")
    _require(Path(candidate.name).name == candidate.name and candidate.name not in {"", ".", ".."}, "unsafe output-root name")
    _require(candidate.parent == private_root, "output root must be a direct child of the private output parent")
    _assert_plain_components(candidate.parent, "output-root parent")
    _require(not os.path.lexists(candidate), "output root already exists or is an alias")
    for protected in protected_paths:
        protected = _lexical_absolute(protected, "protected input path")
        _require(not _paths_overlap(candidate, protected), "output root overlaps a protected input")
    return candidate


def _protected_paths(context: RunContext) -> tuple[Path, ...]:
    paths: set[Path] = set()
    for root in [*context.roots.values(), *context.direct_roots.values()]:
        paths.add(root.lexical_path)
        paths.update(member.lexical_path for member in root.members.values())
    paths.update(item.lexical_path for item in context.files.values())
    return tuple(sorted(paths, key=lambda item: str(item).casefold()))


RESULT_KEYS = {
    "schema_version", "audit", "status", "terminal", "artifact_status",
    "acceptance_eligible", "stage8_family_accepted",
    "bound_audit_inputs_complete_for_this_replay",
    "comparison_end_to_end_perfect", "evidence_end_to_end_exact",
    "input_binding_ledger", "input_bindings_sha256", "gate_code",
    "source_truth", "known_product_findings", "permanent_mutations",
    "replay_contract", "invariants",
}
RESULT_AUDIT = "Stage 8 Highway Sequence audit-only final-family replay gate"
ACCEPTANCE_AUDIT = "Stage 8 Highway Sequence detached audit replay-unit decision"
RESULT_INVARIANT_KEYS = {
    "all_bound_flat_universes_exact",
    "all_bound_json_contracts_exact",
    "all_direct_leg_terminal_records_exact",
    "all_direct_leg_members_physically_distinct",
    "audit_code_roles_exact",
    "direct_twin_r6_r7_byte_identical",
    "in_process_serialization_control_exact",
    "known_product_defects_remain_red",
    "permanent_real_mutations_all_rejected",
    "result_is_nonterminal",
    "single_process_is_not_family_promotion",
    "source_core_exact",
}
ACCEPTANCE_KEYS = {
    "schema_version", "audit", "status", "terminal", "artifact_status",
    "audit_replay_unit_accepted", "stage8_family_accepted",
    "comparison_end_to_end_perfect", "evidence_end_to_end_exact",
    "result", "input_bindings_sha256", "gate_code",
    "known_product_findings", "replay_contract", "invariants",
}
ACCEPTANCE_INVARIANT_KEYS = {
    "all_fallible_checks_completed_before_commit",
    "detached_result_identity_exact",
    "input_binding_digest_exact",
    "known_product_defects_preserved",
    "only_final_acceptance_name_is_authoritative_terminal_pass",
    "second_clean_process_replay_still_required",
    "single_replay_unit_accepted_without_family_promotion",
}
RESULT_REPLAY_KEYS = {
    "one_invocation_one_replay_unit",
    "in_process_rebuild_is_serialization_control_only",
    "second_clean_process_required",
    "second_output_root_must_be_distinct",
    "compare_result_and_acceptance_bytes",
    "family_promotion_after_two_identical_replays_only",
}
ACCEPTANCE_REPLAY_KEYS = {
    "one_invocation_one_replay_unit",
    "second_clean_process_required",
    "compare_result_and_acceptance_bytes",
}
SOURCE_TRUTH = {
    "raw_tsn_records": 69_804,
    "raw_tsn_data_records": 68_806,
    "raw_tsn_equate_records": 998,
    "raw_tsn_unknown_county_equates": 46,
    "raw_pointer_tokens": 565,
    "current_tsmis_excel_rows": 60_494,
    "current_tsmis_pdf_rows": 60_493,
}
MUTATION_RESULT_KEYS = {
    "real_output_alias_mutations",
    "exact_flat_root_changed_content_rejected",
    "exact_flat_root_extra_member_rejected",
    "strict_json_duplicate_key_rejected",
    "strict_json_extra_key_rejected",
    "detached_acceptance_result_binding_rejected",
    "detached_acceptance_semantic_mutations",
    "path_volatile_string_mutations",
    "direct_completion_semantic_mutations",
    "all_mutations_executed_without_skip",
}
OUTPUT_ALIAS_MUTATION_KEYS = {
    "same", "parent", "child", "hardlink", "hardlinked_member",
    "directory_symlink", "file_symlink", "broken_symlink",
}


def _known_findings_public() -> list[dict[str, str]]:
    return [
        {"finding": finding, "product_status": "red", "summary": summary}
        for finding, summary in PRODUCT_RED_FINDINGS
    ]


def _gate_code_public(context: RunContext) -> dict[str, object]:
    captured = context.files["final_family_gate_code"]
    return {
        "logical_path": "build/phase8_highway_sequence_final_family_gate.py",
        "bytes": captured.identity.bytes,
        "sha256": captured.identity.sha256,
    }


def _binding_ledger(context: RunContext) -> dict[str, object]:
    static_roots = [context.roots[role].public() for role in sorted(context.roots)]
    direct_roots = [context.direct_roots[role].public() for role in sorted(context.direct_roots)]
    static_files = [
        {
            "role": role,
            "logical_name": context.files[role].name,
            "bytes": context.files[role].identity.bytes,
            "sha256": context.files[role].identity.sha256,
        }
        for role in sorted(context.files)
    ]
    return {
        "static_roots": static_roots,
        "static_files": static_files,
        "direct_leg_roots": direct_roots,
        "semantic_witnesses": context.public_summary,
    }


def _assert_no_absolute_paths(value: object, label: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _assert_no_absolute_paths(nested, f"{label}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_absolute_paths(nested, f"{label}[{index}]")
    elif isinstance(value, str):
        posix = PurePosixPath(value)
        windows = PureWindowsPath(value)
        _require(
            not posix.is_absolute()
            and not windows.is_absolute()
            and not windows.drive
            and not windows.root,
            f"{label} contains a path-volatile absolute/rooted/drive-relative path",
        )


def _validate_public_root(value: object, label: str) -> None:
    root = _require_keys(
        value,
        {"role", "artifact_names", "files", "bytes", "canonical_members_sha256", "members"},
        label,
    )
    members = root.get("members")
    _require(isinstance(members, list), f"{label} members absent")
    checked_members: list[dict[str, object]] = []
    for index, member_value in enumerate(members):
        member = _require_keys(member_value, {"name", "bytes", "sha256"}, f"{label} member {index}")
        name = member.get("name")
        _require(isinstance(name, str) and Path(name).name == name, f"{label} unsafe member name")
        _require(type(member.get("bytes")) is int and int(member["bytes"]) >= 0, f"{label} invalid member bytes")
        digest = member.get("sha256")
        _require(isinstance(digest, str) and len(digest) == 64, f"{label} invalid member digest")
        checked_members.append(dict(member))
    names = [str(member["name"]) for member in checked_members]
    _require(names == sorted(names) and len(names) == len(set(names)), f"{label} member order/universe drift")
    _require(root.get("artifact_names") == names, f"{label} artifact-name ledger drift")
    _require(root.get("files") == len(checked_members), f"{label} file total drift")
    _require(root.get("bytes") == sum(int(member["bytes"]) for member in checked_members), f"{label} byte total drift")
    _require(root.get("canonical_members_sha256") == _sha_bytes(_canonical_bytes(checked_members)), f"{label} member digest drift")


def _validate_binding_ledger(value: object) -> None:
    ledger = _require_keys(
        value,
        {"static_roots", "static_files", "direct_leg_roots", "semantic_witnesses"},
        "input binding ledger",
    )
    for group in ("static_roots", "direct_leg_roots"):
        roots = ledger.get(group)
        _require(isinstance(roots, list) and roots, f"input binding {group} absent")
        roles: list[str] = []
        for index, root in enumerate(roots):
            _validate_public_root(root, f"input binding {group}[{index}]")
            _require(isinstance(root, Mapping) and isinstance(root.get("role"), str), f"input binding {group} role absent")
            roles.append(str(root["role"]))
        _require(roles == sorted(roles) and len(roles) == len(set(roles)), f"input binding {group} role order drift")
    files = ledger.get("static_files")
    _require(isinstance(files, list) and files, "input binding static files absent")
    file_roles: list[str] = []
    for index, file_value in enumerate(files):
        item = _require_keys(file_value, {"role", "logical_name", "bytes", "sha256"}, f"input binding static file {index}")
        _require(isinstance(item.get("role"), str), "input binding static-file role absent")
        _require(isinstance(item.get("logical_name"), str) and Path(str(item["logical_name"])).name == item["logical_name"], "input binding static-file name drift")
        _require(type(item.get("bytes")) is int and int(item["bytes"]) >= 0, "input binding static-file bytes invalid")
        _require(isinstance(item.get("sha256"), str) and len(str(item["sha256"])) == 64, "input binding static-file digest invalid")
        file_roles.append(str(item["role"]))
    _require(file_roles == sorted(file_roles) and len(file_roles) == len(set(file_roles)), "input binding static-file role order drift")
    _require(isinstance(ledger.get("semantic_witnesses"), Mapping), "semantic witness ledger absent")


def _validate_mutation_result(value: object) -> None:
    result = _require_keys(value, MUTATION_RESULT_KEYS, "permanent mutation result")
    for key in MUTATION_RESULT_KEYS - {
        "real_output_alias_mutations",
        "direct_completion_semantic_mutations",
        "detached_acceptance_semantic_mutations",
        "path_volatile_string_mutations",
    }:
        _require(result[key] is True, f"permanent mutation did not pass: {key}")
    _all_exact_true(result.get("real_output_alias_mutations"), OUTPUT_ALIAS_MUTATION_KEYS, "real output-alias mutations")
    _all_exact_true(
        result.get("path_volatile_string_mutations"),
        {"posix_absolute", "windows_absolute", "windows_root_relative", "windows_drive_relative"},
        "path-volatile string mutations",
    )
    direct = result.get("direct_completion_semantic_mutations")
    _require(isinstance(direct, Mapping) and set(direct) == {"excel_vs_raw_tsn", "pdf_vs_raw_tsn"}, "direct completion mutation leg universe drift")
    base_labels = {
        "completion_extra_key", "completion_audit", "preterminal_audit",
        "terminal_status", "terminal_flag",
        "acceptance_eligible", "stage8_family_accepted", "wrong_leg",
        "preterminal_result_identity", "complete_manifest_total",
        "final_name_universe", "completion_invariant", "terminal_precondition",
        "preterminal_extra_key",
    } | set(DIRECT_PRODUCT_OUTPUT_MUTATION_LABELS.values())
    for leg, value_by_leg in direct.items():
        checked = _require_keys(
            value_by_leg,
            {
                "unchanged_positive_control_before_and_after",
                "semantic_mutations_rejected",
                "audit_code_roles_mutated_and_rejected",
                "all_four_audit_code_roles_mutated",
                "real_mutated_json_files",
                "real_positive_control_json_files",
            },
            f"direct completion mutations {leg}",
        )
        _require(checked["unchanged_positive_control_before_and_after"] is True, f"{leg} positive mutation control failed")
        _require(checked["all_four_audit_code_roles_mutated"] is True, f"{leg} did not mutate four audit-code roles")
        roles = checked["audit_code_roles_mutated_and_rejected"]
        labels = checked["semantic_mutations_rejected"]
        _require(isinstance(roles, list) and roles == sorted(roles) and len(roles) == 4 and len(set(roles)) == 4, f"{leg} audit-code mutation role ledger drift")
        expected_labels = base_labels | {f"audit_code_role_{role}" for role in roles}
        _require(isinstance(labels, list) and set(labels) == expected_labels and len(labels) == len(expected_labels), f"{leg} semantic mutation census drift")
        _require(checked["real_mutated_json_files"] == 2 * len(expected_labels), f"{leg} real mutated-JSON file census drift")
        _require(checked["real_positive_control_json_files"] == 4, f"{leg} real positive-control file census drift")
    acceptance = _require_keys(
        result.get("detached_acceptance_semantic_mutations"),
        {
            "unchanged_positive_control_before_and_after",
            "hostile_semantic_mutations_rejected",
            "real_mutated_json_files",
            "real_positive_control_json_files",
            "no_authoritative_or_pending_residue",
        },
        "detached acceptance semantic mutations",
    )
    acceptance_labels = {
        "extra_top_level", "audit", "status", "terminal", "artifact_status",
        "replay_unit_acceptance", "family_acceptance", "comparison_perfection",
        "evidence_exactness", "result_binding", "input_binding_digest",
        "gate_code_binding", "product_finding_ledger", "replay_contract_extra_key",
        "invariant_false",
    }
    _require(acceptance["unchanged_positive_control_before_and_after"] is True, "acceptance positive mutation control failed")
    _require(acceptance["no_authoritative_or_pending_residue"] is True, "acceptance semantic mutations left authoritative/pending residue")
    observed_labels = acceptance["hostile_semantic_mutations_rejected"]
    _require(isinstance(observed_labels, list) and set(observed_labels) == acceptance_labels and len(observed_labels) == len(acceptance_labels), "acceptance semantic mutation census drift")
    _require(acceptance["real_mutated_json_files"] == len(acceptance_labels), "acceptance real mutated-file census drift")
    _require(acceptance["real_positive_control_json_files"] == 2, "acceptance real positive-control census drift")


def _validate_result_document(document: object) -> Mapping[str, object]:
    result = _require_keys(document, RESULT_KEYS, "final-family nonterminal result")
    _require(type(result.get("schema_version")) is int and result.get("schema_version") == 1, "final-family result schema drift")
    _require(result.get("audit") == RESULT_AUDIT, "final-family result audit identity drift")
    _require(result.get("status") == "PRETERMINAL_REPLAY_UNIT_PENDING_DETACHED_ACCEPTANCE", "final-family result status drift")
    _require(result.get("terminal") is False, "final-family result falsely claims terminal")
    _require(result.get("acceptance_eligible") is False, "final-family result claims acceptance")
    _require(result.get("stage8_family_accepted") is False, "single result claims Stage-8 acceptance")
    _require(result.get("artifact_status") == "AUDIT_REPLAY_UNIT_WITH_DOCUMENTED_PRODUCT_DEFECTS_NOT_FAMILY_PROMOTION", "final-family result artifact status drift")
    _require(result.get("bound_audit_inputs_complete_for_this_replay") is True, "bound audit-input replay is incomplete")
    _require(result.get("comparison_end_to_end_perfect") is False, "known-bad product marked perfect")
    _require(result.get("evidence_end_to_end_exact") is False, "known-bad evidence marked exact")
    _all_exact_true(result.get("invariants"), RESULT_INVARIANT_KEYS, "final-family result invariants")
    expected_findings = _known_findings_public()
    _require(result.get("known_product_findings") == expected_findings, "known product finding ledger drift")
    ledger = result.get("input_binding_ledger")
    _require(isinstance(ledger, Mapping), "input binding ledger absent")
    _validate_binding_ledger(ledger)
    _require(result.get("input_bindings_sha256") == _sha_bytes(_canonical_bytes(ledger)), "input binding digest drift")
    gate_code = _require_keys(result.get("gate_code"), {"logical_path", "bytes", "sha256"}, "final-family gate code")
    _require(gate_code.get("logical_path") == "build/phase8_highway_sequence_final_family_gate.py", "final-family gate logical path drift")
    _require(type(gate_code.get("bytes")) is int and int(gate_code["bytes"]) > 0, "final-family gate byte count invalid")
    _require(isinstance(gate_code.get("sha256"), str) and len(str(gate_code["sha256"])) == 64, "final-family gate digest invalid")
    _require(result.get("source_truth") == SOURCE_TRUTH, "source-truth ledger drift")
    replay = _require_keys(result.get("replay_contract"), RESULT_REPLAY_KEYS, "result replay contract")
    _require(all(replay[key] is True for key in RESULT_REPLAY_KEYS), "result replay contract is not all true")
    _validate_mutation_result(result.get("permanent_mutations"))
    _assert_no_absolute_paths(result, "final-family result")
    return result


def _validate_acceptance_document(
    document: object,
    result_identity: Identity,
    input_digest: str,
    gate_code: Mapping[str, object],
) -> Mapping[str, object]:
    acceptance = _require_keys(document, ACCEPTANCE_KEYS, "detached replay-unit acceptance")
    _require(type(acceptance.get("schema_version")) is int and acceptance.get("schema_version") == 1, "acceptance schema drift")
    _require(acceptance.get("audit") == ACCEPTANCE_AUDIT, "acceptance audit identity drift")
    _require(acceptance.get("status") == "PASS_AUDIT_REPLAY_UNIT_WITH_DOCUMENTED_PRODUCT_DEFECTS_NOT_FAMILY_PROMOTION", "acceptance status drift")
    _require(acceptance.get("terminal") is True, "acceptance is not terminal")
    _require(acceptance.get("artifact_status") == "DETACHED_AUDIT_REPLAY_UNIT_ACCEPTANCE_NOT_FAMILY_PROMOTION", "acceptance artifact status drift")
    _require(acceptance.get("audit_replay_unit_accepted") is True, "replay unit is not accepted")
    _require(acceptance.get("stage8_family_accepted") is False, "single replay falsely promotes Stage 8")
    _require(acceptance.get("comparison_end_to_end_perfect") is False, "acceptance hides product defects")
    _require(acceptance.get("evidence_end_to_end_exact") is False, "acceptance hides evidence defects")
    result_claim = _require_keys(acceptance.get("result"), {"name", "bytes", "sha256"}, "acceptance result binding")
    _require(result_claim.get("name") == RESULT_NAME, "acceptance result name drift")
    _require(result_claim.get("bytes") == result_identity.bytes and result_claim.get("sha256") == result_identity.sha256, "acceptance result identity drift")
    _require(acceptance.get("input_bindings_sha256") == input_digest, "acceptance input digest drift")
    _require(acceptance.get("gate_code") == gate_code, "acceptance gate-code binding drift")
    _require(acceptance.get("known_product_findings") == [item[0] for item in PRODUCT_RED_FINDINGS], "acceptance product finding IDs drift")
    _all_exact_true(acceptance.get("invariants"), ACCEPTANCE_INVARIANT_KEYS, "acceptance invariants")
    replay = _require_keys(acceptance.get("replay_contract"), ACCEPTANCE_REPLAY_KEYS, "acceptance replay contract")
    _require(all(replay[key] is True for key in ACCEPTANCE_REPLAY_KEYS), "acceptance replay contract is not all true")
    _assert_no_absolute_paths(acceptance, "detached acceptance")
    return acceptance


def _build_result(context: RunContext, mutations: Mapping[str, object]) -> dict[str, object]:
    ledger = _binding_ledger(context)
    return {
        "schema_version": 1,
        "audit": RESULT_AUDIT,
        "status": "PRETERMINAL_REPLAY_UNIT_PENDING_DETACHED_ACCEPTANCE",
        "terminal": False,
        "artifact_status": "AUDIT_REPLAY_UNIT_WITH_DOCUMENTED_PRODUCT_DEFECTS_NOT_FAMILY_PROMOTION",
        "acceptance_eligible": False,
        "stage8_family_accepted": False,
        "bound_audit_inputs_complete_for_this_replay": True,
        "comparison_end_to_end_perfect": False,
        "evidence_end_to_end_exact": False,
        "input_binding_ledger": ledger,
        "input_bindings_sha256": _sha_bytes(_canonical_bytes(ledger)),
        "gate_code": _gate_code_public(context),
        "source_truth": dict(SOURCE_TRUTH),
        "known_product_findings": _known_findings_public(),
        "permanent_mutations": dict(mutations),
        "replay_contract": {
            "one_invocation_one_replay_unit": True,
            "in_process_rebuild_is_serialization_control_only": True,
            "second_clean_process_required": True,
            "second_output_root_must_be_distinct": True,
            "compare_result_and_acceptance_bytes": True,
            "family_promotion_after_two_identical_replays_only": True,
        },
        "invariants": {key: True for key in sorted(RESULT_INVARIANT_KEYS)},
    }


def _build_acceptance(result_identity: Identity, result: Mapping[str, object]) -> dict[str, object]:
    gate_code = result["gate_code"]
    _require(isinstance(gate_code, Mapping), "result gate code absent")
    return {
        "schema_version": 1,
        "audit": ACCEPTANCE_AUDIT,
        "status": "PASS_AUDIT_REPLAY_UNIT_WITH_DOCUMENTED_PRODUCT_DEFECTS_NOT_FAMILY_PROMOTION",
        "terminal": True,
        "artifact_status": "DETACHED_AUDIT_REPLAY_UNIT_ACCEPTANCE_NOT_FAMILY_PROMOTION",
        "audit_replay_unit_accepted": True,
        "stage8_family_accepted": False,
        "comparison_end_to_end_perfect": False,
        "evidence_end_to_end_exact": False,
        "result": result_identity.public(RESULT_NAME),
        "input_bindings_sha256": result["input_bindings_sha256"],
        "gate_code": dict(gate_code),
        "known_product_findings": [item[0] for item in PRODUCT_RED_FINDINGS],
        "replay_contract": {
            "one_invocation_one_replay_unit": True,
            "second_clean_process_required": True,
            "compare_result_and_acceptance_bytes": True,
        },
        "invariants": {key: True for key in sorted(ACCEPTANCE_INVARIANT_KEYS)},
    }


def _expect_rejected(action: Callable[[], object], label: str) -> bool:
    try:
        action()
    except GateError:
        return True
    raise GateError(f"permanent mutation escaped rejection: {label}")


def _assert_output_member_independent(member: CapturedFile, protected_paths: Iterable[Path]) -> None:
    _require(member.token[6] == 1, f"new output member has unexpected link count: {member.name}")
    for protected in protected_paths:
        if not os.path.exists(protected):
            continue
        try:
            aliased = os.path.samefile(member.lexical_path, protected)
        except OSError as exc:
            raise GateError("cannot prove output-member physical independence") from exc
        _require(not aliased, f"new output member aliases a protected object: {member.name}")


def _direct_document_mutations(
    context: RunContext,
    bindings: Mapping[str, DirectLegBinding],
    mutation_root: Path,
) -> dict[str, object]:
    mutation_root.mkdir()
    per_leg: dict[str, object] = {}
    for leg in sorted(bindings):
        leg_mutation_root = mutation_root / leg
        leg_mutation_root.mkdir()
        root = context.direct_roots[leg]
        binding = bindings[leg]
        baseline_completion = dict(_parse_member(root, "completion.json", canonical=True))
        baseline_preterminal = dict(_parse_member(root, "result.json", canonical=True))

        def persisted_pair(
            label: str,
            completion: Mapping[str, object],
            preterminal: Mapping[str, object],
        ) -> tuple[Mapping[str, object], Mapping[str, object]]:
            completion_path = leg_mutation_root / f"{label}.completion.json"
            preterminal_path = leg_mutation_root / f"{label}.preterminal.json"
            completion_path.write_bytes(_canonical_bytes(completion))
            preterminal_path.write_bytes(_canonical_bytes(preterminal))
            captured_completion = _stream_identity(completion_path, f"{leg} {label} completion copy")
            captured_preterminal = _stream_identity(preterminal_path, f"{leg} {label} preterminal copy")
            return (
                _parse_file(captured_completion, f"{leg} {label} completion copy", canonical=True),
                _parse_file(captured_preterminal, f"{leg} {label} preterminal copy", canonical=True),
            )

        positive_before = persisted_pair("positive-before", baseline_completion, baseline_preterminal)
        _validate_direct_leg_documents(root, binding, positive_before[0], positive_before[1])

        rejected: list[str] = []

        def reject(label: str, mutate: Callable[[dict[str, object], dict[str, object]], None]) -> None:
            completion = copy.deepcopy(baseline_completion)
            preterminal = copy.deepcopy(baseline_preterminal)
            mutate(completion, preterminal)
            completion_roundtrip, preterminal_roundtrip = persisted_pair(label, completion, preterminal)
            _expect_rejected(
                lambda: _validate_direct_leg_documents(
                    root,
                    binding,
                    completion_roundtrip,  # type: ignore[arg-type]
                    preterminal_roundtrip,  # type: ignore[arg-type]
                ),
                f"{leg}/{label}",
            )
            rejected.append(label)

        reject("completion_extra_key", lambda completion, _pre: completion.__setitem__("hostile_family_acceptance", True))
        reject("completion_audit", lambda completion, _pre: completion.__setitem__("audit", "hostile audit"))
        reject("preterminal_audit", lambda _completion, preterminal: preterminal.__setitem__("audit", "hostile audit"))
        reject("terminal_status", lambda completion, _pre: completion.__setitem__("status", "PASS_HOSTILE_FAMILY_ACCEPTANCE"))
        reject("terminal_flag", lambda completion, _pre: completion.__setitem__("terminal", False))
        reject("acceptance_eligible", lambda completion, _pre: completion.__setitem__("acceptance_eligible", True))
        reject("stage8_family_accepted", lambda completion, _pre: completion.__setitem__("stage8_family_accepted", True))
        reject("wrong_leg", lambda completion, _pre: completion.__setitem__("leg", "hostile_leg"))

        def mutate_result_identity(completion: dict[str, object], _pre: dict[str, object]) -> None:
            claim = completion["preterminal_result"]
            _require(isinstance(claim, dict), "mutation fixture preterminal-result shape drift")
            claim["sha256"] = "0" * 64

        reject("preterminal_result_identity", mutate_result_identity)

        def mutate_manifest_total(completion: dict[str, object], _pre: dict[str, object]) -> None:
            manifest = completion["complete_output_artifact_manifest"]
            _require(isinstance(manifest, dict), "mutation fixture complete-manifest shape drift")
            manifest["bytes"] = int(manifest["bytes"]) + 1

        reject("complete_manifest_total", mutate_manifest_total)

        for product_name, mutation_label in DIRECT_PRODUCT_OUTPUT_MUTATION_LABELS.items():
            def mutate_product_artifact(
                completion: dict[str, object],
                _pre: dict[str, object],
                expected_name: str = product_name,
            ) -> None:
                manifest = completion["complete_output_artifact_manifest"]
                _require(isinstance(manifest, dict), "mutation fixture complete-manifest shape drift")
                members = manifest.get("members")
                _require(isinstance(members, list), "mutation fixture complete-manifest members absent")
                found = False
                for member in members:
                    _require(isinstance(member, dict), "mutation fixture complete-manifest member shape drift")
                    if member.get("relative_path") == expected_name:
                        member["sha256"] = "0" * 64
                        found = True
                _require(found, f"real product artifact absent from mutation fixture: {expected_name}")
                manifest["canonical_members_sha256"] = _sha_bytes(
                    _canonical_compact_bytes(members)
                )

            reject(mutation_label, mutate_product_artifact)

        def mutate_final_names(completion: dict[str, object], _pre: dict[str, object]) -> None:
            names = completion["expected_final_artifact_names"]
            _require(isinstance(names, list) and names, "mutation fixture final-name shape drift")
            names.pop()

        reject("final_name_universe", mutate_final_names)

        def mutate_completion_invariant(completion: dict[str, object], _pre: dict[str, object]) -> None:
            ledger = completion["invariants"]
            _require(isinstance(ledger, dict) and ledger, "mutation fixture completion-invariant shape drift")
            ledger[sorted(ledger)[0]] = False

        reject("completion_invariant", mutate_completion_invariant)

        def mutate_precondition(completion: dict[str, object], _pre: dict[str, object]) -> None:
            ledger = completion["terminal_preconditions"]
            _require(isinstance(ledger, dict) and ledger, "mutation fixture terminal-precondition shape drift")
            ledger[sorted(ledger)[0]] = False

        reject("terminal_precondition", mutate_precondition)
        reject("preterminal_extra_key", lambda _completion, preterminal: preterminal.__setitem__("hostile_claim", True))

        audit_roles_rejected: list[str] = []
        for audit_role in sorted(binding.audit_code):
            def mutate_audit_role(
                completion: dict[str, object],
                preterminal: dict[str, object],
                role: str = audit_role,
            ) -> None:
                for document in (completion, preterminal):
                    manifest = document[binding.audit_code_field]
                    _require(isinstance(manifest, dict), "mutation audit-code manifest shape drift")
                    members = manifest.get("members")
                    _require(isinstance(members, list), "mutation audit-code members absent")
                    found = False
                    for member in members:
                        _require(isinstance(member, dict), "mutation audit-code member shape drift")
                        if member.get("role") == role:
                            member["sha256"] = "0" * 64
                            found = True
                    _require(found, f"mutation audit-code role absent: {role}")
                    manifest["canonical_members_sha256"] = _sha_bytes(
                        _canonical_compact_bytes(members)
                    )

            reject(f"audit_code_role_{audit_role}", mutate_audit_role)
            audit_roles_rejected.append(audit_role)

        positive_after = persisted_pair("positive-after", baseline_completion, baseline_preterminal)
        _validate_direct_leg_documents(root, binding, positive_after[0], positive_after[1])
        per_leg[leg] = {
            "unchanged_positive_control_before_and_after": True,
            "semantic_mutations_rejected": rejected,
            "audit_code_roles_mutated_and_rejected": audit_roles_rejected,
            "all_four_audit_code_roles_mutated": len(audit_roles_rejected) == 4,
            "real_mutated_json_files": 2 * len(rejected),
            "real_positive_control_json_files": 4,
        }
    return per_leg


def _acceptance_semantic_mutations(mutation_root: Path) -> dict[str, object]:
    mutation_root.mkdir()
    result_identity = Identity(123, "1" * 64)
    input_digest = "2" * 64
    gate_code = {
        "logical_path": "build/phase8_highway_sequence_final_family_gate.py",
        "bytes": 456,
        "sha256": "3" * 64,
    }
    dummy_result = {
        "input_bindings_sha256": input_digest,
        "gate_code": gate_code,
    }
    baseline = _build_acceptance(result_identity, dummy_result)

    def persist(label: str, document: Mapping[str, object]) -> Mapping[str, object]:
        path = mutation_root / f"{label}.json"
        path.write_bytes(_canonical_bytes(document))
        captured = _stream_identity(path, f"acceptance semantic mutation {label}")
        return _parse_file(captured, f"acceptance semantic mutation {label}", canonical=True)

    positive_before = persist("positive-before", baseline)
    _validate_acceptance_document(
        positive_before, result_identity, input_digest, gate_code,
    )

    mutations: list[tuple[str, Callable[[dict[str, object]], None]]] = []
    mutations.append(("extra_top_level", lambda document: document.__setitem__("hostile_claim", True)))
    mutations.append(("audit", lambda document: document.__setitem__("audit", "hostile audit")))
    mutations.append(("status", lambda document: document.__setitem__("status", "PASS_HOSTILE_FAMILY_ACCEPTANCE")))
    mutations.append(("terminal", lambda document: document.__setitem__("terminal", False)))
    mutations.append(("artifact_status", lambda document: document.__setitem__("artifact_status", "HOSTILE")))
    mutations.append(("replay_unit_acceptance", lambda document: document.__setitem__("audit_replay_unit_accepted", False)))
    mutations.append(("family_acceptance", lambda document: document.__setitem__("stage8_family_accepted", True)))
    mutations.append(("comparison_perfection", lambda document: document.__setitem__("comparison_end_to_end_perfect", True)))
    mutations.append(("evidence_exactness", lambda document: document.__setitem__("evidence_end_to_end_exact", True)))

    def mutate_result_binding(document: dict[str, object]) -> None:
        claim = document["result"]
        _require(isinstance(claim, dict), "acceptance result mutation fixture shape drift")
        claim["sha256"] = "0" * 64

    mutations.append(("result_binding", mutate_result_binding))
    mutations.append(("input_binding_digest", lambda document: document.__setitem__("input_bindings_sha256", "0" * 64)))

    def mutate_gate_code(document: dict[str, object]) -> None:
        claim = document["gate_code"]
        _require(isinstance(claim, dict), "acceptance gate-code mutation fixture shape drift")
        claim["sha256"] = "0" * 64

    mutations.append(("gate_code_binding", mutate_gate_code))

    def mutate_findings(document: dict[str, object]) -> None:
        findings = document["known_product_findings"]
        _require(isinstance(findings, list) and findings, "acceptance finding mutation fixture shape drift")
        findings.pop()

    mutations.append(("product_finding_ledger", mutate_findings))

    def mutate_replay(document: dict[str, object]) -> None:
        replay = document["replay_contract"]
        _require(isinstance(replay, dict), "acceptance replay mutation fixture shape drift")
        replay["hostile"] = True

    mutations.append(("replay_contract_extra_key", mutate_replay))

    def mutate_invariant(document: dict[str, object]) -> None:
        invariants = document["invariants"]
        _require(isinstance(invariants, dict) and invariants, "acceptance invariant mutation fixture shape drift")
        invariants[sorted(invariants)[0]] = False

    mutations.append(("invariant_false", mutate_invariant))

    rejected: list[str] = []
    for label, mutate in mutations:
        document = copy.deepcopy(baseline)
        mutate(document)
        persisted = persist(label, document)
        _expect_rejected(
            lambda persisted=persisted: _validate_acceptance_document(
                persisted, result_identity, input_digest, gate_code,
            ),
            f"detached acceptance semantic mutation/{label}",
        )
        rejected.append(label)

    positive_after = persist("positive-after", baseline)
    _validate_acceptance_document(
        positive_after, result_identity, input_digest, gate_code,
    )
    residue_free = (
        not os.path.lexists(mutation_root / ACCEPTANCE_NAME)
        and all(
            not item.name.startswith(f".{ACCEPTANCE_NAME}.")
            for item in os.scandir(mutation_root)
        )
    )
    _require(residue_free, "hostile acceptance semantic mutations left authoritative/pending residue")
    return {
        "unchanged_positive_control_before_and_after": True,
        "hostile_semantic_mutations_rejected": rejected,
        "real_mutated_json_files": len(rejected),
        "real_positive_control_json_files": 2,
        "no_authoritative_or_pending_residue": True,
    }


def _path_volatility_mutations(mutation_root: Path) -> dict[str, bool]:
    mutation_root.mkdir()
    cases = {
        "posix_absolute": "/tmp/hostile",
        "windows_absolute": r"C:\hostile",
        "windows_root_relative": r"\hostile",
        "windows_drive_relative": r"C:hostile",
    }
    rejected: dict[str, bool] = {}
    for label, value in cases.items():
        path = mutation_root / f"{label}.json"
        path.write_bytes(_canonical_bytes({"claim": value}))
        captured = _stream_identity(path, f"path-volatility mutation {label}")
        document = _parse_file(captured, f"path-volatility mutation {label}", canonical=True)
        rejected[label] = _expect_rejected(
            lambda document=document: _assert_no_absolute_paths(
                document, f"path-volatility mutation {label}",
            ),
            f"path-volatility mutation/{label}",
        )
    return rejected


def _run_permanent_mutations(
    context: RunContext,
    bindings: Mapping[str, DirectLegBinding],
) -> dict[str, object]:
    _assert_plain_components(VISUAL_ROOT, "mutation private root")
    with tempfile.TemporaryDirectory(
        prefix="phase8-hsl-final-family-mutations-", dir=VISUAL_ROOT,
    ) as temporary_name:
        base = Path(temporary_name).absolute()
        protected_root = base / "protected-input"
        protected_root.mkdir()
        protected_file = protected_root / "bound.bin"
        protected_file.write_bytes(b"bound-input")
        protected = (protected_root, protected_file)
        valid = _validate_new_output_root(base / "valid-control", base, protected)
        _require(valid == base / "valid-control", "valid output-root control drift")

        output_rejections = {
            "same": _expect_rejected(
                lambda: _validate_new_output_root(protected_root, base, protected), "same output/input root",
            ),
            "parent": _expect_rejected(
                lambda: _validate_new_output_root(base, base, protected), "parent output root",
            ),
            "child": _expect_rejected(
                lambda: _validate_new_output_root(protected_root / "child", base, protected), "child output root",
            ),
        }

        hardlink = base / "hardlink-output"
        try:
            os.link(protected_file, hardlink)
        except OSError as exc:
            raise GateError("real hardlink mutation could not execute") from exc
        _require(os.path.samefile(hardlink, protected_file), "hardlink mutation was not physical")
        output_rejections["hardlink"] = _expect_rejected(
            lambda: _validate_new_output_root(hardlink, base, protected), "hardlink output alias",
        )
        captured_hardlink = _stream_identity(hardlink, "hardlinked output member mutation")
        output_rejections["hardlinked_member"] = _expect_rejected(
            lambda: _assert_output_member_independent(captured_hardlink, protected),
            "hardlinked final member",
        )

        symlink_targets = {
            "directory_symlink": (protected_root, True),
            "file_symlink": (protected_file, False),
            "broken_symlink": (base / "missing-target", False),
        }
        for role, (target, is_directory) in symlink_targets.items():
            candidate = base / role
            try:
                os.symlink(target, candidate, target_is_directory=is_directory)
            except (OSError, NotImplementedError) as exc:
                raise GateError(f"real {role} mutation could not execute") from exc
            _require(os.path.lexists(candidate), f"real {role} mutation was not created")
            output_rejections[role] = _expect_rejected(
                lambda candidate=candidate: _validate_new_output_root(candidate, base, protected), role,
            )

        changed_root = base / "changed-root"
        changed_root.mkdir()
        changed_member = changed_root / "member.json"
        changed_member.write_bytes(_canonical_bytes({"value": 1}))
        changed_expected = {"member.json": _stream_identity(changed_member, "changed-root baseline").identity}
        _capture_exact_root("changed-root-positive", changed_root, changed_expected)
        changed_member.write_bytes(_canonical_bytes({"value": 2}))
        changed_content_rejected = _expect_rejected(
            lambda: _capture_exact_root("changed-root-negative", changed_root, changed_expected),
            "changed exact-root member",
        )

        extra_root = base / "extra-root"
        extra_root.mkdir()
        extra_member = extra_root / "member.json"
        extra_member.write_bytes(_canonical_bytes({"value": 1}))
        extra_expected = {"member.json": _stream_identity(extra_member, "extra-root baseline").identity}
        _capture_exact_root("extra-root-positive", extra_root, extra_expected)
        (extra_root / "undeclared.json").write_bytes(_canonical_bytes({"hostile": True}))
        extra_member_rejected = _expect_rejected(
            lambda: _capture_exact_root("extra-root-negative", extra_root, extra_expected),
            "extra exact-root member",
        )

        duplicate_json_rejected = _expect_rejected(
            lambda: _strict_json(b'{"claim":1,"claim":2}\n', "duplicate-key mutation"),
            "duplicate JSON key",
        )
        extra_json_key_rejected = _expect_rejected(
            lambda: _require_keys({"claim": 1, "hostile": 2}, {"claim"}, "extra-key mutation"),
            "extra JSON key",
        )

        acceptance_semantic_mutations = _acceptance_semantic_mutations(
            base / "detached-acceptance-semantic-mutations",
        )
        path_volatility_mutations = _path_volatility_mutations(
            base / "path-volatility-mutations",
        )
        acceptance_binding_rejected = (
            "result_binding"
            in acceptance_semantic_mutations["hostile_semantic_mutations_rejected"]
        )

        direct_mutations = _direct_document_mutations(
            context,
            bindings,
            base / "direct-completion-json-mutations",
        )
        return {
            "real_output_alias_mutations": output_rejections,
            "exact_flat_root_changed_content_rejected": changed_content_rejected,
            "exact_flat_root_extra_member_rejected": extra_member_rejected,
            "strict_json_duplicate_key_rejected": duplicate_json_rejected,
            "strict_json_extra_key_rejected": extra_json_key_rejected,
            "detached_acceptance_result_binding_rejected": acceptance_binding_rejected,
            "detached_acceptance_semantic_mutations": acceptance_semantic_mutations,
            "path_volatile_string_mutations": path_volatility_mutations,
            "direct_completion_semantic_mutations": direct_mutations,
            "all_mutations_executed_without_skip": True,
        }


def _assert_created_output_root(
    root: Path,
    protected_paths: Iterable[Path],
    expected_names: Sequence[str],
    expected_root_token: tuple[object, ...],
) -> None:
    root = _lexical_absolute(root, "created output root")
    _require(root.parent == VISUAL_ROOT, "created output root left its private parent")
    _assert_plain_components(root, "created output root")
    try:
        facts = os.lstat(root)
    except OSError as exc:
        raise GateError("created output root disappeared") from exc
    _require(stat.S_ISDIR(facts.st_mode), "created output root is not an ordinary directory")
    _require(_physical_object_token(facts) == expected_root_token, "created output-root physical identity drift")
    names = sorted(item.name for item in os.scandir(root))
    _require(names == sorted(expected_names), "created output artifact universe drift")
    for protected in protected_paths:
        _require(not _paths_overlap(root, protected), "created output root overlaps a protected path")
        if os.path.exists(protected):
            try:
                aliased = os.path.samefile(root, protected)
            except OSError as exc:
                raise GateError("cannot prove created output-root physical independence") from exc
            _require(not aliased, "created output root physically aliases a protected path")


def _write_exclusive_file(path: Path, payload: bytes, label: str) -> None:
    _require(path.is_absolute(), f"{label} path is not absolute")
    _assert_plain_components(path.parent, f"{label} parent")
    _require(not os.path.lexists(path), f"{label} destination already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0))
    descriptor: int | None = None
    committed = False
    try:
        descriptor = os.open(path, flags, 0o600)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            _require(written > 0, f"{label} made no write progress")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        committed = True
    except (OSError, GateError) as exc:
        if isinstance(exc, GateError):
            raise
        raise GateError(f"{label} exclusive publication failed") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if not committed and os.path.lexists(path):
            try:
                path.unlink()
            except OSError:
                pass


def _create_output_root(
    candidate: Path,
    protected_paths: Iterable[Path],
) -> tuple[Path, tuple[object, ...]]:
    candidate = _validate_new_output_root(candidate, VISUAL_ROOT, protected_paths)
    try:
        os.mkdir(candidate, 0o700)
    except OSError as exc:
        raise GateError("exclusive output-root creation failed") from exc
    try:
        root_token = _physical_object_token(os.lstat(candidate))
    except OSError as exc:
        raise GateError("cannot capture new output-root physical identity") from exc
    _pin_windows_path(candidate, directory=True, deny_write=False)
    _assert_created_output_root(candidate, protected_paths, [], root_token)
    return candidate, root_token


def _publish_final_acceptance(
    path: Path,
    acceptance: Mapping[str, object],
    *,
    result_identity: Identity,
    result_token: tuple[object, ...],
    input_digest: str,
    gate_code: Mapping[str, object],
    expected_acceptance_identity: Identity,
    protected_paths: Iterable[Path],
    output_root_token: tuple[object, ...],
) -> int:
    """Stage, re-open, and exclusively rename terminal acceptance as final I/O.

    The same-directory pending name is never authoritative.  On the required
    Windows runtime the pinned directory/result handles prevent replacement;
    ``os.rename`` refuses an existing destination and is the successful
    process's final filesystem/stdout operation.
    """
    root = path.parent
    validated = _validate_acceptance_document(
        acceptance, result_identity, input_digest, gate_code,
    )
    raw = _canonical_bytes(validated)
    _require(Identity(len(raw), _sha_bytes(raw)) == expected_acceptance_identity, "final acceptance serialization drift")
    _require(b'"terminal":true' in raw and b'"status":"PASS_' in raw, "final acceptance payload is not terminal PASS")
    _require(not os.path.lexists(path), "final acceptance destination already exists")
    _assert_created_output_root(root, protected_paths, [RESULT_NAME], output_root_token)
    result = _stream_identity(root / RESULT_NAME, "publisher-bound nonterminal result")
    _require(result.identity == result_identity and result.token == result_token, "publisher result binding drift")
    _assert_output_member_independent(result, protected_paths)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".pending", dir=root,
    )
    temporary = Path(temporary_name)
    committed = False
    staged_handle: int | None = None
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        staged = _stream_identity(temporary, "staged detached acceptance")
        _require(staged.identity == expected_acceptance_identity, "staged acceptance identity drift")
        _assert_output_member_independent(staged, protected_paths)
        staged_document = _parse_file(staged, "staged detached acceptance", canonical=True)
        _validate_acceptance_document(
            staged_document, result_identity, input_digest, gate_code,
        )
        staged_handle = _pin_windows_path(
            temporary,
            directory=False,
            deny_write=True,
            rename_capable=True,
        )
        try:
            staged_pinned_token = _stat_token(os.lstat(temporary))
        except OSError as exc:
            raise GateError("staged acceptance changed while acquiring its rename handle") from exc
        _require(staged_pinned_token == staged.token, "staged acceptance token drift while pinning")
        _assert_created_output_root(
            root,
            protected_paths,
            [RESULT_NAME, temporary.name],
            output_root_token,
        )
        result_again = _stream_identity(root / RESULT_NAME, "precommit bound result")
        _require(result_again.identity == result_identity and result_again.token == result_token, "precommit result binding drift")
        _require(not os.path.lexists(path), "acceptance destination appeared before commit")
        _require(
            sorted(item.name for item in os.scandir(root))
            == sorted([RESULT_NAME, temporary.name]),
            "precommit output residue drift",
        )
        _validate_acceptance_document(
            staged_document, result_identity, input_digest, gate_code,
        )
        try:
            _require(_stat_token(os.lstat(temporary)) == staged.token, "pinned staged acceptance token drift")
        except OSError as exc:
            raise GateError("pinned staged acceptance disappeared before commit") from exc
        print(
            json.dumps(
                {
                    "status": "DETACHED_ACCEPTANCE_PREPARED_NOT_COMMITTED",
                    "terminal": False,
                    "result": result_identity.public(RESULT_NAME),
                    "acceptance": expected_acceptance_identity.public(ACCEPTANCE_NAME),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        _rename_pinned_windows_handle(staged_handle, path)
        committed = True
        return 0
    finally:
        if not committed:
            if staged_handle is not None:
                _close_windows_pin_on_failure(staged_handle)
            if os.path.lexists(temporary):
                try:
                    temporary.unlink()
                except OSError as exc:
                    raise GateError("failed publication left terminal pending residue") from exc


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel-direct-leg-root", type=Path, required=True)
    parser.add_argument("--pdf-direct-leg-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--allow-documented-product-findings",
        action="store_true",
        help="Acknowledge that this gate preserves the enumerated product defects as red.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _require(args.allow_documented_product_findings, "explicit documented-product-findings acknowledgement is required")

    # This must precede output validation, capture, mutation work, or directory
    # creation.  The scaffold therefore fails closed without leaving artifacts.
    bindings = _require_direct_leg_bindings_ready()
    direct_paths = {
        "excel_vs_raw_tsn": args.excel_direct_leg_root,
        "pdf_vs_raw_tsn": args.pdf_direct_leg_root,
    }
    context = _capture_context(direct_paths, bindings)
    protected = _protected_paths(context)
    output_candidate = _validate_new_output_root(args.output_root, VISUAL_ROOT, protected)

    mutations = _run_permanent_mutations(context, bindings)
    _require(mutations.get("all_mutations_executed_without_skip") is True, "permanent mutation suite incomplete")

    first_result = _build_result(context, mutations)
    _validate_result_document(first_result)
    first_result_bytes = _canonical_bytes(first_result)
    second_result = _build_result(context, mutations)
    _validate_result_document(second_result)
    second_result_bytes = _canonical_bytes(second_result)
    _require(first_result_bytes == second_result_bytes, "in-process result serialization control drift")
    _require(b'"terminal":true' not in first_result_bytes and b'"status":"PASS_' not in first_result_bytes, "nonterminal result contains terminal PASS")

    # Recheck the candidate after disposable mutations, then create it once.
    output_candidate = _validate_new_output_root(output_candidate, VISUAL_ROOT, protected)
    output_root, output_root_token = _create_output_root(output_candidate, protected)
    result_path = output_root / RESULT_NAME
    _write_exclusive_file(result_path, first_result_bytes, "nonterminal result")
    result_capture = _stream_identity(result_path, "published nonterminal result")
    _require(result_capture.identity == Identity(len(first_result_bytes), _sha_bytes(first_result_bytes)), "published result identity drift")
    _assert_output_member_independent(result_capture, protected)
    _pin_windows_path(result_path, directory=False, deny_write=True)
    pinned_result = _stream_identity(result_path, "pinned nonterminal result")
    _require(pinned_result.token == result_capture.token, "result identity changed while its no-write handle was acquired")
    result_capture = pinned_result
    _assert_created_output_root(output_root, protected, [RESULT_NAME], output_root_token)

    # Full exact-byte and semantic revalidation is deliberately after result
    # publication and before detached acceptance construction.
    _recapture_context(context, bindings)
    result_capture = _stream_identity(result_path, "final nonterminal result revalidation")
    _require(result_capture.identity == Identity(len(first_result_bytes), _sha_bytes(first_result_bytes)), "final result revalidation drift")
    _require(result_capture.token == pinned_result.token, "pinned result physical token drift")
    _assert_output_member_independent(result_capture, protected)
    _assert_created_output_root(output_root, protected, [RESULT_NAME], output_root_token)

    acceptance = _build_acceptance(result_capture.identity, first_result)
    _validate_acceptance_document(
        acceptance,
        result_capture.identity,
        str(first_result["input_bindings_sha256"]),
        first_result["gate_code"],  # type: ignore[arg-type]
    )
    acceptance_bytes = _canonical_bytes(acceptance)
    second_acceptance_bytes = _canonical_bytes(_build_acceptance(result_capture.identity, first_result))
    _require(acceptance_bytes == second_acceptance_bytes, "in-process acceptance serialization control drift")
    _require(not os.path.lexists(output_root / ACCEPTANCE_NAME), "detached acceptance destination appeared")
    _require(
        all(not item.name.startswith(f".{ACCEPTANCE_NAME}.") for item in os.scandir(output_root)),
        "detached acceptance staging residue exists",
    )
    _assert_created_output_root(output_root, protected, [RESULT_NAME], output_root_token)
    return _publish_final_acceptance(
        output_root / ACCEPTANCE_NAME,
        acceptance,
        result_identity=result_capture.identity,
        result_token=result_capture.token,
        input_digest=str(first_result["input_bindings_sha256"]),
        gate_code=first_result["gate_code"],  # type: ignore[arg-type]
        expected_acceptance_identity=Identity(
            len(acceptance_bytes), _sha_bytes(acceptance_bytes),
        ),
        protected_paths=protected,
        output_root_token=output_root_token,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BindingUnavailable:
        print("BLOCKED_DIRECT_LEG_BINDINGS_UNAVAILABLE")
        raise SystemExit(2)
    except GateError as exc:
        print(f"FAIL Highway Sequence final-family audit gate: {exc}")
        raise SystemExit(1)
