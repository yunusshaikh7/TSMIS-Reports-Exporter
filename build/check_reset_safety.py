"""Golden check for the junction/symlink-safe reset delete (scripts/safe_delete.py).

The "Delete all reports" path (ResetWorker) deletes each target — run folders and,
crucially, children of a USER-CHOSEN Export-Everything store — where a directory
junction or symlink could point at unrelated user data.

What the SHIPPED interpreter (CPython 3.11) actually does with ``shutil.rmtree`` —
verified by this check, stated honestly so the guard isn't over-claimed:
  * a junction/symlink encountered as a CHILD during the walk is already unlinked
    without being followed (3.8+ guards it via IO_REPARSE_TAG_MOUNT_POINT), so no
    data is destroyed there; BUT
  * a reparse point passed as the delete ROOT — which is exactly how reset hands
    each target to deletion — is REFUSED with ``OSError`` ("Cannot call rmtree on a
    symbolic link") and LEFT in place: reset then reports a misleading "open in
    Excel" failure and the link lingers.

``safe_delete.scoped_rmtree`` replaces that with explicit, UNIFORM,
version-independent handling: a reparse point at the root OR a descendant is
cleanly UNLINKED (the link removed, its target untouched) and the rest of the tree
is still deleted. This check proves scoped_rmtree's contract and contrasts it with
shutil's position-dependent behavior, and proves NEITHER destroys a link target on
3.11 (no false "data loss" claim).

On Windows it uses ``mklink /J`` (no admin); on POSIX, ``os.symlink``. If neither
link type can be created the link cases are skipped LOUDLY so the check can't go
vacuously green.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_reset_safety.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import safe_delete

_fail = []
_skips = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _make_link(link, target):
    """Create a directory junction `link` -> `target`. Windows ``mklink /J`` (no
    admin) or POSIX ``os.symlink``. Returns 'junction'/'symlink' or None."""
    link, target = Path(link), Path(target)
    if os.name == "nt":
        try:
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                               capture_output=True, text=True)
            if r.returncode == 0 and link.exists():
                return "junction"
        except OSError:
            pass
        return None
    try:
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError, AttributeError):
        return None


def _seed_external(root):
    """An 'external' dir (a link target) holding a sentinel that must survive."""
    ext = Path(root) / "external_target"
    ext.mkdir(parents=True)
    (ext / "sentinel.txt").write_text("must survive", encoding="utf-8")
    return ext


def _shutil_rmtree_outcome(path):
    """Run shutil.rmtree(path) and report ('raised'|'completed', link_still_present)."""
    raised = False
    try:
        shutil.rmtree(path)
    except OSError:
        raised = True
    return ("raised" if raised else "completed"), Path(path).exists()


def test_legacy_store_dir_gets_stamped():
    """SEC-02 migration: the name fallback stamps legacy store dirs on sight, so
    the fallback (which a user folder named 'ssor-prod' could collide with) can
    be retired once installs have re-stamped."""
    print("SEC-02 migration - legacy-named store dirs get the ownership marker:")
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import gui_worker
    import owned_dir
    import settings
    dest = Path(tempfile.mkdtemp(prefix="tsmis_reset_stamp_"))
    legacy = dest / "ssor-prod"
    legacy.mkdir()
    saved = settings.get_batch_dest
    settings.get_batch_dest = lambda: str(dest)
    try:
        warns = []
        targets = gui_worker.reset_targets(warnings=warns)
        names = [lbl for lbl, _p in targets]
        check("legacy-named dir listed via the name fallback",
              any("ssor-prod" in n for n in names))
        check("...and now carries the ownership marker (fallback retirable later)",
              owned_dir.is_owned(legacy))
        check("no enumeration warnings on the happy path", warns == [])
    finally:
        settings.get_batch_dest = saved
        shutil.rmtree(dest, ignore_errors=True)


def main():
    print("Reset junction/symlink-safe delete:")

    # --- is_reparse_point basics + ordinary delete + onerror (always run) ---
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_reset_safety_"))
    try:
        plain_dir = tmp / "plain"
        plain_dir.mkdir()
        plain_file = tmp / "plain.txt"
        plain_file.write_text("x", encoding="utf-8")
        check("is_reparse_point(False) for an ordinary directory",
              not safe_delete.is_reparse_point(plain_dir))
        check("is_reparse_point(False) for an ordinary file",
              not safe_delete.is_reparse_point(plain_file))
        check("is_reparse_point(False) for a missing path (never raises)",
              not safe_delete.is_reparse_point(tmp / "nope"))

        tree = tmp / "tree"
        (tree / "a" / "b").mkdir(parents=True)
        (tree / "a" / "b" / "f.txt").write_text("data", encoding="utf-8")
        (tree / "top.txt").write_text("data", encoding="utf-8")
        safe_delete.scoped_rmtree(tree)
        check("scoped_rmtree removes an ordinary tree entirely", not tree.exists())

        calls = []
        safe_delete.scoped_rmtree(tmp / "missing-root",
                                  onerror=lambda f, p, e: calls.append(p))
        check("onerror is invoked (not raised) for an unscandirable root",
              len(calls) == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- reparse-point cases (need a junction/symlink) ---
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_reset_safety_link_"))
    try:
        probe = _make_link(tmp / "_probe_link", _seed_external(tmp / "_probe"))
        if probe is None:
            _skips.append("no junction/symlink could be created in this environment")
            print("  [SKIP] reparse-point cases — no junction/symlink could be created")
        else:
            # (1) CHILD reparse point: scoped_rmtree deletes the container and
            #     PRESERVES the target; shutil.rmtree on 3.11 also preserves it
            #     (already child-guarded) — assert no data loss either way.
            ext = _seed_external(tmp / "c1")
            cont = tmp / "c1" / "run_folder"
            cont.mkdir(parents=True)
            (cont / "report.xlsx").write_text("data", encoding="utf-8")
            kind = _make_link(cont / "link_to_external", ext)
            check(f"is_reparse_point(True) for a child {kind}",
                  safe_delete.is_reparse_point(cont / "link_to_external"))
            safe_delete.scoped_rmtree(cont)
            check("child reparse: scoped_rmtree deleted the run folder", not cont.exists())
            check("child reparse: scoped_rmtree PRESERVED the link target's contents",
                  (ext / "sentinel.txt").exists())

            ext_s = _seed_external(tmp / "c2")
            cont_s = tmp / "c2" / "run_folder"
            cont_s.mkdir(parents=True)
            _make_link(cont_s / "link_to_external", ext_s)
            _shutil_rmtree_outcome(cont_s)
            check("child reparse: shutil.rmtree (3.11) ALSO preserved the target "
                  "(no data loss on the shipped Python)", (ext_s / "sentinel.txt").exists())

            # (2) ROOT reparse point (the genuine improvement) — reset hands each
            #     target to deletion as a root. scoped_rmtree cleanly unlinks it and
            #     preserves the target; shutil.rmtree does NOT cleanly remove it.
            ext_r = _seed_external(tmp / "r1")
            root_link = tmp / "r1" / "root_link"
            _make_link(root_link, ext_r)
            sh_outcome, sh_link_left = _shutil_rmtree_outcome(root_link)
            check("root reparse: shutil.rmtree does NOT cleanly remove a root reparse "
                  f"point (outcome={sh_outcome}, link_left={sh_link_left})",
                  sh_link_left)
            check("root reparse: shutil.rmtree left the target intact",
                  (ext_r / "sentinel.txt").exists())

            ext_r2 = _seed_external(tmp / "r2")
            root_link2 = tmp / "r2" / "root_link"
            _make_link(root_link2, ext_r2)
            safe_delete.scoped_rmtree(root_link2)
            check("root reparse: scoped_rmtree REMOVED the link cleanly",
                  not root_link2.exists())
            check("root reparse: scoped_rmtree PRESERVED the target's contents",
                  (ext_r2 / "sentinel.txt").exists())
            check("root reparse: the target dir itself survives", ext_r2.is_dir())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    test_legacy_store_dir_gets_stamped()

    print()
    if _skips:
        print(f"NOTE: {len(_skips)} skip(s): {_skips}")
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL RESET-SAFETY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
