"""Golden check for the destination-ownership marker (M03; scripts/owned_dir.py).

The Export-Everything store's ``<src>-<env>`` folders and its ``comparisons`` tree
are directories the app creates inside a USER-CHOSEN destination. They were trusted
by NAME alone, so a user folder named, say, ``ssor-prod`` under the same
destination looked app-created. ``owned_dir`` stamps a marker into each directory
the app creates there; ``reset_targets`` now prefers that marker (proving the app
created the dir, whatever its name) and keeps the legacy known-NAME trust only as a
backward-compat fallback for dirs created before the marker existed.

This proves the marker round-trips (and rejects foreign/corrupt markers) and, via a
real ``reset_targets`` run over a temp store, that a MARKED dir with a non-known
NAME is included for deletion (the marker is the deciding factor — not inert) while
an unmarked foreign dir is left untouched.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_owned_dir.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import owned_dir

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def marker_checks():
    print("mark_owned / is_owned / ensure_owned_dir:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_"))
    try:
        d = tmp / "d"
        d.mkdir()
        check("unmarked dir -> is_owned False", not owned_dir.is_owned(d))
        check("mark_owned returns True", owned_dir.mark_owned(d, kind="store") is True)
        check("marked dir -> is_owned True", owned_dir.is_owned(d))
        check("marker records the kind",
              json.loads((d / owned_dir.OWNER_MARKER).read_text(encoding="utf-8"))
              .get("kind") == "store")

        # foreign marker (another app) -> not owned
        foreign = tmp / "foreign"
        foreign.mkdir()
        (foreign / owned_dir.OWNER_MARKER).write_text(
            json.dumps({"app": "Some Other Tool"}), encoding="utf-8")
        check("foreign marker -> is_owned False", not owned_dir.is_owned(foreign))

        # corrupt marker -> not owned (never raises)
        corrupt = tmp / "corrupt"
        corrupt.mkdir()
        (corrupt / owned_dir.OWNER_MARKER).write_text("not json", encoding="utf-8")
        check("corrupt marker -> is_owned False", not owned_dir.is_owned(corrupt))

        # missing path -> False, never raises
        check("missing path -> is_owned False (never raises)",
              not owned_dir.is_owned(tmp / "nope"))

        # ensure_owned_dir creates + marks
        made = owned_dir.ensure_owned_dir(tmp / "made" / "deep", kind="comparisons")
        check("ensure_owned_dir created the directory", made.is_dir())
        check("ensure_owned_dir stamped it owned", owned_dir.is_owned(made))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def reset_targets_integration():
    print("reset_targets honors the marker (integration):")
    import settings
    import gui_worker

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_owned_reset_"))
    store = tmp / "store"
    store.mkdir()
    (store / "ssor-prod").mkdir()                       # known name, UNMARKED -> legacy include
    owned_dir.ensure_owned_dir(store / "my-custom-export")  # MARKED, non-known name -> marker include
    (store / "user-data").mkdir()                       # UNMARKED foreign -> exclude
    (store / "comparisons").mkdir()                     # name -> include

    saved = settings.get_batch_dest
    settings.get_batch_dest = lambda: str(store)
    try:
        targets = gui_worker.reset_targets()
    finally:
        settings.get_batch_dest = saved
        shutil.rmtree(tmp, ignore_errors=True)

    store_names = {lbl.split(": ", 1)[1] for lbl, _p in targets
                   if lbl.startswith("Export Everything store:")}
    check("known-named UNMARKED dir EXCLUDED (SEC-02: the marker is required; "
          "the legacy name fallback is retired)",
          "ssor-prod" not in store_names)
    check("MARKED non-known-named dir included (marker is the deciding factor)",
          "my-custom-export" in store_names)
    check("UNMARKED 'comparisons' excluded too (marker required)",
          "comparisons" not in store_names)
    check("UNMARKED foreign dir NOT included (user data preserved)",
          "user-data" not in store_names)


def main():
    print("Destination-ownership marker (M03):")
    marker_checks()
    reset_targets_integration()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL OWNED-DIR CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
