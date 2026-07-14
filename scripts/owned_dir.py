"""Fail-closed ownership claims for app-created destination directories.

An ownership marker is authority for Reset to recursively delete a directory.
Consequently, this module never adopts an existing unowned directory: it creates
the leaf directory with ``exist_ok=False`` and writes the marker only into that
new directory.  Existing directories are reusable only when they already carry
the current creation claim for the requested purpose.

The top-level marker remains schema 1 until the repository-wide marker-v2
migration.  ``creation_claim`` is the versioned discriminator introduced by the
Phase-1 safety fix; older schema-1 markers lack it and are deliberately LEGACY /
untrusted for deletion.  This temporary retention is safer than guessing that an
old stamp proves creation.

Stdlib only; console-free.  The best-effort creator returns ``None`` when it
cannot establish ownership.  Callers that are about to write use
``require_owned_dir`` to fail the operation before touching the directory.
"""
import dataclasses
import json
import logging
import os
import stat
from pathlib import Path

log = logging.getLogger("tsmis.owned_dir")

OWNER_MARKER = ".tsmis-owned.json"
_APP_TAG = "TSMIS Reports Exporter"
_SCHEMA = 1
_CLAIM_SCHEMA = 1
_KINDS = frozenset(("store", "comparisons"))
_MAX_MARKER_BYTES = 4096

# Public status values let Reset explain why a candidate was retained.
OWNED = "owned"
MISSING = "missing"
LEGACY = "legacy"
WRONG_KIND = "wrong-kind"
INVALID = "invalid"


class OwnershipError(RuntimeError):
    """A requested output root exists but cannot be proven app-created."""


@dataclasses.dataclass(frozen=True)
class OwnershipLease:
    """Authority over one exact currently owned directory identity."""
    path: Path
    kind: str
    identity: tuple

    def is_current(self):
        # A marker reached through a symlink/junction ancestor is not authority
        # over the spelling the caller supplied.  Check from the filesystem
        # anchor down on every use, not only the leased leaf.
        if not _path_chain_is_plain(self.path, allow_missing=False):
            return False
        if _identity(self.path) != self.identity:
            return False
        if not is_owned(self.path, kind=self.kind):
            return False
        # Close a replacement between the first identity read and marker read.
        return _identity(self.path) == self.identity

    def require_current(self, action="write"):
        if not self.is_current():
            name = self.path.name or str(self.path)
            raise OwnershipError(
                f"The app-owned destination folder '{name}' changed before the "
                f"{action}. The current path was left untouched; retry the operation.")
        return self.path

    def is_safe_descendant(self, path, *, anchor_path=None,
                           anchor_identity=None, directory_identity=None):
        """True only when ``path`` is lexically beneath this exact leased root
        and every existing component from the root down is ordinary/non-reparse.

        Missing tail components are allowed so callers can safely create them
        after this check.  Callers recheck at their publish/mutation boundary;
        ``anchor_path``/``anchor_identity`` additionally bind an already-created
        descendant directory (for example a report staging folder) to the same
        exact object while validating a file beneath it. ``directory_identity``
        is retained as the shorthand for binding ``path`` itself.
        """
        if not self.is_current():
            return False
        root = Path(os.path.abspath(self.path))
        candidate = Path(os.path.abspath(path))
        try:
            candidate.relative_to(root)
        except ValueError:  # silent-ok: a lexical non-descendant is the unsafe False result
            return False
        if not _path_chain_is_plain(candidate, allow_missing=True):
            return False

        # Backward-compatible shorthand used by existing callers that bind a
        # directory and validate that directory itself.
        if directory_identity is not None:
            if anchor_path is not None or anchor_identity is not None:
                return False
            anchor_path, anchor_identity = candidate, directory_identity
        if (anchor_path is None) != (anchor_identity is None):
            return False
        if anchor_path is not None:
            anchor = Path(os.path.abspath(anchor_path))
            try:
                anchor.relative_to(root)
                candidate.relative_to(anchor)
            except ValueError:  # silent-ok: anchor/path containment failure is unsafe
                return False
            if (_identity(anchor) != anchor_identity
                    or not _path_chain_is_plain(anchor, allow_missing=False)):
                return False

        # Close replacement of either the root or the bound descendant while
        # components were being inspected.
        if not self.is_current():
            return False
        return anchor_path is None or _identity(anchor) == anchor_identity

    def require_safe_descendant(self, path, action="write", *,
                                anchor_path=None, anchor_identity=None,
                                directory_identity=None):
        if not self.is_safe_descendant(
                path, anchor_path=anchor_path, anchor_identity=anchor_identity,
                directory_identity=directory_identity):
            raise OwnershipError(
                f"The app-owned destination changed or contains a linked folder "
                f"before the {action}. The path was left untouched; retry after "
                f"removing the junction/symlink.")
        return Path(path)

    def guard(self, path=None, *, anchor_path=None, anchor_identity=None,
              directory_identity=None):
        """Predicate adapter for target-aware artifact mutation boundaries."""
        if path is None:
            return self.is_current()
        return self.is_safe_descendant(
            path, anchor_path=anchor_path, anchor_identity=anchor_identity,
            directory_identity=directory_identity)


