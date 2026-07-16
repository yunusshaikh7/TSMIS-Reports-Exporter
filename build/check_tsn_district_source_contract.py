"""CMP-AUD-035 exact internal D01-D12 source contract for HL/HSL."""
import contextlib
import hashlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import consolidate_tsn_highway_log as hl  # noqa: E402
import consolidate_tsn_highway_sequence as hsl  # noqa: E402
from events import ConsolidateResult, Events  # noqa: E402
import outcome  # noqa: E402
import tsn_district_contract as contract  # noqa: E402
import tsn_library  # noqa: E402


failures = []


def check(label, condition):
    print(f"{'OK  ' if condition else 'FAIL'} {label}")
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


def rejected(fn, fragment):
    try:
        fn()
    except ValueError as exc:
        return fragment in str(exc)
    return False


def test_claim_helpers():
    print("internal document claims:")
    check("one internal claim accepted without relying on filename",
          contract.document_district(["1", "01"], "arbitrary.pdf") == "01")
    check("matching filename claim accepted",
          contract.document_district(["12"], "D12 HSL TSN.pdf") == "12")
    check("missing internal claim rejected",
          rejected(lambda: contract.document_district([], "D01.pdf"), "exactly one"))
    check("mixed internal claims rejected",
          rejected(lambda: contract.document_district(["01", "02"], "x.pdf"),
                   "exactly one"))
    check("out-of-domain internal claim rejected",
          rejected(lambda: contract.document_district(["13"], "x.pdf"), "outside"))
    check("filename/document disagreement rejected",
          rejected(lambda: contract.document_district(["01"], "D02 source.pdf"),
                   "disagrees"))
    check("multiple filename Dnn tokens rejected even when one agrees",
          rejected(lambda: contract.document_district(["01"], "D01-D02 source.pdf"),
                   "at most one"))
    check("repeated filename Dnn token rejected as ambiguous",
          rejected(lambda: contract.document_district(["01"], "D01_D01 source.pdf"),
                   "at most one"))
    check("malformed filename district-like token rejected",
          rejected(lambda: contract.document_district(["01"], "D01A source.pdf"),
                   "malformed"))

    exact = [(f"{number:02d}", f"member-{number}") for number in range(1, 13)]
    check("exact D01-D12 universe accepted",
          contract.require_exact_universe(exact) == tuple(exact))
    check("missing district rejected",
          rejected(lambda: contract.require_exact_universe(exact[:-1]), "missing D12"))
    duplicate = exact[:-1] + [("01", "duplicate")]
    check("duplicate district rejected",
          rejected(lambda: contract.require_exact_universe(duplicate), "duplicate D01"))
    check("extra document rejected",
          rejected(lambda: contract.require_exact_universe(exact + [("01", "extra")]),
                   "found 13"))


def test_manifest_helpers(root):
    print("canonical raw content manifest:")
    raw = root / "manifest"
    raw.mkdir()
    upper = raw / "B.pdf"
    lower = raw / "a.pdf"
    upper.write_bytes(b"B")
    lower.write_bytes(b"alpha")
    manifest, captured = contract.capture_raw_manifest([upper, lower], raw)
    check("members sort by case-folded report-raw-relative path",
          [member["relative_path"] for member in manifest["members"]]
          == ["a.pdf", "B.pdf"])
    check("captured bytes and byte total bind the manifest members",
          captured == {"B.pdf": b"B", "a.pdf": b"alpha"}
          and manifest["byte_length"] == 6 and manifest["member_count"] == 2)
    expected_lines = (
        f"a.pdf\t5\t{hashlib.sha256(b'alpha').hexdigest()}\n"
        f"B.pdf\t1\t{hashlib.sha256(b'B').hexdigest()}\n")
    check("aggregate hash uses the dashboard's exact tab/newline serialization",
          manifest["sha256"]
          == hashlib.sha256(expected_lines.encode("utf-8")).hexdigest())
    check("canonical manifest strictly validates",
          contract.validate_raw_manifest(manifest) == manifest)
    malformed = dict(manifest)
    malformed["sha256"] = "A" * 64
    check("uppercase/corrupt aggregate SHA-256 is rejected",
          rejected(lambda: contract.validate_raw_manifest(malformed), "canonical"))
    # CMP-AUD-035: reject float/bool aliases of the canonical integers that the
    # value==canonical dict-equality would otherwise admit (1.0==1, True==1).
    check("version rejects a float alias of the canonical int",
          rejected(lambda: contract.validate_raw_manifest(dict(manifest, version=1.0)),
                   "version"))
    check("byte_length rejects a float alias of the canonical int",
          rejected(lambda: contract.validate_raw_manifest(
              dict(manifest, byte_length=float(manifest["byte_length"]))), "byte_length"))
    _one_member = contract.canonical_raw_manifest([upper], raw)
    check("member_count rejects a bool alias of the canonical int (True==1)",
          rejected(lambda: contract.validate_raw_manifest(
              dict(_one_member, member_count=True)), "member_count"))
    lower.write_bytes(b"ALPHA")
    changed = contract.canonical_raw_manifest([upper, lower], raw)
    check("same-length byte change changes the canonical manifest",
          changed != manifest and changed["byte_length"] == manifest["byte_length"])


