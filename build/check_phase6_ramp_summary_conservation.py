#!/usr/bin/env python3
"""Permanent mutation gate for the independent Ramp Summary conservation oracle."""

from __future__ import annotations

import contextlib
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase6_ramp_summary_conservation as oracle


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    expected = [("A", Decimal("1")), ("B", Decimal("2"))]
    observed = [(2, "A", Decimal("1")), (3, "B", Decimal("2"))]
    exact = oracle._projection_comparison(expected, observed)
    require(exact["ordered_exact"] and exact["multiset_exact"],
            "exact projection fixture did not pass")

    swapped = oracle._projection_comparison(expected, list(reversed(observed)))
    require(not swapped["ordered_exact"] and swapped["multiset_exact"],
            "row-order mutation was not isolated from multiset equality")

    wrong_type = [(2, "A", "1"), (3, "B", Decimal("2"))]
    require(not oracle._projection_comparison(expected, wrong_type)["ordered_exact"],
            "same-text cross-type mutation was not detected")

    changed = [("A", Decimal("2")), ("B", Decimal("2"))]
    require(not oracle._projection_comparison(changed, observed)["ordered_exact"],
            "count mutation was not detected")

    require(oracle._role_for_word(3, {
        "text": "X", "x0": "300.0", "top": "80.0",
        "x1": "301.0", "bottom": "81.0",
    }) is None, "unclassified layout residue was accidentally accepted")

    require(oracle._role_for_word(3, {
        "text": "148", "x0": "91.0", "top": "119.0",
        "x1": "109.0", "bottom": "129.0",
    }) == "highway_groups", "known highway layout role was not classified")

    fixture = {
        section: [
            oracle.CategoryRecord(section, ordinal, code, code, 1, 3,
                                  str(ordinal), "1.0")
            for ordinal, code in enumerate(codes, 1)
        ]
        for section, codes in oracle.EXPECTED_SECTION_CODES.items()
    }
    total = max(sum(record.count for record in rows) for rows in fixture.values())
    # Equalize all four axes to one test universe without altering category shape.
    for rows in fixture.values():
        rows[-1] = oracle.CategoryRecord(
            rows[-1].section, rows[-1].ordinal, rows[-1].code, rows[-1].label,
            rows[-1].count + total - sum(record.count for record in rows),
            rows[-1].page, rows[-1].top, rows[-1].x0)
    validation = oracle._validate_source_categories(fixture, total)
    require(not validation["anomalies"], "valid four-axis fixture did not conserve")
    first = fixture["highway_groups"][0]
    fixture["highway_groups"][0] = oracle.CategoryRecord(
        first.section, first.ordinal, first.code, first.label, first.count + 1,
        first.page, first.top, first.x0)
    require(not oracle._validate_source_categories(fixture, total)[
        "all_four_axes_equal_total"], "axis subtotal mutation was not detected")

    # CMP-AUD-149: changing an internal parser file without changing its package
    # version, byte length, path, inode, or mtime must still fail by content hash.
    with tempfile.TemporaryDirectory() as raw_temp:
        root = Path(raw_temp)
        version_path = root / "_version.py"
        parser_path = root / "parser.py"
        version_path.write_text('__version__ = "1.0"\n', encoding="utf-8")
        parser_path.write_text('TOKEN = "AAAA"\n', encoding="utf-8")
        paths = {
            "parser_module::fixture._version": version_path,
            "parser_module::fixture.parser": parser_path,
        }
        _manifest, identities = oracle._parser_module_manifest(paths)
        original_stat = parser_path.stat()
        parser_path.write_text('TOKEN = "BBBB"\n', encoding="utf-8")
        os.utime(parser_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        current, detail = oracle._revalidate(identities, paths)
        require(not current, "same-version internal parser-file drift was accepted")
        require(not detail["parser_module::fixture.parser"]["current"],
                "parser-file SHA drift was not attributed to the changed module")
        require(detail["parser_module::fixture._version"]["current"],
                "unchanged version module did not remain current")

    roles = ["page_1.cover_title", "page_1.policy_notice"]
    dispositions = [
        {"role_id": "page_1.cover_title"},
        {"role_id": "page_1.policy_notice"},
    ]
    require(oracle._role_disposition_coverage(
        roles, dispositions)["exact_one_to_one_coverage"],
        "exact role-disposition universe did not pass")
    require(not oracle._role_disposition_coverage(
        roles, dispositions[1:])["exact_one_to_one_coverage"],
        "missing role disposition was accepted")
    require(not oracle._role_disposition_coverage(
        roles, dispositions + [dict(dispositions[0])])["exact_one_to_one_coverage"],
        "duplicate role disposition was accepted")
    require(not oracle._role_disposition_coverage(
        roles, dispositions + [{"role_id": "page_9.extra"}])[
            "exact_one_to_one_coverage"],
        "unobserved extra role disposition was accepted")

    # CMP-AUD-152: exercise main(), not just a decision helper.  An audit-false
    # result with otherwise-current sources must produce an explicit rejection,
    # remove a stale acceptance, and never create a positive acceptance record.
    with tempfile.TemporaryDirectory() as raw_temp:
        root = Path(raw_temp)
        output = root / "synthetic.json"
        acceptance = output.with_suffix(output.suffix + ".acceptance.json")
        rejection = output.with_suffix(output.suffix + ".rejection.json")
        acceptance.write_text('{"accepted": true}\n', encoding="utf-8")
        fake_result = {
            "schema_version": 1,
            "audit": "synthetic negative",
            "projection_exact": True,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "audit_invariants": {},
            "findings": {"product_red": []},
        }
        original_run = oracle.run
        original_revalidate = oracle._revalidate
        try:
            oracle.run = lambda: (fake_result, {}, {}, {})
            oracle._revalidate = lambda *_args, **_kwargs: (True, {})
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = oracle.main([
                    "--output", str(output), "--allow-open-findings"])
        finally:
            oracle.run = original_run
            oracle._revalidate = original_revalidate
        require(exit_code == 2, "audit-false main() did not exit 2")
        require(not acceptance.exists(), "audit-false main() left/created acceptance")
        require(rejection.exists(), "audit-false main() did not write rejection")
        decision = json.loads(rejection.read_text(encoding="utf-8"))
        require(decision.get("accepted") is False,
                "rejection record does not explicitly say accepted=false")
        require(decision.get("reason") == "audit_or_projection_incomplete",
                "rejection record has the wrong decision reason")

    print("OK Ramp Summary oracle mutation gate: typed order/multiset, category shape, "
          "four-axis totals, PDF role/disposition coverage, same-version parser drift, "
          "and detached acceptance fail closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
