"""Exact source admission for TSN raw files and D01-D12 PDF families."""
import hashlib
import json
import re
import stat
from collections import Counter
from pathlib import Path


EXPECTED_DISTRICTS = tuple(f"{number:02d}" for number in range(1, 13))
_FILENAME_DISTRICT_RE = re.compile(
    r"(?:^|[^A-Z0-9])D(\d{1,2})(?=$|[^A-Z0-9])", re.IGNORECASE)
_FILENAME_DISTRICT_LIKE_RE = re.compile(
    r"(?:^|[^A-Z0-9])D\d+", re.IGNORECASE)

RAW_MANIFEST_VERSION = 1
RAW_MANIFEST_ALGORITHM = "sha256"
RAW_MANIFEST_SERIALIZATION = "relative_path\\tbyte_length\\tmember_sha256\\n"
_MANIFEST_KEYS = {
    "version", "algorithm", "serialization", "root_scope", "member_count",
    "byte_length", "sha256", "members",
}
_MEMBER_KEYS = {"relative_path", "byte_length", "sha256"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _district(value):
    text = str(value).strip()
    if not text.isdigit():
        raise ValueError(f"invalid internal district claim {value!r}")
    normalized = text.zfill(2)
    if normalized not in EXPECTED_DISTRICTS:
        raise ValueError(f"internal district claim {value!r} is outside D01-D12")
    return normalized


def document_district(claims, pdf_name=""):
    """Return the sole internal D01-D12 claim and reject disagreement.

    A filename is never a substitute for an internal claim. If a filename does
    itself contain a Dnn token, that independent claim must agree.
    """
    normalized = {_district(value) for value in claims}
    if len(normalized) != 1:
        detail = ", ".join(sorted(normalized)) if normalized else "none"
        raise ValueError(
            f"TSN district PDF must claim exactly one internal D01-D12 district "
            f"(found {detail})")
    district = next(iter(normalized))
    if pdf_name:
        stem = Path(pdf_name).stem
        matches = list(_FILENAME_DISTRICT_RE.finditer(stem))
        district_like = list(_FILENAME_DISTRICT_LIKE_RE.finditer(stem))
        if len(matches) != len(district_like):
            raise ValueError(
                f"filename contains a malformed district token: {Path(pdf_name).name}")
        if len(matches) > 1:
            claims = ", ".join(f"D{_district(match.group(1))}" for match in matches)
            raise ValueError(
                f"filename must contain at most one exact Dnn token (found {claims})")
    else:
        matches = []
    if matches:
        filename_district = _district(matches[0].group(1))
        if filename_district != district:
            raise ValueError(
                f"filename district D{filename_district} disagrees with internal "
                f"district D{district}")
    return district


def require_exact_universe(claimed_members):
    """Require exactly one internally claimed document for every D01-D12."""
    claimed = [(str(district).zfill(2), str(path))
               for district, path in claimed_members]
    counts = Counter(district for district, _path in claimed)
    missing = [district for district in EXPECTED_DISTRICTS if counts[district] == 0]
    duplicate = [district for district in EXPECTED_DISTRICTS if counts[district] > 1]
    unexpected = sorted(district for district in counts
                        if district not in EXPECTED_DISTRICTS)
    if len(claimed) != 12 or missing or duplicate or unexpected:
        pieces = [f"found {len(claimed)} document(s)"]
        if missing:
            pieces.append("missing " + ", ".join(f"D{d}" for d in missing))
        if duplicate:
            pieces.append("duplicate " + ", ".join(f"D{d}" for d in duplicate))
        if unexpected:
            pieces.append("unexpected " + ", ".join(f"D{d}" for d in unexpected))
        raise ValueError("TSN district source must be exactly one internally claimed "
                         "document for every D01-D12 (" + "; ".join(pieces) + ")")
    return tuple((district, path) for district, path in sorted(claimed))


def _relative_path(path, root):
    path = Path(path).absolute()
    root = Path(root).absolute()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"TSN raw member is outside its report raw directory: {path}") from exc
    if (not relative or relative.startswith("/") or "\\" in relative
            or "\t" in relative or "\r" in relative or "\n" in relative
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise ValueError(f"TSN raw member has a non-canonical relative path: {relative!r}")
    return relative


def _stable_bytes(path):
    """Read one ordinary member once and reject replacement/mutation while read."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"TSN raw member must be an ordinary file, not a link: {path}")
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"TSN raw member is not an ordinary file: {path}")
        with path.open("rb") as stream:
            data = stream.read()
        after = path.stat()
    except OSError as exc:
        raise ValueError(
            f"TSN raw member could not be read stably: {path} "
            f"({type(exc).__name__}: {exc})") from exc
    signature = lambda value: (  # noqa: E731 - compact exact stat tuple
        int(value.st_size), int(getattr(value, "st_mtime_ns", value.st_mtime * 1e9)),
        int(getattr(value, "st_ctime_ns", value.st_ctime * 1e9)),
        int(getattr(value, "st_dev", 0)), int(getattr(value, "st_ino", 0)),
        stat.S_IFMT(value.st_mode),
    )
    if signature(before) != signature(after) or len(data) != before.st_size:
        raise ValueError(f"TSN raw member changed while it was being read: {path}")
    return data


def _manifest_from_entries(entries):
    entries = sorted(entries, key=lambda item: item["relative_path"].casefold())
    folded = [item["relative_path"].casefold() for item in entries]
    if len(folded) != len(set(folded)):
        raise ValueError("TSN raw member relative paths are not case-insensitively unique")
    lines = "".join(
        f"{item['relative_path']}\t{item['byte_length']}\t{item['sha256']}\n"
        for item in entries)
    return {
        "version": RAW_MANIFEST_VERSION,
        "algorithm": RAW_MANIFEST_ALGORITHM,
        "serialization": RAW_MANIFEST_SERIALIZATION,
        "root_scope": "report_raw_dir",
        "member_count": len(entries),
        "byte_length": sum(item["byte_length"] for item in entries),
        "sha256": hashlib.sha256(lines.encode("utf-8")).hexdigest(),
        "members": entries,
    }


def capture_raw_manifest(paths, root):
    """Return ``(canonical manifest, immutable bytes by relative path)``.

    The representation follows the audit's canonical manifest serialization.
    Captured bytes let long-running district parsers consume exactly the content
    that the manifest names, independent of later source-file replacement.
    """
    entries = []
    captured = {}
    for path in paths:
        relative = _relative_path(path, root)
        data = _stable_bytes(path)
        entry = {
            "relative_path": relative,
            "byte_length": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        entries.append(entry)
        captured[relative] = data
    manifest = _manifest_from_entries(entries)
    validate_raw_manifest(manifest)
    return manifest, captured


def canonical_raw_manifest(paths, root):
    """Return the strict canonical content manifest without retaining member bytes."""
    manifest, _captured = capture_raw_manifest(paths, root)
    return manifest


def validate_raw_manifest(value):
    """Return a strict, deterministic raw manifest or raise ``ValueError``."""
    if not isinstance(value, dict) or set(value) != _MANIFEST_KEYS:
        raise ValueError("TSN raw manifest shape is invalid")
    if (not isinstance(value.get("version"), int)  # CMP-AUD-035: reject 1.0 aliasing 1
            or isinstance(value.get("version"), bool)
            or value.get("version") != RAW_MANIFEST_VERSION
            or value.get("algorithm") != RAW_MANIFEST_ALGORITHM
            or value.get("serialization") != RAW_MANIFEST_SERIALIZATION
            or value.get("root_scope") != "report_raw_dir"):
        raise ValueError("TSN raw manifest version or serialization is invalid")
    # CMP-AUD-035: member_count/byte_length are only otherwise checked by the canonical
    # dict-equality below, and `True == 1`/`1.0 == 1`, so a bool/float would alias the
    # canonical integer. Require exact ints here.
    for _int_field in ("member_count", "byte_length"):
        _v = value.get(_int_field)
        if not isinstance(_v, int) or isinstance(_v, bool):
            raise ValueError(f"TSN raw manifest {_int_field} must be an exact integer")
    members = value.get("members")
    if not isinstance(members, list):
        raise ValueError("TSN raw manifest members must be a list")
    clean = []
    for member in members:
        if not isinstance(member, dict) or set(member) != _MEMBER_KEYS:
            raise ValueError("TSN raw manifest member shape is invalid")
        relative = member.get("relative_path")
        size = member.get("byte_length")
        digest = member.get("sha256")
        if (not isinstance(relative, str) or not relative
                or relative.startswith("/") or "\\" in relative
                or "\t" in relative or "\r" in relative or "\n" in relative
                or any(part in ("", ".", "..") for part in relative.split("/"))):
            raise ValueError("TSN raw manifest relative path is invalid")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("TSN raw manifest byte length is invalid")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValueError("TSN raw manifest member SHA-256 is invalid")
        clean.append({"relative_path": relative, "byte_length": size, "sha256": digest})
    canonical = _manifest_from_entries(clean)
    if value != canonical:
        raise ValueError("TSN raw manifest is not in exact canonical form")
    # Force JSON compatibility now; sidecar publication must never discover a
    # non-serializable value after the normalized workbook has been committed.
    json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return canonical
