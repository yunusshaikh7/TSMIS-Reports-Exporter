# RB-5 — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

Current decision: **RB5-R1-001**, resumed Review 1 — denial **2 of 2**.
The earlier evidence-gap return is preserved below as history; the latest
signed substantive review is at the end of this record.

## Review 1 — Codex — DENIED — EVIDENCE GAP

| Field | Reviewed identity |
|---|---|
| Reviewer / pass | Codex / Review 1, fresh task; not the implementer |
| Implementer | Claude |
| Branch | `hotfix/rb-5-difference-classification` |
| Implementation worktree | `C:\Users\Yunus\Projects\wt-rb5` |
| Recorded base | `87e368c3e9a7eaf26395308e8ddea4aba7d303e5` |
| Runtime head | `444e8d9fecee3f8335f244fa940e168161bfb878` |
| Entry / existing review-record head | `6df43b24646165cea95008a29831caa40fe7f8e0` |
| New review-record commit | This documentation-only commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-5/REVIEW.md` |
| Timer started | 2026-08-31T00:53:39.674Z |
| Substantive work stopped | 2026-08-31T00:59:50.990Z — 6.19 minutes elapsed |
| Signed | 2026-08-31T01:06:03.611Z — 12.40 minutes elapsed at signature |

The fresh task's checkout was detached at the old base. The reviewer located
and used the implementation branch above, which was clean at entry. The only
runtime-to-entry change is `RB-5/IMPLEMENTATION.md`; no runtime file changed.
No prior `RB-5/REVIEW.md` or RB-5 reviewer sign-off existed. The applicable
pass is **Review 1**, not Review 2.

### Preconditions and stopping point

| Precondition | Result |
|---|---|
| Review 1 status | PASS — authoritative plan and implementation record said `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` |
| Exact branch/base/head and retained outputs exist | PASS |
| Every required expensive acceptance operation has a retained result | **FAIL — one bounded HF-09 formulas-twin item below** |
| Review 2 / merge eligibility | NOT REACHED — no approving review exists |

Prompt 05 requires stopping on a failed precondition. This is a precondition
return, **not a completed code/acceptance review**. The 21-file diff inventory
and runtime-to-record identity delta were inspected. The complete implementation
diff, product probes and substantive acceptance review were not reached.

### RB5-R1-EG-001 — retain the HF-09 formulas-twin acceptance result

**Exactly one requested item:** the HF-09 installed-Excel values/formulas
acceptance witness for the eight already-retained RB5-A1 family/edition
comparisons, for example `HF-09/witness/installed-excel-recalc.json`. It must
reference the retained FORMULAS workbooks and existing VALUES twins, identify
the runtime/source generation, and record paths, sizes, SHA-256 identities,
recalculated headline/per-field parity, representation-class disclosure/count,
cached errors and SELF-CHECK results. The eight cases are Highway Log Excel/PDF,
Highway Sequence Excel/PDF, Intersection Detail Excel/PDF, Ramp Detail PDF,
and Clean Road Highway.

Evidence for the gap:

- `BUNDLE.md` RB5-A1 step 4 and HF-09's “Values / formulas and installed-Excel
  checks” require both twins and installed-Excel parity.
- The whole named `HF-09/rb5-a1` tree contains 16 XLSX files: eight base VALUES
  workbooks and eight head VALUES workbooks. No FORMULAS workbook or
  recalculation-result file was retained there.
- All eight head publication outcomes explicitly specify
  `artifact_generation.requested_mode = "values"` and exactly one member,
  with flavor `values`. Their provenance records also have only a `values`
  member. This is publication-state evidence, not a filename assumption.
- `HF-06/witness/installed-excel-recalc.json` and the retained
  `HF-06/rb5-a1/excel-recalc/recalc.json` cover Highway Sequence **self** only.
  They cannot establish the distinct HF-09 vs-TSN/Clean Road outputs.
- `HF-09/witness/representation-class-census.json` expressly describes a census
  of VALUES sheets; it supplies no FORMULAS recalculation result.

**Practical-impact gate — what would a user see differently?** The unresolved
user-facing behavior is the FORMULAS download: whether its recalculated
differences, disclosure and self-checks agree with the VALUES download has not
been demonstrated for HF-09. No incorrect result or crash is alleged. This is
missing acceptance evidence for an actual output flavor, under Prompt 05's
explicit material-evidence-gap rule, rather than a request to tidy a commit
citation or improve cosmetics.

If this result exists elsewhere, supply its exact location and binding;
**do not rerun it**. Otherwise implementation supplies only this missing
acceptance leg. The request does not authorize a reviewer to start Excel,
regenerate the statewide corpus, repeat HF-06's recalculation, recount raw
sources or rerun the full gate. Operations exceeding the owner's resource
limits still require the approval specified by Prompt 05 before starting.
No product edit is requested merely to close this evidence return.

### Reused evidence and identities

Retained roots:

- `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-06\rb5-a1`
- `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-09\rb5-a1`

The following committed witnesses were read and independently SHA-256 hashed.
Paths are relative to `hotfix-bundles/`.

| Witness | Bytes | SHA-256 |
|---|---:|---|
| `HF-06/witness/before-after-counts.json` | 4,730 | `1d47c881665b99aef5b38537a378b885479be9a59666262a92ef2d5fe6cb7a31` |
| `HF-06/witness/equate-relation-census.json` | 9,108 | `b42a1dad0fc79b11f6736a9171148c7a8b2ac759948e5c7faf39fd23d21c651e` |
| `HF-06/witness/installed-excel-recalc.json` | 2,293 | `92d35570085d43feb099f7a1cddfd60fd07ddc984e312185b747878d5de9964b` |
| `HF-09/witness/representation-class-census.json` | 10,978 | `5ac7e43dd6ad4f928d71525f692033dc6e138810ddf470ddd73aae148b13ada9` |

These small outcome records under `HF-09/rb5-a1/head/_state/` were independently
hashed and inspected. Every one records a committed VALUES-only generation.

| Outcome filename | SHA-256 of outcome record |
|---|---|
| `hl_excel vs tsn.xlsx.outcome.json` | `eafbf31be615f2bed4717009d0f656231b6c73e2fce4aaf2f88a305a8b3ba085` |
| `hl_pdf vs tsn.xlsx.outcome.json` | `1fa5305ce53f5100d624825853685a7796c8c78619d2b5d270d0bb8c708f3b18` |
| `hsl_excel vs tsn.xlsx.outcome.json` | `3dd9ecd44208ebb042fbfbf0cc55b6e33c32e1a8ea7fdffc4136ffe21c932ed9` |
| `hsl_pdf vs tsn.xlsx.outcome.json` | `2e20e381db021dd79b703feab56a85ccb811ca61149beefae11dd4d1d0456d3f` |
| `id_excel vs tsn.xlsx.outcome.json` | `018af1c22690bb5c579c6b42ba63513dbcdd2eb294c0ca9aa4240862119e88be` |
| `id_pdf vs tsn.xlsx.outcome.json` | `6dfa30a0838a6d455f51383c61aa8e4474ee281ca05855da40f41c251ec5f61e` |
| `rd_pdf vs tsn.xlsx.outcome.json` | `a28ec5c85f6d407d66b1c7c3033f930f3fcbc600f6d5bad1bedcbde848a25649` |
| `clean_road_highway vs tsn.xlsx.outcome.json` | `5cb9dadb7a6113184149dc5fdbb9efb282415937015be003ef764965af663a60` |

For one concrete example, Highway Log Excel records VALUES at
`HF-09/rb5-a1/head/hl_excel vs tsn.xlsx`, 99,104,342 bytes, SHA-256
`c40315c80bc8f26096c749c788d2fec6ed52a75d067bbd2922fe3fffda43df39`,
generation `5f5b1395-2d90-479c-a23e-d9824b2ceceb`, requested mode `values`.
The large workbook digest was **read from its publication record, not
independently recomputed**. No complete artifact-hash verification is claimed.

### Deliverable, discrepancy and acceptance matrices

Retained claims below were read, not independently approved by this precondition
return. No matrix is presented as a completed substantive review.

| Surface / criteria | Retained claim or observation | Disposition |
|---|---|---|
| HF-06 criteria 1–3: equates, pairing, anti-suppression | 60,254 paired rows; 3,714 cells / 1,395 rows before; 7 cells / 7 rows after; PM Suffix/HG/FT/Description 547/929/1,119/1,119 to 7/0/0/0 | Seven one-sided-E residuals disclosed; no denial for their nonzero count. Raw adjudication and logic challenge not reached |
| HF-06 criterion 4: disclosure | Summary and Notes claim 1,119 normalized relations | Visual inspection not reached; no cosmetic finding |
| HF-06 criteria 5–7: paths, neighbors, canaries | Three self paths report 7; both HSL vs-TSN counts unchanged; scoped opt-in and neighboring control reported | Semantic/state/canary verification not reached |
| HF-06 criterion 8 / HF-09 criterion 7 | Full gate reported 171/171; new checks reported failing at base and passing at head | Gate verification and focused probes not reached; no rerun |
| HF-09 criteria 1–3: classification and counts | HL 1,243/1,243; HSL 12/12; ID 1/1; RD PDF 3; Clean Road 2; VALUES census agrees and all eight headline totals reported unchanged | Claims read; **FORMULAS acceptance is the single missing item** |
| HF-09 criteria 4–6: equality, quote note, neighbors | Disclosure-only hook, preserved quote note, inert non-opted-in families reported | Code/state/evidence challenge not reached |
| Values/formulas | HF-06 reports headline/per-field parity and ten OK self-checks; HF-09 publications are VALUES-only | HF-06 witness scoped to self; HF-09 evidence gap above |
| Visual | Summary/Notes presentation described | No renders opened or created after precondition stop; no layout denial |
| Evidence | No evidence source file in change inventory; invariance reported | Eligibility, accuracy and transaction gates not reached |
| Regression / failure / performance | Ruff, compileall, app self-test and neighboring invariance reported | No new harness, transaction test, performance probe or expensive run |

### Notes that do not block

- Old READY wording in BUNDLE and START-HERE is stale record wording. The
  implementation branch and authoritative plan establish the target; this is
  not a product defect or additional denial.
- The seven HF-06 residuals are explicitly explained as genuine one-sided
  markers. The independent reader's two wrapped-annotation limitations
  (1,117/1,119 relations) and HF-09's measured-count/source deltas are
  disclosed. They are **NOTES, not denial reasons** under the practical gate.
- Disclosed decisions not to repeat additional matrix lanes or a packaged
  build are not turned into extra findings. No request for a tidier commit,
  another full gate or a new acceptance framework is made.
- Review 2's challenge to Review 1 is not applicable; Review 1 has not approved.

### Commands, environment and resource accounting

New work was restricted to `git status`, `git worktree list --porcelain`,
`git branch --all --list '*rb-5*'`, `git log/show`,
`git diff --stat 87e368c..HEAD`, `git diff --name-only 444e8d9..6df43b2`,
scoped `rg --files` / `rg -n`, PowerShell `Get-Content`, `ConvertFrom-Json`,
`Get-FileHash -Algorithm SHA256` on the small witnesses/sidecars, and a
process-memory observation. Finalization edits only review/status documents,
checks their diff and commits them.

The initial sandbox read launches failed before execution with
`helper_unknown_error: apply deny-read ACLs`; normal-access reads succeeded.
One finalization orchestration syntax error also occurred before a shell
launched or files changed. These are reviewer environment/tooling issues,
not product failures. No failed product test or acceptance harness was retried.

The review remains below 30 minutes. No product process, Python test, Excel
process, workbook generation, raw recount, image capture, build or network
operation was started. The observed PowerShell peak working set was 98,365,440
bytes (under 94 MiB), far below 2 GB. Only small documentation changes are
produced, far below 500 MB. No operation expected to exceed five minutes was
started. IMPLEMENTATION.md does not state elapsed implementation effort; the
retained Highway Log publication precedes the runtime commit by over 65 minutes,
whereas this precondition return took only the minutes recorded above. An exact
implementation-effort number is neither invented nor made a second gap.

### Decision and handoff

**DENIED — EVIDENCE GAP**, solely **RB5-R1-EG-001**. This is denial **1 of the
maximum 2** for RB-5, not a finding of a demonstrated runtime defect.

Return the same RB-5 branch to implementation for that one item. Once supplied,
the next applicable pass remains **Review 1**. Review 2 must still be a separate
fresh review that challenges an eventual approving Review 1. Neither approving
sign-off exists yet.

No merge was attempted and there is no merge SHA. No push, branch deletion,
worktree removal or retained-artifact cleanup was performed. `main`, `gh-pages`,
unrelated branches, both implementation/base worktrees and retained evidence
are preserved. **RB-5** is the actionable bundle; **RB-6** is next in order but
remains blocked on RB-5's merge.

Signed: **Codex — independent non-implementing reviewer, Review 1**.

---

## Review 1 resumed — Codex — DENIED — RETURN TO IMPLEMENTATION

| Field | Reviewed identity |
|---|---|
| Reviewer / pass | Codex / resumed Review 1, fresh task; independent non-implementer |
| Implementer | Claude |
| Branch / implementation worktree | `hotfix/rb-5-difference-classification` / `C:\Users\Yunus\Projects\wt-rb5` |
| Base | `87e368c3e9a7eaf26395308e8ddea4aba7d303e5` |
| Runtime head | `444e8d9fecee3f8335f244fa940e168161bfb878` |
| Entry / implementation-record head | `3d5d83b687c7917947c3fe4974036d189c2a3c09` |
| Previous review-record head | `91448fa2a7a4137bbfe5b39cfa92e3b641a0846f` |
| This review-record head | This documentation/witness-only commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-5/REVIEW.md` |
| Started / substantive work stopped | `2026-08-31T07:26:24.543000+00:00` / `2026-08-31T07:39:11.498000+00:00` — 12.78 minutes |
| Signature | `2026-08-31T07:44:41.728778+00:00` — 18.29 minutes from start |

