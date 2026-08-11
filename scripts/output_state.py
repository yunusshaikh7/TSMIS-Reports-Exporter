"""Organized durable state for generated artifacts.

User-facing output directories should contain user-facing artifacts.  The app
still needs outcome/provenance records, comparison payload chunks, matrix
caches, evidence manifests, and publication locks, so those files live in one
``_state`` child of the directory whose artifacts they describe.

Readers remain compatible with the legacy sibling layout.  New writes always
target ``_state``; :func:`organize_tree` performs a conservative copy/verify/
remove migration for existing output trees.
"""
import hashlib
import logging
import os
import re
import secrets
import stat
from pathlib import Path


log = logging.getLogger("tsmis.output_state")

STATE_DIRNAME = "_state"

_EXACT_STATE_NAMES = frozenset({
    "_results.json",
    "_tsn_results.json",
    "_attempts.json",
    ".tsmis-comparison-publication.lock",
})
_STATE_SUFFIXES = (
    ".outcome.json",
    ".outcome.json.tmp",
    ".provenance.json",
    ".provenance.json.tmp",
    ".fingerprint.json",
    " (evidence).json",
)
_STATE_TEMP_RE = re.compile(
    r"^(?:\.cmpmeta\.tmp-.*|\.cmpv3-payload\.tmp-.*|"
    r".*(?:\.fingerprint\.json|_results\.json|"
    r"_tsn_results\.json|_attempts\.json| \(evidence\)\.json)\.tmp(?:-.*)?)$"
)
_PAYLOAD_RE = re.compile(
    r"^\.cmpv3-(?:[0-9a-f]{16}|[0-9a-f]{64})-[0-9]{6}-"
    r"(?:[0-9a-f]{16}|[0-9a-f]{64})"
    r"(?:-f-(?:0[0-7]|[0-9a-f]{64}-[0-9a-f]{16}))?"
    r"\.comparison-payload\.zlib$"
)
_COPY_CHUNK = 1024 * 1024


def state_dir(parent):
    """Return the organized state directory for one artifact directory."""
    return Path(parent) / STATE_DIRNAME


def state_file(parent, name):
    """Return a named state file beneath ``parent/_state``."""
    return state_dir(parent) / str(name)


def artifact_state_file(artifact, suffix):
    """Return state named ``<artifact basename><suffix>``."""
    artifact = Path(artifact)
    return state_file(artifact.parent, artifact.name + str(suffix))


def legacy_artifact_state_file(artifact, suffix):
    """Return the pre-organization sibling path for compatibility reads."""
    artifact = Path(artifact)
    return artifact.with_name(artifact.name + str(suffix))


def legacy_state_file(parent, name):
    """Return the pre-organization sibling path for a named state file."""
    return Path(parent) / str(name)


def _lexists(path):
    return os.path.lexists(Path(path))


def read_path(preferred, legacy):
    """Select new state when present, otherwise the legacy sibling.

    ``lexists`` is intentional: a broken link or other unsafe entry in the new
    namespace must be read (and rejected by the caller), never bypassed to
    resurrect an older trusted legacy record.
    """
    preferred = Path(preferred)
    return preferred if _lexists(preferred) else Path(legacy)


def artifact_read_file(artifact, suffix):
    return read_path(
        artifact_state_file(artifact, suffix),
        legacy_artifact_state_file(artifact, suffix),
    )


def named_read_file(parent, name):
    return read_path(state_file(parent, name), legacy_state_file(parent, name))


