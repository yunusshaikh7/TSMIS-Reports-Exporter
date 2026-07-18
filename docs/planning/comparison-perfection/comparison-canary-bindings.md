# Comparison real-data canary bindings

Last updated: 2026-07-14  
Corpus root: `C:\Users\Yunus\Downloads\TSMIS` (local only; never copy corpus members into the repository)  
Purpose: bind the exact real bytes used to approve comparison behavior before any
semantic re-bless

## Trust policy

- Read the corpus `_INDEX.md` for routing, but do not treat the index, an agent report,
  or a historical comparison workbook as identity proof.
- `ground-truth/` is the acceptance source. `report-samples/` is for parser spot checks,
  `comparison-outputs/` is historical reference only, and `_scratch/` is never an oracle.
- Hash only the selected files or an exact selected member manifest. Do not crawl or
  hash the entire approximately 5.8 GB corpus.
- A changed expected count is a stop condition until exact source identity, code/
  producer versions, and the cell-level delta explain it.

Binding states:

- `baseline-bound`: exact inputs and current code identity are recorded; typed values/
  formulas output and real-Excel recalculation agree with the approved result.
- `input-bound`: exact source files, roles, lengths, and SHA-256 values are recorded;
  pre-change output/code identity is still pending.
- `provisional`: the bundle and expected result are named, but its exact member manifest
  and digest are not yet recorded.
- `blocked`: the available material cannot yet support an unambiguous acceptance result.

## First bound canary — Highway Log Route 1

Canary ID: `HL-R1-E1`  
Flavor: per-route TSMIS Excel versus TSN Excel  
Stable recipe family: Highway Log vs TSN  
Binding state: `baseline-bound`  
Expected approved result: 299 paired / 18 TSMIS-only / 69 TSN-only /
221 differing rows / 969 differing cells

| Role | Exact file | Length | Last write UTC (informational) | SHA-256 |
|---|---|---:|---|---|
| TSMIS | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\inputs\tsmis_highway_log_route 1.xlsx` | 350,655 | 2026-06-11 16:32:57 | `34787055E8710CB656D0C016FD2290F222897089305097F072F146E78F2F15E2` |
| TSN | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\inputs\tsn_highway_log_route 1.xlsx` | 44,299 | 2026-06-16 22:46:21 | `93DA8DF0FF0C147E3456B889A8525C52B04871368AFFD2AAA893C09C02AD3303` |

The timestamps are not trusted identity; SHA-256 and exact role/path are.

### Pre-Phase-3 baseline run — 2026-07-11

- Git base: `0430b4259b86124494729fcd79b4b084aa3ebaed`; the worktree was intentionally
  dirty with the audited Phase-1/2 changes and is not represented by that commit alone.
- Working source manifest: 124 files (`scripts/**/*.py` plus `version.py`), sorted as
  `relative/path|file_sha256` and joined with LF; manifest SHA-256
  `0f89f2dd933917cc839ff54a093f6ecf4f6cd647eb386f95603e635a4907764a`.
- The real comparator ran in `mode="both"` and strict-read one committed generation
  containing values plus formulas. Typed result: complete/diff; 299 paired; 18/69
  one-sided; 221 differing rows; 78 identical paired rows; 969 differing cells;
  8,970 asserted cells.
- Values workbook: 207,665 bytes; SHA-256
  `85dc68bd1def2e0653a0875f7bf8fc7d0e2134485c0df4f58b640344abd9f04c`.
- Formulas workbook before Excel: 743,789 bytes; SHA-256
  `9844c25f8c63bf829a95959f082b404c45dfbae0fd715972842762e0aef2d5bb`.
- Installed Excel ran invisible `CalculateFullRebuild` on a copy. Recalculated copy:
  931,099 bytes; SHA-256
  `F6E36E2D72E7F30431A936935778A4561D4BDC175A21933BFCFED839E8D7382B`.
- Live formulas and values Summary agreed exactly at 299 paired, 18/69 one-sided,
  221 differing, 78 identical, and 969 differing cells. All six Summary SELF-CHECK
  rows and all 30 Spot Check `Agree?` rows read `OK`.
- Both input files were SHA-256 rechecked after the run and matched the pre-run values
  above. The outputs are temporary evidence; their paths are deliberately not an oracle.

### v5 re-bless — 2026-07-17 (CMP-AUD-157/045-HL: the TSN normalizer v5 gate)

The HL vs-TSN loaders now REFUSE a pre-v5 TSN workbook (no "TSN Normalization"
marker sheet), so the frozen TSN input above can no longer feed the comparator —
by design, not by accident. The re-blessed TSN input was built from the live
library's `D01 Highway Log TSN.pdf` with the v5 module and the production
per-route writer:

| Role | Exact file | Length | SHA-256 |
|---|---|---:|---|
| TSN (v5) | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\inputs\tsn_highway_log_route 1 v5.xlsx` | 49,648 | `531F10887BC7EC714E7C993B05AC5A146478F614D964163715CCBFCD679E668D` |

- The v5 file's DATA ROWS are exactly the frozen input's rows (tuple-for-tuple;
  D01 route 001 has no suffixed section and no asterisk-leading description, so
  v5 moves nothing there). Workbook BYTES differ run-to-run (openpyxl docProps
  timestamps + the added marker/legend sheets); the SHA above binds the exact
  filed artifact, and the rows are the oracle.
- The real comparator (frozen TSMIS input vs the v5 TSN input, `mode="both"`)
  reproduced the locked result EXACTLY: typed complete/diff, 299 paired,
  18/69 one-sided, 221 differing rows, 78 identical, 969 differing cells,
  8,970 asserted — and every one of the 30 per-field counts is identical to
  the pre-Phase-3 baseline table. Both frozen inputs were SHA-256 rechecked
  after the run and unchanged.
- Harness: session 119c7c70 scratchpad `route1_canary_v5.py`.

### HL statewide v5 measured reference — 2026-07-17 (diagnostic, NOT a canary)

TSMIS = `All Reports 7.9\2026-07-09 ssor-prod\consolidated\highway_log_consolidated
2026-07-09 ssor-prod.xlsx` (51,884 rows / 252 routes; 284 rows on the ten suffixed
routes); TSN = the v5 normalized consolidated built from the 12 live-library raw
prints (60,083 rows / 273 routes / report date 09/15/25). The ~10-month source
vintage gap makes this a measured reference for future drift comparison — never a
match target. Typed result (values mode, `compare_highway_log.compare`):

- 48,351 paired / 3,533 TSMIS-only / 11,732 TSN-only; 39,623 differing rows
  (140,643 differing cells); 8,728 fully identical; 1,437,881 asserted cells;
  12,649 context (ditto) cells.
- **Every one of the 252 TSMIS routes pairs, including all ten suffixed routes**
  — under v4 the ten suffixed routes were structurally unpairable (their 284
  TSMIS rows read "Only in TSMIS" while TSN's 317 rows inflated the base
  routes). 21 TSN-only routes remain (rows tinted "entire route"), a data-vintage
  fact, honestly one-sided.
- Largest per-field counts (vintage drift): Cnty Odom 21,257 · Sig Chg. Date
  17,914 · MI 9,038 · Med TCB 8,535 · LB ST 6,856 — full table in the session
  transcript; the workbook was temporary evidence.
- Harnesses: scratchpad `statewide_hl_v5_compare.py`; the v5 build via the
  production `consolidate()` (12 documents, 380 per-route members = 369 base +
  the 11 suffixed sections; claims sidecar saved beside the scratch build).
- A read-only D2 token census over 8,736 nonblank TSMIS cells and 10,131 nonblank TSN
  cells found zero Boolean cells, control-whitespace/NBSP strings, Excel-error-token
  strings, literal difference markers, numeric values over 15 significant digits,
  digit strings over 15 digits, or signed/leading-decimal tokens. Lowercase appeared
  only in ten header labels on each side. Route-1 therefore protects ordinary parity
  but cannot decide the controversial D2 edge semantics; synthetic adversarial fixtures
  and affected statewide families remain required.

This is the E1 pre-change baseline. Any equality/formula/count change must rerun the
same bound inputs and source-manifest procedure, then explain every changed cell before
re-blessing.

## Bound Phase-3 gate — current-schema Intersection Detail

Canary ID: `CORE-ID-78-XLSX-TSN`  
Flavor: current 35-column TSMIS Excel versus normalized TSN Excel  
Stable recipe family: Intersection Detail vs TSN  
Binding state: `baseline-bound` — exact member manifest, corrected independent oracle,
current-code production formulas/values generation, schema-v3 payload, and installed-
Excel parity are immutable and independently rehashed

This replaces `CORE-STATEWIDE-619` as the Phase-3 statewide gate. The current
Intersection Detail comparator deliberately refuses the 6.19 TSMIS exports' pre-July
36-column layout, so the historical 6.19 result cannot exercise today's production
loader end to end. The 7.8 bundle uses the accepted 35-column layout and exercises the
shared equality and pairing engine on a real statewide detailed report.

Fixed root aliases and member selectors:

| Role | Root alias | Exact member selector | Required count |
|---|---|---|---:|
| TSMIS Excel (`tsmis_xlsx`) | `id78` = `C:\Users\Yunus\Downloads\TSMIS\ground-truth\Intersection Detail Bundle 7.8` | Direct ordinary-file children of `intersection_detail\` whose names match `^intersection_detail_route_[0-9]{3}[A-Z]?\.xlsx$` | 217 |
| TSN raw Excel (`tsn_xlsx`) | `all619` = `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 6.19` | Exact file `TSN\Intersection Detail\TSAR - INTERSECTION DETAIL_TSN.xlsx` | 1 |

The independently re-enumerated and content-hashed input manifest has exactly **218
members** and **26,384,760 source bytes**. Its versioned serialization is 31,085 bytes
and has SHA-256
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.
The audit found 217 matching TSMIS files, zero other direct files, no reparse members,
no duplicate route tokens, and exactly six suffixed tokens: `008U`, `010S`, `014U`,
`058U`, `178S`, and `210U`. Route 170 is absent; that agrees with the subsequently
confirmed current route universe rather than representing a missing file in only one
edition. The exact TSN member is 2,920,705 bytes with SHA-256
`5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2`.

The independent binding enumeration/content hash was repeated and remained identical.
The binding gate must continue to reject reparse points, non-ordinary files,
case-folded duplicate paths, unexpected direct children, owner-lock files,
selector/count drift, or any input change during the actual comparison run. This
read-only binding pass did not replace the required immediate-pre-run and post-run
content rechecks. Retain the full 218-record manifest with the actual canary run before
promoting this gate to `baseline-bound`; the digest alone binds the current selection
but is not a substitute for that durable per-member record.

Do not include `7.8.zip`, `_verification-scripts\`, the 217 PDF edition files, the TSN
statewide print, a retained consolidated workbook, or a retained normalized library in
this input manifest. Rebuild the TSMIS consolidation and TSN normalized library v3 into
an isolated destination from the selected raw members.

The authored 2026-07-08 production-path run records this provisional expected result:

- TSMIS consolidated: 16,459 rows;
- TSN normalized v3: 16,626 rows / 211 routes;
- 16,199 paired, 260 TSMIS-only, and 427 TSN-only;
- 21,675 differing cells.

Those numbers are now independently established by the corrected oracle below.
The retained `e2e_compare.py` imports production modules and historically counted
difference-marker text. Its companion studies report 16,200 and 16,206 pairings under
different study identities/projections, so neither number may silently replace the
production-path 16,199. Before promotion to `baseline-bound`, a new independent oracle
must implement the approved identity/equality contract without importing the comparison
engine and record the complete typed count vector, including differing rows, identical
paired rows, differing cells, and asserted cells. The TSN print-adapter study also
reported 21 duplicate keys; the binding run must establish which duplicate groups enter
the comparison pairing trace rather than treating that study count as automatic proof.
The approved D2/D3 semantics and the oracle exclusion boundary are recorded in
[`comparison-phase3-decision-gates.md`](comparison-phase3-decision-gates.md).

### Corrected independent oracle — promotable — 2026-07-12

The corrected standalone run completed in 67.242 seconds with the exact raw manifest
unchanged before/after. It established:

- 16,459 TSMIS and 16,626 TSN rows;
- 16,199 paired, 260 TSMIS-only, and 427 TSN-only;
- 16,053 differing rows and 21,675 differing cells;
- 518,368 asserting cells and zero context cells;
- 106 duplicate groups, all exact, none capped; and
- 259 retained route-provenance diagnostics.

Immutable evidence:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase3_oracle\CORE-ID-78-XLSX-TSN-2026-07-12`.

| Member | Records/bytes | SHA-256 |
|---|---:|---|
| result JSON | 2,934 bytes | `13b96442476b952eb2feeb920464eb4c13d9c0ad19fa6f61f0953a85155ed378` |
| differences JSONL | 21,675 / 13,818,255 bytes | `895466c657026995adf6810e193edf27643a5811fe803ddfa6c243172eac9666` |
| pairing trace JSONL | 16,106 / 4,532,544 bytes | `3a0f2b3f13b2ac69291d301783831fe9e61278b9e4b6d2ec364db6ff6117e922` |
| route provenance JSONL | 259 / 53,082 bytes | `a45a52211cdd8111e01ae3bd5a2b398a8b1713331460c92a9194fcf40a69087e` |