The supplied task checkout was detached at the recorded base. Review used the
existing implementation branch, clean at entry. All changes after the runtime
head are documentation/witness changes; no product code moved. The earlier
return stopped at a precondition, so this remains **Review 1**, not Review 2.

### Preconditions and the previous return

The authoritative plan and implementation record say `IMPLEMENTED — AWAITING
ADVERSARIAL REVIEW`; the older denial heading in BUNDLE is stale wording, not a
new blocker. The exact branch, base, runtime and retained outputs exist.

`RB5-R1-EG-001` is **answered for this review**, subject to the explicitly
unclaimed Clean Road leg. Seven completed HF-09 cases retain generated formulas,
recalculated copies and values twins. This reviewer streamed and matched the
size and SHA-256 of all **21 files** against the committed witness. The seven
per-case recalculation records agree with those file bindings, the per-field
maps, disclosure counts and clean self-checks. All eight formulas publication
records match their recorded generation IDs and member digests.

Clean Road's 473,646,751-byte formulas file was generated, but its installed-
Excel run was interrupted by the disclosed host bugcheck. No successful result
is asserted. **What would a user see differently because this acceptance leg
was not completed?** No RB-5-caused behavior change is demonstrated; this is a
measured implementation-machine limitation affecting one of eight cases. It is
a NOTE under Prompt 05, not a repeat denial or authority to retry Excel. The
review does not independently diagnose the machine's graphics driver.

