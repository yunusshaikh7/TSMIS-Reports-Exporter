#!/usr/bin/env python3
"""Freeze the exact Highway Sequence source editions used by the Stage-8 audit.

This module performs byte capture only.  It deliberately imports no application
parser, consolidator, comparator, evidence adapter, or report schema.  Parsing is
kept in a separate process so a parser failure cannot leave the audit silently
pointing back at mutable development folders.

The current TSMIS Excel and PDF trees are one July-9 SSOR-production run.  The
older July-8 Excel / July-9 PDF pair is retained under separate labels solely to
reproduce and retire the historical cross-bundle canary.  The 12 TSN PDFs are
authoritative source; the adjacent instruction text file is a non-source role.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Iterable


SOURCE_ROOT = Path(r"C:\Users\Yunus\Downloads\TSMIS")
CURRENT_RUN = (
    SOURCE_ROOT / "ground-truth" / "All Reports 7.9"
    / "2026-07-09 ssor-prod"
)
HISTORICAL_EXCEL_RUN = (
    SOURCE_ROOT / "ground-truth" / "HSL Bundle 7.8" / "TSMIS"
)
HISTORICAL_PDF_RUN = (
    SOURCE_ROOT / "ground-truth" / "HSL PDF + IS Bundle 7.9" / "TSMIS"
)
TSN_RAW_ROOT = SOURCE_ROOT / "tsn_library" / "highway_sequence" / "raw"

PRIVATE_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
    r"\phase8_highway_sequence_private_sources_r1"
)

ROUTE_MEMBER_RE = re.compile(
    r"^highway_sequence_route_(\d{3}[A-Za-z]?)\.(xlsx|pdf)$"
)

TREE_SOURCES = {
    "current_tsmis_excel": {
        "root": CURRENT_RUN / "highway_sequence",
        "suffix": ".xlsx",
        "files": 252,
        "bytes": 24_634_973,
        "manifest_sha256": (
            "31a13ebc388951fdcadbba69d9188218af4548dd56d68c91e09f96bcb41765c8"
        ),
    },
    "current_tsmis_pdf": {
        "root": CURRENT_RUN / "highway_sequence_pdf",
        "suffix": ".pdf",
        "files": 252,
        "bytes": 39_236_260,
        "manifest_sha256": (
            "072e538e5ebcbf015ec719565f003fb72027973a11d63c42f123802d8856dfa7"
        ),
    },
    "historical_tsmis_excel_7_8": {
        "root": HISTORICAL_EXCEL_RUN / "highway_sequence",
        "suffix": ".xlsx",
        "files": 252,
        "bytes": 24_634_499,
        "manifest_sha256": (
            "4bb040280bab17fd14283aa20178d189b4e499291eea1345adba0e0bb7f72c4f"
        ),
    },
    "historical_tsmis_pdf_7_9": {
        "root": HISTORICAL_PDF_RUN / "highway_sequence_pdf",
        "suffix": ".pdf",
        "files": 252,
        "bytes": 39_236_260,
        "manifest_sha256": (
            "072e538e5ebcbf015ec719565f003fb72027973a11d63c42f123802d8856dfa7"
        ),
    },
}

TSN_BINDINGS = (
    ("D01 HSL TSN.pdf", 204_709, "3a4cb30340a55edae2f72d758dcda62d30e21d919ecc862ec6955d6795252a4a"),
    ("D02 HSL TSN.pdf", 288_696, "f32078eb79f38fa2e4799319bd10f661ecdff669dd7c4ade18a5326723ad5d85"),
    ("D03 HSL TSN.pdf", 373_387, "8c5cd4638dd4901797f9c15e6fac7f998d5bc989749f874e6eedf52f72506fb0"),
    ("D04 HSL TSN.pdf", 625_052, "5facc297fd7d28e8ad760cce8d7f4699b1ee4bc7582f2a007196c0bf739bcd5a"),
    ("D05 HSL TSN.pdf", 265_876, "b8246f8c28e31d0c4acc352b7148988b6a6a0d7abaf56e810943e14816389e7b"),
    ("D06 HSL TSN.pdf", 327_246, "e240f038390109ca02ceb012a5e8e5b82fc8845c49be718506acb56667db3dad"),
    ("D07 HSL TSN.pdf", 555_648, "c791b99789e496efb83b52850aa54e142946aaa541a91b780489fe7e0bc7ec25"),
    ("D08 HSL TSN.pdf", 370_505, "f23b8e3d5a90200cc1a6285ebb40480b828673f9e5a37b06f36fe30bc9697565"),
    ("D09 HSL TSN.pdf", 103_868, "c6984a7e947ff600a450e4387f318aeed4826b05249361a694fbe507d0c7c5c3"),
    ("D10 HSL TSN.pdf", 298_313, "e510a575c56c5af4404968d9fe51271f79cc23377df1e5c651b45b563dbf2ed6"),
    ("D11 HSL TSN.pdf", 315_238, "920e3e352c1f24be415271c9819fc8bddce8ac6ef3095684e9fe06c87cf7378b"),
    ("D12 HSL TSN.pdf", 138_411, "5583c0a0b94feeddaefda8bfa35bf34657cfb9f3b8e0a8d2b047c8fc27cbcc7a"),
)
TSN_NON_SOURCE_NAMES = ("_PUT TSN FILES HERE.txt",)


class CaptureError(RuntimeError):
    """The source corpus changed or the private snapshot is incomplete."""


@dataclass(frozen=True)
class FileEntry:
    name: str
    bytes: int
    sha256: str


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.stat(follow_symlinks=False).st_mode)
    except (FileNotFoundError, OSError):
        return False


def _manifest(paths: Iterable[Path]) -> tuple[dict[str, object], list[FileEntry]]:
    ordered = sorted(paths, key=lambda path: path.name)
    entries = [FileEntry(path.name, path.stat().st_size, _sha_file(path)) for path in ordered]
    wire = "".join(
        f"{entry.name}\t{entry.bytes}\t{entry.sha256}\n" for entry in entries
    ).encode("utf-8")
    return ({
        "files": len(entries),
        "bytes": sum(entry.bytes for entry in entries),
        "manifest_sha256": _sha_bytes(wire),
        "serialization": "name\\tbytes\\tsha256\\n sorted by name",
    }, entries)


def _tree_members(label: str, spec: dict[str, object]) -> tuple[dict[str, object], list[FileEntry]]:
    root = Path(spec["root"])
    if not root.is_dir():
        raise CaptureError(f"{label}: source root is absent: {root}")
    children = sorted(root.iterdir(), key=lambda path: path.name)
    nonfiles = [path.name for path in children if not _regular_file(path)]
    if nonfiles:
        raise CaptureError(f"{label}: source root has non-file roles: {nonfiles}")
    suffix = str(spec["suffix"])
    unexpected = [path.name for path in children if path.suffix.lower() != suffix]
    if unexpected:
        raise CaptureError(f"{label}: unexpected source roles: {unexpected}")
    routes: dict[str, str] = {}
    for path in children:
        match = ROUTE_MEMBER_RE.fullmatch(path.name)
        if match is None or f".{match.group(2)}" != suffix:
            raise CaptureError(f"{label}: unexpected member name: {path.name}")
        route = match.group(1).upper()
        if route in routes:
            raise CaptureError(f"{label}: duplicate route {route}: {routes[route]}, {path.name}")
        routes[route] = path.name
    observed, entries = _manifest(children)
    for key in ("files", "bytes", "manifest_sha256"):
        if observed[key] != spec[key]:
            raise CaptureError(
                f"{label}: {key} drift: {observed[key]!r} != {spec[key]!r}"
            )
    return observed, entries


def _copy_bound_tree(label: str, spec: dict[str, object], destination: Path) -> dict[str, object]:
    root = Path(spec["root"])
    observed, entries = _tree_members(label, spec)
    destination.mkdir(parents=True, exist_ok=False)
    for entry in entries:
        source = root / entry.name
        payload = source.read_bytes()
        if len(payload) != entry.bytes or _sha_bytes(payload) != entry.sha256:
            raise CaptureError(f"{label}: source changed during capture: {entry.name}")
        (destination / entry.name).write_bytes(payload)
    captured, captured_entries = _manifest(destination.iterdir())
    after, _ = _tree_members(label, spec)
    if captured != observed or after != observed:
        raise CaptureError(f"{label}: source or private tree changed across capture")
    return {
        "source_root": str(root.resolve()),
        "private_root": str(destination.resolve()),
        "binding": {key: spec[key] for key in ("suffix", "files", "bytes", "manifest_sha256")},
        "observed": observed,
        "members": [asdict(entry) for entry in captured_entries],
        "routes": sorted(ROUTE_MEMBER_RE.fullmatch(entry.name).group(1).upper()
                         for entry in captured_entries),
    }


def _copy_tsn(destination: Path) -> dict[str, object]:
    expected = {name: (size, digest) for name, size, digest in TSN_BINDINGS}
    actual_names = sorted(path.name for path in TSN_RAW_ROOT.iterdir())
    expected_names = sorted((*expected, *TSN_NON_SOURCE_NAMES))
    if actual_names != expected_names:
        raise CaptureError(
            f"TSN role universe changed: expected {expected_names}, got {actual_names}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    source_entries: list[FileEntry] = []
    for name, size, digest in TSN_BINDINGS:
        source = TSN_RAW_ROOT / name
        if not _regular_file(source):
            raise CaptureError(f"TSN source is not a regular file: {name}")
        payload = source.read_bytes()
        if len(payload) != size or _sha_bytes(payload) != digest:
            raise CaptureError(f"TSN source identity drift: {name}")
        (destination / name).write_bytes(payload)
        source_entries.append(FileEntry(name, size, digest))
    captured, captured_entries = _manifest(destination.iterdir())
    expected_manifest, _ = _manifest(TSN_RAW_ROOT / entry.name for entry in source_entries)
    if captured != expected_manifest:
        raise CaptureError("private TSN capture differs from authoritative PDF manifest")
    non_source = []
    for name in TSN_NON_SOURCE_NAMES:
        path = TSN_RAW_ROOT / name
        if not _regular_file(path):
            raise CaptureError(f"TSN non-source role is not a regular file: {name}")
        non_source.append(asdict(FileEntry(name, path.stat().st_size, _sha_file(path))))
    return {
        "source_root": str(TSN_RAW_ROOT.resolve()),
        "private_root": str(destination.resolve()),
        "observed": captured,
        "members": [asdict(entry) for entry in captured_entries],
        "non_source_roles": non_source,
    }


def main() -> int:
    if PRIVATE_ROOT.exists():
        raise CaptureError(
            f"private capture already exists; never overwrite an immutable audit source: {PRIVATE_ROOT}"
        )
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=False)
    trees = {
        label: _copy_bound_tree(label, spec, PRIVATE_ROOT / label)
        for label, spec in TREE_SOURCES.items()
    }
    tsn = _copy_tsn(PRIVATE_ROOT / "authoritative_tsn_pdf")

    current_routes = trees["current_tsmis_excel"]["routes"]
    route_sets_equal = all(tree["routes"] == current_routes for tree in trees.values())
    current_pdf_equals_historical = (
        trees["current_tsmis_pdf"]["observed"]
        == trees["historical_tsmis_pdf_7_9"]["observed"]
        and all(
            left == right
            for left, right in zip(
                trees["current_tsmis_pdf"]["members"],
                trees["historical_tsmis_pdf_7_9"]["members"],
                strict=True,
            )
        )
    )
    result = {
        "audit": "Stage 8 Highway Sequence immutable raw-source capture",
        "status": "captured" if route_sets_equal and current_pdf_equals_historical else "failed",
        "sources": trees,
        "authoritative_tsn_pdf": tsn,
        "cross_source_invariants": {
            "all_tsmis_route_sets_exact": route_sets_equal,
            "tsmis_route_count": len(current_routes),
            "current_pdf_tree_byte_identical_to_historical_pdf_tree": current_pdf_equals_historical,
            "tsn_authoritative_pdf_count": tsn["observed"]["files"],
        },
    }
    result["stable_capture_sha256"] = _sha_bytes(_canonical_json({
        "sources": {
            label: {
                "binding": value["binding"],
                "observed": value["observed"],
                "members": value["members"],
                "routes": value["routes"],
            }
            for label, value in trees.items()
        },
        "authoritative_tsn_pdf": {
            "observed": tsn["observed"],
            "members": tsn["members"],
            "non_source_roles": tsn["non_source_roles"],
        },
        "cross_source_invariants": result["cross_source_invariants"],
    }))
    if result["status"] != "captured":
        raise CaptureError("cross-source capture invariants failed")
    manifest_path = PRIVATE_ROOT / "capture_manifest.json"
    manifest_path.write_bytes(_canonical_json(result))
    print(
        "PASS Highway Sequence immutable capture: "
        f"{sum(tree['observed']['files'] for tree in trees.values())} TSMIS members + "
        f"{tsn['observed']['files']} TSN PDFs; {result['stable_capture_sha256']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        print(f"FAIL Highway Sequence immutable capture: {exc}")
        raise SystemExit(1)
