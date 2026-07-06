# Review round 1

## 1. Verdict

PASS WITH FIXES

## 2. Blocking findings

None.

## 3. Required fixes

### P15-R01 — Required — Correct stale Intersection Detail control-type/context wording

Evidence:

- `scripts/compare_intersection_detail_tsn.py:99` sets `CONTEXT_FIELDS = ()`, and `scripts/compare_intersection_detail_tsn.py:450` wires that empty tuple into `_SCHEMA.context_fields`.
- `scripts/compare_intersection_detail_tsn.py:80` still says every shared field is compared "EXCEPT the two CONTEXT_FIELDS below", which is false for the accepted P15 behavior.
- `scripts/compare_intersection_detail_tsn.py:118` sets `_SIGNALIZED_LABEL = "S"`, and `build/check_compare_intersection_detail_tsn.py` asserts TSN J-P plus TSMIS S normalize to `"S"`.
- `scripts/compare_intersection_detail_tsn.py:35-40`, `scripts/compare_intersection_detail_tsn.py:215-222`, and the user-visible Notes text in `scripts/compare_intersection_detail_tsn.py:377-383` still say the compared cell displays/readably normalizes to the word `"Signalized"`. The current shipped workbook will instead show `"S"` for the normalized Control Type.

Why this matters:

The behavior itself is correct and locked by the P15 canary, but the source comments and Notes sheet now contradict the contract users and maintainers will read while interpreting a report. This is especially risky because P15 intentionally changes which fields are counted and how TSN signal sub-types fold.

Exact correction expected:

Update the affected source comments/docstrings and the Notes-sheet text to state the actual contract: no context fields are suppressed in Intersection Detail vs-TSN, and TSN J/K/L/M/N/P plus TSMIS S normalize to the code `"S"` / Signalized category rather than to a displayed `"Signalized"` string. Do not change `compare_core`, do not reintroduce `context_fill`, and do not change comparison semantics. Re-run at least `python build/check_compare_intersection_detail_tsn.py` and `python build/check_compare_tsn_common.py`; if the Notes wording is test-locked, include that in the updated phase report.

## 4. Non-blocking recommendations

None.

## 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P15-claude-report.md`, prior P14 report/review, and CR-002 review context.
- Confirmed coordination currently marks P15 `awaiting_review` with baseline `380b7e8`.
- Inspected product diff from `380b7e8` excluding `docs/planning/`; product changes are limited to:
  - `scripts/compare_intersection_detail_tsn.py`
  - `scripts/compare_intersection_summary_tsn.py`
  - `scripts/summary_layout.py`
  - `build/check_compare_intersection_detail_tsn.py`
  - `build/check_compare_intersection_summary_tsn.py`
  - `build/check_compare_tsn_common.py`
  - `build/check_tsn_normalizer.py`
- Confirmed protected files are unchanged from the P15 baseline: `scripts/compare_core.py`, `scripts/compare_intersection_detail_pdf.py`, `version.py`, and `build/app.spec`.
- Confirmed `context_fill` is absent outside planning documentation.
- Compared the Report View/PDF-adapter shape against `origin/main`: the per-call `extra_sheet_writer` behavior and unchanged PDF adapter are consistent with v0.17.8.
- Ran:
  - `python -m compileall -q scripts build version.py`
  - `git diff --check -- . ':!docs/planning'`
  - `python build/check_compare_intersection_detail_tsn.py`
  - `python build/check_compare_intersection_summary_tsn.py`
  - `python build/check_compare_tsn_common.py`
  - `python build/check_tsn_normalizer.py`
  - `python build/check_intersection_detail_pdf.py`
  - `python build/check_compare_audit.py`
  - `python build/check_highway_log_columns.py`
  - `python build/check_highway_log_ditto.py`
  - `python build/check_highway_log_roadbed.py`
  - `python build/check_compare_ramp_detail_tsn.py`
  - `python build/check_compare_ramp_summary_tsn.py`
  - `python build/check_compare_highway_sequence_tsn.py`
  - `python build/check_compare_ramp_detail.py`
  - `python build/check_compare_ramp_summary.py`
  - `python build/check_compare_highway_sequence.py`
  - `python build/check_compare_env_intersection.py`
  - `python build/check_compare_env_highway_log_pdf.py`
  - `python build/check_compare_env_sidelabel.py`
  - `python build/check_tsn_description_leak.py`
  - `python build/check_compare_blankkey.py`
  - `python build/check_compare_keyfield.py`
  - `python build/check_compare_skipwarn.py`
  - `python build/check_compare_injection.py`
  - `python build/check_compare_coercion.py`
  - `python build/check_compare_limits.py`
  - `python build/check_compare_dupmatch.py`
  - `python build/check_compare_ditto.py`
