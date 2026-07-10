"""Golden check for the TSMIS Highway Log (PDF) consolidator's row-drop
RECONCILIATION (scripts/consolidate_tsmis_highway_log_pdf.py).

The cell-rect PDF parser used to drop two classes of row SILENTLY: data-looking
lines on a page with no derivable column band, and data parsed with a previous
page's carried-forward geometry. parse_pdf now returns a `stats` dict
(emitted / skipped_no_geometry / stale_geometry_pages / carried_validated_pages)
and consolidate() surfaces those as banners in summary_lines (and WARNING logs).
Since v0.26.2 a carried-geometry page is VALIDATED (every printed token must fit
one window — pdf_table_lib.carried_line_crossings == 0): validated pages are
ordinary output (an info line, completion COMPLETE); only a page whose text does
NOT fit the carry keeps the ⚠ + PARTIAL escalation. The emit logic is unchanged
— this proves the reconciliation + escalation policy is wired and visible.

parse_pdf is monkeypatched (no real PDF needed, CI-safe) so the check exercises
the consolidate() surfacing path with synthetic anomaly counts.

P12 extends this with the INDEPENDENT expected-row oracle (pdf_row_oracle): it
reconciles against the SAME parse_pdf 3-tuple contract by a different method (text
lines vs cell rectangles), so a row drop is flagged for the P13 evidence kit. Per
RM04 the oracle + capture path ship in v0.18.0; proving the parser correct against
REAL returned PDFs is v0.18.1 acceptance.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsmis_pdf_reconcile.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidate_tsmis_highway_log_pdf as M
import outcome
from events import Events

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _run(in_files):
    """Drive consolidate() over `in_files` (name -> stats), parse_pdf stubbed."""
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_pdf_recon_"))
    in_dir = tmp / "in"
    in_dir.mkdir()
    for name in in_files:
        (in_dir / name).write_bytes(b"%PDF-1.4")

    def fake_parse(path, events, pdf_name=""):
        name = Path(path).name
        stats = dict(in_files[name])
        route = stats.pop("route")
        rows = [["000.001"] + ["x"] * 30]            # one valid 31-col row
        return route, rows, stats

    saved = M.parse_pdf
    M.parse_pdf = fake_parse
    try:
        return M.consolidate(events=Events(), confirm_overwrite=lambda _p: True,
                             input_dir=in_dir, out_path=tmp / "out.xlsx",
                             converted_dir=tmp / "conv")
    finally:
        M.parse_pdf = saved


def oracle_cross_check():
    """The independent oracle reconciles against the SAME parse_pdf 3-tuple the
    consolidator produces — a row drop is flagged for the P13 evidence kit, with the
    parser's own drop stats surfaced. Counts only; no cell contents (RM05)."""
    import pdf_row_oracle as O

    def parse_stub(path, events, pdf_name=""):
        rows = [["%03d.000" % i] + ["x"] * 30 for i in range(2)]   # parser emits 2
        return "001", rows, {"emitted": 2, "pages": 1,
                             "skipped_no_geometry": 3, "stale_geometry_pages": 0,
                             "carried_validated_pages": 1}

    def five_postmile_lines(_path):
        yield ["%03d.001  a  b  c" % i for i in range(5)]          # oracle sees 5

    rec = O.capture_evidence("r001.pdf", parse_stub, page_lines_fn=five_postmile_lines)
    check("oracle reconciles the parse_pdf 3-tuple: a 3-row drop is flagged",
          rec.get("flagged") is True and rec.get("delta") == 3)
    check("oracle evidence surfaces the parser's skip stat",
          rec.get("parser_skipped_no_geometry") == 3)
    check("oracle evidence surfaces the validated-carry stat",
          rec.get("parser_carried_validated_pages") == 1)
    check("oracle evidence is privacy-safe (counts only, no cell contents)",
          not any(k in rec for k in ("rows", "cells", "content", "text")))


def main():
    print("TSMIS Highway Log (PDF) row-drop reconciliation:")

    # parse_pdf must hand back a 3-tuple now (route, rows, stats).
    check("parse_pdf signature accepts the stats 3-tuple contract",
          M.parse_pdf.__code__.co_argcount >= 2)

    res = _run({
        "skip.pdf": {"route": "001", "emitted": 1, "pages": 3,
                     "skipped_no_geometry": 4, "stale_geometry_pages": 0,
                     "carried_validated_pages": 0},
        "stale.pdf": {"route": "002", "emitted": 1, "pages": 3,
                      "skipped_no_geometry": 0, "stale_geometry_pages": 2,
                      "carried_validated_pages": 0},
        "clean.pdf": {"route": "003", "emitted": 1, "pages": 3,
                      "skipped_no_geometry": 0, "stale_geometry_pages": 0,
                      "carried_validated_pages": 0},
    })
    check("consolidate succeeds", res.status == "ok")
    check("INCOMPLETE banner reports the 4 dropped data lines",
          any(s.startswith("⚠ INCOMPLETE") and "4 data line" in s for s in res.summary_lines))
    check("carried-forward geometry banner reports the 2 unvalidated pages",
          any("⚠" in s and "carried-forward geometry" in s and "2 page" in s
              for s in res.summary_lines))
    check("drops/unfit pages escalate the completion to PARTIAL",
          res.completion == outcome.PARTIAL)

    clean = _run({
        "a.pdf": {"route": "001", "emitted": 1, "pages": 2,
                  "skipped_no_geometry": 0, "stale_geometry_pages": 0,
                  "carried_validated_pages": 0},
        "b.pdf": {"route": "002", "emitted": 1, "pages": 2,
                  "skipped_no_geometry": 0, "stale_geometry_pages": 0,
                  "carried_validated_pages": 0},
    })
    check("clean run succeeds", clean.status == "ok")
    check("clean run has NO anomaly banners",
          not any(s.startswith("⚠") for s in clean.summary_lines))
    check("clean run completion is COMPLETE", clean.completion == outcome.COMPLETE)

    # v0.26.2: VALIDATED carried-geometry pages are ordinary output — an info
    # line (no ⚠) and a COMPLETE completion. The blanket flag used to mark every
    # HL (PDF) day partial ("inputs incomplete") because ~280 band-less pages
    # per statewide set are normal zebra-parity artifacts.
    validated = _run({
        "v.pdf": {"route": "004", "emitted": 1, "pages": 5,
                  "skipped_no_geometry": 0, "stale_geometry_pages": 0,
                  "carried_validated_pages": 3},
    })
    check("validated-carry run succeeds", validated.status == "ok")
    check("validated carries get an info line naming the count",
          any("3 band-less page(s)" in s and "validated" in s
              for s in validated.summary_lines))
    check("…which is NOT a ⚠ banner",
          not any(s.startswith("⚠") for s in validated.summary_lines))
    check("validated carries do NOT escalate — completion stays COMPLETE",
          validated.completion == outcome.COMPLETE)

    mixed = _run({
        "m.pdf": {"route": "005", "emitted": 1, "pages": 5,
                  "skipped_no_geometry": 0, "stale_geometry_pages": 1,
                  "carried_validated_pages": 2},
    })
    check("a single unfit page still escalates PARTIAL (validated pages beside it)",
          mixed.completion == outcome.PARTIAL
          and any("⚠" in s and "1 page" in s for s in mixed.summary_lines))

    oracle_cross_check()

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL TSMIS-PDF-RECONCILE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
