"""Adversarial CMP-AUD-035 canonical TSN consumer-identity checks.

Locks the end of the TSN freshness chain: comparison/evidence publication,
Everything/by-day cache truth, and both on-demand evidence entry points all bind
the exact canonical or explicit TSN generation instead of path/mtime alone.
"""
import contextlib
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

from openpyxl import Workbook  # noqa: E402

import consolidation_meta  # noqa: E402
import day_matrix  # noqa: E402
import matrix  # noqa: E402
import matrix_build  # noqa: E402
import outcome  # noqa: E402
import tsn_library  # noqa: E402
from comparison_contract import (ArtifactGeneration, AttemptState,
                                 ComparisonCounts, ComparisonOutcome)  # noqa: E402
from events import ConsolidateResult, Events  # noqa: E402


_fail = []


def check(name, condition, detail=""):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        if detail:
            print(f"       {detail}")
        _fail.append(name)


@contextlib.contextmanager
def patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def _certify(report, workbook):
    manifest = tsn_library._raw_manifest(report)
    identity = tsn_library.normalized_workbook_identity(workbook)
    token = tsn_library.canonical_normalized_identity_token(
        report, manifest, identity)
    result = ConsolidateResult(
        status="ok", output_path=str(workbook), completion=outcome.COMPLETE,
        skipped_inputs=0, failed_inputs=0)
    assert consolidation_meta.write_outcome(
        workbook, result, extra={
            "tsn_normalization_version": tsn_library.get(
                report).normalization_version,
            "tsn_raw_manifest": manifest,
            "tsn_normalized_workbook_identity": identity,
            "tsn_artifact_identity_token": token,
        })
    return token


def _publish_comparison(path, generation_id="consumer-identity-fixture"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"comparison")
    st = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    member = {
        "flavor": "values", "relative_path": path.name, "path": str(path),
        "canonical_path_at_write": str(path.resolve()),
        "commit_role": "canonical", "sha256": digest,
        "size": st.st_size, "mtime_ns": st.st_mtime_ns,
    }
    typed = ComparisonOutcome(
        status="ok", completion=outcome.COMPLETE, verdict="match",
        counts=ComparisonCounts(known=True, paired_rows=1),
        pairing_quality="exact")
    generation = ArtifactGeneration(
        generation_id=generation_id, members=(member,),
        content_digests={"values": digest}, completion=outcome.COMPLETE,
        publication_state="committed", requested_mode="values")
    result = ConsolidateResult(
        status="ok", output_path=str(path), completion=outcome.COMPLETE,
        comparison_outcome=typed, artifact_generation=generation,
        attempt_state=AttemptState(
            state="succeeded", generation_id=generation_id))
    assert consolidation_meta.write_comparison_outcomes(result)
    return result