def test_reuse_cardinality(root):
    print("library reuse content manifest + cardinality:")
    with patch(tsn_library.paths, "TSN_LIBRARY_ROOT", root / "library"):
        for current_report, expected_version in (("highway_log", 4),
                                                  ("highway_sequence", 4)):
            spec = tsn_library.get(current_report)
            raw = tsn_library.raw_dir(current_report)
            raw.mkdir(parents=True)
            for number in range(1, 13):
                (raw / f"D{number:02d}.pdf").write_bytes(b"pdf")
            consolidated = tsn_library.consolidated_path(current_report)
            consolidated.parent.mkdir(parents=True)
            consolidated.write_bytes(b"normalized")
            for member in raw.glob("*.pdf"):
                os.utime(member, (1000, 1000))
            os.utime(consolidated, (2000, 2000))
            manifest = contract.canonical_raw_manifest(list(raw.glob("*.pdf")), raw)
            workbook_identity = tsn_library.normalized_workbook_identity(consolidated)
            tsn_library.consolidation_meta.write_outcome(
                consolidated,
                ConsolidateResult(status="ok", completion=outcome.COMPLETE),
                extra={"tsn_normalization_version": spec.normalization_version,
                       "tsn_raw_manifest": manifest,
                       "tsn_normalized_workbook_identity": workbook_identity,
                       "tsn_artifact_identity_token":
                           tsn_library.canonical_normalized_identity_token(
                               current_report, manifest, workbook_identity)})
            exact = tsn_library.status(current_report)
            (raw / "D12.pdf").unlink()
            missing = tsn_library.status(current_report)
            (raw / "D12.pdf").write_bytes(b"pdf")
            (raw / "extra.pdf").write_bytes(b"pdf")
            extra = tsn_library.status(current_report)
            check(f"{current_report}: version bump forces strict builder generation",
                  spec.normalization_version == expected_version)
            check(f"{current_report}: exactly 12 members may be reusable",
                  exact["raw_admissible"] and exact["current"])
            check(f"{current_report}: 11/13 members cannot reuse last-good",
                  not missing["raw_admissible"] and not missing["current"]
                  and not extra["raw_admissible"] and not extra["current"])
            (raw / "extra.pdf").unlink()
            changed = raw / "D12.pdf"
            changed.write_bytes(b"bad")
            os.utime(changed, (1000, 1000))
            same_count_changed_bytes = tsn_library.status(current_report)
            check(f"{current_report}: preserved-mtime byte change cannot reuse last-good",
                  same_count_changed_bytes["raw_count"] == 12
                  and same_count_changed_bytes["raw_admissible"]
                  and not same_count_changed_bytes["raw_manifest_current"]
                  and not same_count_changed_bytes["current"])


def _raw_set(root, districts):
    root.mkdir(parents=True, exist_ok=True)
    for index, district in enumerate(districts):
        (root / f"member-{index:02d}.pdf").write_bytes(str(district).encode("ascii"))
    return root


