# `RB-4` — Adversarial Review Record

Status: **REVIEW 1 DENIED — RETURN TO IMPLEMENTATION**

## Review 1 verdict — 2026-08-09

**DENIED — RETURN TO IMPLEMENTATION.**

The retained chain10 inspection records one failed image while amended HF-10
criterion 2 requires **100% of retained crops accurate and readable**. The
failed image is `intersection_detail_pdf_tsn / ML_Traffic_Flow_1_pair.png`,
route 232 at `000.807`: its blank `ML Traffic Flow` target is derived from the
PDF's unstroked rectangle metadata, but the crop contains no header or populated
same-column neighbor that lets a reader verify that the red box identifies that
field. The signed inspection reports **336 inspected / 335 passed / 1 failure**
and explicitly leaves the failure unfixed.

This is a concrete visual acceptance failure, not an evidence gap or reviewer-
machine failure. The exact-head verifier passed and every other amended
criterion has same-runtime evidence, but one failed retained crop denies the
combined RB bundle.

## Review identity, entry state, and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 1 |
| Implemented bundle? | **No** — implementer is Claude |
| Bundle / work items | `RB-4` / `HF-05 + HF-10` |
| Branch | `hotfix/rb-4-evidence` |
| Recorded base | `72adf447d45a2b74c562ba714008661a180c5d5f` |
| Acceptance runtime head | `f4b55f2ec75598cf5f8b37c8d23fb8c151490070` |
| Review-entry / review-record head | `3cda54f2588916645a0976557aa185d3c87a6bd0` |
| Remote branch head on entry | `3cda54f2588916645a0976557aa185d3c87a6bd0` — `origin/hotfix/rb-4-evidence` matched local `HEAD` |
| Runtime drift after acceptance | **None** — `f4b55f2..3cda54f` changes only `START-HERE.md`, the two committed witnesses, `IMPLEMENTATION.md`, and `rb4-a1-artifacts.json`; the verifier re-derived all 420 runtime files at `f4b55f2` |
| Review 2 | **BLOCKED** — do not run until this return is implemented and Review 1 re-reviews |
| Merge | **BLOCKED** |
| Elapsed active review | Approximately 30 minutes; stopped at the review-budget boundary |
| Resource budget | **RESPECTED** — no generation, installed Excel, build, full gate, whole-corpus comparison, raw recount, corpus re-hash, archive re-match, or bulk output; one 42-second exact-head verifier, one small deterministic source probe, Git/doc/JSON inspection, and one 136,369-byte temporary image copy |

All substantive Prompt-05 preconditions held on entry: the implementation
status was `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`; the branch was clean and
pushed; exact base and runtime heads were recorded; retained outputs existed;
and expensive operations were represented by hash-bound results. `REVIEW.md`
did not yet exist because this is Review 1, so this record was created from the
repository template.

## Evidence reused and bounded commands

| Evidence / command | Review result |
|---|---|
| Complete base-to-entry diff | 40 changed files, 11,326 insertions / 822 deletions; product scope is the evidence engine/adapters, matrix/UI capability plumbing, focused checks/acceptance tooling, and documentation. The six files outside the initially named union are individually disclosed in `IMPLEMENTATION.md` and are capability/frozen-build plumbing rather than a second product feature |
| Runtime-to-review-head diff | Documentation/evidence records only; no runtime file changed after `f4b55f2` |
| `rb4-a1-artifacts.json` | SHA-256 `D4E176D54F688C3C596520147B579EBD56D7DB0AB4FCD7BD5E5CC7AA307048F2` |
| `rb4-verify-manifest.py` | SHA-256 `12A7C2BF7DF95EBB566D82DBF608BDF7133C6D85958D00E0056D00066E549B54`; cheap invocation returned **VERIFIED — 0 problems**: runtime digest matched across 420 files, base digest matched, 7/7 claimed entries named `f4b55f2`, and both witnesses matched |
| HF-05 witness | `rb4-a1-summary.json`, SHA-256 `68D48E131622D7DDCE05E66AA8E80569CA4BA37E7B09152C47FC5316B45F8A3F`; 12 required / 14 forbidden / 12 discovered; 26/26 count invariance; 254 TSMIS-side re-derivations |
| HF-10 witness | `rb4-a1-env-summary.json`, SHA-256 `F02716FC366606002C72C7E1D46DAC86B51650710C7C8B7AD7E2E055160F60E7`; 12 cameras green, 5 required refusals, four env evidence sets, all five env comparison count records equal |
| Native-scale inspection | `results/inspection-chain10-round1.json`, SHA-256 `346F22F9DC9959E8429330596CE7013ADC1FE4CBBAAB7E0E73E9283B7AFC253C`; **336 inspected / 335 passed / 1 failure / 0 unreadable**; the failure is retained under defect class A and disposition `NOT FIXED` |
| Full gate / frozen app | Reused hash-bound chain10 results: 158/158 checks, compileall clean, ruff clean, frozen self-test passed; not rerun |
| Installed Excel / twins | Reused hash-bound result: 12/12 evidence workbooks opened with Ledger, 336 embedded pictures, and 26/26 formulas twins settled; not rerun |
| Targeted reviewer probe | A synthetic Intersection Detail record with visible glyphs only at x=0..5 and a blank target at column 18 still made `_box_at(rec, (1, 18))` return `(1, (178, 8.0, 192, 22.0), ...)` from `meta['edges']`. This independently reproduces the false-pass mechanism: containment can pass while the crop carries no visible field anchor |