**2026-07-17 SITE EDITION — supersedes the 7.8 reference above (legacy kept for
backward compatibility).** The site shipped a new Intersection Detail build
(`ground-truth/Intersection Detail 2026-07-17/`, ssor-prod). Two changes, both
verified: (1) a **LABEL-ONLY** header correction — `P`→`PP`, `S`→`PS`, the INT
Type/INT Eff-Date labels realigned to sit over their own values, `Ctrl T`→`Ctrl T
Eff-Date`, `Xing P/S`→`Int PS` — with EVERY value in the SAME position (proven
cell-for-cell; the by-position loaders are unaffected). `compare_intersection_detail_tsn`
accepts BOTH editions via `exact_consolidated_header_ok(_TSMIS_HEADER,
_TSMIS_HEADER_LEGACY)` (034 gate preserved — junk/shift/wrong-edition still refused).
(2) a real **DATA refresh** — Int St Eff-Date updated from historical dates to the
bulk stamp `22-01-01` on 16,053 rows (aligning with TSN, which stores bulk stamps),
plus HG (682) and PM-suffix (307) edits, and the equate/junction rows normalized
(0 file≠Location rows, down from 259 — CMP-AUD-070 now moot as well as not-a-defect).
Same 217 routes / 16,459 rows. Observed vs-TSN canary on the NEW edition (same TSN
library; the same harness reproduces the 7.8 **21,675** exactly): **16,886 comparison
rows / 5,092 differing cells** (Int St Eff-Date 16,041→104). A full hash-bound
independent-oracle re-bless of the new edition is the follow-up; this observed count,
plus the label-only-header + real-data-refresh proof, is the current binding note.
Harness: session scratchpad `id_new_vs_old_canary.py` / `id_whatchanged.py`.

An independent first/corrected-pass reconciliation proved exactly 142 removed
artifacts and zero additions. Every removal was field `Intrte Postmile`; exactly two
rows became fully equal; four removals occurred inside duplicate groups; trace costs
fell by 142 total; and no assignment or source-pair changed. This is the required
explained re-bless for the Excel-binary64 lexical correction.

### Clean production and installed-Excel canary — accepted — 2026-07-12

The frozen current-code `r3` run completed in 762.424 seconds under
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase3_production\CORE-ID-78-XLSX-TSN-2026-07-12-r3`.
The exact raw manifest remained identical before comparison, after comparison, and
after Excel: 218 members / 26,384,760 bytes / SHA-256
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.

Production exactly reproduced the corrected independent oracle:

- 16,199 paired rows, 260 TSMIS-only, and 427 TSN-only;
- 16,053 differing rows and 21,675 differing cells;
- 518,368 asserted cells and zero context cells; and
- 106 duplicate traces, all exact, with zero capped groups.

Installed Excel ran invisible full rebuilds on evidence copies. Formula/value parity
covered 16,886 Comparison rows, one typed-state chunk, all 11 Summary self-checks, 56
shared numeric Summary labels, 32 Spot Check fields, 33,087 helper cells, and both
Report Views at exactly 43,350 physical difference rows (`2 × 21,675`).

Schema-v3 publication was complete and exact: generation
`7e992838-e21a-4da0-ac7b-684b71675c87`, one 43,728-byte decoded canonical outcome,
payload SHA-256 `8e47c4791dd0795181f9277f48472cca0a8173d7819ccc67382723df27d30627`,
binding SHA-256 `f8ad0cebecdfc682d390bce3f678c309f5c4421c615e648b9a3825349ea15f75`,
and one 4,702-byte chunk whose SHA-256 is
`844ed56683cde6c355fd518e5b34f0e0c791c8a416801877aa2079748d319cac`.
Both peer sidecars strict-read trusted/current after Excel; no sentinel or Office owner
lock remained. The permanent zero-byte publication lock is separately hashed as the
standard empty SHA-256.

| Evidence member | Bytes | SHA-256 |
|---|---:|---|
| production result JSON | 9,063 | `a54448f621beb27cea4e4b7a82af1b0a65580e84c5eac6df313242959a1111b2` |
| formulas workbook | 57,205,922 | `6289a114a1082bf5c7c2cdac066d9fda69098ac5866da229fd9f5a08090638df` |
| values workbook | 28,727,444 | `b06411048b0b4fab53a1a920d6ead02629818160f72a407cc607334fb02b9bfb` |
| Excel-recalculated formulas copy | 66,355,131 | `51a890b90281798b1e20ad7a21db277ce22c0c6e544451e68d51f74727ee15ca` |
| Excel-recalculated values copy | 35,152,890 | `cadb300f63bc284dbefdee14bd2645a7473619a0317edbeaa89b7007eb9f1139` |
| production pairing trace JSONL | 34,093 | `c891e6b2f2930ace40687bf67523bfea26af23a190949dedc53e4660d2ba61e9` |

The result binds 15 evidence artifacts and 11 production source hashes. A separate
post-run verifier rehashed every artifact/source, strict-read both peers, rechecked the
counts, and confirmed no sentinels/owner locks. The earlier unsuffixed run is retained
as evidence of the corrected uppercase-basename publication defect, and `r2` is an
intentionally aborted code-changing run; neither is an acceptance artifact.

### Independent first pass retained but not promotable — 2026-07-12

The standalone stdlib reader/adapter/oracle completed one fully pre/post-bound pass in
54.6 seconds. The 218-member manifest stayed byte-identical before and after at
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.
It read 16,459 TSMIS and 16,626 TSN rows and reported:

- 16,199 paired, 260 TSMIS-only, 427 TSN-only;
- 16,055 differing rows;
- 21,817 differing cells across 518,368 asserting cells; zero context cells;
- 106 duplicate groups, all assigned exactly with no cap; and
- 259 route-provenance diagnostics, retaining legitimate cross-route source rows
  without altering the authoritative reader.

Immutable first-pass evidence is retained under
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase3_oracle\CORE-ID-78-XLSX-TSN-2026-07-12-first-pass-decimal-lexical`.
Key hashes are:

| Member | Records/bytes | SHA-256 |
|---|---:|---|
| differences JSONL | 21,817 records / 13,910,698 bytes | `262c204bc54ac9dedee0cdab3f018e7470a3ad16c7e8805b2ac0d9a4bc9f98e1` |
| pairing trace JSONL | 16,106 records / 4,532,544 bytes | `2cd0fc30abd1c6e6bc9e1cbe9ce136b790a7aed3c86cd4731c945954a50f0f00` |
| route provenance JSONL | 259 records / 53,082 bytes | `a45a52211cdd8111e01ae3bd5a2b398a8b1713331460c92a9194fcf40a69087e` |

This pass exposed one oracle-reader seam rather than a source difference: 142 TSN
numeric XML lexicals such as `0.92100000000000004` are Excel binary64 cells whose
display/comparison spelling is `0.921`, exactly matching TSMIS text. All 142 independently
collapse to their TSMIS value under the corrected binary64-shortest-representation
rule; no exception was found. A naive subtraction would yield the provisional 21,675
cells and 16,053 differing rows, but four affected cells occur in duplicate groups, so
those totals were **not** promoted by arithmetic. The separately executed corrected
bound rerun above established them directly and preserved this first-pass directory
unchanged.

## Historical engine evidence — pre-July Intersection Detail

Historical ID: `CORE-STATEWIDE-619-HISTORICAL`  
Acceptance status: historical evidence only; **not a current Phase-3 gate**

The old re-proof used the 218 direct-child pre-July TSMIS workbooks under
`ground-truth\All Reports 6.19\TSMIS\Intersection Detail\` plus the one TSN workbook
named above: 219 raw members. It recorded 2,789,732 output cells identical across the
then-current before/after engine builds, with 163,310 differing cells and 677 one-sided
rows unchanged. Those facts remain useful evidence about the historical engine and
dataset, but current production code explicitly refuses that old 36-column TSMIS shape.
Reproducing it requires a pinned historical loader/code identity and must not be reported
as an end-to-end acceptance result for the current comparator.

## Historical-edition parity gate — Intersection Detail 7.8 PDF vs Excel

Canary ID: `ID-78-PDF-XLSX-L6`  
Owning batch: Stage 9 historical editions, with parser mutations remediated in Phase 4 L6  
Binding state: `provisional` — exact bounded selectors are known; member hashes and a
current typed baseline remain deferred until the historical-edition pass

Use the same 217 `id78\intersection_detail\*.xlsx` members selected above and the 217
direct ordinary-file children of `id78\intersection_detail_pdf\` matching
`^intersection_detail_route_[0-9]{3}[A-Z]?\.pdf$`. The read-only selection audit found
the two 217-token route sets identical. The parity input manifest is therefore exactly
**434 members**; it is deliberately separate from the Phase-3 Excel-vs-TSN manifest.

The retained 7.8 authored raw parity census records 16,459/16,459 rows and 576,065 cells, with 278
raw Description whitespace-collapse mismatches and no non-whitespace differences. The
product-level provisional expectation after `_xl_trim` is 16,459 paired, 0/0 one-sided,
and zero differing cells. This is version-pinned history, not current 7.9 truth: `ID-79`
has the exact nine-cell current delta recorded below. Bind and independently re-prove the
7.8 typed result in Stage 9; do not merge the two editions or their expectations.

## Phase-4 raw TSN normalization witness — source-bound, not promoted

Witness ID: `TSN-RAW-7-2026-07-12-R2`  
Source record:
[comparison-phase4-tsn-source-rebaseline.md](comparison-phase4-tsn-source-rebaseline.md)  
Binding state: exact pre-hardening source/output baseline; isolation/completion green;
blocked from comparison-canary promotion by the fresh post-contract production witness,
independent conservation, and later family-identity integration

The owner's raw-only library binds exactly 29 comparison-truth members / 52,670,235
bytes / canonical manifest
`c6c91c378c4010682df72f000212df26f9ed5caae89ba38bb6c6b226393a7c54`.
The separate 14-member evidence-print manifest is
`0f2f1edbb7c6eed04b203fdfd4e8941332f55501fae48c6a3daac404f4c3c048`.
The production-path result is
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r2\result.json`,
SHA-256 `1e9e6e689589f5a30eb32899ed163abffc00e73889806a2a8775179df9fd4e25`.

The later r3/r4/r5/r6 directories are partial rejected audit attempts, not witnesses. r5
was stopped during Highway Log when the consumer/publication/runner lifecycle review
found new CMP-AUD-035 gaps; r6 was stopped on normalized-byte certificate inheritance
and post-ensure raw drift. No result record from either attempt was accepted.

| Dataset | Built rows/categories | Normalized output SHA-256 | Promotion state |
|---|---:|---|---|
| Highway Log v3 | 60,083 | `0547213f2a4c35878849c552acd543b7e525e8be6e851019d3c1461c8bf07398` | pre-hardening source build/isolation baseline; superseded for current-code normalization by r7 and for field conservation by the accepted Stage-6 proof below |
| Ramp Detail v3 | 15,410 | `84e148e3840f23f32d10222abfd0d881e3abb85c7f9154c5c6febb5f8fc0ff75` | source build/admission and independent conservation accepted; complete product identity integration remains Stage 11 |
| Ramp Summary v2 | 31 | `bd2df6b55fe8f158e7e4dd9cac196400263f919fead3d1de61aac33cd541c554` | source build and independent aggregate conservation accepted; printed provenance remains product-red |
| Intersection Summary v2 | 58 | `47beed6caf7cd132a37ae51dd1cc20ace838da711df302c63bf63085cdb6ba3a` | source build and independent aggregate conservation accepted; raw category fold/label/provenance remain product-red |
| Intersection Detail v3 | 16,626 | `985a57f1df22f11a75ad49aa7ab97dccce423e97347c4e26fe505f70d9f588c2` | source build, cross-format proof, and independent conservation accepted; full-PM product integration remains Stage 11 |
| Highway Sequence v2 | 69,758 | `19eaa3226f933e4e5f6cdef2c2d37b88f4a7f1cc42363c8a4c9147138ff47135` | pre-hardening source build baseline; superseded for current-code normalization by r7 and for field conservation by the accepted Stage-6 proof below |
| Highway Detail v2 | 60,083 | `cf4d24b7f1fba58579a2dcb6584b9593e1e47d543b7905e2514ec2be8535ab21` | source build, cross-format proof, and independent conservation accepted; TSMIS vendor shape remains provisional |

### Accepted current-code normalization witness — r7

Witness ID: `TSN-RAW-7-2026-07-12-R7`  
Binding state: `baseline-bound` for the accepted Stage-5 production normalization
lifecycle only; source conservation and family-comparison promotion remain later gates