### RB5-R1-001 — P2 — normalization binds the wrong duplicate occurrence

**What would a user see differently?** Reordering two otherwise unchanged
source rows at the same postmile changes a matching self-check into **six false
differences** and blanks the ordinary row's HG/FT in the published Excel-side
data sheet.

Fault: `scripts/compare_highway_sequence_pdf.py:288-303`, with the print-side
occurrences assigned at `:247`. `keys_for` numbers duplicates in each file's
order; those occurrence numbers are not a cross-source row correspondence.
`_canonicalize_equates` nevertheless uses the print occurrence to choose an
Excel row and clear its HG/FT before the shared engine performs its actual
similarity-based duplicate assignment (`scripts/compare_core.py:4647`). That
later assignment cannot recover the source values already cleared.

The independent challenge used three **synthetic**, correctly marked and
header-valid source rows: an equate annotation, an ordinary row sharing its
physical postmile, and the equate target. Only the first two Excel rows were
swapped. Both runs used `TSMIS_PDF_VS_EXCEL.compare`, not the canonicalizer as an
oracle. No real-data incidence is inferred from this fixture.

| Runtime / input order | Paired / one-sided | Differing cells / rows | PM Suffix / HG / FT / Description |
|---|---|---|---|
| Recorded base / original order | 3 / 0 | 5 / 2 | 2 / 1 / 1 / 1 |
| Recorded base / duplicate rows swapped | 3 / 0 | 5 / 2 | 2 / 1 / 1 / 1 |
| RB-5 / original order | 3 / 0 | 0 / 0 — `match` | 0 / 0 / 0 / 0 |
| RB-5 / duplicate rows swapped | 3 / 0 | **6 / 3 — `diff`** | **2 / 2 / 2 / 0** |

