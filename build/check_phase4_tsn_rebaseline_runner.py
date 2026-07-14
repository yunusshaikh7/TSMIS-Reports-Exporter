"""Hermetic CMP-AUD-035 phase-4 witness-runner contract.

Exercises the real ``tsn_library.build_consolidated`` and ``status`` boundaries with a
tiny catalog and builder while redirecting only their path functions.  No development
corpus, live TSN library, or PDF parser is involved.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT)]

from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook  # noqa: E402
import outcome  # noqa: E402
import run_phase4_tsn_source_rebaseline as runner  # noqa: E402
import tsn_library  # noqa: E402
import tsn_load_ramp_detail as fake_builder_module  # noqa: E402


failures = []


def check(label, condition):
    print(f"  [{'OK ' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


@contextlib.contextmanager
def patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def tree_bytes(root):
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def fake_builder(raw_dir, out_path, events=None, confirm_overwrite=None,
                 mutate_evidence=None):
    del events, confirm_overwrite
    raw_dir = Path(raw_dir)
    sources = sorted(raw_dir.glob("*.xlsx"))
    manifest = runner.raw_contract.canonical_raw_manifest(sources, raw_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Fixture"
    ws.append(["Value"])
    ws.append([sources[0].read_bytes().decode("ascii")])
    wb.save(out_path)
    wb.close()
    if mutate_evidence is not None:
        mutate_evidence.write_bytes(b"late evidence")
    result = ConsolidateResult(
        status="ok", output_path=str(out_path), completion=outcome.COMPLETE,
        skipped_inputs=0, failed_inputs=0, summary_lines=["fixture complete"])
    result.tsn_raw_manifest = manifest
    return result


def main():
    root = Path(tempfile.mkdtemp(prefix="tsmis-phase4-runner-"))
    saved_reports = tsn_library._REPORTS
    original_paths = (tsn_library.raw_dir, tsn_library.pdf_dir,
                      tsn_library.consolidated_path)
    try:
        source = root / "external-source"
        raw = source / "fixture" / "raw"
        evidence = source / "fixture" / "pdf"
        raw.mkdir(parents=True)
        evidence.mkdir(parents=True)
        (raw / "truth.xlsx").write_bytes(b"authoritative raw")
        (evidence / "proof.pdf").write_bytes(b"authoritative evidence")
        source_before = tree_bytes(source)

        spec = tsn_library.TsnReport(
            subdir="fixture", label="Fixture", raw_glob="*.xlsx",
            raw_kind="statewide_xlsx", consolidated_name="normalized.xlsx",
            builder="tsn_load_ramp_detail:build_into", normalization_version=97,
            evidence_pdfs=True)
        tsn_library._REPORTS = {"fixture": spec}
        output = root / "isolated-output"
        result_path = root / "accepted" / "result.json"

        def good_builder(*args, **kwargs):
            return fake_builder(*args, **kwargs)

        with patch(fake_builder_module, "build_into", good_builder):
            payload = runner.run(source, output)
        check("external raw/evidence tree is byte-for-byte unchanged",
              tree_bytes(source) == source_before)
        check("temporary library path redirection is restored",
              (tsn_library.raw_dir, tsn_library.pdf_dir,
               tsn_library.consolidated_path) == original_paths)
        family = payload["families"][0]
        check("real library force-build is complete and builder-certified",
              family["result"]["status"] == "ok"
              and family["result"]["completion"] == "complete"
              and family["result"]["skipped_inputs"] == 0
              and family["result"]["failed_inputs"] == 0
              and family["builder_certificate_matches"])
        check("status is current and immediate non-force call is certified reuse",
              family["status_after_build"]["current"]
              and family["reuse"]["certified"]
              and family["reuse"]["status"]["current"]
              and family["reuse"]["output_unchanged"]
              and family["reuse"]["sidecar_unchanged"])
        out = output / "fixture" / "consolidated" / "normalized.xlsx"
        sidecar = Path(str(out) + ".outcome.json")
        check("workbook and certification sidecar are confined to isolated output",
              out.is_file() and sidecar.is_file()
              and Path(family["output"]["relative_path"]) ==
                  Path("fixture/consolidated/normalized.xlsx")
              and payload["generated_output_artifact_universe_exact"]
              and payload["generated_output_artifact_manifest"]["member_count"] == 2)
        check("global raw/evidence manifests are exact and stable",
              payload["source_universe_stable"]
              and payload["core_raw_manifest"] == payload["core_raw_manifest_after"]
              and payload["optional_evidence_manifest"] ==
                  payload["optional_evidence_manifest_after"]
              and payload["core_raw_manifest"]["member_count"] == 1
              and payload["optional_evidence_manifest"]["member_count"] == 1)
        provenance_paths = {
            item["relative_path"]
            for item in payload["code_provenance_manifest"]["members"]
        }
        check("code provenance binds runner and required shared boundaries",
              "build/run_phase4_tsn_source_rebaseline.py" in provenance_paths
              and "scripts/tsn_library.py" in provenance_paths
              and "scripts/tsn_district_contract.py" in provenance_paths
              and "scripts/consolidation_meta.py" in provenance_paths
              and "scripts/artifact_store.py" in provenance_paths
              and "scripts/report_catalog.py" in provenance_paths
              and "scripts/tsn_load_ramp_detail.py" in provenance_paths
              and "scripts/compare_ramp_detail_tsn.py" in provenance_paths
              and "scripts/compare_tsn_common.py" in provenance_paths
              and payload["code_provenance_stable"]
              and payload["code_provenance_manifest"] ==
                  payload["code_provenance_manifest_after"])

        runner.write_result_atomic(result_path, payload)
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
        check("complete witness result is published atomically",
              loaded == payload and not list(result_path.parent.glob("*.tmp-*")))
        prior = result_path.read_bytes()
        rejected = dict(payload)
        rejected["acceptance"] = "partial"
        try:
            runner.write_result_atomic(result_path, rejected)
            refused = False
        except ValueError:
            refused = True
        check("partial payload is refused without replacing accepted result",
              refused and result_path.read_bytes() == prior)
        raw_result = source / "must-not-write-result.json"
        try:
            runner.write_result_atomic(raw_result, payload)
            source_refused = False
        except ValueError:
            source_refused = True
        check("result publication cannot write into external source tree",
              source_refused and not raw_result.exists())

        # Evidence is in the registered universe but not consumed by this builder.
        # Mutating it after the family succeeds must still invalidate the attempt.
        late_source = root / "late-source"
        shutil.copytree(source, late_source)
        late_output = root / "late-output"
        late_member = late_source / "fixture" / "pdf" / "late.pdf"

        def late_builder(*args, **kwargs):
            return fake_builder(*args, **kwargs, mutate_evidence=late_member)

        with patch(fake_builder_module, "build_into", late_builder):
            try:
                runner.run(late_source, late_output)
                late_rejected = False
            except RuntimeError as exc:
                late_rejected = "universe changed" in str(exc)
        check("late registered evidence addition invalidates whole witness",
              late_rejected)

        print()
        if failures:
            print(f"FAILED: {len(failures)} check(s): {failures}")
            return 1
        print("ALL PHASE-4 TSN REBASELINE RUNNER CHECKS PASSED")
        return 0
    finally:
        tsn_library._REPORTS = saved_reports
        (tsn_library.raw_dir, tsn_library.pdf_dir,
         tsn_library.consolidated_path) = original_paths
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