The accepted result is
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r7\result.json`,
173,124 bytes, SHA-256
`b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa`.
Its schema-v2 record has `acceptance=complete`, 7/7 completed families, stable source
and code universes, and the exact expected generated-artifact universe. It binds the
same 29-member / 52,670,235-byte comparison-truth manifest
`c6c91c378c4010682df72f000212df26f9ed5caae89ba38bb6c6b226393a7c54`
and 14-member / 53,336,889-byte evidence manifest
`0f2f1edbb7c6eed04b203fdfd4e8941332f55501fae48c6a3daac404f4c3c048`.
The operative code manifest is 28 members / 867,593 bytes /
`aee75325c5268e097c0fc389148b65a8ad97564ae314751e90e51062628dbfa7`;
the exact 14-workbook/sidecar generated universe is 20,794,592 bytes /
`56fd098c268f14951ba5b860205ed5d9a40aad4aa809237726f5700fc951f3c4`.

| Dataset | Version | Rows/categories | Normalized output SHA-256 | Sidecar SHA-256 |
|---|---:|---:|---|---|
| Highway Log | 4 | 60,083 | `fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa` | `6a746ce16773724954391894cbfb61dfccdb30c6c763750644deed081c533b1e` |
| Ramp Detail | 3 | 15,410 | `c121a9ca1bed2fad00bfc4b08bfc68fa01cd46da436d6bffa699c5579bb4f5f1` | `980ccd48f0c15438547b32fbb31050329fd11c94a1f199156c3b3a664f82f5b0` |
| Ramp Summary | 2 | 31 | `15e5b9260b79618371d0378afa40f051a8912c7056c8fbf43cdbbde47b143356` | `e5b3b115c674d58b52711a3745d82f7b5cf80a4c3874de0c66a602f41f4bc2b4` |
| Intersection Summary | 2 | 58 | `94befb313416a356a6e9f0363ffae0d065bd03c15ea1fce5bd8e93e0bf59a210` | `aa32f80280182381127cce01af48010543312e67080738b7b0140785530e7a3c` |
| Intersection Detail | 3 | 16,626 | `d4609c3afb8663dd89e6e2e00103d41245a0213d7e4e08fb63e961bc4035b37b` | `9a62c3341d9c78dbab7c9eef01c23c714081499dd44cdeac85ef21b1f1c2a5b8` |
| Highway Sequence | 3 | 69,758 | `9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041` | `fea39608196cdc17dda2a2f585bf9faf1a569488f09c7c493a75d575893d79f0` |
| Highway Detail | 2 | 60,083 | `46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5` | `97a9ccff48d446eab5d4a16d4383bd7858025fd3022cf4a111cbbe0481175327` |

Every family records `status=ok`, `completion=complete`, zero skipped/failed inputs,
an exact builder certificate, coherent current status, a current canonical normalized
identity token, and immediate certified reuse with unchanged workbook and sidecar. An
independent read-only r2/r7 stream compared all seven workbooks: every sheet name, cell
type, and all 5,547,205 cell values were identical. The different XLSX package hashes are
therefore packaging/provenance changes, not normalized-fact changes.

This witness closes the Stage-5 normalized-generation lifecycle only. Visual evidence
still needs Stage-10 immutable capture and exact manifests for the live TSMIS and TSN PDF
read sets; that separate PDF provenance boundary is not a defect in this r7 witness and
does not reopen CMP-AUD-035.

No output is accepted merely because its row count matches its raw source. Promotion
requires independent field/key conservation, exact source-role provenance, and the
applicable source-date-aware Excel-to-PDF record/category/section mapping. The latter
also owns evidence location and layered Report View placement/counts.

### Accepted Phase-4 source-format proofs — not app comparison canaries

These reproduce the authoritative TSN XLSX rows against their evidence/summary prints
and pass the second-review classifier mutations. They do not yet prove production
normalization, the app Comparison sheet, or evidence images.

| Proof | Exact source-format result | Result binding |
|---|---|---|
| Highway Detail | 60,081 PDF records paired to 60,083 XLSX rows over 12 districts / 4,123 pages; exact two XLSX-only duplicate occurrences; 3,003,609 projected-exact cells + 127,455 narrow render equivalents; exact 443-item dated-delta allowlist; 0 PDF-only, parser residue, unsafe attribution, unresolved cells, or SEG_ORDER inversions | `highway_detail_tsn_pdf_oracle_final.json`, SHA-256 `540b1ce575be880f506ebc435acaabe253e238f4eba312a72a310129f4ecdc36`; script `34d7aceb7717d285b48d440e0e762564615be2f4de0fd0b4827fa568277fc45b`; allowlist digest `d101bc1263188dcb436a9218bad6774ab047368e819c205d1e53b9b812b56d8a` |
| Ramp Detail + Summary | 15,410 XLSX = 15,410 PDF; 15,404 extracted-content exact + 6 hash/geometry/font-bound visible clip equivalents; exact four-item `(cid:13)` contract; all 18 XLSX fields disposition-bound; 0 date deltas; 0 unresolved; every Summary category and total exact; PM_SFX 313 = L165/R148 | `ramp_cross_format_oracle-v3.json`, SHA-256 `47383b5d00ed4b72fa72ed711d165c0ec633d2d7c8f86edd695f4f0a2e886ed1`; script `c580336cb2aa5fceae51230fc037f712e8ab2908e68561aa4402728ed93ae8a5` |
| Intersection Detail + Summary | 16,626 XLSX = 16,626 two-line PDF; 598,536 assertions; 578,432 exact + 20,103 directional/measured render equivalents + one exact allowlisted pull-time Description delta; 0 unresolved; 62 raw Summary rows → 58 normalized categories including Total; 116 explicit taxonomy-excluded detail rows conserved | `intersection-tsn-cross-format-oracle-v2.json`, SHA-256 `63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e`; script `ffc364ceb8b6cdbbfb3bff680cc0f3ed77e12c1867978c86122d221de7c78441` |

Both oracles enforce source sizes/hashes and fail-closed negative mutations. Ramp's first
date-delta classification was rejected and replaced with direct PDF content-stream clip
proof; its extraction-artifact and field-disposition gaps are closed. Intersection's
date flags are directional and its Description rule is the exact measured 32-character
boundary. It permits only the exact VEN/Route 001/blank-prefix/PM 23.907
Description pair when all other 35 fields and the source timing contract remain clean;
any second change revokes the authorization. Highway Detail likewise binds exact source
hashes, content-aware duplicate occurrence assignment, five narrow print projections,
and the complete 443-item allowlist; any change fails closed.

### Accepted Stage-6 raw-to-normalized conservation proofs

These consume the exact raw members and accepted `raw-2026-07-12-r7` normalized
artifacts. `audit=true` means the source-bound audit mechanism is complete; `full=false`
retains documented product loss and is not a provisional pass.

| Family | Result / detached acceptance | Exact outcome |
|---|---|---|
| Ramp Detail | Corrected `phase6_ramp_detail_conservation_r7_reissued.json`, 64,727 bytes, SHA-256 `3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd`; acceptance 5,941 bytes, SHA-256 `2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb` | 15,410/15,410 rows; 14/14 invariants and 6/6 mutations; audit true, projection/full false; exact 15 Description losses (9 same-route, 6 different-route), PM suffix, and effective fields remain product-red; two full replays byte-identical. |
| Intersection Detail | `phase6_intersection_detail_conservation_r7_accepted.json`, 453,532 bytes, SHA-256 `4d507661835cdd9e9267f05f7700777ba97b8a3948797ac3e436be8db8d21b88`; acceptance 3,353 bytes, SHA-256 `7077358da9ca016c12a4d1bc2cf8e09c95b20ac588272febf9b307f5856c7b43` | 16,626/16,626 rows; 24 invariants/25 mutations; exact canonical collision census; audit/projection true, full false for three omitted source fields |
| Highway Detail | `highway_detail_conservation_r7.json`, 122,006 bytes, SHA-256 `283315b30605461e748246444ea523542f61b0a205cd70131c73e1f6b77fb20b`; acceptance 3,802 bytes, SHA-256 `d26dee5d11517478312cde6361c4567c30a4f8d534d822539bb36388c170cf03` | 60,083/60,083 rows; 23 invariants/22 mutations; zero unexplained residue; audit true, projection/full false for evidence/date omissions and exact one-cell Length defect |
| Ramp Summary | `ramp_summary_conservation_r7.json`, 384,147 bytes, SHA-256 `38b500489c8a310529c4c7b76bea3fe7461374d6c786b992caaa458e0ef65421`; acceptance 128,177 bytes, SHA-256 `55c43d501960d3ca3702e5eac1202f96ac6c9b3e1df2eb915b19c593669bf74c` | exact three-page PDF; 30 categories+Total; every axis totals 15,410; 18 invariants/13 mutations; audit/projection true, full false only for printed provenance loss |
| Intersection Summary | `intersection_summary_conservation_r7.json`, 245,040 bytes, SHA-256 `f3a0aa0dfb15cf2ca911ec98721c8dcc0d5d9b25c0ce3cc89184d2959aaf64de`; acceptance 44,337 bytes, SHA-256 `cdf63defdb62d2066a2cafb7229d0c1539a0c6d90f80ea1b96c07c77f609b703` | exact three-page PDF; 62 source rows→58 typed category ledgers including Total; 19 invariants/17 mutations; audit/projection true, full false for raw fold/label/provenance findings |
| Highway Sequence | `highway_sequence_conservation_r7.json`, 1,276,684 bytes, SHA-256 `bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2`; acceptance 5,934 bytes, SHA-256 `71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2` | exact 12-PDF/1,540-page/69,804-source-record census→69,758 rows; 22 invariants/14 mutations/47 modules; zero unexplained residue; audit true, projection/full false for CMP-AUD-155/156/158/159 |
| Highway Log | `highway_log_conservation_r1.json`, 10,879,397 bytes, SHA-256 `f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4`; acceptance 6,502 bytes, SHA-256 `012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61` | exact 12-PDF/2,121-page/60,083-row/13,549-total census; 34 invariants/53 mutations/47 modules; exact projection and zero unexplained residue; audit true, full false for CMP-AUD-045/157 product loss |

All seven families now have independently second-reviewed Stage-6 acceptance. Highway
Log's fresh 822-second and 823-second full-corpus replays produced byte-identical result
and acceptance files. Every product-red omission/delta remains open and is not converted
into an exception by these audit results.

### Selected Stage-8–10 TSMIS both-format corpus

Primary root: `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9\`.

- `All Reports 7.9.zip`: 202,739,676 bytes, SHA-256
  `93aea5b9e7180915615c9e75d934a759bbe51465086b54c9a0a1c0b157f7bc27`.
  Its 2,986 members include 11 generated consolidated/sidecar artifacts; those are
  excluded. Extracted per-route raw members are the audit inputs; the archive is their
  immutable provenance container.
- `ramp_summary_excel.zip`: 592,912 bytes, SHA-256
  `e1bf10e6ca32a77a144cfae320f9ee7fbbcb2177188dbe55698891dd45ee9b3d`.
  This is the later same-day Ramp Summary Excel supplement.

| Family | Source/env | Excel members / bytes | PDF members / bytes | Current selection fact |
|---|---|---:|---:|---|
| Ramp Summary | SSOR-prod | 126 / 2,450,040 | 126 / 10,521,961 | PDF base plus Excel sibling; supplement is later than the PDF batch |
| Ramp Detail | SSOR-prod | 126 / 7,858,480 | 126 / 12,792,211 | designated GOLD same-day pair |
| Highway Sequence | SSOR-prod | 252 / 24,634,973 | 252 / 39,236,260 | PDF batch precedes Excel batch |
| Highway Log | SSOR-prod | 252 / 59,441,628 | 252 / 36,545,107 | exact route-token parity |
| Intersection Summary | ARS-prod | 217 / 5,953,364 | 217 / 21,518,480 | Excel base plus PDF sibling; SSOR Excel duplicates ARS Excel byte-for-byte |
| Intersection Detail | ARS-prod | 217 / 23,464,055 | 217 / 31,673,183 | same-site-build fast-mode sequential pair |
| Highway Detail | ARS-prod | 252 / 65,195,848 | 252 / 50,624,128 | same-site-build pair; TSMIS schema remains vendor-provisional |

Every selected family has exact Excel/PDF route-token coverage, including S/U suffixes.
These are dated bundle-level pairs, not proof of per-route single-query coalescing. The
217-route Intersection Summary/Detail universe consistently omits Route 170 relative to
the 6.19 218-route edition across every available 7.9 form.

Older editions are retained with exact version roles, not mixed into the current truth:

- `All Reports 6.19`: historical base; no Highway Detail, pre-July Intersection Detail;
- Highway Detail dev 7.7: 252+252 cross-build/vendor-provisional drift witness;
- Highway Sequence 7.8: 252 XLSX, four routes byte-different from 7.9;
- Intersection Detail 7.8: 217+217, eight XLSX routes byte-different from 7.9;
- copied `HSL PDF + IS Bundle 7.9`: duplicate evidence, not an independent edition;
- six-environment and 6.15 scratch/subset sets: targeted drift evidence only.

Generated `consolidated/`, `.outcome.json`, bundle-root normalized workbooks,
`comparison-outputs/`, `evidence-bundles/`, `report-samples/`, `_scratch/`, and verification
outputs are never raw truth. No fresh TSMIS Excel/PDF sibling is missing. New exports are
needed only for literal same-query coalescing or complete SSOR/ARS/dev/test parity. Raw
TSN Excel siblings are not present for Ramp Summary, Highway Sequence, Highway Log, or
Intersection Summary; app-built normalized XLSX must not be relabelled as those sources.

### Accepted Stage-8 base comparison oracle — Ramp Summary

State: **accepted oracle/value projection; current product comparison semantics red**.

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\ramp_summary_base_r1.json`  
Result bytes / SHA-256: 491,099 /
`f05bad6e7442fd3f345f86c8b61f334f44bd6cbaced1341d4e24b277c2ef3ba2`  
Detached acceptance:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\ramp_summary_base_r1.json.acceptance.json`  
Acceptance bytes / SHA-256: 11,568 /
`46ff47b2c73675b321ac88fc872767ef8446d7d09c3a3d1a36923a23fee782ca`

Oracle / witness / gate identities:

- `build/phase8_ramp_summary_comparison.py`: 104,131 bytes, SHA-256
  `301611ce2688cb12cd90f5c5441d9ac341205872196a9f3a4a5f746077e7a2ed`;
- `build/phase8_ramp_summary_product_witness.py`: 6,589 bytes, SHA-256
  `bf2b4c769b4ac53033cc8896bfaac8278fe5c8ad5469f16e99e7c891793a0ce8`;
- `build/check_phase8_ramp_summary_comparison.py`: 12,785 bytes, SHA-256
  `08f343e290bc78deff93e7c70d7b2ac3cf6f374a05135a364f36a6deb6b0f595`.

Canonical TSMIS member manifests use the explicit UTF-8 serialization
`name<TAB>bytes<TAB>lowercase-member-sha256<LF>`:

| Role | Members / bytes | Canonical manifest SHA-256 |
|---|---:|---|
| Summary PDF base | 126 / 10,521,961 | `81108f5bb35ecffa292fd206724c2ec87001c1d0c32db33f8281a78b24f8c444` |
| Summary Excel sibling | 126 / 2,450,040 | `d74c19b589108e0dcbd21389f63c1adcd4d9373c4959c168a1e4ba8446c6281e` |
| Detail Excel supporting truth | 126 / 7,858,480 | `7c10fbf6b996a8a9fbb0e8c8c30d8d2dac0a80c0befb7c12bdeb0151f7ff7489` |
| Detail PDF supporting truth | 126 / 12,792,211 | `6e8a2b669148738344a0173cca52a16884b972cba4679ba6446547ce8286c4c9` |

All 504 local audit members were compared directly to the authoritative Downloads
trees after the interrupted run: zero member differences. The result also retains the
four earlier inventory digests whose serialization was undocumented; they are provenance
only and are not substituted for the canonical hashes above.

Exact source/comparison facts:

- 126 unique ordered routes in all four TSMIS forms, including `005S`, `010S`, `015S`,
  and `880S`;
- Summary PDF↔Excel: 3,780/3,780 typed values identical, digest
  `57514b890de9d1e49ed605c0fa095fade6a264f821e8177ac19aa852d87c2f1b`;
- Summary total 15,216 on both formats; Detail Excel/PDF each contain 15,216 rows and
  match every route total; 626 Detail PDF pages;
- the nine-route unprinted Ramp-Type residual is exactly 22 same-pull Detail records,
  P=2 and V=20, with zero residue;
- intended TSMIS-vs-TSN truth: 29 shared, 0 TSMIS-only, 2 TSN-only (P/V), 5 identical
  shared, 24 differing shared; ordered `TSMIS - TSN` digest
  `a3cbf7528aa66989f08a0d28efd8ba0e4588b8e3675ef108b0b791fdd35a2d63`;
- TSMIS/TSN totals 15,216/15,410; TSN minus TSMIS = 194.

Production's source-backed projection is exact, including all 3,780 consolidation
values and familiar-sheet numbers. Its current generic comparison is not semantically
accepted: it emits 31 shared + one TSMIS-only row, 26 differing + five identical,
zero-fills P/V on TSMIS, and injects the 59-point no-linework display metric into the
verdict. The exact three semantic gaps are bound to CMP-AUD-024/025; route/completeness
and provenance requirements remain under CMP-AUD-019/020/071/076/146.

The oracle ran production twice per execution using stable XLSX member and workbook-
semantic digests that exclude only timestamp-bearing `docProps/core.xml`; every other
ZIP member is asserted. Two complete source-bound executions then produced byte-identical
result and acceptance files. Terminal state is
`source_truth_exact=true`, `production_value_projection_exact=true`,
`stage8_base_oracle_complete=true`, `production_comparison_semantics_exact=false`, and
`comparison_end_to_end_perfect=false`.

### Accepted Stage-8 base comparison oracle — Intersection Summary

State: **accepted source oracle, value projection, and current comparison semantics;
normalized raw-source conservation and end-to-end perfection remain product-red**.

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\intersection_summary_base_r1.json`  
Result bytes / SHA-256: 1,124,870 /
`7e4acebabd2efc8ac2d765c78493048117eb0bd2431cd01d032c0272cd9ea7bd`  
Detached acceptance:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\intersection_summary_base_r1.json.acceptance.json`  
Acceptance bytes / SHA-256: 11,322 /
`d1758926e6fa7672bbce75e02b51686326ea192275393918667386632fedab31`

The two authoritative TSMIS roots are the current `2026-07-09 ars-prod` pull under
`C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9`: Excel
`intersection_summary` and PDF `intersection_summary_pdf`. Canonical manifests use
`name<TAB>bytes<TAB>lowercase-member-sha256<LF>` sorted by name:

| Role | Members / bytes | Canonical manifest SHA-256 |
|---|---:|---|
| Intersection Summary Excel base | 217 / 5,953,364 | `e3e235e0f48645750b65b9df966a963c5a9bb856798d23661c95ab44056956e5` |
| Intersection Summary PDF sibling | 217 / 21,518,480 | `63f06f7b7f483a1fcd85be60278e7eebfbab51a79a1de955e9d3eac5bb8c8c2a` |

Both trees have the exact same ordered 217-route universe, route-list LF digest
`0dcd88a8b8f8156a87c7cc7834972aa08b018f5c36f03fa469b5750236b01a8d`,
suffix set `008U/010S/014U/058U/178S/210U`, and no route 170. Every workbook is
parsed as the exact fixed 99-row, three-column layout; every PDF is independently parsed
by its two-page geometry and provenance contract. All 14,322 route/category values
(217 × 66 including Total) agree exactly, with zero differences and ordered typed digest
`9c012be4529d358181010dca4c89d0e0e4a759d9c066248feddf0f7149b2f33a`.
The independent statewide aggregate digest is
`0574e4b69729a00e8ce325bca8d515ad8fa1f472599dd13ebfda5503dd3dc7a6`.

Exact TSN/reference dependency bindings:

| Role | Bytes | SHA-256 |
|---|---:|---|
| Raw `Intersection Summary Statewide_TSN.pdf` | 12,326 | `c3ad85848764df1b6da53c0bba0f785b3c045e83675f5983555ef514688a7d46` |
| Accepted r7 normalized workbook | 6,323 | `94befb313416a356a6e9f0363ffae0d065bd03c15ea1fce5bd8e93e0bf59a210` |
| Stage-6 conservation result | 245,040 | `f3a0aa0dfb15cf2ca911ec98721c8dcc0d5d9b25c0ce3cc89184d2959aaf64de` |
| Stage-6 detached acceptance | 44,337 | `cdf63defdb62d2066a2cafb7229d0c1539a0c6d90f80ea1b96c07c77f609b703` |
| Accepted Intersection Detail XLSX↔PDF Summary cross-format oracle | 91,032 | `63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e` |
| `TSNR - Intersection Control and Geometry Type_4.25.24_AT 1.xlsx` | 15,419 | `64140ca7ef38b1d06c2a8112b99d9f327b3812d6c399c1eb417b338dc59db23e` |

Independent comparison truth is **66 union rows, 58 shared, eight TSMIS-only, zero
TSN-only, 53 differing shared, and five identical shared**. TSMIS Total is **16,459**;
TSN Total is **16,626**; `TSMIS - TSN = -167`. The ordered typed comparison digest is
`60459ed21842e53460e10ddc60c66e1cdbab1bf716b76826a5f4128c8b8fc120`.
The eight structurally TSMIS-only rows remain absent—not zero—on TSN: Intersection Type
R/C/P/+, Control R/O/Q, and Left Channelization Y. The five equal shared rows are Highway
Group X, Lighting +, Control Z, Control +, and one lane.

The TSNR reference and the same-pull TSMIS Excel/PDF sources independently prove the
canonical mapping `F = Four-Way Flasher (Red on Mainline)` and `G = Red on All`. The raw
TSN Summary PDF erroneously prints “RED ON ALL” for both F and G. The comparison uses the
proven canonical F meaning, while CMP-AUD-145 remains red because normalization does not
retain the raw contradictory wording plus an explicit correction-provenance record.
Distinct raw J/K/L/M/N/P rows correctly project to shared Control S=2,648, but
CMP-AUD-144 remains red because the normalized artifact cannot reconstruct those six
source rows.

Production exactly reproduces every source-backed consolidated value, formulas/values
workbook twin, generic comparison status, one-sided blank, verdict, and familiar-sheet
number for this current source. It nevertheless is not end-to-end perfect: the exact
open product set is CMP-AUD-020/021/022/023/076/144/145/146/183/184, covering strict
typed count/partition/duplicate handling, route-universe validation, raw fold/correction
provenance, report metadata, and the familiar note's false zero-fill/Ramp-P/V wording.

Oracle / witness / gate identities:

- `build/phase8_intersection_summary_comparison.py`: 120,818 bytes, SHA-256
  `52935f6af8bc309cc7e67a84936f472a77cdb83f11c70405c58d0d23133a4674`;
- `build/phase8_intersection_summary_product_witness.py`: 12,908 bytes, SHA-256
  `6d88d1526aa48855128723f56d6f6ba438e3e089fe212bd5619990cff37d8a7d`;
- `build/check_phase8_intersection_summary_comparison.py`: 19,804 bytes, SHA-256
  `6148e4ebb786a69ebff9672bbf8943a353b5b42179e7c0526b32662c8b93d727`.

Each oracle execution ran production twice in isolation and asserted workbook semantics
plus all non-`core.xml` package members. Two complete executions then read the direct
authoritative Downloads sources and reproduced the result and acceptance byte-for-byte.
Detached revalidation confirms 12/12 source invariants, 24/24 audit invariants, current
source/code identities, exact result bytes/hash, `accepted=true`, and no rejection file.
Terminal state is `source_truth_exact=true`, `production_value_projection_exact=true`,
`production_comparison_semantics_exact=true`, `stage8_base_oracle_complete=true`,
`normalized_source_full_conservation=false`, and `comparison_end_to_end_perfect=false`.

### Accepted Stage-8 base comparison oracle — Ramp Detail (`RD-79`)

State: **accepted source oracle and exact TSMIS projection; current product value and
comparison semantics red**.

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase8_ramp_detail_comparison_r1.json`  
Result bytes / SHA-256: 1,703,996 /
`6cdf3ad5f5c1453df77515ca4cc30535f263bbe36eeaf2ab1e392771adbaf556`  
Detached acceptance: same path plus `.acceptance.json`  
Acceptance bytes / SHA-256: 13,473 /
`77b3af5f5273666296c6304f28eb69137b69f67779d95cd3ca34e4ab6d3bbd64`