def _is_reparse(st):
    attrs = getattr(st, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(st.st_mode) or bool(attrs & flag)


def _plain_directory(path):
    try:
        st = Path(path).lstat()
    except OSError:  # silent-ok: unreadable is the fail-closed "not a plain directory" result
        return False
    return stat.S_ISDIR(st.st_mode) and not _is_reparse(st)


def _path_chain_is_plain(path, *, allow_missing):
    """Reject any symlink/reparse component from the filesystem anchor down.

    ``Path.resolve`` cannot be used for this safety decision because resolving
    follows precisely the aliases we need to reject.  ``abspath`` normalizes the
    lexical spelling while ``lstat`` inspects each object without following it.
    A missing tail is permitted only for a caller that is about to create it.
    """
    path = Path(os.path.abspath(path))
    chain = list(reversed(path.parents)) + [path]
    missing = False
    for index, component in enumerate(chain):
        if missing:
            continue
        try:
            st = component.lstat()
        except FileNotFoundError:  # silent-ok: a missing tail is caller-policy, handled below
            if not allow_missing:
                return False
            missing = True
            continue
        except OSError:  # silent-ok: unreadable path components are unsafe
            return False
        if _is_reparse(st):
            return False
        if index < len(chain) - 1 and not stat.S_ISDIR(st.st_mode):
            return False
    return not missing or allow_missing


def _identity(path):
    """A replacement-sensitive identity for best-effort race cleanup."""
    try:
        st = Path(path).lstat()
    except OSError:  # silent-ok: unavailable file identity means ownership is refused
        return None
    if not stat.S_ISDIR(st.st_mode) or _is_reparse(st):
        return None
    # Directory timestamps change as reports are added, so they cannot bind a
    # persistent claim. Local Windows/NTFS and normal POSIX filesystems expose a
    # stable file ID as (device, inode); if a filesystem does not, fail closed.
    if not st.st_ino:
        return None
    return (st.st_dev, st.st_ino)


def directory_identity(path):
    """Stable identity for a plain directory, or ``None`` when unprovable.

    Reset carries this identity from selection through its atomic quarantine
    handoff.  Exposing the same primitive prevents the selector and deleter from
    quietly drifting onto different notions of "the same directory".
    """
    return _identity(path)


def is_plain_directory_tree(path, identity=None):
    """True iff a directory tree contains no symlink/reparse entry.

    Recursive stage cleanup and promotion must not walk an attacker-planted
    junction.  Bind the root identity before and after the scan so replacing
    the stage while it is inspected fails closed.
    """
    path = Path(path)
    expected = identity if identity is not None else _identity(path)
    if expected is None or _identity(path) != expected:
        return False
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:  # silent-ok: unreadable entries are unsafe
                        return False
                    if _is_reparse(st):
                        return False
                    if stat.S_ISDIR(st.st_mode):
                        pending.append(Path(entry.path))
        except OSError:  # silent-ok: unreadable/replaced trees are unsafe
            return False
    return _identity(path) == expected


def _claim_for(identity):
    return {"schema": _CLAIM_SCHEMA, "mode": "created",
            "device": identity[0], "file_id": identity[1]}


def _read_marker(path):
    path = Path(path)
    if (not _plain_directory(path)
            or not _path_chain_is_plain(path, allow_missing=False)):
        return INVALID, None
    marker = path / OWNER_MARKER
    try:
        mst = marker.lstat()
    except FileNotFoundError:
        return MISSING, None
    except OSError:
        return INVALID, None
    if (not stat.S_ISREG(mst.st_mode) or _is_reparse(mst)
            or mst.st_size > _MAX_MARKER_BYTES):
        return INVALID, None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return INVALID, None
    if not isinstance(data, dict) or data.get("app") != _APP_TAG:
        return INVALID, data
    # Every marker written before this safety fix lacks creation_claim.  Treat
    # unsupported future schemas the same way: retained until an explicit,
    # validated migration understands them.
    claim = data.get("creation_claim")
    if (data.get("schema") != _SCHEMA or not isinstance(claim, dict)
            or claim.get("schema") != _CLAIM_SCHEMA
            or claim.get("mode") != "created"):
        return LEGACY, data
    identity = _identity(path)
    if identity is None or claim != _claim_for(identity):
        return INVALID, data
    if data.get("kind") not in _KINDS:
        return INVALID, data
    return OWNED, data


def ownership_status(path, kind=None):
    """Classify a marker without raising.

    ``kind`` binds authority to its purpose.  A valid comparisons marker never
    authorizes deletion of an environment store (and vice versa).
    """
    if kind is not None and kind not in _KINDS:
        return INVALID
    status, data = _read_marker(path)
    if status == OWNED and kind is not None and data.get("kind") != kind:
        return WRONG_KIND
    return status


def is_owned(path, kind=None):
    """True only for a current creation claim of the requested purpose."""
    return ownership_status(path, kind=kind) == OWNED


def mark_owned(path, kind="store"):
    """Compatibility shim that cannot stamp/adopt a directory.

    Older code exposed this as a stamp-on-sight primitive.  Keeping the name as
    a validation-only shim avoids a surprising AttributeError for extensions,
    while making the unsafe operation impossible.  New code must call
    ``ensure_owned_dir`` before it writes anything.
    """
    ok = is_owned(path, kind=kind)
    if not ok:
        log.warning("ownership marker: refused to adopt existing directory %s", path)
    return ok


def _write_creation_marker(path, kind, identity):
    """Write once; never overwrite a marker planted in a creation race."""
    marker = Path(path) / OWNER_MARKER
    created_file = False
    try:
        with open(marker, "x", encoding="utf-8") as f:
            created_file = True
            json.dump({"app": _APP_TAG, "schema": _SCHEMA, "kind": kind,
                       "creation_claim": _claim_for(identity)}, f, sort_keys=True)
        return True, created_file
    except OSError as e:
        log.warning("ownership marker: could not create %s (%s)",
                    marker, type(e).__name__)
        return False, created_file


def _discard_failed_creation(path, identity, remove_marker):
    """Undo only the exact leaf we created, and only while it remains empty.

    Never recurse: if another process populated or replaced it, fail closed and
    leave everything untouched.
    """
    path = Path(path)
    if identity is None or _identity(path) != identity:
        return
    if remove_marker:
        try:
            (path / OWNER_MARKER).unlink()
        except OSError:  # silent-ok: failed-claim cleanup; the leaf remains untrusted
            pass
    try:
        path.rmdir()
    except OSError:  # silent-ok: never recurse through a raced/populated failed claim
        pass


def ensure_owned_dir(path, kind="store"):
    """Create and mark ``path``, or reuse an already trusted matching path.

    Returns the Path on success and ``None`` on any ambiguity/failure.  In
    particular, a pre-existing unowned, legacy, corrupt, reparse-point, or
    wrong-purpose directory is never stamped or modified.
    """
    path = Path(path)
    if kind not in _KINDS:
        log.warning("ownership marker: refused unknown purpose %r for %s", kind, path)
        return None
    # Refuse creation through an existing alias.  Rechecked after mkdir and by
    # every lease use; the unavoidable final OS-call race remains fail-closed at
    # the next boundary.
    if not _path_chain_is_plain(path.parent, allow_missing=True):
        log.warning("ownership marker: reparse/unreadable ancestor refused: %s", path)
        return None
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        if (_path_chain_is_plain(path, allow_missing=False)
                and is_owned(path, kind=kind)):
            return path
        log.warning("ownership marker: existing directory is not trusted for %s: %s",
                    kind, path)
        return None
    except OSError as e:
        log.warning("ownership marker: could not create %s (%s)",
                    path, type(e).__name__)
        return None

    identity = _identity(path)
    if identity is None or not _path_chain_is_plain(path, allow_missing=False):
        _discard_failed_creation(path, identity, remove_marker=False)
        return None
    wrote, created_marker = _write_creation_marker(path, kind, identity)
    if (not wrote or _identity(path) != identity
            or not is_owned(path, kind=kind)):
        _discard_failed_creation(path, identity, remove_marker=created_marker)
        return None
    return path


def require_owned_dir(path, kind="store"):
    """Create/reuse an owned directory or raise before the caller writes."""
    result = ensure_owned_dir(path, kind=kind)
    if result is None:
        name = Path(path).name or str(path)
        raise OwnershipError(
            f"The destination folder '{name}' already exists or could not be "
            "proven app-created for this operation. It was left untouched; "
            "choose another destination or move/delete it manually.")
    return result


def require_owned_dir_lease(path, kind="store"):
    """Create/reuse an owned directory and bind subsequent writes to its identity."""
    result = require_owned_dir(path, kind=kind)
    identity = _identity(result)
    lease = OwnershipLease(path=Path(result), kind=kind, identity=identity)
    lease.require_current(action="ownership handoff")
    return lease


def require_existing_owned_dir_lease(path, kind="store"):
    """Bind an already-current owned directory without creating/adopting it."""
    path = Path(path)
    if not is_owned(path, kind=kind):
        name = path.name or str(path)
        raise OwnershipError(
            f"The existing folder '{name}' is not currently proven app-created "
            f"for {kind} output. It was left untouched; re-export it first.")
    identity = _identity(path)
    lease = OwnershipLease(path=path, kind=kind, identity=identity)
    lease.require_current(action="existing ownership handoff")
    return lease