def test_publication_and_cache_identity():
    print("canonical raw/normalized drift blocks publication and invalidates cache:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_tsn_consumer_identity_"))
    try:
        report = "ramp_detail"
        with patch(tsn_library.paths, "TSN_LIBRARY_ROOT", root / "library"):
            raw_dir = tsn_library.raw_dir(report)
            raw_dir.mkdir(parents=True)
            raw = raw_dir / "source.xlsx"
            raw.write_bytes(b"raw-A")
            os.utime(raw, (1000.0, 1000.0))
            normalized = tsn_library.consolidated_path(report)
            normalized.parent.mkdir(parents=True)
            normalized.write_bytes(b"normalized-A")
            os.utime(normalized, (9000.0, 9000.0))
            expected_workbook_identity = tsn_library.normalized_workbook_identity(
                normalized)
            token = _certify(report, normalized)
            source = tsn_library.resolve(report)
            captured, current = matrix.tsn_identity_check_for(report, source)
            check("current canonical resolve exposes the certified token",
                  captured == token and current())

            target_calls = []

            def target_guard(path=None, **binding):
                target_calls.append((Path(path) if path is not None else None,
                                     binding))
                return True

            combined = matrix._compose_source_guard(target_guard, current)
            probe = root / "comparison.xlsx"
            check("composed guard preserves target-aware keyword bindings",
                  combined(probe, anchor_path=probe, anchor_identity={"x": 1})
                  and target_calls[-1][1].get("anchor_identity") == {"x": 1})

            legacy_calls = []

            def legacy_path_only_guard(path):
                legacy_calls.append(Path(path))
                return True

            legacy_combined = matrix._compose_source_guard(
                legacy_path_only_guard, current)
            check("legacy path-only target guard still works without a binding",
                  legacy_combined(probe) and legacy_calls == [probe])
            legacy_calls.clear()
            check("legacy path-only guard cannot discard anchor/directory bindings",
                  not legacy_combined(
                      probe, anchor_path=probe, anchor_identity={"x": 1},
                      directory_identity={"y": 2})
                  and not legacy_calls)

            old_raw_mtime = raw.stat().st_mtime
            raw.write_bytes(b"raw-B")
            os.utime(raw, (old_raw_mtime, old_raw_mtime))
            check("preserved-mtime raw replacement denies the publication guard",
                  not combined(probe))

            # The shared comparison boundary must also refuse the output when the
            # raw changes after its initial pre-check but before comparator commit.
            raw.write_bytes(b"raw-A")
            os.utime(raw, (old_raw_mtime, old_raw_mtime))
            check("restoring exact raw bytes restores the captured generation",
                  current())
            store = root / "store"
            persistent = matrix.consolidated_store_path(store, "ramp_summary")
            persistent.parent.mkdir(parents=True)
            persistent.write_bytes(b"tsmis")
            attempted = root / "must-not-publish.xlsx"

            # Synchronized A->B->A interposition: the comparator receives the
            # private A capture even while the live canonical pathname is B.
            interposed = root / "capture-comparison.xlsx"
            capture_seen = {"paths": []}
            import visual_evidence
            decoration_seen = {}

            class InterpositionComparator:
                @staticmethod
                def compare(_a, captured_path, out_path, **kwargs):
                    capture_seen["paths"].append(Path(captured_path))
                    live_mtime = normalized.stat().st_mtime
                    normalized.write_bytes(b"normalized-B")
                    os.utime(normalized, (live_mtime, live_mtime))
                    capture_seen["path"] = Path(captured_path)
                    capture_seen["bytes"] = Path(captured_path).read_bytes()
                    normalized.write_bytes(b"normalized-A")
                    os.utime(normalized, (live_mtime, live_mtime))
                    assert kwargs["commit_guard"](Path(out_path))
                    return _publish_comparison(
                        Path(out_path), generation_id="capture-sidecar")

            def decoration_capture(*args, **_kwargs):
                decoration_seen["path"] = Path(args[2])
                decoration_seen["bytes"] = Path(args[2]).read_bytes()
                return {"note": "same capture"}

            with patch(matrix, "_consolidated_stale", lambda *_a, **_k: False), \
                    patch(matrix, "tsn_comparator_for",
                          lambda _row: InterpositionComparator), \
                    patch(visual_evidence, "generate", decoration_capture):
                captured_result = matrix.consolidate_and_compare_tsn(
                    store, normalized, interposed, "ramp_summary", "ramp_summary",
                    Events(), also_formulas=True,
                    evidence_opts={"tsmis_pdf_dir": root / "pdfs", "examples": 1},
                    source_identity_check=current,
                    source_workbook_identity=expected_workbook_identity)
            capture_record = consolidation_meta.read_comparison_outcome(interposed)
            capture_sidecar_text = consolidation_meta.meta_path(
                interposed).read_text(encoding="utf-8")
            cache_root = root / "cache-root"
            matrix.record_tsn_result(
                cache_root, "ramp_summary|tsn", "ars-prod", "match", 0, 0,
                interposed.stat().st_mtime, completion=outcome.COMPLETE,
                source_identities={"tsn": token},
                generation_id="capture-sidecar")
            cache_text = matrix._tsn_results_path(cache_root).read_text(
                encoding="utf-8")
            check("comparator consumes immutable A during live B->A interposition",
                  captured_result.status == "ok"
                  and capture_seen.get("bytes") == b"normalized-A"
                  and not capture_seen["path"].exists())
            all_capture_paths = capture_seen["paths"] + [decoration_seen.get("path")]
            check("values, formulas, and build-time evidence share one capture",
                  len(capture_seen["paths"]) == 2
                  and decoration_seen.get("bytes") == b"normalized-A"
                  and len(set(all_capture_paths)) == 1)
            check("published sidecar remains trusted after capture cleanup",
                  capture_record is not None and capture_record.trusted
                  and capture_record.current
                  and str(capture_seen["path"]) not in capture_sidecar_text
                  and str(capture_seen["path"]) not in cache_text)

            # Evidence uses the same capture boundary and live-token guard.
            evidence_seen = {}

            def evidence_interposition(*args, **kwargs):
                captured_path = Path(args[2])
                live_mtime = normalized.stat().st_mtime
                normalized.write_bytes(b"normalized-B")
                os.utime(normalized, (live_mtime, live_mtime))
                evidence_seen["path"] = captured_path
                evidence_seen["bytes"] = captured_path.read_bytes()
                normalized.write_bytes(b"normalized-A")
                os.utime(normalized, (live_mtime, live_mtime))
                assert kwargs["commit_guard"](Path(args[3]))
                return {"note": "captured evidence"}

            with patch(matrix, "_consolidated_stale", lambda *_a, **_k: False), \
                    patch(visual_evidence, "capable", lambda _row: True), \
                    patch(visual_evidence, "generate", evidence_interposition):
                evidence_result = matrix.run_evidence_only(
                    "ramp_summary", store, "ramp_summary", normalized,
                    interposed, root / "pdfs", Events(),
                    source_identity_check=current,
                    expected_generation_id="capture-sidecar",
                    source_workbook_identity=expected_workbook_identity,
                    live_tsn_path=normalized)
            check("evidence generator consumes immutable A during live B->A",
                  evidence_result.status == "ok"
                  and evidence_seen.get("bytes") == b"normalized-A"
                  and not evidence_seen["path"].exists())

            persistent_evidence = {}

            def evidence_persistent_drift(*args, **kwargs):
                captured_path = Path(args[2])
                live_mtime = normalized.stat().st_mtime
                normalized.write_bytes(b"normalized-B")
                os.utime(normalized, (live_mtime, live_mtime))
                persistent_evidence["path"] = captured_path
                persistent_evidence["bytes"] = captured_path.read_bytes()
                persistent_evidence["guard"] = kwargs["commit_guard"](
                    Path(args[3]))
                return {"note": "must not publish"}

            persistent_evidence_error = ""
            with patch(matrix, "_consolidated_stale", lambda *_a, **_k: False), \
                    patch(visual_evidence, "capable", lambda _row: True), \
                    patch(visual_evidence, "generate", evidence_persistent_drift):
                try:
                    matrix.run_evidence_only(
                        "ramp_summary", store, "ramp_summary", normalized,
                        interposed, root / "pdfs", Events(),
                        source_identity_check=current,
                        expected_generation_id="capture-sidecar",
                        source_workbook_identity=expected_workbook_identity,
                        live_tsn_path=normalized)
                except ValueError as e:
                    persistent_evidence_error = str(e)
            check("persistent evidence drift fails despite immutable A capture",
                  persistent_evidence.get("bytes") == b"normalized-A"
                  and persistent_evidence.get("guard") is False
                  and not persistent_evidence["path"].exists()
                  and "TSN source generation changed" in persistent_evidence_error,
                  persistent_evidence_error)
            normalized.write_bytes(b"normalized-A")
            os.utime(normalized, (9000.0, 9000.0))
            assert current()

            persistent_normalized = root / "persistent-normalized-drift.xlsx"

            class PersistentNormalizedComparator:
                @staticmethod
                def compare(_a, captured_path, out_path, **kwargs):
                    live_mtime = normalized.stat().st_mtime
                    normalized.write_bytes(b"normalized-B")
                    os.utime(normalized, (live_mtime, live_mtime))
                    capture_seen["persistent_bytes"] = Path(captured_path).read_bytes()
                    if kwargs["commit_guard"](Path(out_path)):
                        Path(out_path).write_bytes(b"FALSE GREEN")
                    return ConsolidateResult(status="ok", output_path=str(out_path))

            persistent_error = ""
            with patch(matrix, "_consolidated_stale", lambda *_a, **_k: False), \
                    patch(matrix, "tsn_comparator_for",
                          lambda _row: PersistentNormalizedComparator):
                try:
                    matrix.consolidate_and_compare_tsn(
                        store, normalized, persistent_normalized,
                        "ramp_summary", "ramp_summary", Events(),
                        source_identity_check=current,
                        source_workbook_identity=expected_workbook_identity)
                except ValueError as e:
                    persistent_error = str(e)
            check("persistent normalized drift still blocks publication",
                  capture_seen.get("persistent_bytes") == b"normalized-A"
                  and not persistent_normalized.exists()
                  and "TSN source generation changed" in persistent_error,
                  persistent_error)
            normalized.write_bytes(b"normalized-A")
            os.utime(normalized, (9000.0, 9000.0))
            assert current()

            class DriftComparator:
                @staticmethod
                def compare(_a, _b, out_path, **kwargs):
                    prior = raw.stat().st_mtime
                    raw.write_bytes(b"raw-B")
                    os.utime(raw, (prior, prior))
                    if kwargs["commit_guard"](Path(out_path)):
                        Path(out_path).write_bytes(b"FALSE GREEN")
                    return ConsolidateResult(status="ok", output_path=str(out_path))

            blocked = ""
            with patch(matrix, "_consolidated_stale", lambda *_a, **_k: False), \
                    patch(matrix, "tsn_comparator_for", lambda _row: DriftComparator):
                try:
                    matrix.consolidate_and_compare_tsn(
                        store, normalized, attempted, "ramp_summary", "ramp_summary",
                        Events(), source_identity_check=current,
                        source_workbook_identity=expected_workbook_identity)
                except ValueError as e:
                    blocked = str(e)
            check("post-ensure raw drift blocks comparator publication",
                  not attempted.exists() and "TSN source generation changed" in blocked,
                  blocked)

            # Restore raw, then prove normalized bytes are independently bound.
            raw.write_bytes(b"raw-A")
            os.utime(raw, (old_raw_mtime, old_raw_mtime))
            check("canonical generation is current again before normalized attack",
                  current())
            normalized_mtime = normalized.stat().st_mtime
            normalized.write_bytes(b"normalized-B")
            os.utime(normalized, (normalized_mtime, normalized_mtime))
            check("preserved-mtime normalized replacement denies the same guard",
                  not combined(probe))

            # Recreate generation A for a strict cache freshness witness.
            normalized.write_bytes(b"normalized-A")
            os.utime(normalized, (normalized_mtime, normalized_mtime))
            assert current()
            out = root / "cached-comparison.xlsx"
            _publish_comparison(out)
            rec = {
                "built_at_mtime": out.stat().st_mtime,
                "verdict": "match", "diff_cells": 0, "one_sided": 0,
                "completion": outcome.COMPLETE,
                "generation_id": "consumer-identity-fixture",
                "source_identities": {"tsn": token},
                # CMP-AUD-084: a current record — isolate the TSN-drift gate under test.
                "producer_versions": matrix.producer_identity(),
            }
            sources = [
                {"name": "cell", "present": True, "mtime": 1.0},
                {"name": "tsn", "present": True, "mtime": 1.0,
                 "identity": token, "identity_required": True},
            ]
            before = matrix._cmp_state(out, sources, rec)
            raw.write_bytes(b"raw-B")
            os.utime(raw, (old_raw_mtime, old_raw_mtime))
            stale_source = tsn_library.resolve(report)
            sources[1]["identity"] = stale_source.get("identity_token")
            after = matrix._cmp_state(out, sources, rec)
            check("matching token cache is fresh before drift",
                  not before["stale"], before.get("reason"))
            check("raw drift invalidates cached Matrix truth without mtime help",
                  after["stale"] and after["reason"] == "source_identity_changed",
                  after.get("reason"))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_both_evidence_entry_points():
    print("Everything and by-day evidence require exact token + cache generation:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_tsn_evidence_identity_"))
    try:
        picked = root / "picked.xlsx"
        wb = Workbook()
        wb.active["A1"] = "TSN"
        wb.save(picked)
        wb.close()
        selection = tsn_library.create_explicit_selection(picked)
        assert consolidation_meta.write_outcome(
            picked, ConsolidateResult(
                status="ok", output_path=str(picked),
                completion=outcome.PARTIAL, skipped_inputs=2, failed_inputs=0))
        source = tsn_library.resolve("highway_log", selected_file=selection)
        token = source["identity_token"]
        explicit_expected = matrix.tsn_expected_workbook_identity(
            "highway_log", source, token)
        explicit_bytes = picked.read_bytes()
        explicit_stat = picked.stat()
        with matrix.captured_tsn_workbook(picked, explicit_expected) as explicit_capture:
            explicit_capture_path = Path(explicit_capture)
            captured_outcome = consolidation_meta.read_outcome(explicit_capture)
            picked.write_bytes(b"B" * len(explicit_bytes))
            picked.write_bytes(explicit_bytes)
            os.utime(picked, ns=(explicit_stat.st_atime_ns,
                                 explicit_stat.st_mtime_ns))
            check("explicit capture preserves exact A through live B->A",
                  explicit_capture_path.read_bytes() == explicit_bytes)
        check("explicit trusted PARTIAL outcome survives capture structurally",
              captured_outcome is not None and captured_outcome.trusted
              and captured_outcome.completion == outcome.PARTIAL
              and captured_outcome.skipped_inputs == 2
              and not explicit_capture_path.exists()
              and not consolidation_meta.meta_path(explicit_capture_path).exists())

        # Cleanup is identity-bound and nonrecursive: a replacement at the
        # captured pathname and an unrelated member must both survive.
        with matrix.captured_tsn_workbook(picked, explicit_expected) as cleanup_capture:
            cleanup_capture = Path(cleanup_capture)
            cleanup_root = cleanup_capture.parent
            cleanup_capture.unlink()
            cleanup_capture.write_bytes(b"foreign replacement")
            foreign_member = cleanup_root / "foreign-member.txt"
            foreign_member.write_bytes(b"foreign member")
        check("capture cleanup retains replacement and foreign directory member",
              cleanup_capture.read_bytes() == b"foreign replacement"
              and foreign_member.read_bytes() == b"foreign member"
              and cleanup_root.exists())
        foreign_member.unlink()
        cleanup_capture.unlink()
        os.rmdir(cleanup_root)

        # If capture begins while the explicit pathname is B, restoring A only
        # after the attempt cannot make the mismatched capture admissible.
        picked.write_bytes(b"B" * len(explicit_bytes))
        try:
            with matrix.captured_tsn_workbook(picked, explicit_expected):
                explicit_mismatch = ""
        except ValueError as e:
            explicit_mismatch = str(e)
        finally:
            picked.write_bytes(explicit_bytes)
            os.utime(picked, ns=(explicit_stat.st_atime_ns,
                                 explicit_stat.st_mtime_ns))
        check("explicit B capture fails even when live path is later restored to A",
              "did not match" in explicit_mismatch, explicit_mismatch)
        everything_calls = []
        day_calls = []

        def everything_run(*args, **kwargs):
            everything_calls.append(kwargs)
            return ConsolidateResult(status="ok", message="fixture")

        def day_run(*args, **kwargs):
            day_calls.append(kwargs)
            return ConsolidateResult(status="ok", message="fixture")

        wrong = {"source_identities": {"tsn": "wrong"},
                 "generation_id": "g1"}
        exact = {"source_identities": {"tsn": token},
                 "generation_id": "g1"}
        stale = {"kind": "consolidated", "path": str(picked),
                 "identity_token": None, "legacy": True}

        with patch(matrix_build, "tsn_source", lambda *_a, **_k: source), \
                patch(matrix, "load_tsn_results", lambda _dest: {
                    "highway_log_pdf|tsn": {"ars-prod": wrong}}), \
                patch(matrix_build, "run_evidence_only", everything_run):
            try:
                matrix_build.evidence_for_cell(
                    root, "highway_log_pdf", "ars-prod", "ssor-prod", Events(),
                    tsn_files={"highway_log": selection})
                everything_wrong = ""
            except ValueError as e:
                everything_wrong = str(e)
        check("Everything evidence rejects a different cached TSN token",
              "different or unrecorded" in everything_wrong
              and not everything_calls, everything_wrong)

        with patch(matrix_build, "tsn_source", lambda *_a, **_k: source), \
                patch(matrix, "load_tsn_results", lambda _dest: {
                    "highway_log_pdf|tsn": {"ars-prod": exact}}), \
                patch(matrix_build, "run_evidence_only", everything_run):
            matrix_build.evidence_for_cell(
                root, "highway_log_pdf", "ars-prod", "ssor-prod", Events(),
                tsn_files={"highway_log": selection})
        check("Everything evidence forwards its exact cached generation",
              len(everything_calls) == 1
              and everything_calls[0].get("expected_generation_id") == "g1"
              and callable(everything_calls[0].get("source_identity_check")))

        day_key = "2026-07-12 ssor-prod|highway_log_pdf"
        with patch(matrix, "tsn_source", lambda *_a, **_k: source), \
                patch(day_matrix, "load_results", lambda: {day_key: wrong}), \
                patch(matrix, "run_evidence_only", day_run):
            try:
                day_matrix.evidence_for_day_cell(
                    "ssor-prod", "2026-07-12", "highway_log_pdf", root, Events(),
                    tsn_files={"highway_log": selection})
                day_wrong = ""
            except ValueError as e:
                day_wrong = str(e)
        check("by-day evidence rejects a different cached TSN token",
              "different or unrecorded" in day_wrong and not day_calls,
              day_wrong)

        with patch(matrix, "tsn_source", lambda *_a, **_k: source), \
                patch(day_matrix, "load_results", lambda: {day_key: exact}), \
                patch(matrix, "run_evidence_only", day_run):
            day_matrix.evidence_for_day_cell(
                "ssor-prod", "2026-07-12", "highway_log_pdf", root, Events(),
                tsn_files={"highway_log": selection})
        check("by-day evidence forwards its exact cached generation",
              len(day_calls) == 1
              and day_calls[0].get("expected_generation_id") == "g1"
              and callable(day_calls[0].get("source_identity_check")))

        everything_calls.clear()
        with patch(matrix_build, "tsn_source", lambda *_a, **_k: stale), \
                patch(matrix_build, "run_evidence_only", everything_run):
            try:
                matrix_build.evidence_for_cell(
                    root, "highway_log_pdf", "ars-prod", "ssor-prod", Events())
                everything_stale = ""
            except ValueError as e:
                everything_stale = str(e)
        day_calls.clear()
        with patch(matrix, "tsn_source", lambda *_a, **_k: stale), \
                patch(matrix, "run_evidence_only", day_run):
            try:
                day_matrix.evidence_for_day_cell(
                    "ssor-prod", "2026-07-12", "highway_log_pdf", root, Events())
                day_stale = ""
            except ValueError as e:
                day_stale = str(e)
        check("both evidence paths reject stale/legacy canonical artifacts",
              not everything_calls and not day_calls
              and "stale, legacy, foreign" in everything_stale
              and "stale, legacy, foreign" in day_stale,
              f"Everything={everything_stale!r}; day={day_stale!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


# Read through getattr so this file degrades to semantic FAILs on a tree that
# predates the fix instead of crashing (the red proof has to be readable).
_CAPTURE_PREFIX = getattr(matrix_build, "_TSN_CAPTURE_PREFIX",
                          "tsmis-tsn-consumer-")
_CARRIED_KEYS = getattr(matrix_build, "_TSN_CARRIED_SIDECAR_KEYS",
                        ("tsn_source_claims", "tsn_normalization_version",
                         "tsn_raw_manifest", "tsn_normalized_workbook_identity",
                         "tsn_artifact_identity_token"))
_ORIGIN_KEY = getattr(matrix_build, "TSN_CAPTURE_ORIGIN_KEY",
                      "tsn_capture_origin")
_STALE_AGE_S = getattr(matrix_build, "_STALE_CAPTURE_AGE_S", 6 * 3600)
_SWEEP = getattr(matrix_build, "_sweep_stale_tsn_captures", lambda *_a: None)


def _capture_dirs():
    return sorted(Path(tempfile.gettempdir()).glob(_CAPTURE_PREFIX + "*"))


def test_capture_carries_its_source_record():
    """PCOA-FINAL-002 / -003 / -016 — the private copy the matrix lanes compare
    must describe itself exactly as the canonical library workbook does, name a
    DURABLE selection, and leave nothing behind."""
    print("\nPrivate TSN capture — claims, provenance and temp lifecycle:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_tsn_capture_record_"))
    before_dirs = set(_capture_dirs())
    try:
        library = root / "tsn_ramp_summary_normalized.xlsx"
        wb = Workbook()
        wb.active["A1"] = "TSN"
        wb.save(library)
        wb.close()
        claims = {"schema_version": 1,
                  "identity": {"report_id": "OTM22270",
                               "event_id": "4843742",
                               "reference_date": "09/15/2025",
                               "submitter": "TRLBUGNI",
                               "generated_time": "09/15/25 08:12",
                               "location_criteria": "STATEWIDE"}}
        identity = tsn_library.normalized_workbook_identity(library)
        result = ConsolidateResult(
            status="ok", output_path=str(library), completion=outcome.COMPLETE,
            skipped_inputs=0, failed_inputs=0)
        assert consolidation_meta.write_outcome(
            library, result, extra={
                "tsn_source_claims": claims,
                "tsn_normalization_version": 7,
                "tsn_raw_manifest": {"files": ["raw.pdf"]},
                "tsn_normalized_workbook_identity": identity,
                "tsn_artifact_identity_token": "token-fixture",
            })

        import compare_ramp_summary_tsn as rstsn
        import compare_tsn_common as ctc
        direct_line = rstsn.claims_notes(
            consolidation_meta.read_extra(library, "tsn_source_claims"))

        with matrix_build.captured_tsn_workbook(library, identity) as captured:
            captured = Path(captured)
            carried = {key: consolidation_meta.read_extra(captured, key)
                       for key in _CARRIED_KEYS}
            lane_line = rstsn.claims_notes(
                consolidation_meta.read_extra(captured, "tsn_source_claims"))
            prov = ctc.capture_input_provenance((("TSN", captured),))[0]
            live_dir = captured.parent
        check("the capture carries every library sidecar claim field",
              carried == {"tsn_source_claims": claims,
                          "tsn_normalization_version": 7,
                          "tsn_raw_manifest": {"files": ["raw.pdf"]},
                          "tsn_normalized_workbook_identity": identity,
                          "tsn_artifact_identity_token": "token-fixture"},
              repr(carried))
        check("a matrix-lane comparison prints the Direct lane's identity line",
              lane_line == direct_line
              and "OTM22270" in lane_line[0]
              and not any("rebuild the TSN library" in line
                          for line in lane_line),
              repr(lane_line))
        check("provenance names the durable selection, never the capture path",
              prov["selection"] == str(library.resolve())
              and str(live_dir) not in prov["selection"]
              and prov.get("read_via")
              and prov["sha256"] == identity["sha256"],
              repr(prov))
        check("the capture's own outcome record still survives capture",
              prov["producer_completion"] == outcome.COMPLETE, repr(prov))
        check("a successful capture leaves no directory behind",
              not live_dir.exists() and set(_capture_dirs()) == before_dirs,
              repr(sorted(set(_capture_dirs()) - before_dirs)))

        # An unverifiable origin record must NOT rewrite the selection.
        loose = root / "loose.xlsx"
        shutil.copy2(library, loose)
        assert consolidation_meta.write_outcome(
            loose, ConsolidateResult(
                status="ok", output_path=str(loose), completion=outcome.COMPLETE),
            extra={_ORIGIN_KEY: {
                "version": 1, "selection": str(root / "missing.xlsx"),
                "identity": identity}})
        forged = ctc.capture_input_provenance((("TSN", loose),))[0]
        check("an origin whose canonical file is gone keeps the literal path",
              forged["selection"] == str(loose.resolve())
              and "read_via" not in forged, repr(forged))

        # Failure and cancellation both unwind through the same cleanup.
        for label, error in (("failure", ValueError("boom")),
                             ("cancellation", KeyboardInterrupt())):
            dirs = None
            try:
                with matrix_build.captured_tsn_workbook(library, identity) as cap:
                    dirs = Path(cap).parent
                    raise error
            except (ValueError, KeyboardInterrupt):
                pass
            check(f"a {label} mid-capture leaves no directory behind",
                  dirs is not None and not dirs.exists()
                  and set(_capture_dirs()) == before_dirs)

        # The killed-process case: an abandoned directory older than any live
        # capture is swept; a fresh one and an unrecognized one are not.
        abandoned = Path(tempfile.mkdtemp(
            prefix=_CAPTURE_PREFIX))
        shutil.copy2(library, abandoned / library.name)
        abandoned_sidecar = consolidation_meta.meta_path(abandoned / library.name)
        abandoned_sidecar.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(consolidation_meta.meta_path(library),
                     abandoned_sidecar)
        fresh = Path(tempfile.mkdtemp(prefix=_CAPTURE_PREFIX))
        shutil.copy2(library, fresh / library.name)
        foreign = Path(tempfile.mkdtemp(prefix=_CAPTURE_PREFIX))
        shutil.copy2(library, foreign / library.name)
        (foreign / "foreign-member.txt").write_bytes(b"not ours")
        old = os.stat(abandoned).st_mtime - _STALE_AGE_S - 60
        for stale_dir in (abandoned, foreign):
            os.utime(stale_dir, (old, old))
        _SWEEP(None)
        check("the sweep removes an abandoned capture directory",
              not abandoned.exists())
        check("the sweep never touches a capture that could still be live",
              fresh.exists() and (fresh / library.name).exists())
        check("the sweep leaves an unrecognized directory alone",
              foreign.exists() and (foreign / "foreign-member.txt").exists())
        shutil.rmtree(fresh, ignore_errors=True)
        shutil.rmtree(foreign, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    test_publication_and_cache_identity()
    test_both_evidence_entry_points()
    test_capture_carries_its_source_record()
    if _fail:
        print(f"\nFAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("\nALL CANONICAL TSN CONSUMER IDENTITY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
