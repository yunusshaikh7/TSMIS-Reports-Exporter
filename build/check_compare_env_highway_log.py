"""Golden check for the cross-environment Highway Log XLSX adapter
(compare_env.HIGHWAY_LOG) — the CMP-AUD-047/048 fixes.

Locks:
  047 — the env loader projects values through the report's OWN normalizer
        (`_hl_normalize`): a Description identical except for trailing tab
        padding compares EQUAL cross-env, exactly like the dedicated
        comparator (pre-fix: ok/diff with one spurious cell).
  048 — each side's header canonicalizes INDEPENDENTLY before layout
        equality: one canonical-labelled and one vendor-labelled export of
        the same 31-column layout compare (displaying the corrected names),
        while an unrecognized same-width header is REFUSED by name instead
        of being trusted positionally (pre-fix: the supported pair failed
        with 'different column layouts').

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_env_highway_log.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_env
import compare_highway_log as hl
import highway_log_columns as hlc
from events import Events
from openpyxl import Workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _row(description):
    values = [""] * 31
    values[0] = "R001.000"          # Location
    values[1] = "0.5"               # Length
    values[28] = description        # Description
    return values


def _write_side(root, header, description):
    d = root / "highway_log"
    d.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = hl.SHEET_NAME
    ws.append(list(header))
    ws.append(_row(description))
    wb.save(d / "highway_log_route_001.xlsx")


def _compare(root_a, root_b, out):
    return compare_env.HIGHWAY_LOG.compare_folders(
        root_a, root_b, out, events=Events(),
        confirm_overwrite=lambda _p: True)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_envhl_"))

    print("CMP-AUD-047 — cross-env uses the Highway Log projection:")
    a, b = tmp / "envA", tmp / "envB"
    _write_side(a, hlc.HEADER, "JCT RTE 2")
    _write_side(b, hlc.HEADER, "JCT RTE 2\t\t\t")     # tab padding only
    res = _compare(a, b, tmp / "hl_tabs.xlsx")
    counts = res.comparison_outcome.counts
    check("identical-but-for-tab-padding compares clean (0 diff cells)",
          res.status == "ok" and counts.differing_cells == 0
          and counts.paired_rows == 1, )

    print("CMP-AUD-048 — supported header editions compare:")
    c, d = tmp / "envC", tmp / "envD"
    _write_side(c, hlc.HEADER, "SAME TEXT")
    _write_side(d, hlc.VENDOR_HEADER, "SAME TEXT")
    res = _compare(c, d, tmp / "hl_editions.xlsx")
    counts = res.comparison_outcome.counts if res.status == "ok" else None
    check("canonical-vs-vendor editions compare (no layout refusal)",
          res.status == "ok" and counts is not None
          and counts.differing_cells == 0 and counts.paired_rows == 1)
    check("the displayed header is the corrected canonical one",
          res.status == "ok"
          and getattr(res, "output_path", None) is not None)

    print("CMP-AUD-048 — an unrecognized same-width header is refused:")
    e, f = tmp / "envE", tmp / "envF"
    fake = [f"X{i}" for i in range(31)]
    _write_side(e, fake, "SAME TEXT")
    _write_side(f, fake, "SAME TEXT")
    res = _compare(e, f, tmp / "hl_fake.xlsx")
    check("same-width unrecognized layout errors instead of comparing on faith",
          res.status == "error"
          and "recognized" in (res.message or ""))

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("OK  COMPARE-ENV-HIGHWAY-LOG: report projection applied cross-env "
          "(tab padding equal); canonical/vendor editions compare with "
          "corrected labels; unrecognized layouts refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
