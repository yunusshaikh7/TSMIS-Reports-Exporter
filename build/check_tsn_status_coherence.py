"""Adversarial TSN status/reuse checks for one coherent complete generation.

Locks two fail-closed properties of the canonical comparison ground truth:

* a possible green status is revalidated against the exact same sidecar
  payload, raw universe/content manifest, and normalized workbook content;
  persistent replacements injected immediately after each initial component
  read stay stale even when their mtimes are restored;
* an identity-valid producer PARTIAL (or nonzero skipped/failed count) remains
  partial and is never reused as synthesized COMPLETE.  Non-force build and
  ensure_current both rebuild it while resolve preserves the diagnostic before
  that rebuild.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsn_status_coherence.py
"""
import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import consolidation_meta  # noqa: E402
import outcome  # noqa: E402
import tsn_library  # noqa: E402
from events import ConsolidateResult  # noqa: E402
from gui_matrix import GuiMatrixMixin  # noqa: E402
from openpyxl import Workbook  # noqa: E402


REPORT = "ramp_detail"  # real exact-one statewide XLSX registration
_fail = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


def _workbook(path, marker):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.active.title = "normalized"
    wb.active.append(["marker"])
    wb.active.append([marker])
    wb.save(path)


def _replace_bytes_preserving_mtime(path, data):
    path = Path(path)
    before = path.stat()
    swap = path.with_name(path.name + ".coherence-swap")
    swap.write_bytes(data)
    os.replace(swap, path)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))