The native-image viewer encountered a Windows sandbox ACL-helper failure before
loading the copied PNG. This reviewer-environment event is not charged to the
product. The verdict does not depend on it: the image's hash-bound native-scale
inspection classifies it as a failure, the implementation repeats that
classification and leaves it unfixed, and the source probe independently
reproduces the mechanism.

## Adversarial challenge

The most plausible false pass was that the automated geometry oracle proves a
box is inside a record and touches no foreign glyph, yet does not prove a human
can identify the boxed blank field. That is exactly what happened:

- `scripts/evidence_intersection_detail.py:_box_at` uses
  `meta["edges"][idx]` whenever a cell has no glyph hit;
- `scripts/visual_evidence.py:_box_within_record` checks only record x/y
  containment;
- the focused checks cover containment, neighboring-glyph exclusion, and
  several other blank-field refusals, but not a visible header or populated
  same-column anchor for this Intersection Detail case; and
- the retained native-scale review found the real-corpus manifestation the
  programmatic gate missed.

The 876/876 validation checks and 158/158 repository checks are internally
consistent but insufficient for the amended human-verifiability criterion. The
implementation criterion table also says 258/258 TSMIS-side re-derivations at
`IMPLEMENTATION.md:519`, while the accepted chain10 result and committed witness
say 254/254; that stale arithmetic must be corrected on return, but it is not
the reason for denial.

## Criterion-by-criterion disposition

| # | Amended criterion | Review 1 disposition |
|---:|---|---|
| HF-05 · 1 | Unbindable and 14 required-silent placements publish no artifacts | **PASS** — 12 required / 14 forbidden / 12 discovered; zero missing, extra, duplicate, or forbidden-present, behind planted positive controls |
| HF-05 · 2 | Every crop value is re-derived from its print or disagreement is disclosed | **PASS** — 254/254 TSMIS-side re-derivations; 0 corpus disagreements; the focused end-to-end fixture covers disclosure |
| HF-05 · 3 | Every blank target is inside the captioned record and touches no other record/field | **PASS AS WRITTEN** — 117 blank-side examples and the shared containment backstop; the denied image is contained and touches no foreign glyph, which is why this criterion alone did not catch the usability failure |
| HF-05 · 4 | No prose asserts an unread source | **PASS** — 453 print members are PDFs under the two declared read folders; legends/read-set declarations are bound |
| HF-05 · 5 | Classic Compare and by-day PDF-vs-Excel remain silent | **PASS** — both real paths wrote zero artifacts after live planted controls |
| HF-05 · 6 | Comparison counts and typed outcomes unchanged | **PASS** — 26/26 base/head typed sidecars equal across substantive fields |
| HF-05 · 7 | Full gate green and new assertions red pre-fix | **PASS** — retained 158/158 + compileall + ruff + frozen self-test; 8 red / 2 green controls / 0 inconclusive at base |
| HF-10 · 1 | Four `_pdf` env cells produce bound PDF/PDF evidence sets | **PASS** — four sets / 82 examples; Ramp Summary comparison runs and its evidence lane is silent |
| HF-10 · 2 | 100% of retained crops accurate and readable, individually reviewed | **FAIL** — exact retained result is 335/336 pass; `ML_Traffic_Flow_1_pair.png` has no visible anchor by which a reader can confirm the blank target's column |
| HF-10 · 3 | Env counts identical with evidence on/off | **PASS** — all five comparison results match, including the silent Ramp Summary control |
| HF-10 · 4 | No other lane's evidence behavior changed | **PASS** — all 14 forbidden placements absent and all 5 camera refusal probes refused |
| HF-10 · 5 | Full gate green and new assertions red pre-fix | **PASS** — same retained gate/base evidence as HF-05 · 7 |

