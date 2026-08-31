# RB-5 — Adversarial Review Record

Status: **MERGED**

Current decision: **JOINTLY APPROVED**. Separate Codex Reviews 1 and 2 approve corrected runtime 0d54799a108d944280ffb7a092260cae59778f76. Review 2 carries RB5-R2-FU-001 under the two-denial ceiling; limitations and both signed records are retained below.

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

---

## Review 1 correction closure — Codex — APPROVED

| Field | Identity |
|---|---|
| Reviewer / pass / implementer | Codex / resumed Review 1, independent non-implementer / Claude |
| Branch / worktree | `hotfix/rb-5-difference-classification` / `C:\Users\Yunus\Projects\wt-rb5` |
| Base | `87e368c3e9a7eaf26395308e8ddea4aba7d303e5` |
| Runtime / entry head | `0d54799a108d944280ffb7a092260cae59778f76` |
| Prior review-record head | `e656dc1c2a3931dfdec9de044dd0908f24a1b46f` |
| Current review-record head | This documentation/witness commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-5/REVIEW.md` |
| Started / substantive work stopped | 2026-08-31T17:40:01.299Z / 2026-08-31T17:56:37.039Z — 16.60 minutes |
| Signed | 2026-08-31T18:11:40.418005+00:00 |
| Verdict | **APPROVED — REVIEW 1 APPROVED — AWAITING REVIEW 2** |

The supplied checkout was detached at the old base. Review located the actual
implementation branch before evaluating preconditions; it was clean at entry.
The plan and implementation record establish the implemented status. Prior
denial headings were historical wording. Neither approval existed, so this is
Review 1. The exact branch/base/runtime and retained outputs exist. Disclosed
hardware and coverage limits are treated under Prompt 05's practical-impact
gate, not silently represented as complete acceptance. Both denials are used;
remaining observations are owner-ranked follow-ups.

**RB5-R1-001 is CLOSED.** The complete product diff, both new checks, correction
diff, status changes and retained witnesses were inspected. Correspondence now
uses postmile/content rather than per-file occurrence order. Target signatures
are resolved before suffix fallback, against original rows. The focused shipped-
adapter test passes both duplicate orders, published ordinary HG/FT retention,
relabelled duplicates, ambiguous annotation refusal, real label/target-HG/
target-FT/one-sided-E changes, delayed/county-boundary cases and scope fences.
The repaired same-source-shape assertions were inspected.

The independent challenge targeted wrong-row mutation before duplicate pairing.
An additional generator produced the prior synthetic witness's first tiny pair,
then stopped on an incorrect assumed FORMULAS filename. It was **not retried**;
planned permutations were not executed. Read-only inspection of its existing
outputs confirms three `EEEEEEE` masks, zero differences, ordinary HG=`U` /
FT=`R`, and identical canonical Excel data rows in both flavors. FORMULAS uses
`original-witness-order.xlsx`. No Excel recalculation was performed. Swapped-
order proof is the passing committed test and retained correction witness.

Final retained `HF-06/rb5-a1/head-r3` generation
`a84d4094-4118-4ada-bfd6-80b55d6be55c` independently verifies **60,254 paired,
zero one-sided, 7 cells / 7 rows; PM Suffix 7, every other field 0**. Its
workbook and compressed/decoded payload hashes match; the typed payload identity
is unchanged from the original 7-cell head. The retained 129-cell `head-r2`
intermediate agrees with its disclosed rejection and is not accepted.

**RB5-R1-EG-001 is CLOSED for seven completed cases**, with Clean Road formulas
explicitly unclaimed. All **21** completed-case workbook sizes/SHA-256 match:
seven VALUES, seven generated FORMULAS and seven recalculated copies. Their
per-field maps, class counts, self-checks and separate recalculation records
agree. The correction changes the self path; unaffected HF-09 evidence is reused.

### Acceptance and result matrices

| Criteria | Evidence / disposition |
|---|---|
| HF-06.1–2 | Retained base 3,714 cells / 1,395 rows to final 7/7; 3,707 representation cells close in all four columns. Duplicate-order return closed. Literal zero-total wording conflicts with required genuine one-sided-E preservation: NOTE, not suppression authority. |
| HF-06.3 | Passing genuine-label, target HG/FT, both one-sided-E, boundary/delayed and unresolved-annotation fixtures. No exhaustive duplicate-target perturbation suite claimed. |
| HF-06.4 | Focused Summary/Notes disclosure test and retained Summary cache state 1,119; per-call counter inspected. Native-scale coverage qualified below. |
| HF-06.5 | Original three-path parity retained in implementation/self Excel witness; Everything payload independently verifies 7/7 and final direct remains 7/7. Both vs-TSN editions' typed/per-field outcomes independently unchanged. |
| HF-06.6–7 | Rule confined to self loader; no shared equality/formula operand change. Off-control preserves cells, masks, snapshots, counts and typed outcome. No canary file moved. |
| HF-06.8 / HF-09.7 | Five focused checks pass. Base failures retained in implementation/prior witnesses and missing mechanisms confirmed in diff; no new base rerun. Corrected gate is recorded 170/171 with the disclosed validation issue, not asserted 171/171. |
| HF-09.1–3 | Additive Summary subset follows already-counted D cells. On/off check retains published cells/masks. All eight retained base/head typed payloads, every field count, status/completion/verdict/pairing quality agree. Independent census and completed formulas counts agree, with disclosed reader/source limitations. |
| HF-09.4 | No equality change, suppressed cell or corrected differing-row claim; equality-policy check passes. |
| HF-09.5–6 | Quote clarifier inspected and unchanged; evidence files unchanged. Self/environment fences and neighboring cell/state/count/outcome controls pass. Extra adapters are documented fences/inherited Ramp Detail sibling; no unrelated scope. |

| HF-09 case | Differing cells / rows, unchanged | Class F = V | Recalc |
|---|---:|---:|---|
| Highway Log Excel | 84,709 / 38,478 | 1,243 | 10 OK; 0 errors |
| Highway Log PDF | 84,202 / 38,931 | 1,243 | 10 OK; 0 errors |
| Highway Sequence Excel | 28,450 / 22,554 | 12 | 10 OK; 0 errors |
| Highway Sequence PDF | 27,601 / 22,728 | 12 | 10 OK; 0 errors |
| Intersection Detail Excel | 5,092 / 2,816 | 1 | 11 OK; 0 errors |
| Intersection Detail PDF | 5,092 / 2,816 | 1 | 11 OK; 0 errors |
| Ramp Detail PDF | 619 / 468 | 3 | 10 OK; 0 errors |
| Clean Road | 281,393 / 48,942; partial both legs | VALUES 2; F unclaimed | Hardware-limited |

All eight base/head VALUES provenance pairs bind identical source hashes/sizes.
HF-06's retained recalc reports 7/7, equal fields and ten OK checks. Reading its
Summary caches confirms total 7, relation count 1,119 and no Summary error cells.
No new full-workbook cached-error scan or recalculation is claimed.

| Surface | Verification / limits |
|---|---|
| Source truth | Independent reader method inspected: raw openpyxl plus separate pdfplumber grammar, 1,117/1,119 annotations, 39 boundaries, two delayed targets and two wrapped blind spots. Complete selected raw PDF page text and XLSX rows checked without app parser. Route 001 page 6 / rows 121–122 confirms normalization; route 032 page 10 / rows 218–219 and route 580 page 8 / row 74 confirm genuine missing-E directions. |
| Visual | Summary/self Notes text tested/read. No native-scale acceptance renders found in named roots; no complete visual approval claimed. Optional image access failed at sandbox ACL setup; raw text worked. |
| Evidence | Quote clarifier and evidence files unchanged; self evidence loader consumes canonicalized pair. Retained implementation gate covers eligibility; no new all-image/absence scan. Publication authentication/tamper-refusal check passed. |
| Provenance / stale cache / failure | Eight source pairs agree. Publication check rejects inconsistent/missing outputs; freshness check retains regeneration guards. Publication substrate/guard path unchanged; no new full transaction suite. |
| Performance | Classification uses existing difference loop; self matching uses local groups/copies. No whole-corpus framework or benchmark. Focused equate test 6.63 seconds. |

### Practical-impact gate and limitations

**What would a user see differently?** Genuine one-sided markers remain visible;
suppressing them would be wrong. Reader blind spots and disclosed 12/3/2 census
deltas establish no new wrong output. HF-09's separate census classifies published
values; it is not a second raw parser. Clean Road's unfinished formulas leg stays
unclaimed, not a product-failure diagnosis or permission to retry Excel.

The recorded validation failure concerns support-bundle duplicate member names
with staged TSN data, outside the RB-5 diff. Implementation records that it passes
without that staging. It remains a separate follow-up; no full-gate log was
independently located. Recorded full gate, ruff, compileall and self-test results
are not fresh reviewer executions.

The earlier HSL VALUES/FORMULAS source-byte mismatch remains qualified despite
matching results; no new wrong output was demonstrated. Native-scale visuals,
dedicated HF-09 Notes count coverage, all extra matrix legs and packaged build
coverage are not independently established here. The useful count/explanation
is proved in Summary; these gaps establish no wrong count or silent failure.
Preserve them as follow-ups, not assertions that every strict criterion passed.

Route 580's raw record is row 74, not the cited 77; head labels and old status
wording change no application behavior. Annotation normalization precedes target
resolution, so “left untouched” overstates the whole-relation behavior when a
target is unresolved. No new wrong-row mutation or false match was established;
a later bounded challenge may examine this boundary without reopening the return.

### Evidence binding, commands and resources

The [approval verification witness](witness/review1-approval-verification.json)
retains exact artifact paths, sizes, SHA-256 identities, generations, typed
results and local-check references. Seven committed witnesses were independently
digested. **31 previously recorded size/hash expectations matched** (21 HF-09
workbooks plus five HF-06 workbook/payload pairs); eleven other hashes are observed
identities, not comparisons to earlier claims. No raw TSMIS rows/images are newly
committed.

Final HF-06 workbook: 34,860,672 bytes,
`e802b1c3b2561edca65e63bdb89dd4ebe6d08547ffb4afc1b52b364c2d5fb395`.
Correction witness: 5,830 bytes,
`96ca7f4b35952b395fbcfcc09c90dd7ab5ca75af976b93f542a6b725b57d7573`.
HF-09 Excel witness: 42,636 bytes,
`593a4946fad3f5ade9fb8590c9132e6ee65c220e4e68449e0ac10dec9f49138a`.

Once each with existing build Python: `check_compare_highway_sequence_equate.py`
(6.63 s), `check_compare_representation_class.py` (1.06 s),
`check_compare_equality_policy.py` (4.04 s), `check_published_comparison.py`
(3.83 s), `check_compare_build_freshness.py` without Excel (0.72 s): **all PASS**.
Other work was scoped Git/file reads, streaming hashes, retained payload/cache
inspection, raw source spots and the one interrupted tiny generator.
Logs: `C:\Users\Yunus\.codex\worktrees\76ed\wt-rb5\.review-rb5`.

Sandbox process/file/image access failed with `apply deny-read ACLs`; permitted
native access worked. The wrong-filename generator was not retried. Two
finalization orchestration parse errors occurred before commands or mutations.
These are reviewer issues, not product failures.

Substantive review stopped at 16.60 minutes. Record finalization reached the
first commit at 31.66 minutes, exceeding the 30-minute ceiling by 1.66 minutes.
This is a reviewer budget deviation, not a product failure; no further
substantive review was performed. The earlier within-budget statement was
corrected at 2026-08-31T18:12:43.526541+00:00 (32.70 minutes from start).
The review remained shorter than the overall recorded implementation effort.
Retained verification took 17.70 s, peak 79,552,512 bytes; observed shell peak
100,954,112 bytes. Pre-finalization output was 214,171 bytes; records keep total
new output below 1 MB. No operation expected above five minutes, 2 GB additional
memory or 500 MB output was started. No Excel, statewide generation, raw recount,
frozen build, full gate, new task or budget exception.

**APPROVED**, signed **Codex — independent non-implementing reviewer, Review 1**,
2026-08-31T18:11:40.418005+00:00. Both returns are closed with the stated notes. **Review 2 remains
pending**; this is not joint approval. Per first-approver protocol, commit and
stop. No fetch, merge, push, branch/worktree cleanup or evidence deletion; no
merge SHA. Preserve main, gh-pages and unrelated work. Next: **RB-5 Review 2**;
**RB-6** remains queued and blocked until RB-5 merges.


---

## Review 2 — Codex — APPROVED

| Field | Identity |
|---|---|
| Reviewer / pass / implementer | Codex / Review 2, separate fresh non-implementing reviewer / Claude |
| Branch / implementation worktree | `hotfix/rb-5-difference-classification` / `C:\Users\Yunus\Projects\wt-rb5` |
| Recorded main base | `87e368c3e9a7eaf26395308e8ddea4aba7d303e5` |
| Corrected runtime | `0d54799a108d944280ffb7a092260cae59778f76` |
| Entry and Review 1 record head | `03ad6b306313e9199acd159e0b6378e9a5ca3db2`; no runtime changes after the correction |
| Review 2 record head | This commit; resolve the commit adding `witness/review2-verification.json` |
| Started / signed UTC | `2026-08-31T18:15:39.110000+00:00` / `2026-08-31T18:32:36.909182+00:00` |
| Elapsed at signed record creation | **16.96 minutes**, including record preparation; closeout timing is recorded below |
| Verdict | **APPROVED; JOINTLY APPROVED**, with the explicit follow-up and limitations below |

The fresh checkout was detached at the recorded old base. The actual local
RB-5 branch was located before evaluating preconditions and was clean at entry.
The current plan, bundle, implementation and signed Review 1 records all establish
`REVIEW 1 APPROVED — AWAITING REVIEW 2`. The exact base/runtime, retained
publications, corrected duplicate-order witness and seven completed HF-09
recalculation cases exist. The disclosed Clean Road hardware-limited leg,
validation limitation and deliberate coverage trade-offs are assessed under
Prompt 05's practical-impact gate, not presented as completed acceptance.
Both denials were already used. No third denial cycle is opened.

### Independent challenge to Review 1

Review 1 proved duplicate ANNOTATION order but did not exhaustively perturb
TARGET duplicate groups; its additional permutation generator stopped on a
filename assumption. It also did not test simultaneous disclosure counters or
non-ASCII classification. Review 2 challenged these distinct mechanisms through
small shipped-path outputs, not another acceptance run:

- **16 combinations** independently reorder annotation and target groups in
  both editions. Every combination reports **0 cells / 0 rows**, preserves
  ordinary neighbor HG/FT, and publishes identical canonical data in both flavors.
- Genuine target City, HG, FT, Distance and Description changes each remain
  visible (**3 cells / 2 rows** each in the ambiguous duplicate case). Resolving
  conservatively leaves two suffix differences as well as the real change;
  no changed target value is erased or converted into agreement.
- A missing E in either direction remains **1 cell / 1 row**. A missing target
  remains **1 differing cell plus 1 print-only row**. Two unresolved targets
  keep their injected HG values and retain **4 cells / 3 rows**.
- Two concurrent calls through the shared adapter independently disclose
  **1** and **0** relations. All **27** cases publish both flavors with equal
  canonical data. This is data-sheet parity, not a fresh Excel recalculation.
- A separate published classifier probe exposed **RB5-R2-FU-001** below.

One initial probe flag was a reviewer assertion error: the unresolved-target
case deliberately changed the neighbor HG to `Y`, while a generic assertion
still required `U`. Inspection of the ALREADY-generated workbook proves `Y/R`
retained on that neighbor, `X/H` on the target, `U/R` on the unchanged annotation
neighbor, and E retained at the unresolved annotation. The original flag and
explanation are preserved in the witness. The harness was **not rerun**.

Raw-source re-derivation deliberately selected cases beyond Review 1's named
001/032/580 spots. Direct openpyxl rows and independent pdfplumber text establish:
route 036 rows 198–200 / PDF page 9 distinguish the wrapped annotation from its
ordinary duplicate; route 215 rows 198/200/201 / page 9 distinguish the bare and
wrapped annotations sharing one postmile; route 063 row 151 / page 7 proves a
genuine missing E, distinct from the ordinary same-postmile row 124 / page 6.
The two oracle blind spots are real wrapping limits; the new check does not
promote that oracle into an exhaustive reader of all other fields. Raw extracts
remain local only; committed evidence includes source identities and conclusions.

### Evidence and acceptance matrix

The complete 27-file branch change inventory is accounted for. Runtime and
focused-test diffs were independently inspected; document changes record scope,
results and prior reviews. Extra sibling adapters only clear inherited hooks or
supply the documented Ramp Detail sibling opt-in. No equality operand, canary,
provenance/publication substrate or evidence renderer changes. Only
`compare_highway_sequence_pdf.py` changed between initial and corrected runtimes,
so unaffected HF-09 acceptance evidence is reused by runtime equivalence.

| Criteria | Exact evidence and result |
|---|---|
| HF-06.1–2: close the ruled class | Hash-bound base payload: 3,714 cells / 1,395 rows, per-field 547 suffix / 929 HG / 1,119 FT / 1,119 Description. Corrected `head-r3`: 7/7, 60,254 paired, zero one-sided, suffix 7 and other fields zero. **3,707** representation cells close. The seven genuine markers must remain; literal zero-total wording is a wording conflict, not suppression authority. |
| HF-06.3: anti-suppression | Existing committed fixture inspected and Review 1 execution reused; Review 2's duplicate-target field perturbations, both E directions, missing/unresolved targets and all 16 order combinations independently challenge false agreement. |
| HF-06.4: normalized disclosure | Shipped tiny outputs and concurrent calls disclose their own 0/1 counts in Summary/Notes. Retained statewide count 1,119 comes from implementation and Review 1's checked cache; complete native-scale visuals remain qualified below. |
| HF-06.5: path / vs-TSN parity | Corrected decoded payload is identical to retained original direct and Everything payloads. By-day/formulas parity is retained in the HF-06 recalc witness. Both HSL vs-TSN base/head typed outcomes and every field count independently agree. |
| HF-06.6–7: fences / canaries | Self-only loader; no shared equality/formula change or canary file changed. Scope opt-out and neighboring semantic checks pass. |
| HF-06.8 / HF-09.7: regression | Base failures and full corrected gate retained, not repeated before merge. Three new focused executions pass; original defect is reproduced in retained base payload. Corrected full gate remains reported **170/171**, with the disclosed validation issue. |
| HF-09.1–3: disclosure / flags / census | All eight base/head typed counts, every field, status/completion/verdict/pairing quality and recorded source pairs independently agree. Seven completed formulas records have equal per-field maps, disclosure counts, clean checks and zero reported cached errors. Existing census agrees. Unicode subset misclassification is explicitly carried as FU-001 under the denial ceiling. |
| HF-09.4: equality / totals | Classification occurs only after a D cell is counted; no headline total or equality changes. The Unicode probe itself remains D and counted. No corrected differing-row claim. |
| HF-09.5–6: quote/evidence/neighbors | Evidence and `_quote_note` code unchanged. Representation on/off check verifies published data, states, counts and outcome invariance; neighboring Highway Sequence and atomic-publication checks pass. |

| HF-09 retained case | Cells / rows, unchanged | Representation count | Recalculation record |
|---|---:|---:|---|
| Highway Log Excel | 84,709 / 38,478 | 1,243 | 10 OK; 0 errors |
| Highway Log PDF | 84,202 / 38,931 | 1,243 | 10 OK; 0 errors |
| Highway Sequence Excel | 28,450 / 22,554 | 12 | 10 OK; 0 errors |
| Highway Sequence PDF | 27,601 / 22,728 | 12 | 10 OK; 0 errors |
| Intersection Detail Excel | 5,092 / 2,816 | 1 | 11 OK; 0 errors |
| Intersection Detail PDF | 5,092 / 2,816 | 1 | 11 OK; 0 errors |
| Ramp Detail PDF | 619 / 468 | 3 | 10 OK; 0 errors |
| Clean Road | 281,393 / 48,942; partial on both legs | VALUES 2 | FORMULAS leg hardware-limited, **unclaimed** |

| Review surface | Result / practical limitation |
|---|---|
| Values/formulas | All 21 completed HF-09 workbook sizes/digests match. Recalc record consistency independently checked; cached-error scans and large Excel recalculations were not repeated. HF-06 retained recalc: 7/7, identical fields, ten OK checks; corrected tiny twins agree. |
| Visual | Summary/Notes text and counts checked in small output; native-scale acceptance renders were not identified by the prior review. No complete visual approval claimed and no cosmetic denial. |
| Evidence eligibility / fidelity | Unchanged code and retained gate; no new corpus-wide image/absence audit. Atomic-publication integrity/refusal check passes. |
| Provenance / stale cache / failure | All eight base/head source-pair records agree; current corrected self inputs also match their own source hashes and sizes. Earlier HSL VALUES versus FORMULAS source-byte mismatch stays qualified; results agree but identical bytes across those pairs are not asserted. Publication/freshness substrate unchanged. |
| Source truth | Independent reader method and limitations inspected; three selected raw cases re-derived. No whole-corpus recount. |
| Performance / rerun | Classifier runs inside the existing difference loop; matching resolves local groups against original rows. Tiny shipped-path suite: 18.281 s. No extra expensive work is introduced by the review. |

### Practical-impact gate and follow-ups

**RB5-R2-FU-001 — non-ASCII letters can be mislabeled as presentation**
(`scripts/compare_core.py`, `_REPRESENTATION_STRIP_RE` / `representation_only`).
The regex retains only ASCII letters/digits. A shipped-engine VALUES probe for
`PEÑA ROAD` versus `PEA ROAD` reports a representation-only subset of **1**.
**What would a user see differently?** A real dropped letter is described as
presentation-only, which could lead a reader to discount it. The differing-cell
total remains **1**, the displayed pair remains visible and its mask remains
**D**. This is a concrete classification follow-up; frozen-corpus incidence is
not established. Preserve Unicode letters when forming the class key and add
this negative fixture in owner-authorized follow-up work. **Not a third denial:**
Prompt 05 explicitly caps this bundle at two denials and directs remaining
findings to owner-ranked follow-ups while the bundle proceeds. No runtime fix
or new acceptance run is smuggled into this review.

Other carried notes, each assessed before the verdict:

- Genuine E residuals: hiding them would change user output incorrectly; keep
  all seven. Wrapped-reader limits and measured 12/3/2 class counts are disclosed.
- Clean Road's 452 MB formulas leg is unclaimed after the recorded hardware
  failure; no new wrong output is established and no rebuild is attempted.
- The staged-library duplicate archive-member validation issue is outside the
  diff and separately disclosed. The recorded gate is not relabeled 171/171.
- Missing complete native-scale/matrix/packaged acceptance coverage and prior
  source-byte qualifications remain limits, not invented successful runs.
- Review 1's acknowledged finalization overrun changes no application behavior;
  it is not grounds to repeat acceptance or withhold this separate review.

### Binding, commands, budget and signatures

[Review 2 verification](witness/review2-verification.json) binds all new scripts,
logs, small outputs, source spots, decoded typed results and reused evidence.
**42 distinct retained file identities match**, including the 21 completed
HF-09 workbooks, prior correction witnesses and the corrected self publication.
The corrected self workbook is 34,860,672 bytes, SHA-256
`e802b1c3b2561edca65e63bdb89dd4ebe6d08547ffb4afc1b52b364c2d5fb395`,
generation `a84d4094-4118-4ada-bfd6-80b55d6be55c`; its decoded payload digest is
`225b92d7bd5155a4e1459d4f5fa777b7558e6ab1df9565f33863a0bed8ac8bae`.
The rejected 129-cell intermediate is not accepted evidence for the final result.

New checks, once each with the existing build Python:
`check_compare_representation_class.py` **PASS** (1.328 s),
`check_compare_highway_sequence.py` **PASS** (2.063 s),
`check_published_comparison.py` **PASS** (4.968 s). Other new commands were scoped
Git/diff/file reads, streaming hashes (2.719 s), retained JSON/payload inspection,
the 27 tiny shipped-path cases plus one classifier case, and three raw-source
spots. No full gate ran during substantive review; it runs once after merge.

The first sandbox launch failed before execution on `apply deny-read ACLs`;
permitted normal-access execution worked. One Windows filename-glob search
returned an invalid-pattern diagnostic; it was not retried. These and the
single flawed probe assertion are reviewer issues, not product failures.
Observed shell peak was 89,407,488 bytes; the largest new comparison has four
rows. New review output is under 5 MB. No operation expected above five minutes,
2 GB additional working memory or 500 MB output was started; no full rebuild,
statewide generation, full raw recount or repeated acceptance occurred. Record
creation is within 30 minutes and far shorter than the recorded implementation
(seven Excel legs alone total over an hour). No budget exception requested.

**APPROVED**, signed **Codex — Review 2, independent non-implementer**,
`2026-08-31T18:32:36.909182+00:00`. Review 1's independent Codex approval at `03ad6b306313e9199acd159e0b6378e9a5ca3db2`
and this separate Review 2 both approve runtime `0d54799a108d944280ffb7a092260cae59778f76`; implementer is
Claude. **JOINTLY APPROVED.** Proceed with the prescribed fetch, no-force merge,
once-only post-merge smoke, push and bounded cleanup. RB-6 becomes eligible only
after RB-5's merge closeout. No RB-6 implementation is authorized here.


## Post-merge smoke — 2026-08-31

RB-5 merged without force as `f11f9d2546b7775e432a22d5174f895f01210c35` after both separate Codex approvals.
Fetched remote main and local main both equaled base `87e368c3e9a7eaf26395308e8ddea4aba7d303e5`; the user's feature checkout was untouched.
The merged runtime is identical to reviewed `0d54799`.

- `build/run_checks.py -j 4 -k`: **171 passed, 0 failed**, 123.531 seconds; measured process-tree peak 1,399,373,824 bytes. This is the once-only full post-merge gate, including `check_validation`, on the clean main worktree without the acceptance TSN staging. It does not erase the separately documented staged-library defect.
- `build/build.ps1 -SelfTest`: **PASS**, 72.750 seconds; measured process-tree peak 868,896,768 bytes. The real windowed packaged application passed its self-test. Existing pinned build environment reused; no Excel recalculation or acceptance regeneration.
- New retained build/review output measured 217,103,457 bytes, below 500 MB. Both operations individually stayed below five minutes and 2 GB, with a process-tree resource guard.

Exact logs and hashes: [merge closeout](witness/merge-closeout.json) and [full post-merge gate](witness/postmerge-gate.log).
Review plus this record finalization: **25.03 minutes** at `2026-08-31T18:40:41.079391+00:00`.
The plan now records MERGED with the exact merge SHA. Push, bounded cleanup and RB-6 readiness are recorded in the final closeout, not pre-claimed here.


## Final cleanup and readiness — 2026-08-31

Main's merge and passing smoke closeout were pushed before cleanup. The fully
merged local and remote `hotfix/rb-5-difference-classification` branches were
removed. Only the implementation worktree registration at
`C:\Users\Yunus\Projects\wt-rb5` was removed. Its retained `output/`,
`tsn_library/`, `arcgis_layers/`, `config.json` and `compare_timings.json` were
moved temporarily, then restored byte-preserving at their ORIGINAL paths in a
plain artifact-only folder; no `.git` remains there. Main, gh-pages, the user's
feature branch/checkouts, unrelated review worktrees, pre-fix evidence worktree,
audit roots and review documents are preserved. The detailed preservation and
branch checks are in [cleanup verification](witness/cleanup-verification.json).

**Next eligible bundle: RB-6 — READY**, full HF-07/HF-08/HF-11 contract prepared
from pushed main `a0787e7710b326945797c7c51f56acb7081d0f20`. No RB-6 branch, implementation, rebuild or
acceptance run started. `report_catalog.TSN` was observed to contain 11 entries;
an optional identifier-print expression assumed `.id` and stopped with an
AttributeError after printing that count. It was not retried and is not a
product failure.

Review and record finalization reached **29.93 minutes** at
`2026-08-31T18:45:35.043861+00:00`, within the 30-minute ceiling. Final record commit and
normal push follow immediately. Verdict remains **APPROVED**, both separate
Codex non-implementer sign-offs retained, runtime `f11f9d2546b7775e432a22d5174f895f01210c35` merged;
RB5-R2-FU-001 remains an owner-ranked follow-up under the two-denial ceiling.