The current TSMIS source is the `2026-07-09 ssor-prod` pull under `All Reports 7.9`.
Canonical tree manifests use the same sorted
`name<TAB>bytes<TAB>lowercase-member-sha256<LF>` serialization as the other accepted
Stage-8 oracles:

| Role | Members / bytes | Canonical manifest SHA-256 |
|---|---:|---|
| Ramp Detail Excel | 126 / 7,858,480 | `7c10fbf6b996a8a9fbb0e8c8c30d8d2dac0a80c0befb7c12bdeb0151f7ff7489` |
| Ramp Detail PDF | 126 / 12,792,211 | `6e8a2b669148738344a0173cca52a16884b972cba4679ba6446547ce8286c4c9` |

Exact TSN and accepted dependency bindings:

| Role | Bytes | SHA-256 |
|---|---:|---|
| Raw `TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx` | 1,590,431 | `3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856` |
| Raw `Ramp Detail Statewide_TSN.pdf` | 1,384,895 | `0d1e31054e8f866de3be924ba350a5bd77f9230d453e58d761dea079f4505a49` |
| Accepted r7 normalized workbook | 1,009,829 | `c121a9ca1bed2fad00bfc4b08bfc68fa01cd46da436d6bffa699c5579bb4f5f1` |
| r7 normalized sidecar | 910 | `980ccd48f0c15438547b32fbb31050329fd11c94a1f199156c3b3a664f82f5b0` |
| Corrected Stage-6 result | 64,727 | `3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd` |
| Stage-6 detached acceptance | 5,941 | `2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb` |
| Accepted TSN XLSX↔PDF oracle v3 | 72,950 | `47383b5d00ed4b72fa72ed711d165c0ec633d2d7c8f86edd695f4f0a2e886ed1` |

Independent source truth keys rows by
`(Route, County, norm_pm(PM))`; `PR` and `PM_SFX` remain separately asserted facts.
The raw TSN side has 15,410 unique D4 identities. TSMIS has 15,216 rows, 15,215 unique
identities, and one exact duplicate group. The four TSMIS-only occurrences are
`005/LA/25.218`, `050/SAC/15.715`, `050/SAC/15.823`, and the extra duplicate at
`101/LA/1.284`; TSN has 198 one-sided identities. Exact comparison truth is:

| Flavor | Paired | TSMIS / TSN only | Identical / differing rows | Differing cells | Per-field differences |
|---|---:|---:|---:|---:|---|
| TSMIS Excel vs raw TSN | 15,212 | 4 / 198 | 14,471 / 741 | 847 | District 1; Date 15; HG 364; Area 4 58; City 156; R/U 68; Description 185; PR 0 |
| TSMIS PDF vs raw TSN | 15,212 | 4 / 198 | 14,438 / 774 | 998 | District 1; Date 15; HG 364; Area 4 58; City 156; R/U 68; Description 181; On/Off 95; Ramp Type 60; PR 0 |
| TSMIS PDF vs Excel | 15,216 | 0 / 0 | 15,212 / 4 | 4 | Description 4 |

The PDF↔Excel differences are the four route-010/RIV rest-area rows at PM 71.863,
72.028, 72.200, and 72.355 where Excel contains a literal `_x000d_` escape/newline and
the PDF omits it. All other observed render differences are fully classified: 306
HTML-whitespace collapses, 59 PDF dashes for Excel blanks, and 59 printed
`NO RAMP LINEAR EVENT` values for Excel blanks. The 500-data-page TSN PDF contributes
15,410 records with zero parser residue; its cross-format mapping accounts for every
XLSX field and all source-date differences.

Raw TSN vs normalized r7 pairs all 15,410 rows. Every asserted field is exact except
exactly 15 Description cells where production deletes an authoritative leading numeric
prefix. The current product therefore produces the same wrong output from raw and
normalized TSN: Excel-vs-TSN has 750 differing rows / 861 cells (Description 200), and
PDF-vs-TSN has 783 differing rows / 1,012 cells (Description 196). Relative to source
truth this adds 15 false Description differences and hides the one real District
difference. At `005/SD/72.366`, TSMIS Excel/PDF says District 12 and TSN says District
11; production omits District and reports the row fully identical. Its Route+PM key is
also unsafe: 81 weak TSN keys span 163 county identities. These exact red paths are
CMP-AUD-045/133/135/185; audit acceptance does not bless them.