## Exact deliverable and discrepancy results

| Domain | Retained result |
|---|---|
| Evidence population | 12 sets / 336 PNGs; Everything vs-TSN 127, By Day vs-TSN 127, Everything ENV 82 |
| Required silence | 14 matrix placements plus classic Compare and by-day PDF-vs-Excel; zero artifacts behind positive-control probes |
| Values / discrepancy truth | 26/26 base/head typed sidecars equal; ENV figures reproduce the audit: Ramp Summary 67; ID-PDF 17,562; RD-PDF 376 + 5/8 one-sided; HL-PDF 88,238 + 2,095/1,174; HSL-PDF 1,904 + 7/246 |
| Formulas | 26/26 installed-Excel-settled twins agree with values workbooks |
| Read sets | 453 print members plus compared workbooks, bound by paths and hashes; no unread-source prose found |
| Visual result | **335 pass / 1 failure**; no workbook-style panels, clipping, caption overlap, multi-column boxes, or record mis-targeting elsewhere |

## Values, formulas, visual, evidence, and regression matrices

| Domain | Review 1 result |
|---|---|
| Values / source truth | **PASS ON RETAINED EVIDENCE** — count invariance and ENV audit figures agree; no whole-corpus recount duplicated |
| Formulas / installed Excel | **PASS ON RETAINED EVIDENCE** — 26/26 twins settled; 12/12 evidence books opened with Ledger and matching embedded-image count |
| Visual / presentation | **FAIL** — one retained blank-cell crop is not human-verifiable, contrary to HF-10 · 2 and the owner's independent-spot-check purpose |
| Evidence eligibility / exact source | **PASS** — four `_pdf` rows in TSN/ENV only; SELF, Excel-row TSN, and Ramp Summary ENV refused; manifests bind declared print sources |
| Sibling parity | **PASS ON RETAINED EVIDENCE** — comparison content and typed outcomes are invariant; PDF/PDF evidence does not alter sibling results |
| Neighboring behavior | **PASS** — silent classic/PDF-vs-Excel controls and all 14 forbidden placements remain silent; Highway Detail stays pre-release and unexercised |
| Performance / atomic publication / stale cache / failure | **PASS ON RETAINED EVIDENCE** — published sets are generation-bound, unbindable pairs retire prior sets, failures remain decoration-only, and the verifier fails closed |
| Regression | **PASS ON RETAINED EVIDENCE** — full retained gate and frozen self-test green; no runtime drift after `f4b55f2` |

## Actionable failure and bounded return

| ID | Priority | Acceptance failure | Required return |
|---|---|---|---|
| `RB4-R1-001` | P1 / blocking | HF-10 · 2 requires 100% accurate/readable crops, but `intersection_detail_pdf_tsn / ML_Traffic_Flow_1_pair.png` is retained as a failed, human-unverifiable crop. Invisible PDF rectangle metadata identifies the blank cell to code, while the crop gives the reader no visible way to verify the field. | On the existing RB-4 branch, make every retained blank Intersection Detail target visibly attributable to its field — for example by extending the crop to a print header or a populated same-column anchor — or refuse the example and record the reason rather than publishing an unverifiable spot check. Add a focused failing check for the unanchored-blank/`meta['edges']` mechanism, regenerate and re-inspect affected evidence under one new runtime head, rebind dependent witnesses/manifest, and reach 100% visual passes. Correct the stale 258/258 implementation arithmetic while updating the record. Then return Prompt 05 for Review 1 re-review. |

**Reviewer signature:** Codex, Review 1 — **DENIED — RETURN TO IMPLEMENTATION** —
`2026-08-09T23:17:06.6050179-07:00`.

Do not merge and do not begin Review 2. Resume Prompt 04 on the existing
`hotfix/rb-4-evidence` branch only to close `RB4-R1-001` and rebind the affected
acceptance evidence.