def _claimed(path):
    if isinstance(path, io.BytesIO):
        return path.getvalue().decode("ascii").zfill(2)
    return Path(path).read_text(encoding="ascii").zfill(2)


class _FakePage:
    def __init__(self, text=""):
        self._text = text

    def extract_words(self, **_kwargs):
        return []

    def extract_text(self):
        return self._text


# A structurally valid HSL cover (CMP-AUD-155: parse_pdf reads page 1's report
# id / Reference Date / District / reliability NOTE before any data page).
_HSL_COVER = ("OTM22025\nHighway Locations\nReference Date: 15-SEP-25\n"
              "District: 01\n* * * N O T E * * *\nThe landmark descriptions "
              "may be wrong at Route Breaks and Equates.")


class _FakePdf:
    def __init__(self, pages=None):
        self.pages = [_FakePage()] if pages is None else pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_parser_ownership_guards():
    print("parser row/group ownership guards:")
    fake_open = lambda _path: _FakePdf()

    hl_malformed = [(60, [
        {"text": "1", "x0": 260}, {"text": "MEN", "x0": 275}], [])]
    with patch(hl.pdfplumber, "open", fake_open), \
            patch(hl, "_lines", lambda _page: hl_malformed):
        check("HL malformed centered group header fails before route carry-over",
              rejected(lambda: hl.parse_pdf(io.BytesIO(b"pdf"), Events(), "source.pdf"),
                       "malformed centered"))

    hl_unowned = [(60, [{"text": "000.000", "x0": 5}], [])]
    with patch(hl.pdfplumber, "open", fake_open), \
            patch(hl, "_lines", lambda _page: hl_unowned):
        check("HL recognizable data without an owning route fails",
              rejected(lambda: hl.parse_pdf(io.BytesIO(b"pdf"), Events(), "source.pdf"),
                       "before any owning route"))

    # HSL parses page 1 as the COVER (CMP-AUD-155) and data pages after it, so
    # the guard fixtures are two-page fakes: a valid cover + the bad data page.
    hsl_open = lambda _path: _FakePdf([_FakePage(_HSL_COVER), _FakePage()])

    hsl_malformed = [[
        {"text": "DIST", "x0": 250}, {"text": "01", "x0": 280},
        {"text": "RTE", "x0": 300}, {"text": "???", "x0": 330},
        {"text": "DIR", "x0": 360}, {"text": "S-N", "x0": 390},
    ]]
    with patch(hsl.pdfplumber, "open", hsl_open), \
            patch(hsl, "_cluster_lines", lambda _words: hsl_malformed):
        check("HSL malformed DIST/RTE/DIR header fails before route carry-over",
              rejected(lambda: hsl.parse_pdf(io.BytesIO(b"pdf"), Events(), "source.pdf"),
                       "malformed DIST/RTE/DIR"))

    hsl_unowned = [[
        {"text": "MEN", "x0": 1}, {"text": "000.000", "x0": 110},
    ]]
    with patch(hsl.pdfplumber, "open", hsl_open), \
            patch(hsl, "_cluster_lines", lambda _words: hsl_unowned):
        check("HSL recognizable data without an owning route fails",
              rejected(lambda: hsl.parse_pdf(io.BytesIO(b"pdf"), Events(), "source.pdf"),
                       "before any owning route"))

    # a cover missing the reliability NOTE refuses before any data page is read
    with patch(hsl.pdfplumber, "open",
               lambda _path: _FakePdf([_FakePage("OTM22025 only"), _FakePage()])):
        check("HSL cover without the reliability NOTE fails",
              rejected(lambda: hsl.parse_pdf(io.BytesIO(b"pdf"), Events(), "source.pdf"),
                       "reliability NOTE"))