Oracle / witness / gate identities:

- `build/phase8_ramp_detail_comparison.py`: 130,247 bytes, SHA-256
  `02d0b142445a59514722259d9190dd436c612a2a921ffc3c2bb3608287e452f0`;
- `build/phase8_ramp_detail_product_witness.py`: 8,972 bytes, SHA-256
  `9bf55da666bc1183a68c9f77600649990ff9d4be82940b15cd873aa4f6b3330e`;
- `build/check_phase8_ramp_detail_comparison.py`: 14,327 bytes, SHA-256
  `417d48dbc4ec2c100fafe812604ec9e377d117ba113651db601351ce6e30f0a7`.

Each oracle run consolidates both TSMIS representations and executes five production
legs in `mode="both"`: Excel/PDF against raw and normalized TSN plus PDF↔Excel. Two
complete executions took the direct authoritative inputs and reproduced both accepted
artifacts byte-for-byte; the second took 818 seconds. Independent post-run checks found
36/36 permanent assertions green, exact code/source identities, no private-work
entries, and the protected Fable document unchanged. Terminal state is
`source_truth_exact=true`, `production_tsmis_projection_exact=true`,
`production_value_projection_exact=false`,
`production_comparison_semantics_exact=false`, `stage8_base_oracle_complete=true`, and
`comparison_end_to_end_perfect=false`.

### Accepted Stage-8 base comparison oracle — Intersection Detail (`ID-79`)

State: **accepted source oracle and exact overlapping production-cell projection;
current product source visibility and physical-identity semantics red**.

Canonical accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase8_intersection_detail_comparison_r1.json`  
Result bytes / SHA-256: 1,059,072 /
`7c7734aae212fbf9ad55de554cd2a0111549479b764ff3b91695fb524f21d86c`  
Detached acceptance: same path plus `.acceptance.json`  
Acceptance bytes / SHA-256: 2,063 /
`67a267b491ecd380a8156af6b5d216cb27d875ac20175e5fe964acc61a0bbb30`

The second full replay published
`phase8_intersection_detail_comparison_r2.json` with the exact same byte count and
SHA-256. Its 2,063-byte acceptance SHA-256 is
`737ceb082ecf0f18d9a21d44b29d1893e4e455e854798d5e9a46779493d659b8`.
The two acceptance JSON documents are semantically identical and differ only in their
bound `result` pathname; both say accepted and pass every post-write source, live-origin,
dependency, code, consolidation, comparison-workbook, and witness identity.

The current TSMIS source is the `2026-07-09 ars-prod` pull under `All Reports 7.9`:

| Role | Members / bytes | Canonical manifest SHA-256 |
|---|---:|---|
| Intersection Detail Excel | 217 / 23,464,055 | `885149005ab9a261ca83b686f68cfc3fc4fe550d8fd42d99252dcd36fb365bc9` |
| Intersection Detail PDF | 217 / 31,673,183 | `01e62eb195ab0bd5494cdb1b7a6a5ccbc35bd451bb5320a9bab0a045c58773c9` |

Exact TSN and accepted dependency bindings:

| Role | Bytes | SHA-256 |
|---|---:|---|
| Raw `TSAR - INTERSECTION DETAIL_TSN.xlsx` | 2,920,705 | `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2` |
| Raw `Intersection Detail Statewide_TSN.pdf` | 9,284,543 | `1230b955176a1a34223ce8f79eeeed1b46970031372acc510ffb78a45c2f1f46` |
| Accepted r7 normalized workbook | 2,084,691 | `d4609c3afb8663dd89e6e2e00103d41245a0213d7e4e08fb63e961bc4035b37b` |
| r7 normalized sidecar | 903 | `9a62c3341d9c78dbab7c9eef01c23c714081499dd44cdeac85ef21b1f1c2a5b8` |
| Accepted Stage-6 result | 453,532 | `4d507661835cdd9e9267f05f7700777ba97b8a3948797ac3e436be8db8d21b88` |
| Stage-6 detached acceptance | 3,353 | `7077358da9ca016c12a4d1bc2cf8e09c95b20ac588272febf9b307f5856c7b43` |
| Accepted TSN XLSX↔PDF oracle v2 | 91,032 | `63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e` |

Independent source truth keys rows by
`(base Route, County, complete PP, numeric Post Mile)`. The raw TSN side has 16,611
unique identities plus 15 exact duplicate groups / 30 duplicate occurrences. The weak
Route+numeric-PM shape has 78 cross-county keys / 156 county identities; even adding
complete PP leaves 71 cross-county keys / 142 identities. More importantly, six
within-county Route+numeric-PM groups contain distinct complete-PP values, so complete
PP is part of identity rather than merely a display claim. Exact source truth is:

| Flavor | Paired | TSMIS / TSN only | Identical / differing rows | Differing cells | Asserted cells |
|---|---:|---:|---:|---:|---:|
| TSMIS Excel vs raw TSN | 16,199 | 260 / 427 | 146 / 16,053 | 21,676 | 550,766 |
| TSMIS PDF vs raw TSN | 16,199 | 260 / 427 | 146 / 16,053 | 21,683 | 550,766 |
| TSMIS PDF vs Excel | 16,459 | 0 / 0 | 16,450 / 9 | 9 | 559,606 |
| Raw TSN vs normalized r7 | 16,626 | 0 / 0 | 16,626 / 0 | 0 | 565,284 |

The 217 TSMIS PDFs contribute 1,844 pages and all 16,459 expected records with zero
parser residue under independent per-document grids. The exact nine PDF↔Excel cells are
eight Description values whose Excel cells end in tab characters that PDF cannot render,
plus one HG disagreement at `108/TUO/<blank>/5.87`. At that row Excel says `U`; PDF,
raw TSN, and normalized TSN all say `D`, so the disagreement is classified as a current
TSMIS Excel export defect and remains visible. This replaces the stale shorthand that
the current PDF and Excel forms have zero non-whitespace differences.

The production witness rebuilt both TSMIS representations and executed five legs in
`mode="both"`: Excel/PDF against raw/normalized TSN plus PDF↔Excel. Independent workbook
inspection proved exact sheet universes, formula/value structures, source sheets,
very-hidden snapshots, paired-cell ledgers, one-sided inventories, and per-sheet formula
censuses on all ten workbooks. Production consolidation preserves every nonblank typed
cell and every explicit member Route/physical `S` value. Excel's only representation
change is exactly 125,152 explicit empty-string cells serialized as physical blanks;
PDF consolidation is raw-representation exact.

The raw product Report View has 16,886 logical records / 33,772 physical rows and maps
all 16,626 nonblank `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT` claims. The normalized
leg emits the same record universe but all three columns are blank. Both PDF-vs-TSN legs
omit Report View. Every product comparison still declares and uses Route+PM, omits County
and District from Comparison, and re-derives Route/Suffix instead of exposing the exact
consolidated claims. The current corpus happens to reproduce the expected overlapping
cell and one-sided counts, but the permanent county/complete-PP swap mutations prove
that this weak identity can mask real changes. These exact red paths remain
CMP-AUD-045/068/070/133; no duplicate finding was created.

Oracle / witness / gate identities:

- `build/phase8_intersection_detail_comparison.py`: 107,061 bytes, SHA-256
  `b4bf58eb55146b1a0ac18476c6c3137ea9f1e92ddc6c2f9d1f1c93a934df6d51`;
- `build/phase8_intersection_detail_product_witness.py`: 10,317 bytes, SHA-256
  `ecd935e11564310efc3c253adaebe45f9910f9b1c6a3d563ad855cc402df84f3`;
- `build/check_phase8_intersection_detail_comparison.py`: 12,326 bytes, SHA-256
  `c070c64708b7fcfc57cac16a5f4a6415049f6be1a9d1d4c13c67ae16f0928790`.

All 24 audit invariants and all 31 permanent gate assertions pass. Terminal state is
`source_truth_exact=true`, `production_tsmis_projection_exact=true`,
`production_overlapping_comparison_cells_exact=true`,
`production_value_projection_exact=false`,
`production_comparison_semantics_exact=false`, `stage8_base_oracle_complete=true`, and
`comparison_end_to_end_perfect=false`.

### Accepted Stage-8 base comparison oracle — Highway Detail (`HD-79`)

State: **accepted source oracle with complete snapshot-backed TSMIS identity; current
product parsing, identity, source conservation, and evidence semantics red**. The TSMIS
edition remains vendor-provisional and is version-pinned rather than generalized.

Canonical accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase8_highway_detail_comparison_r1.json`  
Result bytes / SHA-256: 3,384,044 /
`9d793fb166197701e20d8ac6bc8aa34bd64221a15507dff5bbe7416bc7095554`  
Replay-1 detached acceptance bytes / SHA-256: 3,805 /
`30b35ebc672a8cfaf57652464fc4617cd200063f17ac31e25342c00d27f4c508`

The second complete replay published `phase8_highway_detail_comparison_r2.json` with
the exact same bytes and SHA-256. Its 3,805-byte acceptance SHA-256 is
`9f8983a4af8e5a0394ae8f7b94d82ce7a8b6b59dd123791925a9a8ac71a85684`.
The two result files are byte-identical. The two acceptance objects are semantically
identical and differ only in the required bound `result` path.

Current and exact snapshot-owner source bindings:

| Role | Members / bytes | Canonical manifest or file SHA-256 |
|---|---:|---|
| Current TSMIS Excel | 252 / 65,195,848 | `ca8e8a9478d00ed5514eb4026cd4b54f1d2df373bcdfff18e04898f60e852848` |
| Current TSMIS PDF | 252 / 50,624,128 | `590aad859c46be2044cc116e3a563b7f3224a13fb63039e34d49569dfd994480` |
| Selected 7.7 owner Excel (`005`, `005S`) | 2 / 3,887,485 | `234b57d9e07c72f1355cb2abc5f91fd952d440172f054d25a81322bf7a284821` |
| Selected 7.7 owner PDF (`005`, `005S`) | 2 / 1,549,484 | `9ab6b7daca9eb26ade07305781d237739a17fb39da9b6718cc09e0b5c5cc14eb` |
| Raw TSN Highway Detail XLSX | 1 / 16,356,075 | `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1` |
| Accepted r7 normalized TSN workbook | 1 / 8,478,589 | `46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5` |
| Normalized TSN sidecar | 1 / 900 | `97a9ccff48d446eab5d4a16d4383bd7858025fd3022cf4a111cbbe0481175327` |
| TSN evidence PDF tree | 12 / 42,667,451 | `92e91831be1c399af1630a5f9937c2fa2770e203438ad28d51db1ef0df1c3a46` |
| Accepted Stage-6 result | 1 / 122,006 | `283315b30605461e748246444ea523542f61b0a205cd70131c73e1f6b77fb20b` |
| Stage-6 detached acceptance | 1 / 3,802 | `d26dee5d11517478312cde6361c4567c30a4f8d534d822539bb36388c170cf03` |
| Accepted TSN XLSX↔PDF oracle | 1 / 664,322 | `540b1ce575be880f506ebc435acaabe253e238f4eba312a72a310129f4ecdc36` |

The audit-owned TSMIS parser reconstructs all 51,273 Excel rows and 51,216 PDF rows,
including 4,065 printed DCR headers, with zero unclassified PDF groups. Every Excel row
has non-circular snapshot-backed District/County ownership: 48,143 exact current
companion signatures, three unique-owner current companion keys, 3,125 exact same-build
7.7 route-005 rows, and two current 005S composite-description owner attestations. The
005S rule attests owner only; it synthesizes no PDF row or other cells. The later
route-005 PDF stays a separate snapshot, with all eight changed DCR owners frozen in
ledger `45a306a0f2872883cc0c1410b759f5c185cd23d890c1af9cfc659a7ef397a747`.
The 51,273-row classification ledger is
`87f92d930dd33187502e60f1b6d7dbf8f52b2d532fc0b806efeeb87c54bfc49b`;
zero owners come from TSN-only evidence.

Exact source truth is:

| Flavor | Paired | TSMIS / TSN only | Differing rows | Differing cells | Asserted cells |
|---|---:|---:|---:|---:|---:|
| Snapshot-aware TSMIS Excel vs raw TSN | 48,647 | 2,626 / 11,436 | 48,494 | 205,809 | 1,751,292 |
| Snapshot-aware TSMIS Excel vs normalized TSN | 48,647 | 2,626 / 11,436 | 48,494 | 205,809 | 1,751,292 |
| Current TSMIS PDF vs raw TSN | 48,163 | 3,053 / 11,920 | 48,010 | 203,320 | 1,733,868 |
| Current TSMIS PDF vs normalized TSN | 48,163 | 3,053 / 11,920 | 48,010 | 203,320 | 1,733,868 |
| Raw TSN vs normalized TSN | 60,083 | 0 / 0 | 1 | 1 Length | 2,162,988 |

The complete production witness authenticates both consolidations and all five
formula/value comparison pairs, including exact workbooks, sidecars, compressed payloads,
one-sided inventories, paired-cell ledgers, duplicate assignments, hidden snapshots, and
sheet/formula censuses. This exact reproduction is intentionally not semantic approval.
CMP-AUD-042/045/054/068/076/133/138/142/186 remain product-red for PS loss, weak
Route+Post-Mile identity, PDF parse loss, missing PDF Report View, absent durable source
identity, omitted source claims, one Length conversion, omitted snapshot dates, and the
route-395 multi-baseline truncation.

Audit-code bindings:

- `build/phase8_highway_detail_comparison.py`: 188,928 bytes, SHA-256
  `6112975a1fd43b3c3d33ca846c8ce9eb6b82e14c1b1db6766dfd2060e86a9576`;
- `build/phase8_highway_detail_source_oracle.py`: 59,632 bytes, SHA-256
  `b4973bd43781194c2a78286240ba3bda297fe9165d9c58937d54fb56dbc1f67e`;
- `build/phase8_highway_detail_product_witness.py`: 17,212 bytes, SHA-256
  `caa985fff851dee0a60e72636eb97b4c226ce3f3b24e5d08d089445f99de5f52`;
- `build/check_phase8_highway_detail_comparison.py`: 32,527 bytes, SHA-256
  `bca5762f0935d5e576b73ea985b62734d85dd7396809f0f4ba91a7ddcd44d16f`.

All 34 terminal invariants and all 79 permanent assertions pass. Terminal state is
`source_truth_exact=true`, `production_overlapping_comparison_cells_exact=true`,
`production_tsmis_projection_exact=false`, `production_value_projection_exact=false`,
`production_comparison_semantics_exact=false`, `stage8_base_oracle_complete=true`, and
`comparison_end_to_end_perfect=false`.

### Active Stage-8 base comparison oracle — Highway Sequence (`HSL-79-current`)

Binding state: **input-bound / in progress; not accepted**  
Current source edition: July-9 `All Reports 7.9\2026-07-09 ssor-prod` same-run pair  
Authoritative TSN edition: clean 12-district PDF library plus accepted Stage-6 chain  
Historical fixtures kept separate: 7.8 Excel and byte-identical first/current 7.9 PDFs

Current immutable source census:

| Role | Members | Bytes | Bound manifest / file SHA-256 |
|---|---:|---:|---|
| current TSMIS Excel | 252 | 24,634,973 | `31a13ebc388951fdcadbba69d9188218af4548dd56d68c91e09f96bcb41765c8` |
| current TSMIS PDF | 252 | 39,236,260 | `072e538e5ebcbf015ec719565f003fb72027973a11d63c42f123802d8856dfa7` |
| historical 7.8 TSMIS Excel | 252 | 24,634,499 | `4bb040280bab17fd14283aa20178d189b4e499291eea1345adba0e0bb7f72c4f` |
| historical 7.9 TSMIS PDF | 252 | 39,236,260 | `072e538e5ebcbf015ec719565f003fb72027973a11d63c42f123802d8856dfa7` |
| authoritative raw TSN PDF | 12 | 3,866,949 | `91d63fc20e82c8368044a9ef00224cd4b9b55309af55109fd34e4dacba7e72a2` |
| accepted normalized TSN XLSX | 1 | 2,536,901 | `9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041` |

The immutable private capture contains 1,008 TSMIS members plus 12 TSN PDFs. Its stable
capture SHA is `e6fd69838aef7fca34fd1c5cdd8b79e5ddb1c72e229bcf1928f63934ac91eceb`;
the 145,434-byte capture manifest SHA is
`6f41566c350797f135916e0d5b9f0de434e000faa5882ae1309d866f87cc6534`.
The accepted Stage-6 result and acceptance SHAs are respectively
`bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2`
and `71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2`.

Current source truth already proved, but final replay is pending:

- exact independent census: 60,494 Excel / 60,493 PDF rows, 60,493 semantic
  PDF↔Excel pairs, zero PDF-only, and one Excel-only described row;
- four paired PDF Description omissions plus that Excel-only row: five unrepresented
  Description claims total; route 037 `003.809` is fixed in the current same-run pair;
- 1,410 paired rows / 3,721 same-source cells: Description 1,133, FT 1,129, HG 910,
  suffix 549; suffix comprises 272 two-row moves (544 cells) plus five PDF-only values;
- raw TSN has 69,804 records (68,806 data + 998 equates), including 46 pre-county
  equates; normalization emits 69,758 rows, blanks 565 pointer tokens, and changes one
  Description punctuation value;
- installed Excel proves four lowercase `_x000d_` cells decode to CRLF; product treats
  them as false Description differences;
- raw and normalized TSN each preserve 154 numeric-prefix Descriptions, while current
  product false-cleans 81 real differences by deleting authoritative TSN prefixes.

Direct-source checkpoint r2 is 98,943,666 bytes at SHA-256
`a8da9a24a50bf2b1ba58a8062566c1813a6518d9bede9d6fc2dec24d7fa657ce`;
its bound 112,009-byte script SHA is
`469c57d9b419b6bfbe6b0ee7a1e7171f896e3585af47cc392c00ebb2383d9dd2`.
It parses the exact captured bytes of all four 252-member TSMIS trees, reparses all 12
raw TSN PDFs, and streams the accepted normalized workbook. Complete raw shapes are
Excel 57,072 / 3,422 / 12,732 and PDF 57,505 / 2,988 / 12,299; the separately named
69,758-row keyable shapes end at 12,686 / 12,253. The 46-record unkeyed ledger SHA is
`bbd85ad3b3de2bf5312e6a2945270b4d1a521acc690de62dabe833a810f8aeab`.
All nine actual gate mutations are rejected and source residue is zero. The checkpoint
is deliberately `acceptance_eligible=false` and does not advance the 5/7 family count.
Independent review rehashed all 1,028 bound files and reconstructed every leg without
contradiction. That r2 checkpoint still exposes the CMP-AUD-224 hardening requirement:
current data has exactly 998 annotation-to-`E` and 998 `E`-to-annotation links with zero
orphan `E` rows, but r2 persists only the forward predicate. The final direct-source
audit-input twin below closes that predicate gap at its own builder layer; it does not
promote r2 or the Highway Sequence family.

Current product-source artifacts:

- product consolidations: Excel 2,424,212 bytes / SHA
  `cf5905332db3d3eb5a49a87d603f6e36f209cad9a84173b381dace6600168b20`;
  PDF 2,371,547 bytes / SHA
  `070afe51ea3bf84c9704d0a36a02702b65189941badab6374b03461db8ef6ccc`;
  both are cell-for-cell exact against the independent source;
- exact product-source parity artifact: 1,739 bytes / SHA
  `011b5dc5d017b95f16125dc9d991aa030d96da923d852b65e9ffa1c933093f9d`;
- clean per-leg comparison result SHAs: Excel→TSN
  `b1cf6f791c18917dfb51b3f9f2d8331075091992ce3d3c3415032108ee9bec83`,
  PDF→TSN `65d79577e9dbc7dfbce22d3d12fa4b8a670edb78b439b56b2802afeaa077a59a`,
  PDF→Excel `972ea8466903a27d2cc609769d6fead11aceb5e2dd8d1a4e653cc0b92309f581`;
- independent six-workbook parity: 42,381 bytes / SHA
  `bb7c8550724b71e657781f86579e25b2f70c96bf8bf3380d049f70118f98961f`,
  status `pass_with_expected_product_defect`. It authenticates product PDF→Excel
  59,946 / 547 / 548 while rejecting that as source truth against 60,493 / 0 / 1;
- replay-stable Description-normalization probe: 174,929 bytes / SHA
  `202fcb82b6ba62d15fcd273b19f4f35de672d06da39fd710982ba65350e8bdd1`.
- exact-byte four-leg residual classifier: 2,475,505 bytes / SHA
  `ebe0f9efb6025525024d7183211e52f5cf4a10fba1dc9bfcbe02513ce38cb45b`,
  two byte-identical runs. Its four persisted pair maps, cell counts, and aggregate
  projection-plus-assignment arithmetic reproduce exactly. On fixed source pairs each leg has
  81 CMP-AUD-204 false-cleans plus 15 false-positive Description states; the product
  projection also mutates 90 cross-route TSMIS prefixes per form (plus four Excel
  CMP-AUD-197 CRLF rows). CMP-AUD-220 separately binds asserted-only assignment changes
  in 445/448 Excel and 357/360 PDF duplicate groups across raw/normalized TSN.
  Independent review found that its assignment zero-unexplained flag is tautological
  (CMP-AUD-221), its link guard dereferences before testing (CMP-AUD-222), and unrestricted
  output can alias/replace a frozen input after the final guard (CMP-AUD-223). This is
  explicitly cache-backed non-acceptance evidence, not a promoted canary; its exact
  arithmetic remains useful, but its original all-residuals-classified claim is
  superseded by the hardened result below.
- hardened four-leg residual classifier: 3,509,121 bytes / SHA-256
  `f6fa06569b28cdba66d059e6e9c9f40b4464149754a2561075b02c6c0307c8cc`,
  reproduced byte-for-byte in independent r3/r4 full runs. The 95,630-byte checker SHA
  is `ca4c458b5e80faead676222ca8cada74090edaa8fb332a4a478f2173b7022cec`.
  Every authentic changed group has an executable source/product optimum proof
  (445/448 Excel and 357/360 PDF); an arbitrary 3-by-3 swap yields one terminal
  unexplained record. Real Windows file/directory symlink, hardlink, lexical-output,
  and bound-input-output probes reject. CMP-AUD-221/222/223 are remediated in the
  classifier. It remains cache-backed non-acceptance evidence until direct-source
  acceptance reproduces the same contracts.
- development raw-TSN twin: 2,541,734-byte XLSX / SHA
  `d594e2441b81c4d4d81c11aa5bbf01418bcd2dcc0bedf3ee9a6221a66cb03fa1`,
  23,610,997-byte provenance SHA
  `f27c7724f9acc8988bfd65c896e8278853b70690ed36d0317fabf6c5af8920f2`,
  terminal result SHA
  `51a0cfb70611442fc5b7ca4bb1acbb2779446b7d5400d10590d31c798629d1bc`;
  it is exact for all 69,804 cache-bound records but is not acceptance source truth;
- final direct-source raw-TSN audit-input twin: the 57,219-byte builder
  `build/build_phase8_highway_sequence_raw_tsn_direct_twin.py` has SHA-256
  `86d271619f4e446590fe6edaa40e9e85d74da2ca9623f9a5bfcf7877c7101ea5`.
  The promotable input-fixture roots are
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_highway_sequence_raw_tsn_direct_twin_r6`
  and
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_highway_sequence_raw_tsn_direct_twin_r7`.
  They contain the same exact four artifacts: workbook 2,422,010 bytes / SHA-256
  `68b28921c4ca8290810c92653b4a96077d6a28bdb7954447c287cf3e78d3f67d`,
  provenance 31,368,272 bytes / SHA-256
  `95c0229fc0c96eb2f1e8966c300c5916c0978a17f73c39cdf829f909a1ff441b`,
  manifest 388,864 bytes / SHA-256
  `97541aaa963d784dbf6537cf3e6f46d32fb161f012be0ecb3abda441708b1d91`,
  and result 5,183 bytes / SHA-256
  `d4c0a5759b0ca9731047b0f7d57fabedb228f7a61697f0c6af3cb4ef8fc4d134`.
  Their ordered 69,804-row digest is
  `5ef81b31622730e8f1369d1989cc92c717be7eb4ad8f29061b3750ff78f767fc`:
  68,806 data + 998 equates, all 46 blank-County equates and 565 pointer tokens retained.
  Both directions bind the same 998 equate/data-`E` pairs with zero orphan rows; a
  reverse-only extra-`E` mutation is rejected. Delayed in-memory builds, fixed
  `docProps/core.xml` created/modified times, canonical ZIP structure, a planted core-time
  mutation, pre-resolve lexical/reparse guards, a real multi-level directory-symlink
  control, output-root disjointness, and zero formulas/errors are all green. Direct
  provenance also matches the prior development twin over all 69,804 values, references,
  contexts, and routes while reading no development cache. r1-r5 remain diagnostic/stale:
  r1 retains volatile core metadata, r2/r3 predate CMP-AUD-227, and r4/r5 resolve before
  their component walk. Most importantly, `result.json` says
  `acceptance_eligible=false`, `stage8_family_accepted=false`, and
  `PASS_DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE`. This twin is only a promotable
  direct-source input fixture; the CMP-AUD-225 runner half and newly verified
  CMP-AUD-228 through 231 runner-gate defects remain open, as do product comparisons,
  Comparison/evidence verification, the permanent gate, detached decision, and final
  replay;
- development raw product results: Excel→raw result SHA
  `2691fe4a5d6d1ed757d788c16bed7226a7966db8c1950423daf194369e6ae58c`
  reports 57,072 / 3,422 / 12,732 with 5,516 cells; PDF→raw result SHA
  `31656c378240c30218054ae57972d5480f68aa37045140a2c9d6a3aa3e7b2b81`
  reports 57,505 / 2,988 / 12,299 with 4,929 cells. Their row shapes match the
  independent complete-raw universe. The independent 36,706-byte raw-output audit at
  SHA-256 `8b59cb5062be9e3345b68b7d7024436275dd5de8ee9cb0d20bb90a7d4b0e0abd`
  passes all 15 invariants: it authenticates the six inputs per leg, every raw provenance
  row, both formula/value twins, embedded source rows/cells, Comparison/one-sided/Routes
  sheets, pairing traces, sidecars/chunks, and exact artifact trees. Its status is
  `pass_with_product_defects` and `acceptance_artifact=false`; the cell semantics remain
  product-red and the cache-derived raw twin cannot replace the final direct-PDF replay.
- five-leg Summary/Spot semantic oracle: 35,937 bytes / SHA-256
  `331d4aba8321cb8e61080678f5b71357f3da249cdf02f5ad23b18ae01b9f7395`;
  checker 80,667 bytes / SHA-256
  `374ea7f8d4994a0e07b8dece903cb1ade5362bca014e0a5a85e11c8b7fcccb96`.
  It passes 13/13 invariants over all five legs and ten workbook twins, reconstructing
  every Comparison cell and exhaustive Summary/Spot maps from exact captured bytes.
  CMP-AUD-214 is present in all ten workbooks; CMP-AUD-218 wrong-pair and false-one-sided
  mutations each still return six `OK`s in every leg. Status remains
  `pass_with_expected_product_defects`, `acceptance_artifact=false`.