def _replace_json_preserving_mtime(path, payload):
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    _replace_bytes_preserving_mtime(path, encoded)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_tsn_coherent_"))
    rawd = tmp / "raw"
    cons = tmp / "consolidated" / "tsn_ramp_detail_normalized.xlsx"
    raw = rawd / "TSN export.xlsx"
    alt_raw = tmp / "alternate-raw.xlsx"
    alt_cons = tmp / "alternate-normalized.xlsx"
    saved_raw_dir = tsn_library.raw_dir
    saved_cons_path = tsn_library.consolidated_path
    saved_import_module = tsn_library.importlib.import_module
    builds = []

    def build_into(_raw_dir, out_path, events=None, confirm_overwrite=None):
        del events, confirm_overwrite
        builds.append(len(builds) + 1)
        _workbook(out_path, f"certified build {len(builds)}")
        result = ConsolidateResult(
            status="ok", message="stub built", output_path=str(out_path),
            completion=outcome.COMPLETE, skipped_inputs=0, failed_inputs=0)
        result.tsn_raw_manifest = tsn_library._raw_manifest(REPORT)
        return result

    tsn_library.raw_dir = lambda _report: rawd
    tsn_library.consolidated_path = lambda _report: cons
    tsn_library.importlib = types.SimpleNamespace(
        import_module=lambda _name: types.SimpleNamespace(build_into=build_into))
    try:
        rawd.mkdir(parents=True)
        _workbook(raw, "authoritative raw A")
        _workbook(alt_raw, "authoritative raw B")
        _workbook(alt_cons, "unrelated normalized bytes")
        raw_a_bytes = raw.read_bytes()
        raw_b_bytes = alt_raw.read_bytes()

        clean = tsn_library.build_consolidated(REPORT, force=True)
        clean_status = tsn_library.status(REPORT)
        check("fixture starts as one coherent COMPLETE generation",
              clean.status == "ok" and clean_status["current"] is True
              and clean_status["producer_complete"] is True
              and clean_status["coherent_snapshot_current"] is True,
              repr(clean_status))

        # Persistent raw replacement after either the initial manifest read or
        # the first revalidation read.  Its mtime is restored, so content
        # revalidation (not freshness timestamps) must withdraw green.
        original_raw_manifest = tsn_library._raw_manifest
        for target_call in (1, 2):
            raw_calls = []
            replacement = (raw_b_bytes if raw.read_bytes() == raw_a_bytes
                           else raw_a_bytes)

            def mutate_raw(report, raws=None, target=target_call,
                           replacement_bytes=replacement):
                value = original_raw_manifest(report, raws)
                raw_calls.append(1)
                if len(raw_calls) == target:
                    _replace_bytes_preserving_mtime(raw, replacement_bytes)
                return value

            tsn_library._raw_manifest = mutate_raw
            try:
                raw_drift = tsn_library.status(REPORT)
            finally:
                tsn_library._raw_manifest = original_raw_manifest
            check(f"raw mutation after manifest read {target_call} cannot produce current",
                  raw_drift["current"] is False
                  and raw_drift["coherent_snapshot_current"] is False
                  and raw_drift["raw_manifest_current"] is False
                  and raw_drift["identity_token"] is None
                  and len(raw_calls) >= target_call + 1,
                  repr(raw_drift))
            assert tsn_library.build_consolidated(REPORT, force=True).status == "ok"

        # Replace the normalized path after either its initial identity read or
        # first revalidation identity read, preserving its certified mtime.
        original_identity = tsn_library.normalized_workbook_identity
        alt_cons_bytes = alt_cons.read_bytes()
        for target_call in (1, 2):
            workbook_calls = []

            def mutate_workbook(path, target=target_call):
                value = original_identity(path)
                if Path(path).absolute() == cons.absolute():
                    workbook_calls.append(1)
                    if len(workbook_calls) == target:
                        _replace_bytes_preserving_mtime(cons, alt_cons_bytes)
                return value

            tsn_library.normalized_workbook_identity = mutate_workbook
            try:
                workbook_drift = tsn_library.status(REPORT)
            finally:
                tsn_library.normalized_workbook_identity = original_identity
            check(f"workbook mutation after identity read {target_call} cannot produce current",
                  workbook_drift["current"] is False
                  and workbook_drift["coherent_snapshot_current"] is False
                  and workbook_drift["normalized_workbook_current"] is False
                  and workbook_drift["identity_token"] is None
                  and len(workbook_calls) >= target_call + 1,
                  repr(workbook_drift))
            assert tsn_library.build_consolidated(REPORT, force=True).status == "ok"

        # Atomically change only the sidecar payload after either its initial
        # bound read or first revalidation read.  The extra field leaves every
        # provenance claim individually valid; exact payload revalidation must
        # still catch it.
        original_sidecar = tsn_library._bound_sidecar_payload
        sidecar = consolidation_meta.meta_path(cons)
        for target_call in (1, 2):
            sidecar_calls = []

            def mutate_sidecar(path, target=target_call):
                value = original_sidecar(path)
                if Path(path).absolute() == Path(sidecar).absolute():
                    sidecar_calls.append(1)
                    if len(sidecar_calls) == target:
                        changed = dict(value)
                        changed["coherence_probe"] = f"replacement after read {target}"
                        _replace_json_preserving_mtime(sidecar, changed)
                return value

            tsn_library._bound_sidecar_payload = mutate_sidecar
            try:
                sidecar_drift = tsn_library.status(REPORT)
            finally:
                tsn_library._bound_sidecar_payload = original_sidecar
            check(f"sidecar mutation after payload read {target_call} cannot produce current",
                  sidecar_drift["current"] is False
                  and sidecar_drift["coherent_snapshot_current"] is False
                  and sidecar_drift["metadata_current"] is False
                  and sidecar_drift["producer_complete"] is False
                  and sidecar_drift["normalization_current"] is False
                  and sidecar_drift["identity_token_current"] is False
                  and sidecar_drift["identity_token"] is None
                  and len(sidecar_calls) >= target_call + 1,
                  repr(sidecar_drift))
            assert tsn_library.build_consolidated(REPORT, force=True).status == "ok"

        # Establish a fresh complete sidecar, then retain all identity fields
        # while changing only the producer outcome to a valid PARTIAL.

        # Even the literal COMPLETE vocabulary cannot override nonzero omitted
        # or failed input counts.  The generic sidecar reader conservatively
        # diagnoses these inconsistent payloads as partial; TSN status must also
        # withdraw current and non-force reuse must rebuild them.
        for count_field in ("skipped_inputs", "failed_inputs"):
            payload = original_sidecar(sidecar)
            payload["completion"] = outcome.COMPLETE
            payload["skipped_inputs"] = 0
            payload["failed_inputs"] = 0
            payload[count_field] = 1
            _replace_json_preserving_mtime(sidecar, payload)
            counted_status = tsn_library.status(REPORT)
            counted_source = tsn_library.resolve(REPORT)
            before = len(builds)
            counted_rebuild = tsn_library.build_consolidated(REPORT)
            check(f"COMPLETE plus nonzero {count_field} is stale and rebuilt",
                  counted_status["current"] is False
                  and counted_status["producer_complete"] is False
                  and counted_source.get("completion") == outcome.PARTIAL
                  and counted_rebuild.status == "ok"
                  and len(builds) == before + 1,
                  repr(counted_status))

        def mark_partial():
            payload = original_sidecar(sidecar)
            payload["completion"] = outcome.PARTIAL
            payload["skipped_inputs"] = 1
            payload["failed_inputs"] = 0
            _replace_json_preserving_mtime(sidecar, payload)

        mark_partial()
        partial_status = tsn_library.status(REPORT)
        partial_source = tsn_library.resolve(REPORT)
        check("identity-bound PARTIAL is never current/green",
              partial_status["metadata_current"] is True
              and partial_status["normalization_current"] is True
              and partial_status["raw_manifest_current"] is True
              and partial_status["normalized_workbook_current"] is True
              and partial_status["producer_complete"] is False
              and partial_status["current"] is False,
              repr(partial_status))
        check("resolve preserves persisted PARTIAL diagnostic before rebuild",
              partial_source.get("kind") == "consolidated"
              and partial_source.get("completion") == outcome.PARTIAL
              and partial_source.get("identity_token") is None,
              repr(partial_source))
        original_all_status = tsn_library.all_status
        tsn_library.all_status = lambda: [partial_status]
        try:
            settings_rows = GuiMatrixMixin()._tsn_library_status()
        finally:
            tsn_library.all_status = original_all_status
        check("Settings-facing status exposes PARTIAL artifact as not current",
              len(settings_rows) == 1
              and settings_rows[0].get("report") == REPORT
              and settings_rows[0].get("current") is False,
              repr(settings_rows))

        before = len(builds)
        rebuilt = tsn_library.build_consolidated(REPORT)
        check("non-force build rebuilds PARTIAL instead of synthesizing reuse",
              rebuilt.status == "ok" and len(builds) == before + 1
              and "reused" not in (rebuilt.message or "").lower()
              and tsn_library.status(REPORT)["current"] is True,
              repr(rebuilt))

        mark_partial()
        before = len(builds)
        healed = tsn_library.ensure_current(REPORT)
        healed_source = tsn_library.resolve(REPORT)
        check("ensure_current rebuilds admissible identity-bound PARTIAL",
              healed is not None and healed.status == "ok"
              and len(builds) == before + 1
              and tsn_library.status(REPORT)["current"] is True,
              repr(healed))
        check("resolve reports COMPLETE only after the successful rebuild",
              healed_source.get("completion") == outcome.COMPLETE
              and isinstance(healed_source.get("identity_token"), str),
              repr(healed_source))
    finally:
        tsn_library.raw_dir = saved_raw_dir
        tsn_library.consolidated_path = saved_cons_path
        import importlib as real_importlib
        tsn_library.importlib = real_importlib
        # Keep this reference-use explicit: the test replaced only the module's
        # import surface and did not mutate Python's global import system.
        assert saved_import_module is not None
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print("TSN coherent status + complete-only reuse:")
    main()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")