The head runs publish **both** flavors. The VALUES `Comparison` sheet was read
back and has masks `EEEDDEE`, `EDEDDEE`, `EDEEEEE` (2 + 3 + 1 actual `D`
states); the control has three `EEEEEEE` masks. The reordered Excel-side data
sheet loses the ordinary row's original `U`/`R`, while the actual annotation
retains `D`/`H` and its unmoved `E`. This is a published-cell/state/typed-outcome
failure, not a display-separator inference or a console-only allegation. The
small formulas files were generated, **not recalculated**.

This violates HF-06's pair-aware closure criterion 2 and its scope/correctness
guardrails: normalize the actual equate relation without rewriting another
record; preserve the approved D3 duplicate identity contract. The standard new
fixtures pass because they do not permute a duplicate group containing an
equate annotation.

**Bounded correction:** resolve the annotation and target to the corresponding
source occurrences before mutation; do not use independent file-order ordinals
as that correspondence. Add this duplicate-order fixture through the shipped
adapter, retain the ordinary HG/FT, require zero differences for either order,
and keep genuine label/target-HG/target-FT/one-sided-E divergences visible.
Do not fix it by suppressing discrepancies after the wrong row was rewritten.

The self-contained synthetic witness is
[`witness/review1-duplicate-occurrence.json`](witness/review1-duplicate-occurrence.json).
It contains exact source arrays, the row permutation, base/head outcomes,
published state masks, runtime identities and a path/size/SHA-256 artifact
manifest. The local files remain under
`C:\Users\Yunus\.codex\worktrees\8ec9\wt-rb5\.review-rb5\duplicate-probe`:
27 files / 198,900 bytes before the small manifest itself.