The 49,304,637-byte TSMIS row cache, 28,829,216-byte TSN row cache, 113,580,300-byte
comparison draft, 4,008,580-byte source-oracle draft, and Description-normalization
probe are explicitly development/non-acceptance accelerators. They may inform the final
gate but cannot replace reparsing the immutable sources. The direct-raw-PDF-built TSN
twin is now bound above as an input fixture only. Promotion still requires correction
and replay of the direct-source runner, product publications, permanent mutations,
evidence/flat-view coverage, terminal artifact-universe checks, detached acceptance,
and two byte-identical complete family replays.
`HSL-PDF-79` below remains the separately named historical cross-bundle canary.

**Product-loader verification (2026-07-16 — NOT family acceptance).** The Wave-4
Highway Sequence batch (CMP-AUD-045/155/156/158/159/199/204) rebuilt the normalized
TSN workbook at v4 from the 12 bound raw PDFs (`HSL Bundle 7.8\TSN\highway_sequence\
raw`, the 3,866,949-byte authoritative set) and verified against the same-run ssor-prod
7.9 consolidated pair:

- normalized workbook: **69,804 rows** (68,806 data + 998 equates; 46 blank-County
  annotations, all `EQUATES TO`), 283 `*P*` + 282 `-------->` pointer tokens verbatim,
  the KER 014 `018.365` join with no invented comma, 154 numeric-prefix Descriptions
  preserved, direction census {S-N 190, W-E 172, E-W 5, N-S 2}, one distinct policy
  text, identity claims OTM22025 / 15-SEP-25 / 15 SEP 2025 across all 12 documents;
- product leg SHAPES == `EXPECTED_CURRENT_LEGS` exactly: Excel-vs-TSN
  60,494 / 69,804 / **57,072 / 3,422 / 12,732**; PDF-vs-TSN 60,493 / 69,804 /
  **57,505 / 2,988 / 12,299**; PDF-vs-Excel **60,493 / 0 / 1** (CMP-AUD-199's
  suffix-free identity; PM Suffix 549 and HG 910 exact as compared cells);
- re-pairing the product-LOADED rows under the oracle's own assignment objective
  (all-field diffs, char distance, position) reproduces the oracle's complete
  per-field tables EXACTLY on all three legs (with the four proven-CRLF `_x000d_`
  Excel cells unescaped) — so the loader values/identities carry zero residual
  defects, and the live product's remaining deltas were precisely CMP-AUD-220
  (assignment objective; live counts asserted 5,582 / 4,995 / 3,725 vs the oracle's
  5,589 / 5,001 / 3,721+4) plus CMP-AUD-197 (the four `_x000d_` cells).

**Post-CMP-AUD-220 product counts (2026-07-16, same day, later — the live
current-canary numbers).** With the owner-approved assignment/verdict split and
the HSL `_v` OOXML decode live, the PRODUCT ENGINE itself lands on the Stage-8
oracle table EXACTLY on the same inputs — these are now the bound HSL vs-TSN
comparison canaries:

- Excel-vs-TSN: asserted **4,894 rows / 5,589 cells {Description 4,894,
  FT 695}**; all-field 23,691 / 30,005 {City 15,026, Desc 4,894, Distance
  6,972, FT 695, HG 2,418}; shape 60,494/69,804/57,072/3,422/12,732;
- PDF-vs-TSN: asserted **4,916 / 5,001 {Description 4,916, FT 85}**; all-field
  23,872 / 29,189 {City 15,140, Desc 4,916, Distance 7,056, FT 85, HG 1,992};
  shape 60,493/69,804/57,505/2,988/12,299;
- PDF-vs-Excel: **1,410 / 3,721 {Desc 1,133, FT 1,129, HG 910, PM Suffix
  549}**, 60,493/0/1 — unchanged;
- zero literal `_x000d_` survives the vs-TSN loader (the 197 HSL half).

Cross-family assignment re-bless bound to the same batch: RD (all 3 legs, the
one 101/LA/1.284 duplicate group) and ID (all 3 legs, 16/16/18 groups) pair
byte-identically under old and new objectives — every RD/ID canary above is
unchanged; HL Route-1 stays exactly **299 both / 18 / 69 / 221 / 969**; the
June `ground-truth/inputs` HL statewide diagnostic pair re-pairs 57/1,002
duplicate groups toward full-content identity (asserted cells in changed
groups 457→500; 96 TSMIS / 16 TSN one-sided membership moves) — that pair is
a diagnostic input, not a bound canary. **Highway Detail statewide was
re-measured 2026-07-16 (later the same day) and is EXACT under the post-220
objective**: the bound 7.7-bundle harness (`hd_full_verify.py`, re-run
unchanged but for the filed-bundle path) reproduces **48,644 both / 2,599
TSMIS-only / 11,439 TSN-only / 208,596 differing cells with RU Eff 48,211**
digit-for-digit — the objective change moved nothing statewide (RD/ID-class
behavior; consolidate `complete`, TSN normalize 60,083 rows / 273 routes,
both exact). The bundle's PDF↔Excel self-check leg reports 2,487 both /
5 cells on 3 rows with one-sided 2/5 against the pre-v0.26.0 README's 3/5 —
the v0.26.0 HD-PDF July-print parser fix legitimately changed that
secondary leg's parse; the bound statewide vs-TSN canary above is what this
re-measure blesses.

These are product-code verification facts for the Wave-4 batch; they do not advance
the Stage-8 family acceptance above (direct-source runner, permanent mutations,
evidence coverage, detached acceptance, and the two byte-identical replays remain
owner-gated).

**CMP-AUD-218 workbook-shape note (2026-07-16, later).** The comparison
workbook's Comparison sheet gained one hidden trailing literal column
(`__CMP_E2_KEY_V1_TOKEN`, both twins) and Spot Check gained the independent
key-token row match + Row-integrity line. NO count, status, or display
semantics moved: the same ssor-prod 7.9 HSL PDF-vs-Excel build returns the
bound 1,410 / 3,721 exactly, its token column is complete + injective over the
full 60,494-row union in both twins, the clean installed-Excel rebuild reads
all-OK (Row integrity OK, Summary SELF-CHECK OK), and a planted
consistently-relinked pair flips Row integrity to CHECK at statewide scale.
Pre-218 workbook BYTES are not comparable (one extra hidden column); every
bound COUNT canary in this file is unchanged.

**CMP-AUD-197 RD amendment (2026-07-16, later).** RD-79's **Excel-vs-TSN**
leg is amended: the four Cactus City Description diffs (route 010 @ 71.863 /
72.028 / 72.200 / 72.355) were the Excel export's OOXML-encoded CR
(`…_x000d_\n`) against a raw TSN extract that carries ZERO literal `_x000d_`
anywhere — export encoding, not data. With the load-boundary decode
(`compare_ramp_detail_tsn._v` / `_strip_desc_prefix`), the bound RD
Excel-vs-TSN canary is now **15,212 both / 4 / 198 · 737 differing rows /
843 cells {Area 4 58, City Code 156, Date of Record 15, Description 181,
District 1, HG 364, R/U 68}** (was 741 / 847 {Description 185}; every other
number identical). PDF-vs-TSN stays exactly **774 / 998** and PDF-vs-Excel
stays **15,216 fully identical** — both re-measured post-decode.

## Remaining canary queue

| Canary | Flavor / acceptance fact | Corpus source | State / blocker |
|---|---|---|---|
| `HD-77` | Historical full-edition compatibility/drift gate; its route-005 same-build pair is already bound for current Excel ownership, but the remaining 7.7 family must stay version-separated | `ground-truth\Hwy Detail Dev Bundle 7.7\` | `provisional` — Stage 9 historical-edition gate; current `HD-79` is accepted above and may not be blended with this vendor-provisional edition |
| `ID-78-PDF-XLSX-L6` | Historical-edition PDF↔Excel parity for the retained 7.8 pair; do not reuse the superseded zero-difference shorthand for current 7.9 | `ground-truth\Intersection Detail Bundle 7.8\` | `provisional` — Stage 9 historical-edition gate; current `ID-79` is accepted above, while the exact 7.8 434-member hashes and typed delta census remain to be bound |
| `HSL-78` | 57,071 paired, 3,422/12,687 one-sided, 5,521 differing cells; routes 242/10/21 | `ground-truth\HSL Bundle 7.8\` | `provisional` — exact consolidated/TSN member identities pending |
| `HSL-PDF-79` | PDF↔TSN 57,505 paired and 4,930 differing cells; PDF↔Excel 59,946 paired, 547/547 one-sided, 59,082 identical | `ground-truth\HSL PDF + IS Bundle 7.9\` plus the HSL 7.8 Excel/TSN sides | `provisional` — cross-bundle role manifest and hashes pending |
| `HL-PDF-TSN` | Historical pulls reported 46,755 paired / 175,048 cells and later 46,919 / 175,269 | exact pull not durably recorded in the old artifacts | `blocked` — select one current corpus pair and independently establish a new identity-bound baseline; neither historical count is an oracle |
| `HL-PDF-XLSX` | The 7.9 corpus has 252 Excel and 252 PDF exports | `ground-truth\All Reports 7.9\` | `provisional` — an approved identity-bound self-check count has not been recorded |
| `BASELINE-ALL12` | One real two-day run over all 12 Matrix rows | no complete accepted pair selected | `blocked` — synthetic fixtures do not satisfy this acceptance gate |

`CORE-ID-78-XLSX-TSN` is intentionally not repeated in the remaining queue: it is the
baseline-bound Phase-3 gate described above. `CORE-STATEWIDE-619-HISTORICAL` is intentionally
absent because historical-only evidence is not pending acceptance work. `IS-79` is also
absent because it was promoted to the accepted Stage-8 Intersection Summary oracle above;
`RD-79` is absent because it was promoted to the accepted Stage-8 Ramp Detail oracle
above. `ID-79` is absent for the same reason; `ID-78-PDF-XLSX-L6` remains only as a
version-pinned historical Stage-9 gate. `HD-79` is also accepted above; `HD-77` remains
only as a separately versioned historical/vendor-drift gate. The earlier provisional/
blocked counts are superseded, not retained as competing truth.

## Deterministic member-manifest procedure

Use this procedure for `CORE-ID-78-XLSX-TSN` and every later directory-backed canary;
do not substitute a recursive corpus crawl, timestamp-only fingerprint, newest-file
selection, retained derived workbook, or historical comparison output.

1. Record the canary ID and the fixed absolute root-alias map. Resolve every path and
   require it to remain within its declared root. Enumerate only the exact depth and
   selector recorded by that canary.
2. Before hashing, enforce the required count, strict filename grammar, unique route
   token where applicable, unique case-folded relative path, and ordinary-file/no-
   reparse-point policy. Reject unexpected direct children and Office owner-lock files;
   do not merely omit them and continue.
3. For each selected member, stream SHA-256 from a stable read handle. Compare the file
   size and race-detection metadata before and after that read and abort if they change.
   Metadata is only a mutation guard; it is never content identity.
4. Begin with the literal header `# tsmis-comparison-canary-manifest-v1`. Serialize each
   record beneath it with exactly these tab-separated fields: `role`, `root_alias`,
   forward-slash `relative_path`, decimal byte `length`, and lowercase hexadecimal
   `sha256`. Record each canary's exact role tokens; this gate uses `tsmis_xlsx` and
   `tsn_xlsx`. Reject tabs, CR, LF, or ambiguous path components in names. Sort the full
   serialized record lines ordinally; that is equivalent to tuple order here.
5. Encode the header and records as UTF-8 without BOM, with LF line endings and one
   terminal LF, then SHA-256 those exact bytes. Record the member count, byte length,
   digest, absolute root map, and the full manifest itself with the canary run.
6. Immediately before producer execution, repeat exact enumeration and hashing and
   require the same manifest digest. After all comparison/Excel/independent-oracle work,
   repeat it again. Any membership, length, or content-digest change aborts the run and
   prevents re-blessing; pre/post timestamps alone never satisfy CMP-AUD-098.
7. Record derived consolidations, normalized libraries, values/formulas workbooks,
   comparison metadata, and Excel-recalculated copies as output members with their own
   identities. They are not raw input-manifest members. Separately bind the production
   source manifest, independent-oracle source digest, and all parser/consolidator/
   normalizer versions used by the run.

## Per-run binding record

For every semantic batch, append a dated record containing:

1. canary ID and exact side roles;
2. canonical paths plus file SHA-256/length, or a sorted member manifest and its SHA-256;
3. app/code identity, comparator/parser/normalizer/consolidator versions, and dirty-patch
   identity if the run is not from a clean commit;
4. pre-run and post-run input digests (CMP-AUD-098 remains open);
5. independently recomputed expected counts without importing the comparison engine;
6. values output counts and digest;
7. formulas output after Excel `CalculateFullRebuild`, all self-checks, parity result,
   and digest; and
8. any changed cells with a source-identity and domain explanation before re-blessing.

## 2026-07-14 — Highway Sequence final Stage-8 base binding

Highway Sequence is accepted at the audit/base-oracle layer, not remediated product
perfection. The final direct runner is 199,740 bytes / SHA-256
`bcc952fb3469b0e790e72eb25e1397f4639ef78ef1427ae2ea626d22ca001e91`.
Its immutable direct-leg terminal bindings are:

- Excel-vs-raw: `result.json` 37,574 bytes / SHA-256
  `2d60f9c48b72bf109769118f193575ccb099d0f5fcb1cc1e216ff4a46301e7e5`;
  `completion.json` 11,198 bytes / SHA-256
  `6aee127601ae5caeffa85f4404f1a34c44097fa22d7214ddee87a94e15f784a0`;
  counts 57,072 paired / 3,422 TSMIS-only / 12,732 TSN-only / 4,822 differing
  rows / 5,516 differing cells.
- PDF-vs-raw: `result.json` 37,735 bytes / SHA-256
  `b2b66cdaef898453e32d4f7480746b43f44b7378a5f5ba0df9031442f6081c47`;
  `completion.json` 11,190 bytes / SHA-256
  `2a61f7f861f6c1ce4d0736cfd849b2f5ea2309a358edac78bfec6b40d57a32b9`;
  counts 57,505 paired / 2,988 TSMIS-only / 12,299 TSN-only / 4,845 differing
  rows / 4,929 differing cells.

Each root has exactly 10 ordinary singly linked files and no transient residue. The
139,453-byte final gate SHA-256 is
`b875437981626449810234922eeafe5f5aa5c716e893d22a5df5b7c65cf66a79`.
Two separate clean roots produced byte-identical 42,140-byte `result.json` files at
SHA-256 `f7f60e526b21935df8109e3772fc99b4cc3aded85e7294a6a83c7f19398d82fe`
and byte-identical 1,510-byte `acceptance.json` files at SHA-256
`7e2e9ce44c14e3f5a095fa410548ff1de71eaf5820a2c348ed9ed52e40ca1c6c`.
The acceptance preserves all 14 known Highway Sequence product/evidence findings as red,
sets Stage-8 family promotion and end-to-end perfection false inside each single replay,
and authorizes only this documented two-replay base-audit conclusion. No product code
was changed.

## 2026-07-14 — Highway Log final Stage-8 base binding

Highway Log closes the Stage-8 base-family audits at **7/7**. This is acceptance of the
source-bound projection/current-product audit handoff only—not product perfection,
full-physical source conservation, workbook-cell evidence, or end-to-end perfection.

Frozen source and dependency bindings:

| Role | Members / bytes | SHA-256 |
|---|---:|---|
| TSMIS Excel source manifest | 252 / 59,441,628 | `f9cafb2958842550b2eeefd2117b061db45d8a02ace51428d5c97b68f8e9155e` |
| TSMIS PDF source manifest | 252 / 36,545,107 | `26fec6f7fec944681c96d7970ae6ed5c2791f173379c1e74ce050f44484c9d15` |
| Product-source runner | 7,922 | `909dd5811680862bc50180375318bf210fb754081e167178198da3f4fa6306e3` |
| Product-source `result.json` | 239,655 | `4fc4009c5b3be05b0be3d90cab5823e8397d34d623543a6215a03a238c27b8a1` |
| Consolidated TSMIS Excel | 5,735,685 | `329ccf68caf0c476d9360cb69dd28c0ab78a588d0e9bd9c816d5b484444fd660` |
| Consolidated TSMIS PDF | 5,684,466 | `17c04bb7400eded5c7b372d4ca87728735f8481fd37394c592e7dd0180f0333d` |
| Accepted normalized TSN | 6,663,062 | `fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa` |
| TSN outcome sidecar | 2,521 | `6a746ce16773724954391894cbfb61dfccdb30c6c763750644deed081c533b1e` |
| Stage-6 conservation result | 10,879,397 | `f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4` |
| Stage-6 detached acceptance | 6,502 | `012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61` |

Independent oracle and product-leg bindings:

| Role | Bytes | SHA-256 |
|---|---:|---|
| Projection-oracle code | 42,121 | `5125cffceb913df8da6bf34470425fe48f58c9a2b764329b949f1a116a90f580` |
| Projection-oracle result | 34,203 | `3b778c089e2070f4da9bea82aa0584b8bc4c35840dd0273fef1b2cd9f8c6a121` |
| Product-leg runner | 24,232 | `1e801e91cb8e86de13843d5b4f9eca1eb13d85ef05bc0aea5a34981482dfd360` |
| Excel-vs-TSN r2 `result.json` | 21,821 | `028c9caeedd1a080150f0dc96739b4641190af6b564ca2d5d2ab7f7195adabab` |
| PDF-vs-TSN r2 `result.json` | 21,819 | `5df98a2233986a7665f6cdfe181c2e22e479d5d5985ae4c5aca763755cdb3227` |

The oracle and product legs agree exactly on every per-field count and all 989 duplicate
assignments in each leg:

| Leg | Paired | TSMIS-only | TSN-only | Identical | Differing rows | Differing cells | Asserted cells | Context cells |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Excel vs TSN | 48,094 | 3,790 | 11,989 | 8,628 | 39,466 | 140,333 | 1,430,451 | 12,369 |
| PDF vs TSN | 48,096 | 3,790 | 11,987 | 8,633 | 39,463 | 139,786 | 1,430,511 | 12,369 |

Each r2 product root contains exactly seven ordinary files with no transient residue.
The Excel universe is 351,360,881 bytes with canonical manifest SHA-256
`b84b83ddd936ade42b4106b302e506703b28f4845cd10c89ff20aac50fe6033d`;
the PDF universe is 356,198,281 bytes with canonical manifest SHA-256
`008ae161651f23db5ffca5dde18a339200a524c36a9be593345449269eaadf43`.

The earlier r1 product attempts are explicitly **nonaccepting**. Excel r1 stopped with
an incomplete transient publication and no terminal result. PDF r1 produced compact
canonical sidecars without a trailing LF, which the stale audit-runner byte check
rejected; it likewise produced no accepted leg result. Neither r1 root participates in
this binding. Both r2 legs were fresh, absent sibling roots and completed once without
deletion or retry.

Final-gate bindings:

- `build/phase8_highway_log_final_family_gate.py`: 33,702 bytes / SHA-256
  `c92a1c34c9460aeffa1fa2a3b4483c416ef8eef055a6742f0d198d330e82ad59`;
- two byte-identical 9,036-byte `result.json` files / SHA-256
  `7acf9986055750bbc49be0d4fa422329d06893f379da0cd6ded945936549860b`;
- two byte-identical 839-byte `acceptance.json` files / SHA-256
  `170d622d751e96e97c7f8420c0a60172e57a31838a3d1b3de090c76972dd62b6`.

Terminal state is `accepted_stage8_base_family_audit_only` with
`stage8_base_family_audit_complete=true`. The gate deliberately preserves
`stage8_family_accepted=false`, `product_comparison_perfect=false`,
`product_end_to_end_perfect=false`, `comparison_end_to_end_perfect=false`,
`full_physical_identity_perfect=false`, `evidence_end_to_end_exact=false`, and
`workbook_cell_evidence_end_to_end_exact=false`. Open findings are
CMP-AUD-045/047/048/049/050/066/067/157. The bounded source/oracle/leg/gate closeout
changed no product code; the frozen 321-file product-script manifest is 7,423,809 bytes
at SHA-256 `df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`.

## 2026-07-14 — Intersection Summary route-universe positive control (CMP-AUD-183)

Bound to the authoritative 217-file ars-prod tree
`Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ars-prod\intersection_summary\`
(the same corpus as the Stage-8 Intersection Summary oracle) versus the raw
`Downloads\TSMIS\tsn_library\intersection_summary\raw\Intersection Summary Statewide_TSN.pdf`:

- the production consolidator's persisted `route_census` is exactly **217 ordered
  routes, `001`–`905`**, with the suffixed identities
  `008U, 010S, 014U, 058U, 178S, 210U` and **route `170` absent** (the dated
  universe fact — 6.19 had 218);
- the production comparison census-verifies (familiar-sheet note
  `TSMIS route universe verified against the producer census: 217 routes (001–905).`)
  and reproduces the accepted Stage-8 oracle unchanged: 58 shared / 8 TSMIS-only /
  0 TSN-only, 5 identical / 53 differing, totals 16,459 / 16,626;
- the finding's two isolated mutations on a sidecar-coupled copy now REFUSE:
  route `905` deleted → "the aggregated routes do not match the producer's route
  census"; route `001` duplicated → "route(s) 001 appear on more than one row".

Re-run via the production modules (consolidate → `write_outcome(extra=result.
producer_extra)` → compare); the hermetic mutation battery lives in
`build/check_compare_intersection_summary_tsn.py::test_route_universe`.

## 2026-07-14 — Ramp Detail production re-bless against `RD-79` (CMP-AUD-045/135/185)

The D4-integrated production comparators (county-aware `PhysicalKey`, District
compared, TSN Descriptions preserved with oracle-contract edge trimming,
route-matched TSMIS prefix strip, `ramp_detail` library v4) reproduce the
accepted RD-79 oracle **exactly, all three legs and every per-field count**,
from the same bound inputs (the ssor-prod 7.9 Excel consolidated workbook, the
scratch-consolidated 126-route ramp_detail_pdf tree, and the raw
`TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx`):

| Flavor | Paired | TSMIS/TSN only | Identical / differing rows | Cells |
|---|---:|---:|---:|---:|
| Excel vs raw TSN | 15,212 | 4 / 198 | 14,471 / 741 | 847 |
| PDF vs raw TSN | 15,212 | 4 / 198 | 14,438 / 774 | 998 |
| PDF vs Excel | 15,216 | 0 / 0 | 15,212 / 4 | 4 |

Per-field: District 1 (the 005/SD/72.366 12-vs-11 disagreement now visible),
Date 15, HG 364, Area 4 58, City 156, R/U 68, PR 0; Description 185 (Excel) /
181 (PDF) / 4 (PDF↔Excel); On/Off 95 and Ramp Type 60 on the PDF leg. The two
route-126 trailing-tab rows compare equal per the oracle's declared edge-trim
reading contract; the four route-010 `_x000d_` rows stay honest differences.
The pre-fix production numbers (750/861 Excel, 783/1,012 PDF, Description
200/196, District omitted) are retired. Hermetic locks:
`check_compare_physical_identity` (RD contracts promoted to TESTS),
`check_compare_ramp_detail_tsn` (canonical-display keys + the two-county swap
+ v3-library refusal), `check_visual_evidence` (county-aware RD adapter).

## 2026-07-14 — Intersection Detail production re-bless against `ID-79` (CMP-AUD-045-ID)

The ID-79-integrated production comparators (county+PP-aware `PhysicalKey`,
District + County asserted compared fields, `intersection_detail` library v4)
reproduce the accepted ID-79 oracle **exactly, all three legs**, from the bound
inputs (both ars-prod 7.9 217-route trees scratch-consolidated + the raw
`TSAR - INTERSECTION DETAIL_TSN.xlsx`):

| Flavor | Paired | TSMIS/TSN only | Identical / differing | Cells | Asserted |
|---|---:|---:|---:|---:|---:|
| Excel vs raw TSN | 16,199 | 260 / 427 | 146 / 16,053 | 21,676 | 550,766 |
| PDF vs raw TSN | 16,199 | 260 / 427 | 146 / 16,053 | 21,683 | 550,766 |
| PDF vs Excel | 16,459 | 0 / 0 | 16,450 / 9 | 9 | 559,606 |

Pairing quality `exact` on every leg (TSN's 15 real duplicate groups ride the
Hungarian assignment). The 9 PDF↔Excel differences remain the 8 trailing-tab
Excel Descriptions (database data the PDF render drops) plus the REAL
`108/TUO/<blank>/5.87` HG defect (Excel `U` vs PDF+TSN `D`) — no edge-trimming
in this family. The pre-fix production shape (Route+PM keys, District/County
invisible, canary 21,675) is retired. Hermetic locks:
`check_compare_physical_identity` (ID contracts promoted, 8 green / 2
known-red), `check_compare_intersection_detail_tsn` (canonical displays, PP
identity probe, pre-v4 refusal), `check_visual_evidence` (county-aware ID
adapter, 34 FIELDS).

## 2026-07-17 — CMP-AUD-063 post-mile code vocabulary census (HSL-PDF + RD-PDF)

The unexpected-token → PARTIAL escalation must never false-fire on real data, so
it is bound to a read-only, serialized statewide census proving the current
corpora carry ONLY the accepted, versioned vocabulary (`PREFIX_SET =
frozenset("CDGHLMNRST")`; Highway Sequence equate `SUFFIX_SET = frozenset("E")`;
Ramp Detail has no suffix column; `PM_VOCAB_VERSION = 1`).

- **Bound corpus:** `ground-truth/All Reports 7.9/2026-07-09 ssor-prod/` —
  `highway_sequence_pdf/` (252 route PDFs) and `ramp_detail_pdf/` (126 route
  PDFs); the same 7.9 ssor-prod set the HSL Stage-8 / CMP-AUD-220 bindings use.
  ars-prod carries no PDF exports in this bundle.
- **Census result (via the production `parse_pdf`):**

| Report | PDFs | Rows | Prefix tokens seen | Suffix tokens | Unclassified / stray |
|---|---:|---:|---|---|---:|
| Highway Sequence (PDF) | 252 | 60,493 | C D G H L M N R S T | E (1,132) | 0 / 0 |
| Ramp Detail (PDF) | 126 | 15,216 | C L M R S T | (no column) | 0 / 0 |

  Every token ⊆ the accepted set, so both statewide consolidations STAY COMPLETE
  under the new gate (no false PARTIAL). Row counts are canary-exact (HSL 60,493,
  RD 15,216). If any future pull surfaces a token outside the set, it is a DATA
  question (disposition + a deliberate `PM_VOCAB_VERSION` bump), never a silent
  escalation. Census harness: this session's scratchpad
  `census_063_pm_tokens.py`; hermetic lock: `check_pm_code_vocabulary.py`.