def _is_reparse(st):
    attrs = getattr(st, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(st.st_mode) or bool(attrs & flag)


def _plain_directory(path):
    try:
        st = Path(path).lstat()
    except OSError:  # silent-ok: callers treat an unprovable state directory as unavailable
        return False
    return stat.S_ISDIR(st.st_mode) and not _is_reparse(st)


def _guard_allows(commit_guard, path):
    if commit_guard is None:
        return True
    try:
        return bool(commit_guard(Path(path)))
    except TypeError:
        try:
            return bool(commit_guard())
        except Exception as e:  # noqa: BLE001 - a callback defect denies mutation
            log.warning("state ownership check failed (%s: %s)", type(e).__name__, e)
            return False
    except Exception as e:  # noqa: BLE001 - a callback defect denies mutation
        log.warning("state ownership check failed (%s: %s)", type(e).__name__, e)
        return False


def ensure_state_dir(parent, commit_guard=None):
    """Create/reuse one ordinary ``_state`` directory, or return ``None``.

    The exact parent and child are guard-checked before and after creation.  A
    symlink/junction/reparse point is never accepted as the state namespace.
    """
    parent = Path(parent)
    target = state_dir(parent)
    if not (_guard_allows(commit_guard, parent)
            and _guard_allows(commit_guard, target)):
        return None
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.warning("could not create state parent %s (%s: %s)",
                    parent, type(e).__name__, e)
        return None
    if (not _plain_directory(parent)
            or not _guard_allows(commit_guard, parent)):
        log.warning("organized state parent is not an ordinary authorized folder: %s",
                    parent)
        return None
    try:
        target.mkdir(exist_ok=False)
    except FileExistsError:  # silent-ok: an existing ordinary directory is validated below
        pass
    except OSError as e:
        log.warning("could not create organized state directory %s (%s: %s)",
                    target, type(e).__name__, e)
        return None
    if (not _plain_directory(target)
            or not _guard_allows(commit_guard, parent)
            or not _guard_allows(commit_guard, target)):
        log.warning("organized state directory is not an ordinary authorized folder: %s",
                    target)
        return None
    return target


def is_legacy_state_name(name):
    """Whether one sibling basename belongs in ``_state``.

    The allowlist is deliberately exact.  Arbitrary JSON (for example a site
    capture manifest supplied for diagnostics) remains a user-visible artifact.
    """
    name = str(name)
    return (name in _EXACT_STATE_NAMES
            or name.endswith(_STATE_SUFFIXES)
            or bool(_STATE_TEMP_RE.fullmatch(name))
            or bool(_PAYLOAD_RE.fullmatch(name)))


def _file_identity(path):
    try:
        st = Path(path).lstat()
    except OSError:  # silent-ok: migration retains any unprovable entry
        return None
    if not stat.S_ISREG(st.st_mode) or _is_reparse(st):
        return None
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def _digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(_COPY_CHUNK)
            if not block:
                break
            value.update(block)
    return value.hexdigest()


def _copy_verified(source, destination):
    """Install an identical destination without replacing an existing entry.

    Returns ``(ready, source_identity, source_digest)``.  ``ready`` means the
    destination is byte-identical and the source stayed bound throughout; only
    then may the caller remove the legacy source.
    """
    source, destination = Path(source), Path(destination)
    before = _file_identity(source)
    if before is None:
        return False, None, None
    try:
        source_digest = _digest(source)
    except OSError:
        return False, None, None
    if _file_identity(source) != before:
        return False, None, None

    if _lexists(destination):
        current = _file_identity(destination)
        if current is None:
            return False, None, None
        try:
            same = current[2] == before[2] and _digest(destination) == source_digest
        except OSError:  # silent-ok: an unreadable conflict is retained, never replaced
            same = False
        return (same and _file_identity(source) == before), before, source_digest

    tmp = destination.with_name(
        f".{destination.name}.organize-{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    fd = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with open(source, "rb") as incoming, os.fdopen(fd, "wb") as outgoing:
            fd = None
            while True:
                block = incoming.read(_COPY_CHUNK)
                if not block:
                    break
                outgoing.write(block)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        if (_file_identity(source) != before
                or _file_identity(tmp) is None
                or _digest(tmp) != source_digest):
            return False, None, None
        # A hard-link install is atomic and refuses a raced destination on both
        # Windows and POSIX.  The temp and destination are in the same folder.
        os.link(tmp, destination)
        if (_file_identity(source) != before
                or _file_identity(destination) is None
                or _digest(destination) != source_digest):
            return False, None, None
        return True, before, source_digest
    except OSError:
        return False, None, None
    finally:
        if fd is not None:
            os.close(fd)
        try:
            tmp.unlink()
        except OSError:  # silent-ok: a failed temp cleanup is retained for inspection
            pass


def _remove_verified_source(source, identity, digest):
    source = Path(source)
    try:
        if _file_identity(source) != identity or _digest(source) != digest:
            return False
        source.unlink()
        return not _lexists(source)
    except OSError:  # silent-ok: migration is conservative and retains the legacy file
        return False


def _plain_dirs(root):
    """Yield ordinary directories without traversing links or ``_state``."""
    root = Path(root)
    if not _plain_directory(root):
        return
    pending = [root]
    while pending:
        current = pending.pop()
        yield current
        try:
            with os.scandir(current) as entries:
                children = []
                for entry in entries:
                    if entry.name == STATE_DIRNAME:
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:  # silent-ok: an unreadable child is retained and not traversed
                        continue
                    if stat.S_ISDIR(st.st_mode) and not _is_reparse(st):
                        children.append(Path(entry.path))
                pending.extend(reversed(sorted(children, key=lambda p: p.name.lower())))
        except OSError:  # silent-ok: an unreadable directory is retained and skipped
            continue


def organize_tree(root):
    """Move recognized legacy state into per-directory ``_state`` folders.

    Every file is copied, SHA-256 verified, and installed without replacement
    before the exact unchanged source is removed.  Conflicts and races are
    retained and reported.  The function never follows a link/reparse point and
    never moves arbitrary JSON.
    """
    result = {"organized": 0, "already": 0, "retained": 0, "directories": 0}
    root = Path(root)
    if not _plain_directory(root):
        return result
    for parent in _plain_dirs(root):
        try:
            with os.scandir(parent) as scan:
                entries = [Path(entry.path) for entry in scan
                           if entry.is_file(follow_symlinks=False)
                           and is_legacy_state_name(entry.name)]
        except OSError:  # silent-ok: the retained count surfaces a directory scan failure
            result["retained"] += 1
            continue
        if not entries:
            continue
        target_dir = ensure_state_dir(parent)
        if target_dir is None:
            result["retained"] += len(entries)
            continue
        result["directories"] += 1
        ready_entries = []
        for source in sorted(entries, key=lambda p: p.name.lower()):
            destination = target_dir / source.name
            existed = _lexists(destination)
            ready, identity, digest = _copy_verified(source, destination)
            if not ready:
                result["retained"] += 1
                continue
            ready_entries.append((source, identity, digest, existed))

        # Finish every verified copy in this directory before removing any
        # legacy source.  A crash during the copy phase therefore leaves the
        # complete legacy namespace readable; the next run resumes safely.
        for source, identity, digest, existed in ready_entries:
            if _remove_verified_source(source, identity, digest):
                result["already" if existed else "organized"] += 1
            else:
                result["retained"] += 1
    return result