### Reused evidence and acceptance coverage

The complete base-to-entry change inventory is 24 files. The product diff,
both new check files, status changes and the relevant committed witnesses were
inspected. Extra adapter files only clear the HF-09 opt-in on self/environment
comparisons; Ramp Detail Excel inherits the disclosed sibling opt-in. No
unrelated product change or shared equality/formula edit was found.

Witness paths below are relative to `hotfix-bundles/`; all five hashes were
independently recomputed.

| Witness | Bytes | SHA-256 |
|---|---:|---|
| HF-06 `before-after-counts.json` | 4,730 | `1d47c881665b99aef5b38537a378b885479be9a59666262a92ef2d5fe6cb7a31` |
| HF-06 `equate-relation-census.json` | 9,108 | `b42a1dad0fc79b11f6736a9171148c7a8b2ac759948e5c7faf39fd23d21c651e` |
| HF-06 `installed-excel-recalc.json` | 2,293 | `92d35570085d43feb099f7a1cddfd60fd07ddc984e312185b747878d5de9964b` |
| HF-09 `representation-class-census.json` | 10,978 | `5ac7e43dd6ad4f928d71525f692033dc6e138810ddf470ddd73aae148b13ada9` |
| HF-09 `installed-excel-recalc.json` | 42,636 | `593a4946fad3f5ade9fb8590c9132e6ee65c220e4e68449e0ac10dec9f49138a` |