def test_highway_sequence_boundary(root):
    print("Highway Sequence production boundary:")

    def _fake_claims(district, pdf_name, reference_date="15 SEP 2025"):
        # the CMP-AUD-155 per-document claims record parse_pdf now returns
        return {
            "member": pdf_name or f"member-{district}.pdf",
            "district": district,
            "report_id": "OTM22025", "report_title": "Highway Locations",
            "report_date": "15-SEP-25", "reference_date": reference_date,
            "cover_reference_date": "15-SEP-25",
            "generation_time": "01:05 PM", "pages": 2,
            "policy_sha256": "0" * 64,
            "policy_text": "* * * N O T E * * * boilerplate",
            "directions": {district: "S-N"},
        }

    def parse(path, _events, pdf_name=""):
        district = _claimed(path)
        return (district, {district: [{"district": district}]},
                _fake_claims(district, pdf_name))

    def write(_rows, out, proceed=None):
        if proceed is not None and not proceed():
            return False
        Path(out).write_text("normalized", encoding="utf-8")
        return True

    exact = _raw_set(root / "hsl-exact", range(1, 13))
    missing = _raw_set(root / "hsl-missing", range(1, 12))
    duplicate = _raw_set(root / "hsl-duplicate", list(range(1, 12)) + [1])

    with patch(hsl, "_DEPS_OK", True), patch(hsl, "parse_pdf", parse), \
            patch(hsl, "_write_workbook", write):
        good_out = root / "hsl-good.xlsx"
        good = hsl.consolidate(input_dir=exact, out_path=good_out, events=Events())
        check("HSL exact internally claimed D01-D12 publishes complete",
              good.status == "ok" and good.completion == outcome.COMPLETE
              and good.failed_inputs == 0 and good_out.is_file()
              and contract.validate_raw_manifest(good.tsn_raw_manifest)
              == good.tsn_raw_manifest)
        missing_out = root / "hsl-missing.xlsx"
        miss = hsl.consolidate(input_dir=missing, out_path=missing_out, events=Events())
        check("HSL missing D12 fails before publication",
              miss.status == "error" and "missing D12" in miss.message
              and not missing_out.exists())
        duplicate_out = root / "hsl-duplicate.xlsx"
        dup = hsl.consolidate(input_dir=duplicate, out_path=duplicate_out, events=Events())
        check("HSL duplicate D01 fails before publication",
              dup.status == "error" and "Duplicate internal district claim D01" in dup.message
              and not duplicate_out.exists())
        check("HSL complete result carries the source claims (CMP-AUD-155)",
              (getattr(good, "producer_extra", None) or {}).get(
                  "tsn_source_claims", {}).get("report_id") == "OTM22025")

        # CMP-AUD-155: one member from a DIFFERENT TSN pull refuses.
        def parse_mixed(path, _events, pdf_name=""):
            district = _claimed(path)
            ref = "16 SEP 2025" if district == "05" else "15 SEP 2025"
            return (district, {district: [{"district": district}]},
                    _fake_claims(district, pdf_name, reference_date=ref))

        mixed_raw = _raw_set(root / "hsl-mixed-pull", range(1, 13))
        mixed_out = root / "hsl-mixed-pull.xlsx"
        with patch(hsl, "parse_pdf", parse_mixed):
            mixed = hsl.consolidate(
                input_dir=mixed_raw, out_path=mixed_out, events=Events())
        check("HSL cross-member reference-date disagreement fails before publication",
              mixed.status == "error"
              and "disagree on the reference date" in mixed.message
              and not mixed_out.exists())

        changed_raw = _raw_set(root / "hsl-source-change", range(1, 13))
        changed_out = root / "hsl-source-change.xlsx"
        changed_out.write_text("last-good", encoding="utf-8")

        def mutate_before_commit(_rows, out, proceed=None):
            (changed_raw / "member-11.pdf").write_bytes(b"11-changed")
            if proceed is not None and not proceed():
                return False
            Path(out).write_text("bad", encoding="utf-8")
            return True

        with patch(hsl, "_write_workbook", mutate_before_commit):
            changed = hsl.consolidate(
                input_dir=changed_raw, out_path=changed_out, events=Events())
        check("HSL source mutation at atomic gate fails and preserves last-good",
              changed.status == "error" and "raw source changed" in changed.message
              and changed_out.read_text(encoding="utf-8") == "last-good")

        cancel_raw = _raw_set(root / "hsl-cancel-commit", range(1, 13))
        cancel_out = root / "hsl-cancel-commit.xlsx"
        cancelled = {"value": False}

        def cancel_inside_commit(_rows, out, proceed=None):
            cancelled["value"] = True
            if proceed is not None and not proceed():
                return False
            Path(out).write_text("bad", encoding="utf-8")
            return True

        with patch(hsl, "_write_workbook", cancel_inside_commit):
            cancelled_result = hsl.consolidate(
                input_dir=cancel_raw, out_path=cancel_out,
                events=Events(is_cancelled=lambda: cancelled["value"]))
        check("HSL cancellation inside atomic commit gate publishes nothing",
              cancelled_result.status == "cancelled" and not cancel_out.exists())


