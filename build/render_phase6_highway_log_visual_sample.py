"""Render and bind the Stage-6 Highway Log first/middle/final visual sample.

The script deliberately refuses an existing output directory.  A prior failed render
therefore cannot satisfy a later filename census or overwrite a different page role.
It binds each PNG to an exact source PDF and physical page, then writes a deterministic
manifest containing only stable byte identities.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys


RAW_DIR = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\highway_log\raw"
)
PDFTOPPM = Path(
    r"C:\Users\Yunus\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "tmp" / "pdfs" / "phase6-hl-visual-r2"
)
RAW_BINDINGS = (
    ("D01 Highway Log TSN.pdf", 1_633_209, "0e26d5ef011891f0a77be774e3b655a18a7add616c5139676ab99950e54ddc34", 116),
    ("D02 Highway Log TSN.pdf", 2_045_757, "d610f137d88c41cf61d239aa29c6ecad1c2621d307d4c984a8ea5aa15289b6a4", 149),
    ("D03 Highway Log TSN.pdf", 2_725_260, "139b14eb4893ee6427153def005262589d1e2dc4bdb2766831579d284307081f", 205),
    ("D04 Highway Log TSN.pdf", 4_376_185, "6046fd7a8f60cf3a85d497cd13278fc936d949221820b75235eaab1a263e8433", 330),
    ("D05 Highway Log TSN.pdf", 2_060_100, "633ac80514b4791886ee58c8b41be166fd75a03ed0e8c974369fe521035799f5", 154),
    ("D06 Highway Log TSN.pdf", 2_226_816, "ac6409f35047a0ecfac93ba00347cf355dbf99bb41e5da69788c3c4a4d387282", 168),
    ("D07 Highway Log TSN.pdf", 3_626_589, "7d1151142d103df72e8b3f6ba9193001a88a2806c580ab4dda775053dd0a4371", 287),
    ("D08 Highway Log TSN.pdf", 2_744_102, "e2efb38281e9bfcc18a02a54bdc4ad1068045fdcbd812f00584e6c6092109cd3", 217),
    ("D09 Highway Log TSN.pdf", 844_675, "38470f27cc49ee1d2eb0813ef653a1348a17522a519a903155ef995ea8c63903", 63),
    ("D10 Highway Log TSN.pdf", 2_080_827, "f6aff2dba133da9d66a46d81ffa5f723f38aab5e48a6d8b1824dbfb4a085c123", 157),
    ("D11 Highway Log TSN.pdf", 2_311_316, "d7a1eba4ddf75d98874e42a379b7cf189699436dcebe557bffd140b287091a76", 179),
    ("D12 Highway Log TSN.pdf", 1_237_155, "36e56bf834063a11be8f2c24cc1e3c93cfd89ac4bc745dd8a494ed6311b39a97", 96),
)
NON_SOURCE_BINDING = (
    "_PUT TSN FILES HERE.txt", 446,
    "fcb06a243e57f311692a7c0019025adfda20c9a98fa0ab29b7c0bf8d419ac0d5",
)


class SampleError(ValueError):
    pass


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _verify_file(path: Path, size: int, digest: str) -> None:
    if not path.is_file():
        raise SampleError(f"bound file missing: {path}")
    actual_size = path.stat().st_size
    actual_digest = _sha_file(path)
    if (actual_size, actual_digest) != (size, digest):
        raise SampleError(
            f"bound file changed: {path.name} expected {size}/{digest}, "
            f"got {actual_size}/{actual_digest}"
        )


def _sample_roles(page_count: int) -> tuple[tuple[str, int], ...]:
    roles = (
        ("first", 1),
        ("middle", (page_count + 1) // 2),
        ("final", page_count),
    )
    if len({page for _role, page in roles}) != 3:
        raise SampleError(f"sample page roles alias for {page_count} pages")
    return roles


def build_sample(output_dir: Path, *, dpi: int = 120) -> tuple[Path, bytes]:
    if output_dir.exists():
        raise SampleError(f"output directory already exists: {output_dir}")
    if not PDFTOPPM.is_file():
        raise SampleError(f"renderer missing: {PDFTOPPM}")

    expected_names = {name for name, _size, _digest, _pages in RAW_BINDINGS}
    expected_names.add(NON_SOURCE_BINDING[0])
    actual_names = {path.name for path in RAW_DIR.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise SampleError(
            f"raw role universe changed: missing={sorted(expected_names - actual_names)} "
            f"extra={sorted(actual_names - expected_names)}"
        )
    for name, size, digest, _pages in RAW_BINDINGS:
        _verify_file(RAW_DIR / name, size, digest)
    _verify_file(RAW_DIR / NON_SOURCE_BINDING[0],
                 NON_SOURCE_BINDING[1], NON_SOURCE_BINDING[2])

    output_dir.mkdir(parents=True, exist_ok=False)
    samples: list[dict[str, object]] = []
    image_digests_by_member: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
    expected_pngs: set[str] = set()

    for district, (name, size, digest, page_count) in enumerate(RAW_BINDINGS, 1):
        source = RAW_DIR / name
        for role, page in _sample_roles(page_count):
            output_name = f"d{district:02d}_p{page:03d}.png"
            expected_pngs.add(output_name)
            prefix = output_dir / output_name.removesuffix(".png")
            completed = subprocess.run(
                [str(PDFTOPPM), "-f", str(page), "-l", str(page),
                 "-singlefile", "-png", "-r", str(dpi),
                 str(source), str(prefix)],
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise SampleError(
                    f"renderer failed for {name} page {page}: "
                    f"{completed.stderr.decode('utf-8', errors='replace')[-500:]}"
                )
            output_path = output_dir / output_name
            if not output_path.is_file() or output_path.stat().st_size == 0:
                raise SampleError(f"render output missing/empty: {output_name}")
            image_digest = _sha_file(output_path)
            image_digests_by_member[name].append((role, image_digest))
            samples.append({
                "member": name,
                "source_size": size,
                "source_sha256": digest,
                "source_page_count": page_count,
                "role": role,
                "physical_page": page,
                "output_name": output_name,
                "image_size": output_path.stat().st_size,
                "image_sha256": image_digest,
            })

    actual_pngs = {path.name for path in output_dir.glob("*.png")}
    if actual_pngs != expected_pngs or len(samples) != 36:
        raise SampleError(
            f"render role universe changed: samples={len(samples)} "
            f"missing={sorted(expected_pngs - actual_pngs)} "
            f"extra={sorted(actual_pngs - expected_pngs)}"
        )
    aliases = {
        member: roles
        for member, roles in image_digests_by_member.items()
        if len({digest for _role, digest in roles}) != len(roles)
    }
    if aliases:
        raise SampleError(f"same-document render roles alias: {aliases}")

    manifest = {
        "schema_version": 1,
        "sample_complete": True,
        "dpi": dpi,
        "sample_count": len(samples),
        "renderer": {
            "name": PDFTOPPM.name,
            "size": PDFTOPPM.stat().st_size,
            "sha256": _sha_file(PDFTOPPM),
        },
        "non_source_role": {
            "name": NON_SOURCE_BINDING[0],
            "size": NON_SOURCE_BINDING[1],
            "sha256": NON_SOURCE_BINDING[2],
        },
        "samples": samples,
    }
    payload = _json_bytes(manifest)
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("xb") as stream:
        stream.write(payload)
    return manifest_path, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args(argv)
    if args.dpi < 72 or args.dpi > 300:
        raise SampleError("dpi must be between 72 and 300")
    try:
        manifest_path, payload = build_sample(args.output_dir, dpi=args.dpi)
    except Exception as exc:
        print(f"FAIL Highway Log visual sample: {type(exc).__name__}: {exc}")
        return 1
    print(
        "PASS Highway Log visual sample: "
        f"36 roles; manifest {len(payload)} bytes/{hashlib.sha256(payload).hexdigest()}; "
        f"{manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
