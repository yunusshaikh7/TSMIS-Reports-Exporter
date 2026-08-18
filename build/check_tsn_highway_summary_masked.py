"""Golden check: a MASKED TSN Highway Summary category is disregarded, but a
genuinely ABSENT one still reports PARTIAL (D4, owner decision 2026-08-18).

The statewide TSN print masks a value that overflows its column width with
`**********`. On the bound 2025-09-15 print that is exactly
`MEDIAN BARRIER: Z- NO BARRIER`. TSMIS replaced TSN, so this print is a FROZEN
artifact of the retired database -- there will never be a version stating that
figure. Holding the whole library at PARTIAL for a gap that can never close left
the Highway Summary vs-TSN cell permanently amber with nothing to act on.

Owner decision: disregard a masked value and disclose it. What must NOT change:
  * the masked figure is never coerced to 0 (CMP-AUD-021 absent-vs-zero) -- it is
    omitted, so the comparison shows it ONE-SIDED with the TSMIS value visible
  * a category the print never MENTIONS is a different thing: that may mean the
    parse or the shared taxonomy drifted, so it still reports PARTIAL and its
    skipped-input count still reaches the comparison

Runs on the plain build venv python (no login, no Excel, no PDF):
  build\\.venv\\Scripts\\python.exe build\\check_tsn_highway_summary_masked.py
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001 - console encoding is best-effort
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import compare_highway_summary_tsn as hstsn   # noqa: E402
import highway_summary_columns as hsc         # noqa: E402
import outcome                                # noqa: E402
import report_catalog                         # noqa: E402
import tsn_load_highway_summary as loader     # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}" + (f"  -> {detail}" if not cond and detail else ""))
    if not cond:
        FAILS.append(name)


CATS = list(hsc.cats_for("tsn"))
ALL_SLUGS = [c.slug for c in CATS]


def project_with(omit_slugs, masked_slugs):
    """Run the real _project with the PDF parse stubbed: `omit_slugs` carry no
    value, and `masked_slugs` are the subset the print masked."""
    def fake_parse(path, masked_out=None):
        vals = {s: 1000 for s in ALL_SLUGS if s not in omit_slugs}
        vals[hsc.TOTAL_SLUG] = 12345
        if masked_out is not None:
            masked_out.update(masked_slugs)
        return vals

    real_parse, real_claims = hstsn.parse_tsn_pdf, hstsn.parse_tsn_source_claims
    hstsn.parse_tsn_pdf = fake_parse
    hstsn.parse_tsn_source_claims = lambda p: {"identity": {"report_id": "OTM22230"}}
    try:
        _rows, make_result = loader._project("stub.pdf")
        return make_result("out.xlsx")
    finally:
        hstsn.parse_tsn_pdf, hstsn.parse_tsn_source_claims = real_parse, real_claims


masked_slug = ALL_SLUGS[0]
absent_slug = ALL_SLUGS[1]

print("=== a MASKED category is disregarded ===")
r = project_with({masked_slug}, {masked_slug})
check("completion is COMPLETE", r.completion == outcome.COMPLETE, str(r.completion))
check("skipped_inputs is 0", r.skipped_inputs == 0, str(r.skipped_inputs))
extra = r.producer_extra or {}
check("the masked category is DISCLOSED in the sidecar",
      len(extra.get("tsn_masked_categories") or []) == 1,
      str(extra.get("tsn_masked_categories")))
joined = " ".join(r.summary_lines or [])
check("the summary says it was masked and disregarded",
      "masked" in joined.lower() and "disregard" in joined.lower())
check("the summary does NOT call the build incomplete",
      "INCOMPLETE" not in joined)

print("\n=== a genuinely ABSENT category still reports PARTIAL ===")
r2 = project_with({absent_slug}, set())
check("completion is PARTIAL", r2.completion == outcome.PARTIAL, str(r2.completion))
check("skipped_inputs is 1", r2.skipped_inputs == 1, str(r2.skipped_inputs))
check("the summary WARNS it is incomplete",
      "INCOMPLETE" in " ".join(r2.summary_lines or []))

print("\n=== both at once: the absent one still drives the verdict ===")
r3 = project_with({masked_slug, absent_slug}, {masked_slug})
check("completion is PARTIAL", r3.completion == outcome.PARTIAL, str(r3.completion))
check("skipped_inputs counts ONLY the absent one (1)", r3.skipped_inputs == 1,
      str(r3.skipped_inputs))
check("the masked one is still disclosed",
      len((r3.producer_extra or {}).get("tsn_masked_categories") or []) == 1)

print("\n=== nothing missing at all ===")
r4 = project_with(set(), set())
check("completion is COMPLETE", r4.completion == outcome.COMPLETE)
check("skipped_inputs is 0", r4.skipped_inputs == 0)
check("no masked categories disclosed",
      not (r4.producer_extra or {}).get("tsn_masked_categories"))

print("\n=== the library rebuilds once so the new outcome is picked up ===")
entry = next(e for e in report_catalog.tsn_entries() if e.subdir == "highway_summary")
check("normalization_version is at least 2", entry.normalization_version >= 2,
      str(entry.normalization_version))

print("\nRESULT:", "ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