| Criteria / surface | Evidence and disposition |
|---|---|
| HF-06.1–2: frozen equates and pair-aware closure | Retained before/after witness: 60,254 paired rows, 3,714/1,395 cells/rows to 7/7; affected columns 547/929/1,119/1,119 to 7/0/0/0. Seven genuine one-sided-E residuals and the app-free reader's 1,117/1,119 coverage are disclosed NOTES; neither causes this denial. **The new duplicate-order counterexample fails pair-aware closure.** |
| HF-06.3: anti-suppression | The committed shipped-path check passes changed-label, target-HG, target-FT, both one-sided-E directions, delayed/county boundary and non-annotation cases. The independent challenge identifies wrong-source-row mutation outside that fixture coverage. |
| HF-06.4: disclosure | Code and focused check establish run-resolved relation count in Summary and Notes. Per-call counter avoids singleton count sharing. Cosmetic native-scale rendering was not duplicated. |
| HF-06.5: paths / vs-TSN | Retained record reports three self paths agreeing at 7/7 and unchanged HSL vs-TSN totals; loaders keep self normalization separate. No matrix corpus regeneration. |
| HF-06.6–7: neighbors / canaries | Self rule remains comparator-local; the HF-09 off-control proves published data/Comparison/Routes/snapshot cells and typed counts invariant. No canary file changed. Frozen corpus/source incidence was not re-counted after the decisive failure. |
| HF-06.8 / HF-09.7: tests / full gate | Both new checks pass here; the equality-policy neighboring check ends `all good`. Implementation records 171/171, ruff, compileall, app self-test and pre-fix failures. Full-gate logs and every individual pre-fix assertion were not independently revalidated; no full gate or packaged build was rerun. No complete acceptance sign-off is claimed. |
| HF-09.1–3: disclosure / flagged cells / census | Reviewed opt-in predicate, additive Summary subset, eight-family census and completed recalculation records; all complete cases' disclosed counts agree with the census. The focused on/off check retains cells, snapshots, counts and typed verdict. All eight base/head VALUES provenance pairs bind identical source digests. |
| HF-09.4: equality / totals | Diff adds a subtotal only after the cell is already counted; no equality operand or formula changes and no corrected differing-row claim. The equality-policy check passes. |
| HF-09.5–6: evidence / unset hook | Evidence code including the quote clarifier is unchanged; five inheriting self/environment schemas explicitly clear the hook and the focused wiring check passes. The implementation's evidence gate is retained as reported, not rerun. |

| HF-09 completed case | Retained differing cells / rows | Class F = V | SELF-CHECKs | Cached errors |
|---|---:|---:|---:|---:|
| Highway Log Excel | 84,709 / 38,478 | 1,243 | 10 OK | 0 |
| Highway Log PDF | 84,202 / 38,931 | 1,243 | 10 OK | 0 |
| Highway Sequence Excel | 28,450 / 22,554 | 12 | 10 OK | 0 |
| Highway Sequence PDF | 27,601 / 22,728 | 12 | 10 OK | 0 |
| Intersection Detail Excel | 5,092 / 2,816 | 1 | 11 OK | 0 |
| Intersection Detail PDF | 5,092 / 2,816 | 1 | 11 OK | 0 |
| Ramp Detail PDF | 619 / 468 | 3 | 10 OK | 0 |
| Clean Road (VALUES only accepted as retained evidence) | 281,393 / 48,942 | VALUES: 2 | Excel leg unclaimed | Unclaimed |

Values/formulas **result claims** in this table come from the implementation's
recalculation records; this reviewer verified their internal agreement and file
bindings, not a fresh cached-cell scan. HF-06's separate retained recalc reports
7/7, matching per-field maps and ten OK checks. Native-scale renders, the raw
source recount, full transaction/failure suite and large acceptance outputs
were not regenerated. No rendering, transaction or source-truth approval is
implied for unperformed reviewer work.

### Notes and bounded follow-ups, not additional denials