- Ran a read-only import probe confirming:
  - `len(compare_intersection_detail_tsn.SHARED_HEADER) == 33`
  - `compare_intersection_detail_tsn._SCHEMA.context_fields == ()`
  - `compare_intersection_detail_tsn._SCHEMA.extra_sheet_writer is None`
  - both PDF adapters reuse the evolved 33-column header and empty context fields
  - PDF adapters do not receive the per-call Report View writer

All executed checks passed. `git diff --check` produced only line-ending normalization warnings for two touched check files, not whitespace errors.

## 6. Whether Claude may proceed toward phase approval

Claude may not proceed to phase approval until P15-R01 is corrected and the targeted checks are re-run. No separate user approval is required because the fix is a wording/diagnostic correction within the approved P15 scope and must preserve the already-verified comparison behavior.

# Review round 2

## 1. Verdict

PASS

## 2. Blocking findings

None.

## 3. Required fixes

None. Prior required finding **P15-R01** is resolved.

Evidence for P15-R01 resolution:

- `scripts/compare_intersection_detail_tsn.py:79-80` now states that every field present in both systems is compared and counted, with `CONTEXT_FIELDS` empty.
- `scripts/compare_intersection_detail_tsn.py:99` remains `CONTEXT_FIELDS = ()`, and `scripts/compare_intersection_detail_tsn.py:451` wires that empty tuple into `_SCHEMA.context_fields`.
- `scripts/compare_intersection_detail_tsn.py:112-118`, `scripts/compare_intersection_detail_tsn.py:216-220`, and `scripts/compare_intersection_detail_tsn.py:378-385` now describe the actual Detail behavior: TSN J/K/L/M/N/P plus TSMIS S normalize to displayed code `"S"` / the Signalized category, not to a displayed `"Signalized"` string.
- A read-only Notes writer probe confirmed the generated Notes sheet contains `Control Type cell reads 'S'` and no longer says the cell reads the word `Signalized`.

## 4. Non-blocking recommendations

None.

## 5. Verification performed

- Re-read the current phase state in `docs/planning/v0.18.0/00-coordination.md`; P15 remains `awaiting_review` with baseline `380b7e8`.
- Re-read the P15 section of `docs/planning/v0.18.0/05-claude-final-plan.md`, the updated `docs/planning/v0.18.0/phases/P15-claude-report.md` remediation section, prior `docs/planning/v0.18.0/phases/P15-codex-review.md` round 1, and relevant P14/CR-002 context.
- Inspected the product diff from baseline `380b7e8` excluding `docs/planning/`; product/check touch set remains the same 7 intended files:
  - `scripts/compare_intersection_detail_tsn.py`
  - `scripts/compare_intersection_summary_tsn.py`
  - `scripts/summary_layout.py`
  - `build/check_compare_intersection_detail_tsn.py`
  - `build/check_compare_intersection_summary_tsn.py`
  - `build/check_compare_tsn_common.py`
  - `build/check_tsn_normalizer.py`
- Confirmed protected files are unchanged from the P15 baseline: `scripts/compare_core.py`, `scripts/compare_intersection_detail_pdf.py`, `version.py`, and `build/app.spec`.
- Confirmed `context_fill` remains absent outside planning documentation.
- Ran:
  - `python build/check_compare_intersection_detail_tsn.py`
  - `python build/check_compare_tsn_common.py`
  - `python build/check_compare_intersection_summary_tsn.py`
  - `python build/check_tsn_normalizer.py`
  - `python -m compileall -q scripts build version.py`
  - `git diff --check -- . ':!docs/planning'`
  - `python build/check_intersection_detail_pdf.py`
  - `python build/check_compare_audit.py`
  - `python build/check_compare_ramp_detail_tsn.py`
  - `python build/check_compare_ramp_summary_tsn.py`
  - `python build/check_compare_highway_sequence_tsn.py`
  - `python build/check_tsn_description_leak.py`
  - `python build/check_highway_log_columns.py`
  - `python build/check_highway_log_ditto.py`
  - `python build/check_highway_log_roadbed.py`
  - `python build/check_compare_env_intersection.py`
  - `python build/check_compare_env_highway_log_pdf.py`
  - `python build/check_compare_env_sidelabel.py`
- Ran a read-only import/Notes probe confirming:
  - `compare_intersection_detail_tsn._SCHEMA.context_fields == ()`
  - `compare_intersection_detail_tsn._norm_control_type("P") == "S"`
  - generated Notes text now says the Control Type cell reads `'S'`
  - generated Notes text no longer says the cell reads the word `Signalized`

All executed checks passed. `git diff --check` emitted only line-ending normalization warnings for `build/check_compare_tsn_common.py` and `build/check_tsn_normalizer.py`, not whitespace errors.

## 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval/commit for P15. No blocking, required, or non-blocking findings remain from this review round.
