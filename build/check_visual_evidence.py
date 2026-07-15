"""Golden check for the visual-evidence generator (scripts/visual_evidence.py +
scripts/evidence_highway_detail.py) — the render-free logic layer.

Locks: the row registry + the TSMIS-PDF/TSN-PDF source resolution and the
examples clamp; the caller-side gate (matrix_build.evidence_opts_for); the
sibling artifact naming (the "(formulas).xlsx" family); the adapter's LOCKSTEP
pins against the Highway Detail PDF consolidator (window counts, the postmile /
date-token regex behavior its mirrored walk relies on); the field→TSN-print
group map (complete, RB half mirrored) and the two-line TASAS regexes on
realistic print lines (prefix/roadbed/equation/optional-city/empty-description);
the span→x-box math including the empty-optional-group case; the verification
projections (PS derived, NA fold via the comparator's own projection); the
unique-key diff enumeration with the district/county sidecar; and the TSN
loader's sidecar contract (tsn_rows_with_dcr row-identical to the locked
tsn_rows_from_raw; the normalized sheet appending exactly the sidecar columns;
load_sides reading it back and refusing a sidecar-less legacy library with the
rebuild hint). Rendering itself is exercised by the frozen self-test's
render-stack step (scripts/self_test.py) — no rasterizing here; CI-safe.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_visual_evidence.py
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_highway_detail_tsn as cht
import compare_highway_log as chl_cmp
import compare_highway_sequence_tsn as chsl_cmp
import compare_ramp_detail_pdf as crdp
import compare_ramp_detail_tsn as crd_cmp
import consolidate_tsmis_highway_detail_pdf as chd
import consolidate_tsmis_highway_sequence_pdf as chslp
import consolidate_tsmis_ramp_detail_pdf as crdpdf
import consolidate_tsn_highway_log as ctnl
import consolidate_tsn_highway_sequence as ctnsl
import evidence_highway_detail as ehd
import evidence_highway_log as ehl
import evidence_highway_sequence as ehsl
import evidence_ramp_detail as erd
import highway_detail_columns as hdc
import highway_log_columns as hlc
import matrix_build
import tsn_library
import tsn_load_highway_detail as tlh
import visual_evidence as ve
import artifact_store
import consolidation_meta
from comparison_contract import ArtifactGeneration, ComparisonCounts, ComparisonOutcome
from events import ConsolidateResult
from openpyxl import Workbook, load_workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
print("registry + sources + clamp")
check("rows: the Highway Detail + Highway Log + Highway Sequence + Intersection "
      "Detail + Ramp Detail pairs, nothing else",
      ve.rows() == ["highway_detail", "highway_detail_pdf",
                    "highway_log", "highway_log_pdf",
                    "highway_sequence", "highway_sequence_pdf",
                    "intersection_detail", "intersection_detail_pdf",
                    "ramp_detail", "ramp_detail_pdf"])
check("capable() matches rows()",
      all(ve.capable(r) for r in ve.rows()) and not ve.capable("ramp_summary"))
check("TSMIS visuals come from each report's (PDF)-edition export subdir",
      ve.pdf_subdir_for("highway_detail") == "highway_detail_pdf"
      and ve.pdf_subdir_for("highway_detail_pdf") == "highway_detail_pdf"
      and ve.pdf_subdir_for("intersection_detail") == "intersection_detail_pdf"
      and ve.pdf_subdir_for("intersection_detail_pdf") == "intersection_detail_pdf"
      and ve.pdf_subdir_for("highway_log") == "highway_log_pdf"
      and ve.pdf_subdir_for("highway_log_pdf") == "highway_log_pdf"
      and ve.pdf_subdir_for("highway_sequence") == "highway_sequence_pdf"
      and ve.pdf_subdir_for("highway_sequence_pdf") == "highway_sequence_pdf"
      and ve.pdf_subdir_for("ramp_detail") == "ramp_detail_pdf"
      and ve.pdf_subdir_for("ramp_detail_pdf") == "ramp_detail_pdf")
check("TSN prints live in each report's library pdf folder — except the Highway "
      "Log and Highway Sequence, whose district prints ARE the library's raw "
      "inputs (no duplicate drop)",
      str(ve.tsn_pdf_dir("highway_detail")).replace("\\", "/")
      .endswith("tsn_library/highway_detail/pdf")
      and str(ve.tsn_pdf_dir("intersection_detail")).replace("\\", "/")
      .endswith("tsn_library/intersection_detail/pdf")
      and str(ve.tsn_pdf_dir("ramp_detail")).replace("\\", "/")
      .endswith("tsn_library/ramp_detail/pdf")
      and str(ve.tsn_pdf_dir("ramp_detail_pdf")).replace("\\", "/")
      .endswith("tsn_library/ramp_detail/pdf")
      and str(ve.tsn_pdf_dir("highway_log")).replace("\\", "/")
      .endswith("tsn_library/highway_log/raw")
      and str(ve.tsn_pdf_dir("highway_log_pdf")).replace("\\", "/")
      .endswith("tsn_library/highway_log/raw")
      and str(ve.tsn_pdf_dir("highway_sequence")).replace("\\", "/")
      .endswith("tsn_library/highway_sequence/raw")
      and str(ve.tsn_pdf_dir("highway_sequence_pdf")).replace("\\", "/")
      .endswith("tsn_library/highway_sequence/raw"))
check("clamp: default/garbage/low/high",
      (ve.clamp_examples(None), ve.clamp_examples("x"), ve.clamp_examples(0),
       ve.clamp_examples(99), ve.clamp_examples("7"))
      == (2, 2, 1, 10, 7))
wbp, imgp = ve.sibling_paths(Path(r"C:\x\comparisons\hd vs tsn.xlsx"))
check("sibling naming: '(evidence).xlsx' + '(evidence images)' folder",
      wbp.name == "hd vs tsn (evidence).xlsx"
      and imgp.name == "hd vs tsn (evidence images)")
_alias_tmp = Path(tempfile.mkdtemp(prefix="evidence_alias_guard_"))
try:
    _alias_cmp = _alias_tmp / "comparison.xlsx"
    _alias_wb, _alias_img = ve.sibling_paths(_alias_cmp)
    _alias_wb.write_bytes(b"selected source")
    try:
        ve._safe_sibling_paths(_alias_cmp, (_alias_wb,))
        _wb_alias_rejected = False
    except ValueError:
        _wb_alias_rejected = True
    check("the derived evidence workbook cannot alias a comparison source",
          _wb_alias_rejected and _alias_wb.read_bytes() == b"selected source")
    _alias_wb.unlink()
    _alias_img.mkdir()
    try:
        ve._safe_sibling_paths(_alias_cmp, (_alias_img,))
        _dir_alias_rejected = False
    except ValueError:
        _dir_alias_rejected = True
    check("the derived evidence image folder cannot alias a source directory",
          _dir_alias_rejected and _alias_img.is_dir())

    # Stable identity must survive a rename+decoy race across the image-folder
    # transaction, not merely compare the two current pathnames.
    _swap_source = _alias_tmp / "swap-source"
    _swap_source.mkdir()
    (_swap_source / "selected.txt").write_bytes(b"selected source directory")
    _swap_tmp = _alias_tmp / "rendered.tmp"
    _swap_tmp.mkdir()
    (_swap_tmp / "new.txt").write_bytes(b"new evidence")
    _swap_target = _alias_tmp / "evidence-images"
    _captured = ve.artifact_store.capture_source_identities((_swap_source,))
    _real_guard = ve.artifact_store.ensure_outputs_do_not_alias_sources
    _guard_calls = [0]

    def _swap_then_guard(destinations, sources, **kwargs):
        _guard_calls[0] += 1
        if _guard_calls[0] == 2:
            os.replace(_swap_source, _swap_target)
            _swap_source.mkdir()                    # same-name decoy
        return _real_guard(destinations, sources, **kwargs)

    ve.artifact_store.ensure_outputs_do_not_alias_sources = _swap_then_guard
    try:
        try:
            ve._swap_dir(
                _swap_tmp, _swap_target, source_paths=(_swap_source,),
                captured_sources=_captured)
            _swap_rejected = False
        except ValueError:
            _swap_rejected = True
    finally:
        ve.artifact_store.ensure_outputs_do_not_alias_sources = _real_guard
    check("a renamed evidence source plus decoy is rejected during folder swap",
          _swap_rejected)
    check("...the originally selected directory survives at its moved path",
          (_swap_target / "selected.txt").read_bytes()
          == b"selected source directory")

    # A guard failure after canonical target -> quarantine used to escape the
    # OSError-only handler and leave the canonical image directory missing.
    _rollback_target = _alias_tmp / "rollback-images"
    _rollback_target.mkdir()
    (_rollback_target / "prior.txt").write_bytes(b"prior image set")
    _rollback_tmp = _alias_tmp / "rollback-rendered"
    _rollback_tmp.mkdir()
    (_rollback_tmp / "new.txt").write_bytes(b"new image set")
    _source_checks = [0]

    def _fail_after_quarantine():
        _source_checks[0] += 1
        if _source_checks[0] == 2:
            raise ValueError("source set changed after quarantine")

    try:
        ve._swap_dir(_rollback_tmp, _rollback_target,
                     source_set_check=_fail_after_quarantine)
        _rollback_rejected = False
    except ValueError:
        _rollback_rejected = True
    check("ValueError after target quarantine restores the canonical directory",
          _rollback_rejected
          and (_rollback_target / "prior.txt").read_bytes() == b"prior image set"
          and (_rollback_tmp / "new.txt").read_bytes() == b"new image set")

    # The same rollback must run when the canonical publish first raises OSError
    # and a guard then fails before the alternate move (the former pre-alt gap).
    _late_target = _alias_tmp / "late-guard-images"
    _late_target.mkdir()
    (_late_target / "prior.txt").write_bytes(b"late prior image set")
    _late_tmp = _alias_tmp / "late-guard-rendered"
    _late_tmp.mkdir()
    (_late_tmp / "new.txt").write_bytes(b"late new image set")
    _late_checks = [0]
    _real_replace = ve.os.replace

    def _late_guard():
        _late_checks[0] += 1
        if _late_checks[0] == 3:       # fallback guard, after target -> old
            raise ValueError("source set changed before alternate")

    def _fail_canonical_publish(src, dst):
        if Path(src) == _late_tmp and Path(dst) == _late_target:
            raise PermissionError("simulated locked image destination")
        return _real_replace(src, dst)

    ve.os.replace = _fail_canonical_publish
    try:
        try:
            ve._swap_dir(_late_tmp, _late_target,
                         source_set_check=_late_guard)
            _late_rejected = False
        except ValueError:
            _late_rejected = True
    finally:
        ve.os.replace = _real_replace
    check("fallback guard failure also restores the quarantined prior set",
          _late_rejected
          and (_late_target / "prior.txt").read_bytes() == b"late prior image set"
          and (_late_tmp / "new.txt").read_bytes() == b"late new image set")

    # Fixed .old/.new names may already contain unrelated material. The swap
    # now uses random per-operation names and must never delete those sentinels.
    _foreign_target = _alias_tmp / "foreign-images"
    _foreign_target.mkdir()
    (_foreign_target / "prior.txt").write_bytes(b"prior")
    _foreign_tmp = _alias_tmp / "foreign-rendered"
    _foreign_tmp.mkdir()
    (_foreign_tmp / "new.txt").write_bytes(b"published")
    _fixed_old = _alias_tmp / "foreign-images.old"
    _fixed_new = _alias_tmp / "foreign-images.new"
    _fixed_old.mkdir(); (_fixed_old / "sentinel.txt").write_bytes(b"foreign old")
    _fixed_new.mkdir(); (_fixed_new / "sentinel.txt").write_bytes(b"foreign new")
    ve._swap_dir(_foreign_tmp, _foreign_target)
    check("foreign fixed .old/.new directories survive a successful swap",
          (_fixed_old / "sentinel.txt").read_bytes() == b"foreign old"
          and (_fixed_new / "sentinel.txt").read_bytes() == b"foreign new"
          and (_foreign_target / "new.txt").read_bytes() == b"published")

    # Workbook lock fallback is random + exclusively reserved too; a legacy
    # fixed '<stem>.new.xlsx' file is foreign and must remain byte-identical.
    _fallback_wb = _alias_tmp / "fallback evidence.xlsx"
    _fallback_wb.write_bytes(b"locked prior workbook")
    _fixed_wb_alt = _alias_tmp / "fallback evidence.new.xlsx"
    _fixed_wb_alt.write_bytes(b"foreign workbook sentinel")
    _fallback_images = _alias_tmp / "fallback-images"; _fallback_images.mkdir()
    _replace_calls = [0]
    _real_replace = ve.os.replace

    def _lock_only_primary(src, dst):
        if Path(dst) == _fallback_wb and _replace_calls[0] == 0:
            _replace_calls[0] += 1
            raise PermissionError("simulated workbook open in Excel")
        return _real_replace(src, dst)

    ve.os.replace = _lock_only_primary
    try:
        _fallback_note = ve._write_workbook(
            _fallback_wb, _fallback_images, [], {},
            {"report": "Probe", "comparison": "probe.xlsx",
             "examples": 1, "seed": "00000000",
             "tsmis_dir": "A", "tsn_dir": "B"})
    finally:
        ve.os.replace = _real_replace
    _random_alts = list(_alias_tmp.glob("fallback evidence.new-*.xlsx"))
    check("foreign fixed workbook .new sentinel is preserved",
          _fixed_wb_alt.read_bytes() == b"foreign workbook sentinel")
    check("locked workbook diverts only to a disclosed random fallback",
          len(_random_alts) == 1 and _random_alts[0].name in _fallback_note)

    # Matrix/Everything evidence is nested under an exact comparisons lease.
    # The lease must reach the workbook and image transactions as a target-aware
    # predicate, not merely as a one-time worker preflight.
    _leased_root = _alias_tmp / "leased-comparisons"
    _lease = ve.owned_dir.require_owned_dir_lease(
        _leased_root, kind="comparisons")
    _leased_tmp = _leased_root / "fresh-images"
    _leased_tmp.mkdir()
    (_leased_tmp / "new.txt").write_bytes(b"new leased images")
    _leased_target = _leased_root / "evidence-images"
    ve._swap_dir(
        _leased_tmp, _leased_target, commit_guard=_lease.guard,
        tmp_directory_identity=ve.owned_dir.directory_identity(_leased_tmp))
    check("a current comparisons lease authorizes the complete image swap",
          (_leased_target / "new.txt").read_bytes() == b"new leased images")

    _guarded_wb = _leased_root / "guarded evidence.xlsx"
    _guarded_wb.write_bytes(b"prior guarded workbook")
    _guarded_images = _leased_root / "guarded-images"
    _guarded_images.mkdir()
    _guard_paths = []

    def _deny_workbook_publish(path=None, **kwargs):
        if path is None:
            return _lease.is_current()
        path = Path(path)
        _guard_paths.append(path)
        return path != _guarded_wb and _lease.guard(path, **kwargs)

    try:
        ve._write_workbook(
            _guarded_wb, _guarded_images, [], {},
            {"report": "Probe", "comparison": "probe.xlsx",
             "examples": 1, "seed": "00000000",
             "tsmis_dir": "A", "tsn_dir": "B"},
            commit_guard=_deny_workbook_publish)
        _guarded_wb_rejected = False
    except ve.owned_dir.OwnershipError:
        _guarded_wb_rejected = True
    check("a late target-aware workbook guard preserves the prior workbook",
          _guarded_wb_rejected
          and _guarded_wb.read_bytes() == b"prior guarded workbook"
          and _guarded_wb in _guard_paths
          and not list(_leased_root.glob(".guarded evidence.tmp-*.xlsx")))

    # If the fresh temp becomes untrusted after prior images were quarantined,
    # rollback is still allowed through the live lease and restores last-good.
    _rollback_guard_target = _leased_root / "guard-rollback-images"
    _rollback_guard_target.mkdir()
    (_rollback_guard_target / "prior.txt").write_bytes(b"guarded prior")
    _rollback_guard_tmp = _leased_root / "guard-rollback-fresh"
    _rollback_guard_tmp.mkdir()
    (_rollback_guard_tmp / "new.txt").write_bytes(b"guarded new")
    _reject_guard_tmp = [False]
    _real_replace = ve.os.replace

    def _reject_temp_after_quarantine(src, dst):
        result = _real_replace(src, dst)
        if (Path(src) == _rollback_guard_target
                and Path(dst).name.startswith(
                    _rollback_guard_target.name + ".old-")):
            _reject_guard_tmp[0] = True
        return result

    def _selective_guard(path=None, **kwargs):
        if path is None:
            return _lease.is_current()
        if _reject_guard_tmp[0] and Path(path) == _rollback_guard_tmp:
            return False
        return _lease.guard(path, **kwargs)

    ve.os.replace = _reject_temp_after_quarantine
    try:
        try:
            ve._swap_dir(
                _rollback_guard_tmp, _rollback_guard_target,
                commit_guard=_selective_guard,
                tmp_directory_identity=ve.owned_dir.directory_identity(
                    _rollback_guard_tmp))
            _late_lease_rejected = False
        except ve.owned_dir.OwnershipError:
            _late_lease_rejected = True
    finally:
        ve.os.replace = _real_replace
    check("a guard failure after quarantine restores last-good images",
          _late_lease_rejected
          and (_rollback_guard_target / "prior.txt").read_bytes()
          == b"guarded prior"
          and (_rollback_guard_tmp / "new.txt").read_bytes()
          == b"guarded new")

    # Workbook serialization uses an exclusive unpredictable temp handle.  If
    # a selected source is moved onto that temp after serialization but before
    # publication, the post-save identity check must reject it and cleanup must
    # retain (not unlink) the selected object.
    _save_source = _alias_tmp / "save-source.xlsx"
    _save_source.write_bytes(b"selected workbook source")
    _save_prior = _save_source.read_bytes()
    _save_target = _alias_tmp / "evidence.xlsx"
    _save_img_dir = _alias_tmp / "empty-images"; _save_img_dir.mkdir()
    _save_captured = ve.artifact_store.capture_source_identities((_save_source,))
    _real_save = ve.Workbook.save
    _moved_save_temp = [None]

    def _save_then_swap_source(workbook, target):
        _real_save(workbook, target)
        target.flush()
        target.close()
        _moved_save_temp[0] = Path(target.name)
        os.replace(_save_source, _moved_save_temp[0])
        _save_source.write_bytes(b"same-path decoy")

    ve.Workbook.save = _save_then_swap_source
    try:
        try:
            ve._write_workbook(
                _save_target, _save_img_dir, [], {},
                {"report": "Probe", "comparison": "probe.xlsx",
                 "examples": 1, "seed": "00000000",
                 "tsmis_dir": "A", "tsn_dir": "B"},
                source_paths=(_save_source,),
                captured_sources=_save_captured)
            _save_swap_rejected = False
        except ValueError:
            _save_swap_rejected = True
    finally:
        ve.Workbook.save = _real_save
    check("a source moved onto the evidence temp at save-time is rejected",
          _save_swap_rejected and not _save_target.exists())
    check("...source-safe cleanup retains the selected workbook bytes",
          _moved_save_temp[0].read_bytes() == _save_prior)
    _moved_save_temp[0].unlink()

    _pdf_a = _alias_tmp / "pdf-a"; _pdf_a.mkdir()
    _pdf_b = _alias_tmp / "pdf-b"; _pdf_b.mkdir()
    (_pdf_a / "one.pdf").write_bytes(b"one")
    _pdf_initial = ve._pdf_source_files(_pdf_a, _pdf_b)
    _pdf_expected = ve.artifact_store.canonical_path_identities(
        (*_pdf_initial[0], *_pdf_initial[1]))
    ve._ensure_pdf_source_set(_pdf_a, _pdf_b, _pdf_expected)
    (_pdf_b / "late.pdf").write_bytes(b"late")
    try:
        ve._ensure_pdf_source_set(_pdf_a, _pdf_b, _pdf_expected)
        _pdf_add_rejected = False
    except ValueError:
        _pdf_add_rejected = True
    check("a PDF added after evidence discovery fails the set-equality tripwire",
          _pdf_add_rejected)
finally:
    shutil.rmtree(_alias_tmp, ignore_errors=True)
# The strip crop is a FULL-WIDTH page band stretched over the cell box
# (v0.26.0): the adapters' xspan covers only the record's own words, so a crop
# keyed to it clipped a blank cell's red box (drawn where the value WOULD
# print) and truncated the neighbors' longer text — the HSL clipped-box defect.
_cw = ve._crop_window(2000, 3000, (500, 100, 700, 110), (100, 110))
check("crop is full page width, record band ± the vertical context",
      _cw == (0, int((100 - ve._CTX_PT) * ve._SC), 2000,
              int((110 + ve._CTX_PT + 2) * ve._SC)))
_cw2 = ve._crop_window(2000, 3000, (500, 60, 700, 180), (100, 110))
check("a cell box taller than the record stretches the band over it",
      _cw2[1] == int(56 * ve._SC) and _cw2[3] == int(184 * ve._SC))
check("the band clamps to the page edges",
      ve._crop_window(2000, 300, (0, 0, 10, 10), (0, 4))[1] == 0
      and ve._crop_window(2000, 300, (0, 100, 10, 110), (110, 118))[3] == 300)
# The quote-characters clarifier: a diff whose values differ ONLY in quote
# characters ('' vs " vs ') prints near-identically, so the evidence header
# must SAY the difference is real and name both sides' characters (the
# censused case: Intersection Detail KER 046 @ 50.904).
_qn = ve._quote_note("''F'' ST", '"F" ST')
check("quote-only diff -> note names both sides' quote characters",
      "quote characters only" in _qn and "two apostrophes" in _qn
      and "a quotation mark" in _qn)
check("quote-only detection is direction- and kind-aware",
      "one apostrophe" in ve._quote_note("'F' ST", '"F" ST')
      and "TSMIS prints \" (a quotation mark)" in ve._quote_note('"F" ST', "''F'' ST"))
check("genuinely different values -> no note",
      ve._quote_note("MYRTLE ST", "SANFORD AVE") == ""
      and ve._quote_note("''F'' ST", '"F" AVE') == "")
check("identical values (incl. both blank) -> no note",
      ve._quote_note("''E'' ST", "''E'' ST") == ""
      and ve._quote_note(None, "") == "")
avail = ve.availability()
check("availability shape (rows/tsn_pdfs/ready/dir/reports/row_reports/deps_ok)",
      set(avail) >= {"rows", "tsn_pdfs", "ready", "dir", "reports", "row_reports",
                     "deps_ok"})
check("availability reports every evidence report, per-dir + source kind",
      [r["key"] for r in avail["reports"]]
      == ["highway_detail", "highway_log", "highway_sequence",
          "intersection_detail", "ramp_detail"]
      and all(set(r) >= {"key", "label", "tsn_pdfs", "dir", "source"}
              for r in avail["reports"])
      and {r["key"]: r["source"] for r in avail["reports"]}
      == {"highway_detail": "pdf", "highway_log": "raw",
          "highway_sequence": "raw", "intersection_detail": "pdf",
          "ramp_detail": "pdf"})
check("row_reports maps every capable row to its report (the per-cell action's gate)",
      avail["row_reports"] == ve.TSN_PDF_REPORT
      and set(avail["row_reports"]) == set(ve.rows()))

print("caller-side gate (matrix_build.evidence_opts_for)")
check("toggle off -> None",
      matrix_build.evidence_opts_for(None, "highway_detail", lambda s: s) is None
      and matrix_build.evidence_opts_for({"enabled": False, "examples": 5},
                                         "highway_detail", lambda s: s) is None)
check("unsupported row -> None",
      matrix_build.evidence_opts_for({"enabled": True}, "ramp_summary",
                                     lambda s: s) is None)
opts = matrix_build.evidence_opts_for({"enabled": True, "examples": 99},
                                      "highway_detail",
                                      lambda s: Path("cell") / s)
check("supported row -> resolved PDF dir + clamped examples",
      opts == {"tsmis_pdf_dir": Path("cell") / "highway_detail_pdf",
               "examples": 10})

# --------------------------------------------------------------------------- #
print("adapter LOCKSTEP pins vs the PDF consolidator")
check("window shapes: 10-cell line 1 + 25-cell line 2 == the 34 columns",
      chd.N_COLS_L1 == 10 and chd.N_COLS_L2 == 25 and len(hdc.HEADER) == 34
      and 9 + chd.N_COLS_L2 == len(hdc.HEADER))
check("postmile token regex accepts the glued forms the walk classifies on",
      all(chd.PM_TOKEN_RE.match(t)
          for t in ("S000.000", "000.000E", "R012.243R", "C043.925R"))
      and not chd.PM_TOKEN_RE.match("11 IMP 007"))
check("date-token guard: TASAS date yes, page-header date no",
      bool(chd.DATE_TOKEN_RE.search("64-01-01"))
      and not chd.DATE_TOKEN_RE.search("2026-07-07"))
check("FIELDS = every shared column except the key (PS included)",
      ehd.FIELDS == [f for f in cht.SHARED_HEADER if f != "Post Mile"]
      and "PS" in ehd.FIELDS and len(ehd.FIELDS) == 34)
check("TSN group map covers exactly FIELDS",
      set(ehd.TSN_GROUP) == set(ehd.FIELDS))
check("RB half of the TSN map is MIRRORED (inner before width before outer)",
      (ehd.TSN_GROUP["RB IN-TO"], ehd.TSN_GROUP["RB Wid"],
       ehd.TSN_GROUP["RB OT-TO"]) == ("rbto1", "rbwid", "rbto2"))

print("TSN print regexes on realistic two-line records")
l1 = "R 004.972E  000.123  11-08-01  D  F  Y15-05-18  LGNB  R  22-01-01  054062  S"
m1 = ehd.L1_RE.match(l1)
check("line 1: prefix + equation marker + sig-flagged eff + city all parse",
      bool(m1) and (m1.group("pp").strip(), m1.group("mile"), m1.group("ps"),
                    m1.group("city"), m1.group("ru"), m1.group("beg"))
      == ("R", "004.972", "E", "LGNB", "R", "22-01-01"))
l1b = "000.000  000.055  64-01-01  U  C  64-01-01  B  21-01-01  242400"
m1b = ehd.L1_RE.match(l1b)
check("line 1: bare PM, no city, no marker",
      bool(m1b) and m1b.group("pp") is None and m1b.group("ps") is None
      and m1b.group("city") is None and m1b.group("ru") == "B")
l2 = ("SANDHILLS DITCH  A  Y90-03-15  C  5  N  8  8  64  8  8  "
      "*90-03-15  H  7  F  12V  Y85-12-27  C  4  N  2  2  44  8  8")
m2 = ehd.L2_RE.match(l2)
check("line 2: desc + NA + the three sig-flagged blocks parse",
      bool(m2) and (m2.group("desc"), m2.group("na"), m2.group("lbeff"),
                    m2.group("medwda"), m2.group("rbto2"))
      == ("SANDHILLS DITCH", "A", "90-03-15", "12V", "8"))
l2e = ("A  Y90-03-15  C  5  N  8  8  64  8  8  "
       "*90-03-15  H  7  F  12V  Y85-12-27  C  4  N  2  2  44  8  8")
m2e = ehd.L2_RE.match(l2e)
check("line 2: EMPTY description still parses (the \\s* fix)",
      bool(m2e) and m2e.group("desc") == "" and m2e.group("na") == "A")
# the REAL fully-dittoed right-roadbed block from the D04 print (route 237 @
# R008.816L): width-matched '+' runs — an 8-char run for the dittoed eff DATE,
# '+++' for the 3-digit width.
l2d = ("EB 37-84K A 02-12-09 H 3 N 10 10 36 10 10 "
       "02-12-09 H 7 E 30V ++++++++ + ++ + ++ ++ +++ ++ ++")
m2d = ehd.L2_RE.match(l2d)
check("line 2: TSN width-matched DITTO runs parse (dates included)",
      bool(m2d) and (m2d.group("rbeff"), m2d.group("rbt"), m2d.group("rbln"),
                     m2d.group("rbwid"), m2d.group("rbtr2"))
      == ("++++++++", "+", "++", "+++", "++")
      and ehd.project("RB #Ln", m2d.group("rbln")) == "++"
      and ehd.project("RB Eff", m2d.group("rbeff")) == "++++++++")

print("span→box math (word-indexed line)")
ln = {"text": "AA BBB C", "offs": [(0, 2, {"x0": 10.0, "x1": 20.0}),
                                   (3, 6, {"x0": 30.0, "x1": 45.0}),
                                   (7, 8, {"x0": 55.0, "x1": 60.0})]}
check("value span boxes its words", ehd._span_box(ln, 3, 6) == (30.0, 45.0))
check("empty span boxes the neighbor gap",
      ehd._span_box(ln, 3, 3) == (21.0, 29.0))

print("verification projections")
check("PS is marker-derived", ehd.project("PS", "E") == "E"
      and ehd.project("PS", "") == "" and ehd.project("PS", None) == "")
check("other fields ride the comparator's own projection (NA fold, WDA glue)",
      ehd.project("NA", "A") == "" and ehd.project("NA", "N") == "N"
      and ehd.project("Med V/WDA", "8V") == "08V")

# --------------------------------------------------------------------------- #
print("diff enumeration (unique keys + sidecar)")
def _row(route, key, **over):
    r = [route] + [""] * len(cht.SHARED_HEADER)
    r[1 + cht.SHARED_HEADER.index("Post Mile")] = key
    for f, v in over.items():
        r[1 + cht.SHARED_HEADER.index(f)] = v
    return r

a_rows = [_row("001", "001.000", **{"LB Wid": "24"}),
          _row("001", "002.000", **{"LB Wid": "24"}),   # dup key: excluded
          _row("001", "002.000", **{"LB Wid": "25"}),
          _row("001", "003.000", **{"AC": "F"})]
b_rows = [_row("001", "001.000", **{"LB Wid": "26"}),
          _row("001", "002.000", **{"LB Wid": "24"}),
          _row("001", "003.000", **{"AC": "F"})]
sc = {("001", "001.000"): [("06", "TUL")], ("001", "003.000"): [("06", "TUL")]}
diffs = ehd.enumerate_diffs(a_rows, b_rows, sc)
check("only the unique-key LB Wid diff is enumerated, with its district",
      list(diffs) == ["LB Wid"] and len(diffs["LB Wid"]) == 1
      and diffs["LB Wid"][0]["key"] == "001.000"
      and (diffs["LB Wid"][0]["dist"], diffs["LB Wid"][0]["cnty"]) == ("06", "TUL")
      and (diffs["LB Wid"][0]["va"], diffs["LB Wid"][0]["vb"]) == ("24", "26"))

# --------------------------------------------------------------------------- #
print("TSN loader sidecar contract")
tmp = Path(tempfile.mkdtemp())
try:
    raw_dir = tmp / "raw"
    raw_dir.mkdir()
    raw = raw_dir / "raw.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = cht.TSN_SHEET
    cols = list(cht.TSN_RAW_HEADER)
    ws.append(cols)
    base = {c: "" for c in cols}
    base.update(DIST="06", CNTY="TUL.", RTE="99", PP="R", POSTMILE="004.972",
                E_IND="E", HG="R", LENGTH="0.123", NON_ADD="A", M_WID="8",
                M_VA="V", DESCRIPTION="X  Y")
    ws.append([base[c] for c in cols])
    wb.save(raw)
    wb.close()

    rows_locked = cht.tsn_rows_from_raw(raw)
    rows_dcr, dcr = tlh.tsn_rows_with_dcr(raw)
    check("tsn_rows_with_dcr rows are IDENTICAL to the locked loader's",
          rows_dcr == rows_locked and len(rows_dcr) == 1)
    check("…and the sidecar carries (district, county-dot-stripped)",
          dcr == [("06", "TUL")])

    # the normalized library sheet: shared header + EXACTLY the sidecar columns
    out = tmp / "norm.xlsx"
    res = tlh.build_into(raw_dir, out, events=None, confirm_overwrite=lambda p: True)
    nwb = load_workbook(out)
    nws = nwb[cht.NORMALIZED_SHEET]
    hdr = [c.value for c in nws[1]]
    first = [c.value for c in nws[2]]
    nwb.close()
    check("normalized header = Route + shared + sidecar",
          res.status == "ok"
          and hdr == ["Route"] + cht.SHARED_HEADER + tlh.SIDECAR_HEADER)
    check("normalized row carries the sidecar values at the tail",
          first[-2:] == ["06", "TUL"] and first[0] == "099")

    # load_sides reads the sidecar back; the comparator side stays shared-width
    a_cons = tmp / "cons.xlsx"
    cw = Workbook()
    cs = cw.active
    cs.title = cht.TSMIS_SHEET
    cs.append(["Route"] + [f"c{i}" for i in range(1, 35)])
    cs.append(["099", "R004.972R", "000.123"] + [""] * 32)
    cw.save(a_cons)
    cw.close()
    ar, br, sc2, note = ehd.load_sides(a_cons, out)
    check("load_sides: rows in comparator shape, sidecar keyed by (route,key)",
          note is None and len(ar) == 1 and len(br) == 1
          and len(br[0]) == 1 + len(cht.SHARED_HEADER)
          and sc2.get(("099", br[0][1])) == [("06", "TUL")])
    check("both sides land on the same canonical key (roadbed-aware)",
          ar[0][1] == br[0][1] == "R004.972R")

    # a LEGACY normalized library (no sidecar) is refused with the rebuild hint
    old = tmp / "old.xlsx"
    ow = Workbook()
    os_ = ow.active
    os_.title = cht.NORMALIZED_SHEET
    os_.append(["Route"] + cht.SHARED_HEADER)
    os_.append(br[0])
    ow.save(old)
    ow.close()
    _a, _b, sc3, note3 = ehd.load_sides(a_cons, old)
    check("legacy library -> sidecar None + 'rebuild the TSN library' hint",
          sc3 is None and note3 and "rebuild the TSN library" in note3)
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Intersection Detail adapter (v0.22.0): maps + windows + LOCKSTEP")
import compare_intersection_detail_tsn as idt                # noqa: E402
import consolidate_tsmis_intersection_detail_pdf as idpdf    # noqa: E402
import evidence_intersection_detail as eid                   # noqa: E402
import tsn_load_intersection_detail as tli                   # noqa: E402

check("ID FIELDS = every shared column except the key (34 — District/County "
      "joined per ID-79; Route Suffix included)",
      eid.FIELDS == [f for f in idt.SHARED_HEADER if f != idt.KEY]
      and "Route Suffix" in eid.FIELDS and "District" in eid.FIELDS
      and "County" in eid.FIELDS and len(eid.FIELDS) == 34)
check("ID TSMIS cell map covers exactly FIELDS",
      set(eid._TSMIS_CELL) == set(eid.FIELDS))
check("ID TSN cell map covers exactly FIELDS",
      set(eid.TSN_CELL) == set(eid.FIELDS))
_l1n = {n for n, _lo, _hi in eid._L1_WIN}
_l2n = {n for n, _lo, _hi in eid._L2_WIN}
check("every TSN cell target has a fixed window on its line",
      all((n in _l1n if ln == 1 else n in _l2n)
          for ln, n in eid.TSN_CELL.values()))
check("ID TSMIS value positions mirror the comparator's (consolidated - Route)",
      eid._TSMIS_SRC == {f: p - 1 for f, p in idt._TSMIS_POS.items()})
check("Xing Line Lgth: TSMIS boxes rowB window 17, TSN boxes LINE 1's X-OVR "
      "(each side its own print position)",
      eid._TSMIS_CELL["Xing Line Lgth"] == (2, 17)
      and eid.TSN_CELL["Xing Line Lgth"] == (1, "X_CROSS_OVERRIDE"))
check("the Intrte swap mirrored: TSMIS boxes Route at rowB window 12",
      eid._TSMIS_CELL["Intrte Route"] == (2, 12)
      and eid._TSMIS_CELL["Intrte PM Suffix"] == (2, 16))
check("Route Suffix boxes the Location cell on both sides",
      eid._TSMIS_CELL["Route Suffix"] == (1, 3)
      and eid.TSN_CELL["Route Suffix"] == (1, "LOC"))
check("LOCKSTEP handles the consolidator's own pieces (rowA/rowB discriminators)",
      idpdf._is_rowA(["", "000.204", "", "12 ORA 001"] + [""] * 17)
      and bool(idpdf.INT_ROWB_RE.match("11050"))
      and bool(idpdf.OLD_PM_RE.match("0.204")))

print("ID TSN print: fixed windows, max-overlap, flag strip, LOC tokens")
check("LOC tokenizer: 3-char / dotted / 2-char counties + a route suffix",
      bool(eid._LOC_RE.match("12 ORA 001")) and bool(eid._LOC_RE.match("04 CC. 004"))
      and bool(eid._LOC_RE.match("07 LA 001")) and bool(eid._LOC_RE.match("07 LA 210U"))
      and not eid._LOC_RE.match("NB ON FROM SB RTE 5"))
_w1 = [{"t": "R", "x0": 14.0, "x1": 19.0}, {"t": "000.204", "x0": 25.0, "x1": 59.0},
       {"t": "12", "x0": 72.0, "x1": 82.0}, {"t": "ORA", "x0": 86.0, "x1": 101.0},
       {"t": "210U", "x0": 106.0, "x1": 125.0},
       {"t": "Y91-08-24", "x0": 406.0, "x1": 454.0}]
_a1 = eid._assign_win(_w1, eid._L1_WIN)
check("LOCATION is ONE window (a 2-char county can't shift the route out of it)",
      _a1["LOC"][0] == "12 ORA 210U")
check("max-overlap: a signature-flagged date leaning left stays in its DATE window",
      _a1["EFF_DATE_LT"][0] == "Y91-08-24" and _a1["TY_CT"][0] == "")
_l1 = {"page": 3, "words": _w1, "top": 100.0, "bottom": 110.0}
_w2 = [{"t": "JCT", "x0": 72.0, "x1": 86.0}, {"t": "5", "x0": 90.0, "x1": 95.0}]
_l2 = {"page": 3, "words": _w2, "top": 111.0, "bottom": 121.0}
_rec = {"l1": _l1, "a1": _a1, "l2": _l2, "a2": eid._assign_win(_w2, eid._L2_WIN),
        "dist": "12"}
check("the glued flag is stripped from the VALUE ('Y91-08-24' -> 1991-08-24)…",
      eid._tsn_raw(_rec, "Lighting Eff-Date") == "91-08-24"
      and eid.tsn_value(_rec, "Lighting Eff-Date") == "1991-08-24")
_pg, _box, _yspan, _xspan = eid.tsn_box(_rec, "Lighting Eff-Date")
check("…while the BOX keeps the printed token (flag included)",
      _pg == 3 and _box[0] <= 406.0 and _box[2] >= 454.0)
_pg2, _box2, _y2, _x2 = eid.tsn_box(_rec, "Int St Eff-Date")
check("a BLANK cell boxes its fixed template window (the window IS the cell)",
      _pg2 == 3 and 405 <= _box2[0] <= 415 and 440 <= _box2[2] <= 460
      and _box2[1] < _box2[3])
check("Route Suffix reads the LOC route token ('210U' -> 'U')",
      eid.tsn_value(_rec, "Route Suffix") == "U")

print("ID diff enumeration: unique keys, sidecar, the comparison's own trim")
def _idrow(route, pm, **over):
    r = [route] + [""] * len(idt.SHARED_HEADER)
    r[1 + idt.KEY_FIELD] = pm
    for f, v in over.items():
        r[1 + idt.SHARED_HEADER.index(f)] = v
    return r

_ar = [_idrow("001", "0.204", HG="D", Description="A  B"),
       _idrow("001", "1.000", HG="D"),      # dup key: excluded
       _idrow("001", "1.000", HG="U")]
_br = [_idrow("001", "0.204", HG="U", Description="A B"),
       _idrow("001", "1.000", HG="D")]
_sc = {("001", "0.204"): [("12", "ORA")]}
_diffs = eid.enumerate_diffs(_ar, _br, _sc)
check("only the unique-key HG diff is enumerated, with its district/county",
      list(_diffs) == ["HG"] and len(_diffs["HG"]) == 1
      and (_diffs["HG"][0]["dist"], _diffs["HG"][0]["cnty"]) == ("12", "ORA")
      and (_diffs["HG"][0]["va"], _diffs["HG"][0]["vb"]) == ("D", "U"))
check("a whitespace-run-only difference is NOT enumerated (compare_core's trim)",
      "Description" not in _diffs)

print("ID TSN loader sidecar contract")
tmp2 = Path(tempfile.mkdtemp())
try:
    raw_dir2 = tmp2 / "raw"
    raw_dir2.mkdir()
    raw2 = raw_dir2 / "raw.xlsx"
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = idt.TSN_SHEET
    cols2 = list(idt.TSN_RAW_HEADER)
    ws2.append(cols2)
    _b2 = {c: "" for c in cols2}
    _b2.update(PP="R", POST_MILE=" 000.204", LOCATION="04 CC. 004",
               DATE_REC="73-10-19", HG="D", RU="U", X_CROSS_OVERRIDE="0250")
    ws2.append([_b2[c] for c in cols2])
    wb2.save(raw2)
    wb2.close()

    rows_locked2 = idt.tsn_rows_from_raw(raw2)
    rows_dcr2, dcr2 = tli.tsn_rows_with_dcr(raw2)
    check("tsn_rows_with_dcr rows are IDENTICAL to the locked loader's",
          rows_dcr2 == rows_locked2 and len(rows_dcr2) == 1)
    check("…and the sidecar carries (district, county-dot-stripped)",
          dcr2 == [("04", "CC")])

    out2 = tmp2 / "norm.xlsx"
    res2 = tli.build_into(raw_dir2, out2, events=None, confirm_overwrite=lambda p: True)
    nwb2 = load_workbook(out2)
    nws2 = nwb2[idt.NORMALIZED_SHEET]
    hdr2 = [c.value for c in nws2[1]]
    first2 = [c.value for c in nws2[2]]
    nwb2.close()
    check("normalized header = Route + shared + sidecar (v3 shape, XLL included)",
          res2.status == "ok"
          and hdr2 == ["Route"] + idt.SHARED_HEADER + tli.SIDECAR_HEADER
          and "Xing Line Lgth" in hdr2 and "ML 2nd Eff-Date" not in hdr2)
    check("normalized row carries the sidecar values at the tail",
          first2[-2:] == ["04", "CC"] and first2[0] == "004")

    a_cons2 = tmp2 / "cons.xlsx"
    cw2 = Workbook()
    cs2 = cw2.active
    cs2.title = idt.TSMIS_SHEET
    cs2.append(["Route"] + [f"c{i}" for i in range(1, 35)] + ["Xing Line Lgth"])
    _r2 = [None] * 36
    _r2[0], _r2[1], _r2[2], _r2[4] = "004", "R", "000.204", "04 CC. 004"
    cs2.append(_r2)
    cw2.save(a_cons2)
    cw2.close()
    ar2, br2, sc22, note2 = eid.load_sides(a_cons2, out2)
    check("load_sides: rows in comparator shape, sidecar keyed by (route,key)",
          note2 is None and len(ar2) == 1 and len(br2) == 1
          and len(br2[0]) == 1 + len(idt.SHARED_HEADER)
          and sc22.get(("004", br2[0][1 + idt.KEY_FIELD])) == [("04", "CC")])
    # CMP-AUD-045: the keys are county-aware PhysicalKeys — identity-equal
    # across sides, displaying the normalized PM text.
    check("both sides land on the same physical key (display '0.204')",
          ar2[0][1 + idt.KEY_FIELD] == br2[0][1 + idt.KEY_FIELD]
          and str(ar2[0][1 + idt.KEY_FIELD]) == "0.204")

    old2 = tmp2 / "old.xlsx"
    ow2 = Workbook()
    os2 = ow2.active
    os2.title = idt.NORMALIZED_SHEET
    os2.append(["Route"] + idt.SHARED_HEADER)
    os2.append(br2[0])
    ow2.save(old2)
    ow2.close()
    _a2, _bx2, sc32, note32 = eid.load_sides(a_cons2, old2)
    check("legacy library -> sidecar None + 'rebuild the TSN library' hint",
          sc32 is None and note32 and "rebuild the TSN library" in note32)
finally:
    import shutil
    shutil.rmtree(tmp2, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("on-demand per-cell evidence (v0.23.0): the freshness gate")
import time                                                # noqa: E402
import matrix                                              # noqa: E402

tmp3 = Path(tempfile.mkdtemp())
try:
    store = tmp3 / "cell" / "highway_detail_pdf"
    store.mkdir(parents=True)
    consolidated = matrix.consolidated_store_path(store, "highway_detail_pdf")
    tsn = tmp3 / "tsn.xlsx"
    cmpwb = tmp3 / "cmp.xlsx"
    pdfdir = tmp3 / "pdfs"

    def _touch(p, when):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        os.utime(p, (when, when))

    def _publish_comparison(p):
        import hashlib
        st = p.stat()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        member = {
            "flavor": "values", "relative_path": p.name, "path": str(p),
            "canonical_path_at_write": str(p.resolve()),
            "commit_role": "canonical", "sha256": digest,
            "size": st.st_size, "mtime_ns": st.st_mtime_ns,
        }
        typed = ComparisonOutcome(
            status="ok", completion="complete", verdict="match",
            counts=ComparisonCounts(known=True, paired_rows=1),
            pairing_quality="exact")
        generation = ArtifactGeneration(
            generation_id="evidence-fixture", members=(member,),
            content_digests={"values": digest}, completion="complete",
            publication_state="committed", requested_mode="values")
        result = ConsolidateResult(
            status="ok", output_path=str(p), verdict="match",
            completion="complete", skipped_inputs=0, failed_inputs=0,
            comparison_outcome=typed, artifact_generation=generation)
        assert consolidation_meta.write_comparison_outcomes(result)

    def _publish_consolidation(p):
        assert consolidation_meta.write_outcome(
            p, ConsolidateResult(
                status="ok", output_path=str(p), completion="complete",
                skipped_inputs=0, failed_inputs=0))

    def _gate_error(expected_generation="evidence-fixture"):
        try:
            matrix.run_evidence_only("highway_detail_pdf", store,
                                     "highway_detail_pdf", tsn, cmpwb, pdfdir,
                                     events=None, examples=2,
                                     source_identity_check=lambda: True,
                                     expected_generation_id=expected_generation,
                                     source_workbook_identity=(
                                         tsn_library.normalized_workbook_identity(tsn)),
                                     live_tsn_path=tsn)
        except ValueError as e:
            return str(e)
        return None

    try:
        matrix.run_evidence_only("ramp_summary", store, "ramp_summary", tsn, cmpwb,
                                 pdfdir, events=None)
        _cap_err = None
    except ValueError as e:
        _cap_err = str(e)
    check("an evidence-incapable row is refused with the reason",
          _cap_err and "doesn't support evidence images" in _cap_err)

    _touch(tsn, time.time() - 200)
    err = _gate_error()
    check("missing comparison -> 'run the comparison first'",
          err and "run the comparison first" in err)

    now = time.time()
    _touch(cmpwb, now - 50)
    _publish_comparison(cmpwb)
    generation_err = _gate_error("wrong-generation")
    check("cache generation mismatch is refused before evidence rendering",
          generation_err and "cache generation do not match" in generation_err)
    err = _gate_error()
    check("missing consolidated -> 'run the comparison first'",
          err and "no consolidated" in err and "run the comparison first" in err)

    # a store file NEWER than the consolidated -> the store-changed refusal
    _touch(consolidated, now - 100)
    artifact_store.write_consolidated_fingerprint(consolidated, store)
    _publish_consolidation(consolidated)
    _touch(store / "highway_detail_route_001.pdf", now - 20)
    err = _gate_error()
    check("store changed since the consolidation -> refuse with the refresh hint",
          err and "exports changed" in err and "refresh the comparison" in err)

    # consolidated fresh vs store, but NEWER than the comparison -> refuse.
    # (No fingerprint sidecar exists for this synthetic store; stub the staleness
    # probe so the mtime gates are what's under test.)
    _real_stale = matrix._consolidated_stale
    matrix._consolidated_stale = lambda *_a, **_k: False
    try:
        _touch(consolidated, now - 10)
        err = _gate_error()
        check("consolidated newer than the comparison -> refuse with the hint",
              err and "newer than" in err and "refresh the comparison" in err)

        _touch(consolidated, now - 100)
        _touch(tsn, now - 5)
        err = _gate_error()
        check("TSN workbook newer than the comparison -> refuse with the hint",
              err and "TSN workbook is newer" in err)

        # everything consistent -> the gate passes through to the generator; a
        # stubbed generate proves the call shape + the ok result + note.
        _touch(tsn, now - 200)
        import visual_evidence as _ve2
        _real_gen = _ve2.generate
        _ve2.generate = (lambda *_a, **_k:
                         {"note": "evidence: 2 example(s) across 1/1 …"})
        try:
            res = matrix.run_evidence_only(
                "highway_detail_pdf", store, "highway_detail_pdf", tsn, cmpwb,
                pdfdir, events=None, examples=2,
                source_identity_check=lambda: True,
                expected_generation_id="evidence-fixture",
                source_workbook_identity=(
                    tsn_library.normalized_workbook_identity(tsn)),
                live_tsn_path=tsn)
        finally:
            _ve2.generate = _real_gen
        check("fresh inputs -> ok result carrying the generator's note",
              res.status == "ok" and "example(s)" in (res.message or "")
              and res.summary_lines == [res.message])
    finally:
        matrix._consolidated_stale = _real_stale
finally:
    import shutil
    shutil.rmtree(tmp3, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Highway Log adapter (v0.24.0): fields, window map, routing, ditto discipline")
check("FIELDS = every Highway Log column except the Location key",
      ehl.FIELDS == [f for f in hlc.HEADER if f != hlc.HEADER[0]]
      and len(ehl.FIELDS) == 30)
check("field -> TSN window map is positional over ROW_KEYS and complete "
      "(Description alone has no window — its own follow-on lines)",
      ehl._TSN_WIN_KEY == dict(zip(hlc.HEADER, ctnl.ROW_KEYS))
      and all(f == "Description" or ehl._TSN_WIN_KEY[f] in ehl._TSN_WINDOWS
              for f in ehl.FIELDS))
check("verification projection == the comparator's load normalization + Excel TRIM "
      "(tab-padded values compare clean, numerics match the trim)",
      ehl.project("HG", "D\t\t") == "D"
      and ehl.project("Length (MI) [MI]", " 000.075 ") == "000.075")
check("canonical key: the comparator's roadbed_canonical_location (suffix "
      "authoritative; a dittoed LEFT block tags the row R)",
      ehl._canon(["012.887R"] + [None] * 30) == "012.887R"
      and ehl._canon(["012.887"] + [None] * 9 + ["+"] * 8 + [None] * 13) == "012.887R")
check("district_index is the sentinel single-folder entry (per-print routing)",
      ehl.district_index(Path("C:/anywhere")) == {"": Path("C:/anywhere")})
# Ditto discipline: a `+`-run cell on either side is NON-ASSERTING in the
# comparison, so enumerate_diffs must never sample it — while a genuine text
# diff in the same row still enumerates.
_hl_a = ["001"] + ["012.887"] + ["a"] * 30
_hl_b = ["001"] + ["012.887"] + ["a"] * 30
_hl_a[2], _hl_b[2] = "X", "+"                       # ditto side -> non-asserting
_hl_a[3], _hl_b[3] = "Y", "Z"                       # a real diff
_diffs = ehl.enumerate_diffs([_hl_a], [_hl_b], {"routing": "per-print"})
check("enumerate_diffs skips ditto cells but keeps real diffs (compared_cell semantics)",
      hlc.HEADER[1] not in _diffs and [e["key"] for e in _diffs[hlc.HEADER[2]]] == ["012.887"]
      and _diffs[hlc.HEADER[2]][0]["dist"] == "" and _diffs[hlc.HEADER[2]][0]["cnty"] == "")
check("enumerate_diffs judges through the LIVE schema (ditto_nonasserting set)",
      chl_cmp._SCHEMA.ditto_nonasserting is True)
# load_sides refuses per-route (route-less) workbooks: evidence groups by the
# leading Route column, which a per-route export doesn't carry.
_hl_tmp = Path(tempfile.mkdtemp(prefix="tsmis_ev_hl_"))
_wb = Workbook()
_ws = _wb.active
_ws.title = chl_cmp.SHEET_NAME
_ws.append(hlc.HEADER)                              # per-route: NO Route column
_ws.append(["012.887"] + ["a"] * 30)
_wb.save(_hl_tmp / "per_route.xlsx")
_r_t, _r_n, _sc, _note = ehl.load_sides(str(_hl_tmp / "per_route.xlsx"),
                                        str(_hl_tmp / "per_route.xlsx"))
check("load_sides refuses per-route (route-less) workbooks with a clear note",
      _sc is None and "Route column" in (_note or ""))
_wb2 = Workbook()
_ws2 = _wb2.active
_ws2.title = chl_cmp.SHEET_NAME
_ws2.append([hlc.ROUTE_COL] + hlc.HEADER)           # consolidated shape
_ws2.append(["001", "012.887"] + ["a"] * 30)
_wb2.save(_hl_tmp / "consolidated.xlsx")
_r_t, _r_n, _sc2, _note2 = ehl.load_sides(str(_hl_tmp / "consolidated.xlsx"),
                                          str(_hl_tmp / "consolidated.xlsx"))
check("load_sides accepts consolidated workbooks (truthy routing sidecar, no note)",
      _sc2 == {"routing": "per-print"} and _note2 is None
      and len(_r_t) == 1 and _r_t[0][0] == "001")
import shutil as _sh
_sh.rmtree(_hl_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Highway Sequence adapter (v0.25.0): fields, maps, routing, context discipline")
check("FIELDS = every shared column except the PM key",
      ehsl.FIELDS == [f for f in chsl_cmp.SHARED_HEADER if f != "PM"]
      and len(ehsl.FIELDS) == 6)
check("field -> TSMIS print column / TSN print window maps are complete",
      all(f in ehsl._TSMIS_COL for f in ehsl.FIELDS)
      and all(f == "Description" or f in ehsl._TSN_WIN for f in ehsl.FIELDS))
check("verification projection == the comparator's per-field normalization + TRIM "
      "(route-prefix strip + whitespace collapse on Description; county period)",
      ehsl.project("Description", "001/NB  OFF TO X ") == "NB OFF TO X"
      and ehsl.project("County", "LA.") == "LA"
      and ehsl.project("FT", " H\t") == "H")
check("canonical key: 'COUNTY GLUED-POSTMILE', county normalized",
      ehsl._canon("LA.", "R000.129") == "LA R000.129"
      and ehsl._canon("ORA", "018.530E") == "ORA 018.530E")
check("district_index is the sentinel single-folder entry (per-print routing)",
      ehsl.district_index(Path("C:/anywhere")) == {"": Path("C:/anywhere")})
# Context discipline: HG / City / Distance are CONTEXT fields (never counted by
# the comparison), so enumerate_diffs must never sample them — while FT and
# Description diffs in the same row still enumerate.
_hs_a = ["001", "ORA", "R000.129", "LGNB", "D", "H", "000.100", "JCT 5"]
_hs_b = ["001", "ORA", "R000.129", "",     "U", "I", "000.900", "JCT 5 UC"]
_hs_diffs = ehsl.enumerate_diffs([_hs_a], [_hs_b], {"routing": "per-print"})
check("enumerate_diffs skips context fields but keeps FT + Description diffs",
      set(_hs_diffs) == {"FT", "Description"}
      and [e["key"] for e in _hs_diffs["FT"]] == ["ORA R000.129"]
      and _hs_diffs["FT"][0]["dist"] == "" and _hs_diffs["FT"][0]["cnty"] == "")
check("enumerate_diffs judges through the LIVE schema (context fields set)",
      set(chsl_cmp._SCHEMA.context_fields)
      == {"HG", "City", "Distance To Next Point"})
# LOCKSTEP pins vs the PDF consolidator: the wrap join, the PM-less data test,
# the trailer heading, and the evidence twin of the word classifier.
check("join_desc_parts: bare after a hyphen, one space otherwise, empties skipped",
      chslp.join_desc_parts(["UC 55-", "1107"]) == "UC 55-1107"
      and chslp.join_desc_parts(["A", "", "B"]) == "A B"
      and chslp.join_desc_parts(["", "X"]) == "X")
check("PM-less data rows accepted (END OF ROUTE / CITY END), furniture rejected",
      chslp._is_pmless_data({"pm": "", "prefix": "", "suffix": "",
                             "desc": "END OF ROUTE 043", "hg": "D", "ft": "H",
                             "county": "", "city": "", "dist": "000.000"})
      and not chslp._is_pmless_data({"pm": "", "prefix": "", "suffix": "Direction:",
                                     "desc": "S - N", "hg": "", "ft": "",
                                     "county": "", "city": "", "dist": ""})
      and not chslp._is_pmless_data({"pm": "", "prefix": "", "suffix": "",
                                     "desc": "", "hg": "D", "ft": "H",
                                     "county": "", "city": "", "dist": ""}))
check("the trailer heading pin (parsing hard-stops there)",
      chslp.TRAILER_HEADING == "Unresolved Intersections")
# The evidence classifier is the word-object-keeping TWIN of the consolidator's:
# the same synthetic line must classify identically through both.
_hd7 = {"COUNTY": {"x0": 31, "x1": 68}, "CITY": {"x0": 84, "x1": 103},
        "PM": {"x0": 149, "x1": 163}, "HG": {"x0": 201, "x1": 214},
        "FT": {"x0": 225, "x1": 235}, "NEXT": {"x0": 251, "x1": 274},
        "DESCRIPTION": {"x0": 317, "x1": 376}}
_bounds = chslp._boundaries(_hd7)
_line = [{"text": "ORA", "x0": 40, "x1": 59}, {"text": "LGNB", "x0": 82, "x1": 105},
         {"text": "R", "x0": 127, "x1": 133}, {"text": "000.129", "x0": 140, "x1": 173},
         {"text": "E", "x0": 184, "x1": 189}, {"text": "D", "x0": 204, "x1": 211},
         {"text": "H", "x0": 233, "x1": 239}, {"text": "000.124", "x0": 262, "x1": 294},
         {"text": "COUNTY", "x0": 317, "x1": 353}, {"text": "BEGIN:", "x0": 356, "x1": 384}]
_vals = chslp._classify_words(_line, _bounds)
_cols = ehsl._classify_line_words(_line, _bounds)
check("consolidator + evidence classify one line identically (LOCKSTEP twin)",
      _vals == {k: " ".join(w["text"] for w in ws) for k, ws in _cols.items()}
      and _vals["county"] == "ORA" and _vals["prefix"] == "R"
      and _vals["pm"] == "000.129" and _vals["suffix"] == "E"
      and _vals["hg"] == "D" and _vals["ft"] == "H"
      and _vals["dist"] == "000.124" and _vals["desc"] == "COUNTY BEGIN:")
# load_sides refuses a NON-consolidated TSMIS workbook (no Route column) with the
# comparator's own hint, and accepts the consolidated + normalized-TSN pair.
_hs_tmp = Path(tempfile.mkdtemp(prefix="tsmis_ev_hsl_"))
_wbp = Workbook()
_wsp = _wbp.active
_wsp.title = chsl_cmp.TSMIS_SHEET
_wsp.append(["County", "City", None, "PM", None, "HG", "FT",
             "Distance To Next Point", "Description"])   # per-route: NO Route col
_wsp.append(["ORA", None, "R", "000.129", None, "D", "H", "000.124", "X"])
_wbp.save(_hs_tmp / "per_route.xlsx")
_wbn = Workbook()
_wsn = _wbn.active
_wsn.title = ctnsl.NORMALIZED_SHEET
_wsn.append(ctnsl.NORMALIZED_HEADER)
_wsn.append(["001", "ORA", "R000.129", None, "D", "H", "000.102", "X"])
_wbn.save(_hs_tmp / "tsn.xlsx")
_r_t, _r_n, _sc3, _note3 = ehsl.load_sides(str(_hs_tmp / "per_route.xlsx"),
                                           str(_hs_tmp / "tsn.xlsx"))
check("load_sides refuses per-route (route-less) workbooks with a clear note",
      _sc3 is None and "consolidate first" in (_note3 or ""))
_wbc = Workbook()
_wsc = _wbc.active
_wsc.title = chsl_cmp.TSMIS_SHEET
_wsc.append(["Route", "County", "City", None, "PM", None, "HG", "FT",
             "Distance To Next Point", "Description"])    # consolidated shape
_wsc.append(["001", "ORA", None, "R", "000.129", None, "D", "H", "000.124", "X"])
_wbc.save(_hs_tmp / "consolidated.xlsx")
_r_t, _r_n, _sc4, _note4 = ehsl.load_sides(str(_hs_tmp / "consolidated.xlsx"),
                                           str(_hs_tmp / "tsn.xlsx"))
check("load_sides accepts the consolidated + normalized-TSN pair (glued key both sides)",
      _sc4 == {"routing": "per-print"} and _note4 is None
      and len(_r_t) == 1 and _r_t[0][0] == "001" and _r_t[0][2] == "R000.129"
      and len(_r_n) == 1 and _r_n[0][2] == "R000.129")
_sh.rmtree(_hs_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Ramp Detail adapter (v0.26.0): fields, maps, projections, dual-row discipline")
check("FIELDS = the union of both flavors' compared columns (PM key + the two "
      "always-context TSN columns excluded; District joined in CMP-AUD-185)",
      erd.FIELDS == ["PR", "District", "Date of Record", "HG", "Area 4",
                     "City Code", "R/U", "Description", "On/Off", "Ramp Type"])
check("field -> TSMIS print column / TSN print window maps are complete",
      all(f in erd._TSMIS_COL for f in erd.FIELDS)
      and all(f in erd.TSN_CELL for f in erd.FIELDS)
      and set(erd._TSMIS_COL.values()) <= set(crdpdf._COL_ORDER) | {"loc"}
      and all(n in {w[0] for w in erd._L_WIN} for n in erd.TSN_CELL.values()))
check("TSN windows are x-ordered and non-overlapping (the fixed template)",
      all(erd._L_WIN[i][2] <= erd._L_WIN[i + 1][1]
          for i in range(len(erd._L_WIN) - 1)))
check("verification projection == the PDF flavor's per-field normalization + TRIM "
      "(route-prefix strip + collapse + the null-render message on Description; "
      "the '-' null marks; the print's N -> TSN's O)",
      erd.project("Description", "001/NB  OFF TO X ") == "NB OFF TO X"
      and erd.project("Description", "NO RAMP LINEAR EVENT") == ""
      and erd.project("Area 4", "-") == ""
      and erd.project("On/Off", "-") == ""
      and erd.project("On/Off", "N") == "O"
      and erd.project("On/Off", "F") == "F"
      and erd.project("Date of Record", "02/25/1976") == "1976-02-25"
      and erd.project("Ramp Type", " D ") == "D")
# Dual-row discipline: the Excel row's comparison keeps On/Off + Ramp Type as
# context (never enumerated); the PDF row's comparison COMPARES them. Ramp Name
# and ADT never enumerate on either row.
# The PM key cells carry the D4 PhysicalKey (CMP-AUD-045); District is a
# compared column, equal here so it never enumerates.
_rd_k = crd_cmp._physical_pm_key("001", "ORA", "000.606",
                                 (("route", "001"),), "fixture")
_rd_a = ["001", "R", _rd_k, "12", "1976-02-25", "D", "Y", "DAPT", "U",
         "NB OFF X", "", "O", "D", ""]
_rd_b = ["001", "M", crd_cmp._physical_pm_key("001", "ORA", "000.606",
                                              (("route", "001"),), "fixture"),
         "12", "1976-02-25", "L", "Y", "DAPT", "U",
         "NB OFF Y", "RAMP NM", "F", "L", "070"]
_dc = {("001", _rd_k): [("12", "ORA")]}
_dx = erd.enumerate_diffs([_rd_a], [_rd_b], {"dc": _dc, "pdf": False})
check("Excel-row enumerate_diffs skips the print-only + TSN-only columns",
      set(_dx) == {"PR", "HG", "Description"}
      and _dx["PR"][0]["dist"] == "12" and _dx["PR"][0]["cnty"] == "ORA")
_dp = erd.enumerate_diffs([_rd_a], [_rd_b], {"dc": _dc, "pdf": True})
check("PDF-row enumerate_diffs ALSO samples On/Off + Ramp Type (compared there)",
      set(_dp) == {"PR", "HG", "Description", "On/Off", "Ramp Type"})
check("enumerate_diffs judges through the LIVE schemas (context sets)",
      set(crd_cmp._SCHEMA.context_fields)
      == {"Ramp Name", "On/Off", "Ramp Type", "ADT"}
      and set(crdp.TSMIS_PDF_VS_TSN._schema.context_fields)
      == {"Ramp Name", "ADT"})
# LOCKSTEP pins vs the PDF consolidator: the wrap join, the PM test, the prefix
# legend, and the null-render tokens the projections must keep matching.
check("join_desc_parts: bare after a hyphen, one space otherwise, empties skipped",
      crdpdf.join_desc_parts(["UC 55-", "1107"]) == "UC 55-1107"
      and crdpdf.join_desc_parts(["A", "", "B"]) == "A B")
check("the PM row test + prefix legend pins",
      crdpdf.PM_RE.fullmatch("000.606") and not crdpdf.PM_RE.fullmatch("0.606")
      and crdpdf.PREFIX_SET == frozenset("CDGHLMNRST"))
check("the null-render token pins (the comparison flavors project these)",
      crdp._NULL_DESC == "NO RAMP LINEAR EVENT" and crdp._NULL_MARK == "-")
# The consolidated-workbook source detector: the PDF-consolidated carries the
# print-only "On/Off" header; the Excel-consolidated doesn't.
_rd_tmp = Path(tempfile.mkdtemp(prefix="tsmis_ev_rd_"))
_wbe = Workbook()
_wse = _wbe.active
_wse.title = crd_cmp.TSMIS_SHEET
_wse.append(["Route", "Location", None, "PM", "Date of Record", None, "HG",
             "Area 4", None, "City Code", "R/U", "Description"])
_wse.append(["001", "12-ORA-001", "R", "000.606", "02/25/1976", None, "D", "Y",
             "DAPT", "U", "001/NB OFF X", None])
_wbe.save(_rd_tmp / "excel_cons.xlsx")
_wbP = Workbook()
_wsP = _wbP.active
_wsP.title = crd_cmp.TSMIS_SHEET
_wsP.append(["Route"] + list(crdpdf.HEADER))
_wsP.append(["001", "12-ORA-001", "R", "000.606", "02/25/1976", None, "D", "Y",
             "DAPT", "U", "001/NB OFF X", None, "N", "D"])
_wbP.save(_rd_tmp / "pdf_cons.xlsx")
check("_is_pdf_consolidated tells the two consolidated shapes apart",
      erd._is_pdf_consolidated(str(_rd_tmp / "pdf_cons.xlsx"))
      and not erd._is_pdf_consolidated(str(_rd_tmp / "excel_cons.xlsx")))
# load_sides on a sidecar-less normalized TSN library returns the rebuild note
# instead of guessing (the pre-v3 library case).
_wbn = Workbook()
_wsn = _wbn.active
_wsn.title = crd_cmp.NORMALIZED_SHEET
_wsn.append(["Route"] + [h for h in crd_cmp.SHARED_HEADER if h != "District"]
            + ["TSN District", "TSN County"])           # v3: pre-county identity
_wsn.append(["001", "R", "000.606", "1976-02-25", "D", "Y", "DAPT", "U",
             "NB OFF X", "", "O", "D", "", "12", "ORA"])
_wbn.save(_rd_tmp / "tsn_v2.xlsx")
_t_r, _t_n, _meta, _note = erd.load_sides(str(_rd_tmp / "pdf_cons.xlsx"),
                                          str(_rd_tmp / "tsn_v2.xlsx"))
check("load_sides refuses a sidecar-less (pre-v3) TSN library with the rebuild note",
      _meta is None and "rebuild the TSN library" in (_note or ""))
_sh.rmtree(_rd_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("engine misc")
check("reason summarizer dedupes and caps",
      ve._summarize_reasons(["a", "a", "b", "c", "d"]) == "a; b; c"
      and ve._summarize_reasons([]) == "no candidates")
check("evidence never keys off visible text (regex sanity: safe filename)",
      re.sub(r"[^A-Za-z0-9]+", "_", "Med V/WDA").strip("_") == "Med_V_WDA")

# ----------------------------------------------------------------------------- #
print("the pdf/ drop folder exists for the user (v0.21.1 — the update-day gap)")
import paths                                              # noqa: E402
import report_catalog                                     # noqa: E402
_pdf_drop_reports = set(ve.TSN_PDF_REPORT.values()) - ve._TSN_PDFS_IN_RAW
check("every pdf/-drop TSN source is catalog-flagged evidence_pdfs (and only those)",
      {report_catalog.TSN[[e.subdir for e in report_catalog.TSN].index(r)].evidence_pdfs
       for r in _pdf_drop_reports} == {True}
      and {e.subdir for e in report_catalog.TSN if e.evidence_pdfs}
      == _pdf_drop_reports)
check("every raw-sourced evidence report is a district_pdfs TSN library (its "
      "prints ARE the raw inputs, so no pdf/ drop folder is flagged)",
      all(report_catalog.TSN[[e.subdir for e in report_catalog.TSN].index(r)].raw_kind
          == "district_pdfs"
          and not report_catalog.TSN[[e.subdir for e in report_catalog.TSN]
                                     .index(r)].evidence_pdfs
          for r in ve._TSN_PDFS_IN_RAW)
      and ve._TSN_PDFS_IN_RAW <= set(ve.TSN_PDF_REPORT.values()))
_tmp = Path(tempfile.mkdtemp())
_old_root = paths.TSN_LIBRARY_ROOT
try:
    paths.TSN_LIBRARY_ROOT = _tmp / "tsn_library"
    root = tsn_library.ensure_layout()
    pdf = root / "highway_detail" / "pdf"
    check("ensure_layout creates highway_detail/pdf/ + drops the hint",
          pdf.is_dir() and any(pdf.glob("_PUT TSN DISTRICT PDFS HERE.txt")))
    check("…and the pdf/ path == the engine's tsn_pdf_dir (one location)",
          pdf == ve.tsn_pdf_dir("highway_detail") == tsn_library.pdf_dir("highway_detail"))
    ipdf = root / "intersection_detail" / "pdf"
    check("ensure_layout creates intersection_detail/pdf/ + its hint (v0.22.0)",
          ipdf.is_dir() and any(ipdf.glob("_PUT TSN DISTRICT PDFS HERE.txt")))
    check("…and it too == the engine's tsn_pdf_dir",
          ipdf == ve.tsn_pdf_dir("intersection_detail")
          == tsn_library.pdf_dir("intersection_detail"))
    rpdf = root / "ramp_detail" / "pdf"
    check("ensure_layout creates ramp_detail/pdf/ + its hint (v0.26.0)",
          rpdf.is_dir() and any(rpdf.glob("_PUT TSN DISTRICT PDFS HERE.txt")))
    check("…and it too == the engine's tsn_pdf_dir",
          rpdf == ve.tsn_pdf_dir("ramp_detail")
          == tsn_library.pdf_dir("ramp_detail"))
    readme = root / tsn_library._README_NAME
    check("the root README documents BOTH pdf/ folders",
          readme.is_file()
          and "highway_detail/pdf/" in readme.read_text(encoding="utf-8")
          and "intersection_detail/pdf/" in readme.read_text(encoding="utf-8"))
    # an OUTDATED readme (an updated install) refreshes on the next launch
    readme.write_text("old text from a previous version\n", encoding="utf-8")
    tsn_library.ensure_layout()
    check("a stale README from an older install is refreshed",
          "highway_detail/pdf/" in readme.read_text(encoding="utf-8"))
finally:
    paths.TSN_LIBRARY_ROOT = _old_root
    import shutil as _sh
    _sh.rmtree(_tmp, ignore_errors=True)

print()
if _fail:
    print(f"FAILED: {len(_fail)} check(s):")
    for f in _fail:
        print(f"  - {f}")
    sys.exit(1)
print("check_visual_evidence: all checks passed")