- **HSL formulas source binding:** base/head VALUES use Excel-source digest
  `7ccb8d98e67822d4005b48d1d39c0e67e6a6f459c0deb9f14bcd7d85897255bc`
  and PDF-source digest
  `29f96642efdff4b7fe956c2e7b73888084c5db65fda0a446f1ce1f533687ece8`.
  FORMULAS provenance instead records
  `a970568ad931ace4b181b9e84a281e26ab2e7ef332a34dfebc8486479b700546`
  and `b8cd4d2f9bc8aa687dffdb9e783e9c4dcb2f7a6a622dfee020bc0284288a23a3`.
  The same filenames carry different digests and producer completion changed
  from null to complete; source-byte identity is therefore **not** proved across
  these two pairs. Recorded totals/per-field results do agree. What would a
  user see differently? No additional incorrect output was demonstrated.
  Preserve this qualification; do not assert all eight pairs have identical
  source bytes or demand an expensive rerun merely to tidy the binding.
- The old zero-total criterion conflicts with preserving seven genuine
  one-sided markers. The measured residuals, two wrapped oracle annotations,
  12/3/2 representation counts and deliberate skipped matrix/build legs are
  already disclosed. No new user-facing failure is inferred from their wording.
- No native-scale renders were identified in the named HF-06/HF-09 acceptance
  directories. Visual cosmetics are not a blocking finding under Prompt 05.
- Review 2's challenge to an approving Review 1 is not yet applicable.

### Commands, resources and decision

New work: read-only Git status/log/diff/worktree identity; scoped file/JSON
reads; streaming SHA-256 checks; source/generation/provenance comparisons;
`check_compare_highway_sequence_equate.py`,
`check_compare_representation_class.py`, and
`check_compare_equality_policy.py` once each using the existing build Python;
two three-row head cases through the shipped adapter in `mode="both"`, then
the same inputs at the recorded base in `mode="values"`; read-back of the
tiny published cells and masks. The witness records exact inputs and outcomes.
Review logs are retained alongside `duplicate-probe`; the new fixture is
synthetic and never copies real TSMIS data into the repository.

Reviewer tooling issues are separate: the initial sandbox launches failed
before execution (`apply deny-read ACLs`), so normal-access shell reads were
used. The one-off bulk hash reader matched all 21 completed-case files before
raising `KeyError: 'sha256'` on the intentionally incomplete Clean Road values
entry; it was **not rerun**, and no Clean Road file-hash check is claimed from
that reader. An optional filename search yielded no usable acceptance log;
it did not trigger another search or a gate rerun. No product failure is
inferred from any of these events.

The review stayed under 30 minutes and below the implementation's retained
29-minute Highway Log Excel leg alone. The independent workbook probes each had three rows;
large files were hashed by streaming, never loaded for recalculation. No
operation expected above five minutes or 2 GB additional memory was started;
observed reviewer PowerShell peak was 94,846,976 bytes. Probe files total under
0.2 MB before the manifest; all new output is far below 500 MB. No installed
Excel, full rebuild, statewide generation, full raw recount, image recapture,
frozen build or full repository gate was started. No exception was requested.

**Verdict: DENIED — RETURN TO IMPLEMENTATION, solely `RB5-R1-001`.**
This is denial **2 of 2**, the final allowed denial for RB-5. It is a concrete
product regression; it is not another request for the supplied HF-09 acceptance
leg. Correct this bounded defect on the same branch. Remaining observations
are follow-ups for the owner, not grounds for a third denial or an expanding
review cycle. Reuse unaffected HF-09 evidence; this finding does not authorize
another Clean Road rebuild or statewide acceptance regeneration.

Neither approving sign-off exists. The applicable pass after correction is
still Review 1; Review 2 remains a separate fresh review. No merge, push,
branch/worktree cleanup or next-bundle implementation was attempted. There is
no merge SHA. `main`, `gh-pages`, unrelated work and retained evidence are
preserved. **RB-5** is actionable; **RB-6** remains next in order and blocked
until RB-5 merges.

Signed: **Codex — independent non-implementing reviewer, resumed Review 1**.
