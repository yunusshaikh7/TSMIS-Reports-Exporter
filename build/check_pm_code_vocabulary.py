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


def main():
    test_helper_vocabulary()
    test_hsl_parse_and_escalation()
    test_rd_parse_and_escalation()
    print("OK  post-mile code vocabulary (CMP-AUD-063): the membership rule is "
          "exhaustively locked, and an unexpected prefix/suffix escalates both "
          "PDF consolidators to PARTIAL while a clean render stays COMPLETE.")


if __name__ == "__main__":
    main()
