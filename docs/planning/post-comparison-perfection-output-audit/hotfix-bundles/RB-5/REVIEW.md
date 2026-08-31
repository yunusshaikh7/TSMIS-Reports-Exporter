# RB-5 — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

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