def test_highway_log_boundary(root):
    print("Highway Log production boundary:")

    def parse(path, _events, pdf_name=""):
        district = _claimed(path)
        return district, {district: [{"district": district}]}

    def write(rows, out):
        Path(out).write_text(rows[0]["district"], encoding="utf-8")

    def combine(**kwargs):
        out = Path(kwargs["out_path"])
        guard = kwargs.get("commit_guard")
        if guard is not None and not guard(out):
            return ConsolidateResult(status="cancelled", message="guard refused")
        out.write_text("normalized", encoding="utf-8")
        return ConsolidateResult(status="ok", output_path=str(out),
                                 completion=outcome.COMPLETE)

    exact = _raw_set(root / "hl-exact", range(1, 13))
    missing = _raw_set(root / "hl-missing", range(1, 12))
    duplicate = _raw_set(root / "hl-duplicate", list(range(1, 12)) + [1])

    with patch(hl, "_DEPS_OK", True), patch(hl, "parse_pdf", parse), \
            patch(hl, "_write_route_workbook", write), \
            patch(hl, "consolidate_xlsx", combine):
        good_out = root / "hl-good.xlsx"
        good = hl.consolidate(input_dir=exact, out_path=good_out, events=Events())
        check("HL exact internally claimed D01-D12 publishes complete",
              good.status == "ok" and good.completion == outcome.COMPLETE
              and good.failed_inputs == 0 and good_out.is_file()
              and contract.validate_raw_manifest(good.tsn_raw_manifest)
              == good.tsn_raw_manifest)
        missing_out = root / "hl-missing.xlsx"
        miss = hl.consolidate(input_dir=missing, out_path=missing_out, events=Events())
        check("HL missing D12 fails before publication",
              miss.status == "error" and "missing D12" in miss.message
              and not missing_out.exists())
        duplicate_out = root / "hl-duplicate.xlsx"
        dup = hl.consolidate(input_dir=duplicate, out_path=duplicate_out, events=Events())
        check("HL duplicate D01 fails before publication",
              dup.status == "error" and "Duplicate internal district claim D01" in dup.message
              and not duplicate_out.exists())

        changed_raw = _raw_set(root / "hl-source-change", range(1, 13))
        changed_out = root / "hl-source-change.xlsx"
        changed_out.write_text("last-good", encoding="utf-8")

        def mutate_then_combine(**kwargs):
            (changed_raw / "member-11.pdf").write_bytes(b"11-changed")
            guard = kwargs.get("commit_guard")
            if guard is not None and not guard(Path(kwargs["out_path"])):
                return ConsolidateResult(status="cancelled", message="guard refused")
            Path(kwargs["out_path"]).write_text("bad", encoding="utf-8")
            return ConsolidateResult(status="ok", completion=outcome.COMPLETE)

        with patch(hl, "consolidate_xlsx", mutate_then_combine):
            changed = hl.consolidate(
                input_dir=changed_raw, out_path=changed_out, events=Events())
        check("HL source mutation at atomic guard fails and preserves last-good",
              changed.status == "error" and "raw source changed" in changed.message
              and changed_out.read_text(encoding="utf-8") == "last-good")


def main():
    root = Path(tempfile.mkdtemp(prefix="tsmis-tsn-district-contract-"))
    try:
        test_claim_helpers()
        test_manifest_helpers(root)
        test_reuse_cardinality(root)
        test_parser_ownership_guards()
        test_highway_sequence_boundary(root)
        test_highway_log_boundary(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if failures:
        print(f"FAILED: {len(failures)} check(s): {failures}")
        return 1
    print("TSN INTERNAL D01-D12 SOURCE CONTRACT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
