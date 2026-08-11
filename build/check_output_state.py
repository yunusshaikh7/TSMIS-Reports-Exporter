"""Regression checks for organized generated-artifact state.

Run from the repository root:
    build\\.venv\\Scripts\\python.exe build\\check_output_state.py
"""
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import output_state as state  # noqa: E402


_failures = []


def check(label, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {label}")
    if not condition:
        _failures.append(label)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def main():
    print("path helpers and exact filename ownership:")
    artifact = Path("generated") / "report.xlsx"
    check("artifact state is grouped under one _state directory",
          state.artifact_state_file(artifact, ".outcome.json")
          == Path("generated") / "_state" / "report.xlsx.outcome.json")
    check("the legacy helper preserves the former sibling path",
          state.legacy_artifact_state_file(artifact, ".outcome.json")
          == Path("generated") / "report.xlsx.outcome.json")

    payload_name = (
        ".cmpv3-" + "a" * 16 + "-000000-" + "b" * 16
        + ".comparison-payload.zlib")
    recognized = {
        "report.xlsx.outcome.json": b"outcome",
        "report.xlsx.outcome.json.tmp": b"sentinel",
        "report.xlsx.provenance.json": b"provenance",
        "report.xlsx.provenance.json.tmp": b"provenance-temp",
        "report.xlsx.fingerprint.json": b"fingerprint",
        "report.xlsx.fingerprint.json.tmp-token": b"fingerprint-temp",
        "report (evidence).json": b"evidence",
        "_results.json": b"results",
        "_tsn_results.json": b"tsn-results",
        "_attempts.json": b"attempts",
        ".tsmis-comparison-publication.lock": b"",
        ".cmpmeta.tmp-token": b"metadata-temp",
        ".cmpv3-payload.tmp-token": b"payload-temp",
        payload_name: b"payload",
    }
    untouched = {
        "site-capture.json": b"diagnostic input",
        "notes.lock": b"user file",
        "raw.zlib": b"user data",
        ".tsmis-owned.json": b"deletion authority",
        ".gitkeep": b"",
        "report.xlsx": b"workbook",
    }
    check("every app-owned state pattern is recognized",
          all(state.is_legacy_state_name(name) for name in recognized))
    check("arbitrary JSON/zlib/lock and ownership files are not claimed",
          not any(state.is_legacy_state_name(name) for name in untouched))

    with tempfile.TemporaryDirectory(prefix="tsmis_output_state_") as raw:
        root = Path(raw) / "output"
        root.mkdir()
        for name, data in {**recognized, **untouched}.items():
            _write(root / name, data)
        nested = root / "nested"
        nested.mkdir()
        nested_name = "nested.xlsx.outcome.json"
        _write(nested / nested_name, b"nested")

        legacy = root / "report.xlsx.outcome.json"
        preferred = root / "_state" / legacy.name
        check("legacy reads work before migration",
              state.read_path(preferred, legacy) == legacy)

        result = state.organize_tree(root)
        moved = len(recognized) + 1
        check("all recognized state files migrate without loss",
              result == {
                  "organized": moved,
                  "already": 0,
                  "retained": 0,
                  "directories": 2,
              })
        check("every migrated root file has identical bytes in _state",
              all(not (root / name).exists()
                  and (root / "_state" / name).read_bytes() == data
                  for name, data in recognized.items()))
        check("nested generation state is organized independently",
              not (nested / nested_name).exists()
              and (nested / "_state" / nested_name).read_bytes() == b"nested")
        check("deliverables, arbitrary diagnostics, and deletion authority stay put",
              all((root / name).read_bytes() == data
                  for name, data in untouched.items()))
        check("readers prefer organized state after migration",
              state.read_path(preferred, legacy) == preferred)
        check("organizing an already-clean tree is an idempotent no-op",
              state.organize_tree(root)
              == {"organized": 0, "already": 0, "retained": 0, "directories": 0})

        identical = root / "identical"
        identical.mkdir()
        identical_name = "same.xlsx.outcome.json"
        _write(identical / identical_name, b"same")
        _write(identical / "_state" / identical_name, b"same")
        same_result = state.organize_tree(identical)
        check("an identical pre-existing destination removes only the duplicate legacy file",
              same_result["already"] == 1
              and same_result["retained"] == 0
              and not (identical / identical_name).exists()
              and (identical / "_state" / identical_name).read_bytes() == b"same")

        conflict = root / "conflict"
        conflict.mkdir()
        conflict_name = "conflict.xlsx.outcome.json"
        _write(conflict / conflict_name, b"legacy")
        _write(conflict / "_state" / conflict_name, b"organized")
        conflict_result = state.organize_tree(conflict)
        check("a conflicting destination is never replaced or deleted",
              conflict_result["retained"] == 1
              and (conflict / conflict_name).read_bytes() == b"legacy"
              and (conflict / "_state" / conflict_name).read_bytes() == b"organized")
        check("a present organized entry remains authoritative during a conflict",
              state.named_read_file(conflict, conflict_name)
              == conflict / "_state" / conflict_name)

        blocked = root / "blocked"
        blocked.mkdir()
        _write(blocked / "_state", b"not a directory")
        check("a non-directory _state entry is refused",
              state.ensure_state_dir(blocked) is None)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} output-state check(s)")
        return 1
    print("ALL OUTPUT-STATE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
