"""Golden checks for the post-mile CODE vocabulary gate (CMP-AUD-063).

The TSMIS Highway Sequence (PDF) and Ramp Detail (PDF) parsers know the accepted
post-mile prefix vocabulary (`PREFIX_SET`) and — for Highway Sequence — the one
documented nonblank equate suffix ("E", `SUFFIX_SET`). Before this gate, an
unexpected PREFIX was logged but KEPT under a COMPLETE producer outcome, and
Highway Sequence never validated the suffix at all (a stray `Z` was silently
accepted). Such a token alters the canonical post-mile key and can turn a
schema/extraction anomaly into ordinary one-sided comparison rows with no durable
indication the source was suspect.

The fix (census-first — the bound 7.9 ssor-prod corpus carries ONLY accepted
tokens, so this never false-fires there): the parsers count every unexpected
prefix/suffix token in a structured `bad_tokens` diagnostic, and the producer
escalates the combined-workbook completion to at least PARTIAL. The versioned
vocabulary (`PM_VOCAB_VERSION`) makes a future legend addition a deliberate bump.

These tests are hermetic and CI-safe: the vocabulary rule is unit-tested
exhaustively, and hand-rolled positioned-Helvetica fixture PDFs drive the REAL
pdfplumber consolidators end to end (no real corpus needed) to prove the
escalation fires on an unexpected token and stays COMPLETE on a clean render.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_pm_code_vocabulary.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))            # for _hl_fixture_pdf

from _hl_fixture_pdf import make_pdf                      # noqa: E402

import outcome                                            # noqa: E402
import pdf_table_lib                                      # noqa: E402
from events import Events                                 # noqa: E402
import consolidate_tsmis_highway_sequence_pdf as HSL      # noqa: E402
import consolidate_tsmis_ramp_detail_pdf as RD            # noqa: E402


def _check(msg, cond):
    if not cond:
        raise AssertionError(msg)
    print(f"  ok  {msg}")


# --------------------------------------------------------------------------- #
# 1. the vocabulary rule — exhaustive (every known code, blank, lowercase,
#    joined, multi-char, unknown, on BOTH sides of the PM)
# --------------------------------------------------------------------------- #
def test_helper_vocabulary():
    print("unexpected_pm_tokens — the membership rule:")
    u = pdf_table_lib.unexpected_pm_tokens
    P = frozenset("CDGHLMNRST")
    S = frozenset("E")

    # The two parsers own the versioned vocabulary; lock the values.
    _check("HSL PREFIX_SET is the legend codes", HSL.PREFIX_SET == P)
    _check("HSL SUFFIX_SET is the equate suffix 'E'", HSL.SUFFIX_SET == S)
    _check("RD PREFIX_SET is the legend codes", RD.PREFIX_SET == P)
    _check("HSL vocab version == 1", HSL.PM_VOCAB_VERSION == 1)
    _check("RD vocab version == 1", RD.PM_VOCAB_VERSION == 1)

    # Every KNOWN prefix code is accepted (no suffix).
    for c in "CDGHLMNRST":
        _check(f"prefix {c!r} accepted", u(c, "", prefix_set=P, suffix_set=S) == [])
    # BLANK windows are the common case — never flagged.
    _check("blank prefix + blank suffix", u("", "", prefix_set=P, suffix_set=S) == [])
    # The one accepted nonblank suffix.
    _check("suffix 'E' accepted", u("", "E", prefix_set=P, suffix_set=S) == [])
    _check("valid prefix + valid suffix", u("R", "E", prefix_set=P, suffix_set=S) == [])

    # LOWERCASE is not the same token (exact membership).
    _check("lowercase prefix 'c'", u("c", "", prefix_set=P, suffix_set=S) == [("prefix", "c")])
    _check("lowercase suffix 'e'", u("", "e", prefix_set=P, suffix_set=S) == [("suffix", "e")])
    # JOINED / MULTI-CHAR windows.
    _check("joined prefix 'CE'", u("CE", "", prefix_set=P, suffix_set=S) == [("prefix", "CE")])
    _check("multi prefix 'QQ'", u("QQ", "", prefix_set=P, suffix_set=S) == [("prefix", "QQ")])
    _check("multi suffix 'EE'", u("", "EE", prefix_set=P, suffix_set=S) == [("suffix", "EE")])
    # UNKNOWN single letters.
    _check("unknown prefix 'Q'", u("Q", "", prefix_set=P, suffix_set=S) == [("prefix", "Q")])
    _check("unknown suffix 'Z'", u("", "Z", prefix_set=P, suffix_set=S) == [("suffix", "Z")])
    # BOTH sides bad -> two entries, prefix first.
    _check("both bad -> 2", u("Q", "Z", prefix_set=P, suffix_set=S)
           == [("prefix", "Q"), ("suffix", "Z")])
    _check("valid prefix + bad suffix -> only suffix",
           u("R", "Z", prefix_set=P, suffix_set=S) == [("suffix", "Z")])

    # Ramp Detail has NO suffix column: the empty default suffix_set means a
    # (never-passed) suffix would be strict, and the prefix-only calls behave.
    _check("RD no-suffix: valid prefix", u("R", "", prefix_set=P) == [])
    _check("RD no-suffix: unknown prefix", u("Q", "", prefix_set=P) == [("prefix", "Q")])
    _check("empty suffix_set rejects any suffix text",
           u("", "E", prefix_set=P) == [("suffix", "E")])


# --------------------------------------------------------------------------- #
# 2. fixture PDFs — the exact column-window layouts the two parsers anchor on
# --------------------------------------------------------------------------- #
def _hsl_page(rows, route="001"):
    """A Highway Sequence (PDF) data page: the 7 header words at wide,
    boundary-robust x-positions, a route banner, then one line per row dict
    (prefix/pm/suffix/desc placed at their window centers)."""
    header = [(30, 70, "COUNTY"), (110, 70, "CITY"), (210, 70, "PM"),
              (300, 70, "HG"), (360, 70, "FT"), (430, 70, "NEXT"),
              (520, 70, "DESCRIPTION")]
    banner = [(30, 50, f"District: 07 Route: {route} Direction: W - E")]
    runs = banner + header
    top = 110
    for r in rows:
        runs.append((30, top, "LA"))                     # county
        if r.get("prefix"):
            runs.append((165, top, r["prefix"]))         # prefix window ~[140,200)
        runs.append((205, top, r["pm"]))                 # PM window ~[200,233)
        if r.get("suffix"):
            runs.append((262, top, r["suffix"]))         # suffix window ~[233,296)
        runs.append((522, top, r.get("desc", "PLACE")))  # description
        top += 20
    return runs


def _rd_page(rows, route="001"):
    """A Ramp Detail (PDF) data page: the 7 multi-letter header words + the 4
    single-letter columns (the prefix 'E' between LOCATION and PM; the R/U,
    On/Off, Type letters between CODE and DESCRIPTION) the parser requires, a
    route banner, then one line per row dict (pr/pm/desc at window centers)."""
    header = [(20, 70, "LOCATION"), (90, 70, "E"), (140, 70, "PM"),
              (180, 70, "RECORD"), (240, 70, "AREA"), (290, 70, "CITY"),
              (340, 70, "CODE"), (380, 70, "U"), (410, 70, "F"), (440, 70, "Y"),
              (480, 70, "DESCRIPTION")]
    banner = [(30, 50, f"Route: {route} Direction: W - E")]
    runs = banner + header
    top = 110
    for r in rows:
        runs.append((20, top, "LA"))                     # location
        if r.get("prefix"):
            runs.append((103, top, r["prefix"]))         # pr window ~[84,128)
        runs.append((133, top, r["pm"]))                 # PM window ~[128,172)
        runs.append((480, top, r.get("desc", "RAMP")))   # description
        top += 20
    return runs


def _consolidate(module, page, tmp, fname):
    in_dir = tmp / "in"
    in_dir.mkdir(parents=True, exist_ok=True)
    make_pdf(in_dir / fname, [page])
    logs = []
    result = module.consolidate(
        events=Events(on_log=logs.append), confirm_overwrite=lambda _p: True,
        input_dir=in_dir, out_path=tmp / "out.xlsx", converted_dir=tmp / "conv")
    return result, logs


def test_hsl_parse_and_escalation():
    print("Highway Sequence (PDF) — parse + escalation:")
    tmp = Path(tempfile.mkdtemp(prefix="cmp063_hsl_"))
    try:
        fname = "highway_sequence_route_001.pdf"
        bad_rows = [
            dict(prefix="Q", pm="001.000", suffix="", desc="ALPHA"),   # bad prefix
            dict(prefix="", pm="002.000", suffix="Z", desc="BETA"),    # bad suffix
            dict(prefix="R", pm="003.000", suffix="E", desc="GAMMA"),  # clean
        ]
        p = tmp / fname
        make_pdf(p, [_hsl_page(bad_rows)])
        rows, stats = HSL.parse_pdf(str(p), Events())
        seen = [(r[2], r[3], r[4]) for r in rows]         # (prefix, pm, suffix)
        _check(f"HSL parsed 3 data rows (got {len(rows)}: {seen})", len(rows) == 3)
        _check(f"HSL counted BOTH unexpected tokens (bad_tokens={stats['bad_tokens']}, "
               f"rows={seen})", stats["bad_tokens"] == 2)
        _check("HSL kept the clean R/003.000/E row", ("R", "003.000", "E") in seen)

        result, logs = _consolidate(HSL, _hsl_page(bad_rows), tmp, fname)
        _check(f"HSL combine ok (status={result.status}: {result.message!r})",
               result.status == "ok")
        _check(f"HSL escalates to PARTIAL (completion={result.completion!r})",
               result.completion == outcome.PARTIAL)
        _check("HSL summary names the unexpected-token note",
               any("unexpected postmile code token" in ln for ln in result.summary_lines))
        _check("HSL log names the token + vocab version",
               any("unexpected postmile" in ln and "vocab v1" in ln for ln in logs))

        # A CLEAN render must NOT false-fire (census invariant, in miniature).
        clean_rows = [dict(prefix="R", pm="001.000", suffix="E", desc="GAMMA"),
                      dict(prefix="", pm="002.000", suffix="", desc="DELTA")]
        clean_tmp = tmp / "clean"
        clean_tmp.mkdir()
        r2, _ = _consolidate(HSL, _hsl_page(clean_rows), clean_tmp, fname)
        _check(f"HSL clean render stays COMPLETE (completion={r2.completion!r})",
               r2.completion == outcome.COMPLETE)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rd_parse_and_escalation():
    print("Ramp Detail (PDF) — parse + escalation (no suffix column):")
    tmp = Path(tempfile.mkdtemp(prefix="cmp063_rd_"))
    try:
        fname = "tsar_ramp_detail_route_001.pdf"
        bad_rows = [
            dict(prefix="Q", pm="001.000", desc="RAMP A"),   # bad prefix
            dict(prefix="R", pm="002.000", desc="RAMP B"),   # clean
        ]
        p = tmp / fname
        make_pdf(p, [_rd_page(bad_rows)])
        rows, stats = RD.parse_pdf(str(p), Events())
        seen = [(r[1], r[2]) for r in rows]               # (pr, pm)
        _check(f"RD parsed 2 data rows (got {len(rows)}: {seen})", len(rows) == 2)
        _check(f"RD counted the unexpected prefix (bad_tokens={stats['bad_tokens']}, "
               f"rows={seen})", stats["bad_tokens"] == 1)
        _check("RD kept the clean R/002.000 row", ("R", "002.000") in seen)

        result, logs = _consolidate(RD, _rd_page(bad_rows), tmp, fname)
        _check(f"RD combine ok (status={result.status}: {result.message!r})",
               result.status == "ok")
        _check(f"RD escalates to PARTIAL (completion={result.completion!r})",
               result.completion == outcome.PARTIAL)
        _check("RD summary names the unexpected-token note",
               any("unexpected postmile code token" in ln for ln in result.summary_lines))
        _check("RD log names the token + vocab version",
               any("unexpected postmile" in ln and "vocab v1" in ln for ln in logs))

        clean_rows = [dict(prefix="R", pm="001.000", desc="RAMP A"),
                      dict(prefix="", pm="002.000", desc="RAMP B")]
        clean_tmp = tmp / "clean"
        clean_tmp.mkdir()
        r2, _ = _consolidate(RD, _rd_page(clean_rows), clean_tmp, fname)
        _check(f"RD clean render stays COMPLETE (completion={r2.completion!r})",
               r2.completion == outcome.COMPLETE)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _loud_hsl_page():
    # 1 clean row + 3 lines the parser can't classify (invalid PM + a non-desc
    # column present) -> emitted 1, unclassified 3 (the finding's exact scenario).
    return _hsl_page([dict(prefix="R", pm="001.000", suffix="E", desc="GOOD"),
                      dict(pm="XYZ", desc="BAD1"), dict(pm="QQQ", desc="BAD2"),
                      dict(pm="ZZZ", desc="BAD3")])


def _loud_rd_page():
    return _rd_page([dict(prefix="R", pm="001.000", desc="GOOD"),
                     dict(pm="XYZ", desc="BAD1"), dict(pm="QQQ", desc="BAD2"),
                     dict(pm="ZZZ", desc="BAD3")])


def test_line_anomalies_are_not_file_counts():
    """CMP-AUD-064: unparsed LINE anomalies (unclassified lines / stray fragments)
    must NOT fill the file-level skipped_inputs — ONE PDF with three malformed lines
    is ONE affected input, not three skips. They escalate completion, ride a
    structured parse-anomalies diagnostic, and stay file-bounded."""
    print("line anomalies stay out of the file-count fields (CMP-AUD-064):")
    for tag, module, page_fn, stem in (
            ("HSL", HSL, _loud_hsl_page, "highway_sequence_route_001.pdf"),
            ("RD", RD, _loud_rd_page, "tsar_ramp_detail_route_001.pdf")):
        tmp = Path(tempfile.mkdtemp(prefix="cmp064_"))
        try:
            result, _logs = _consolidate(module, page_fn(), tmp, stem)
            _check(f"{tag} combine ok (status={result.status})", result.status == "ok")
            _check(f"{tag} escalates to PARTIAL (3 unparsed lines)",
                   result.completion == outcome.PARTIAL)
            # The one PDF converted cleanly (emitted a row), so ZERO files were
            # skipped or failed — the 3 unparsed lines must not inflate either field
            # (before the fix skipped_inputs was 3; the clamp alone would leave 1).
            _check(f"{tag} skipped_inputs is 0, NOT the 3 unparsed lines "
                   f"(got {result.skipped_inputs}; 1 clean PDF)",
                   result.skipped_inputs == 0)
            _check(f"{tag} failed_inputs is 0 (got {result.failed_inputs})",
                   result.failed_inputs == 0)
            pe = (result.producer_extra or {}).get("parse_anomalies", {})
            _check(f"{tag} the 3 unparsed lines ride the structured diagnostic "
                   f"(parse_anomalies={pe})", pe.get("unparsed_lines") == 3)
            _check(f"{tag} summary names the unparsed-line note",
                   any("unparsed line" in ln for ln in result.summary_lines))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _hsl_damaged(rows, route="001"):
    """A Highway Sequence data page that lost its DESCRIPTION column-header anchor
    but still carries data rows (a postmile) — the CMP-AUD-055 damaged-header page."""
    return [r for r in _hsl_page(rows, route) if r[2] != "DESCRIPTION"]


def _rd_damaged(rows, route="001"):
    """A Ramp Detail data page that lost its DESCRIPTION anchor but still carries
    data rows — the CMP-AUD-055 damaged-header page."""
    return [r for r in _rd_page(rows, route) if r[2] != "DESCRIPTION"]


def test_damaged_header_data_page():
    """CMP-AUD-055: once a document has entered its data section, a page with
    data-shaped rows (a postmile) but missing/damaged column-header anchors is
    flagged (damaged_pages) and escalates the producer to PARTIAL — instead of
    being skipped wholesale as a cover/legend, silently dropping the data. Censused
    0-occurrence, so a clean multi-page render stays COMPLETE."""
    print("damaged-header data page escalates, not skipped (CMP-AUD-055):")
    for tag, module, clean_fn, dmg_fn, stem in (
            ("HSL", HSL, _hsl_page, _hsl_damaged, "highway_sequence_route_001.pdf"),
            ("RD", RD, _rd_page, _rd_damaged, "tsar_ramp_detail_route_001.pdf")):
        clean = clean_fn([dict(prefix="R", pm="001.000", suffix="E", desc="ALPHA")])
        damaged = dmg_fn([dict(prefix="", pm="002.000", suffix="", desc="BETA")])
        tmp = Path(tempfile.mkdtemp(prefix="cmp055_"))
        try:
            in_dir = tmp / "in"
            in_dir.mkdir()
            # page 1 establishes the data section; page 2 is the damaged data page.
            make_pdf(in_dir / stem, [clean, damaged])
            logs = []
            result = module.consolidate(
                events=Events(on_log=logs.append), confirm_overwrite=lambda _p: True,
                input_dir=in_dir, out_path=tmp / "out.xlsx", converted_dir=tmp / "conv")
            _check(f"{tag} combine ok (status={result.status})", result.status == "ok")
            _check(f"{tag} damaged-header data page escalates to PARTIAL "
                   f"(completion={result.completion!r})",
                   result.completion == outcome.PARTIAL)
            pe = (result.producer_extra or {}).get("parse_anomalies", {})
            _check(f"{tag} rides parse_anomalies.damaged_header_pages "
                   f"(pe={pe}, skipped={result.skipped_inputs})",
                   pe.get("damaged_header_pages") == 1 and result.skipped_inputs == 0
                   and result.failed_inputs == 0)
            _check(f"{tag} summary + log name the CMP-AUD-055 page",
                   any("no column header" in ln for ln in result.summary_lines
                       + logs) or any("CMP-AUD-055" in ln for ln in logs))

            # a clean multi-page render (no damaged page) stays COMPLETE.
            clean_tmp = tmp / "clean"
            clean_tmp.mkdir()
            make_pdf(clean_tmp / stem, [clean, clean_fn(
                [dict(prefix="", pm="003.000", suffix="", desc="GAMMA")])])
            r2 = module.consolidate(
                events=Events(), confirm_overwrite=lambda _p: True,
                input_dir=clean_tmp, out_path=clean_tmp / "out.xlsx",
                converted_dir=clean_tmp / "conv")
            _check(f"{tag} clean multi-page render stays COMPLETE "
                   f"(completion={r2.completion!r})", r2.completion == outcome.COMPLETE)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_clamp_invariant():
    """CMP-AUD-064: the shared _clamp_input_counts caps file-level skipped/failed to
    the discovered input count — a leaked line-anomaly count can never present as an
    impossible source count; a legitimate count is left untouched."""
    print("file-count clamp invariant (CMP-AUD-064):")
    from events import ConsolidateResult
    logs = []
    r = ConsolidateResult(status="ok", skipped_inputs=3, failed_inputs=0)
    pdf_table_lib._clamp_input_counts(r, 1, Events(on_log=logs.append))
    _check(f"skipped_inputs=3 with 1 discovered clamps to 1 (got {r.skipped_inputs})",
           r.skipped_inputs == 1)
    _check("the clamp logs a NOTE", any("exceeds 1 discovered" in ln for ln in logs))
    r2 = ConsolidateResult(status="ok", skipped_inputs=1, failed_inputs=1)
    pdf_table_lib._clamp_input_counts(r2, 5, Events())
    _check(f"legitimate counts (1,1 of 5) are untouched "
           f"(got {r2.skipped_inputs},{r2.failed_inputs})",
           r2.skipped_inputs == 1 and r2.failed_inputs == 1)


def main():
    test_helper_vocabulary()
    test_hsl_parse_and_escalation()
    test_rd_parse_and_escalation()
    test_line_anomalies_are_not_file_counts()
    test_damaged_header_data_page()
    test_clamp_invariant()
    print("OK  post-mile code vocabulary (CMP-AUD-063): the membership rule is "
          "exhaustively locked, and an unexpected prefix/suffix escalates both "
          "PDF consolidators to PARTIAL while a clean render stays COMPLETE. "
          "CMP-AUD-064: line-level anomalies stay out of the file-count fields.")


if __name__ == "__main__":
    main()
