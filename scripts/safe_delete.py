"""Reparse-point-safe recursive delete for the "Delete all reports" path.

"Delete all reports" runs over the app's run folders AND a user-chosen
Export-Everything store, where a directory JUNCTION or symlink (dropped by a user
or a file-sync / backup tool) could point at unrelated data. The shipped CPython
3.11 ``shutil.rmtree`` already refuses to FOLLOW a junction: a CHILD junction it
unlinks WITHOUT deleting the target's contents (guarded since 3.8 via
``IO_REPARSE_TAG_MOUNT_POINT``), and a reparse point passed as the delete ROOT it
REFUSES with ``OSError`` ("Cannot call rmtree on a symbolic link"), leaving the
link in place. So no data is destroyed on 3.11; the residual gaps are (a) reset
hands every target to deletion AS A ROOT, so a target that is itself a
junction/symlink errors and lingers (with a misleading message) instead of being
cleanly removed, and (b) the protection would otherwise ride entirely on a stdlib
behavior that DID change across versions.

``scoped_rmtree`` makes the handling EXPLICIT, UNIFORM, and version-independent: a
reparse point — at the root OR any descendant — is UNLINKED and its target left
untouched, while the rest of the tree is still deleted. It mirrors
``shutil.rmtree``'s ``onerror(func, path, exc_info)`` callback exactly, so the
existing ResetWorker reporting (a file held open in Excel is surfaced, never
silently skipped) is unchanged.

Stdlib only; console-free (it raises / reports through `onerror`, never prints).
The reparse-point check is Windows-aware but harmless elsewhere:
``st_file_attributes`` is absent on POSIX, so nothing there is mistaken for a
reparse point, while a POSIX symlink is still caught via its lstat mode.
"""
import os
import stat
import sys


def is_reparse_point(path):
    """True iff `path` is a Windows reparse point (junction OR symlink) or a POSIX
    symlink — an entry a recursive delete must NOT descend through. Never raises;
    a missing / unstatable path is simply "not a reparse point"."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    # Windows: a junction AND a symlink both set FILE_ATTRIBUTE_REPARSE_POINT;
    # os.path.islink() catches only the symlink, so check the attribute directly.
    attrs = getattr(st, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if reparse_flag and (attrs & reparse_flag):
        return True
    # POSIX symlinks (and, redundantly, Windows symlinks) by lstat mode.
    return stat.S_ISLNK(st.st_mode)


def _unlink_reparse_point(path, onerror):
    """Remove a reparse point WITHOUT touching its target: a directory junction or
    dir-symlink is dropped with ``os.rmdir`` (which unlinks the reparse point, not
    the target's contents), a file symlink with ``os.unlink``. A failure is routed
    to `onerror`, matching ``shutil.rmtree``."""
    try:
        os.rmdir(path)                       # directory junction / dir-symlink
        return
    except OSError:
        pass
    try:
        os.unlink(path)                      # file symlink
    except OSError:
        onerror(os.unlink, path, sys.exc_info())


def _reraise_first(_func, _path, exc_info):
    raise exc_info[1]


def scoped_rmtree(root, onerror=None):
    """Delete `root` and everything beneath it, but NEVER recurse through a
    junction or symlink: a reparse point — at the root or any descendant — is
    unlinked and its target left intact. `onerror(func, path, exc_info)` is invoked
    for every failure (default: re-raise the first), exactly like
    ``shutil.rmtree(onerror=...)``, so callers keep their existing reporting."""
    if onerror is None:
        onerror = _reraise_first
    root = os.fspath(root)

    # A reparse point AT THE ROOT: remove only the link, never its target.
    if is_reparse_point(root):
        _unlink_reparse_point(root, onerror)
        return

    try:
        entries = list(os.scandir(root))
    except OSError:
        onerror(os.scandir, root, sys.exc_info())
        return

    for entry in entries:
        path = entry.path
        if is_reparse_point(path):
            _unlink_reparse_point(path, onerror)   # junction/symlink child: drop the link only
            continue
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
            is_dir = False
        if is_dir:
            scoped_rmtree(path, onerror)
        else:
            try:
                os.unlink(path)
            except OSError:
                onerror(os.unlink, path, sys.exc_info())

    try:
        os.rmdir(root)
    except OSError:
        onerror(os.rmdir, root, sys.exc_info())
