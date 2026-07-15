# Phase 4 TSN source re-baseline

Last updated: 2026-07-14  
State: raw members bound; r7 accepted as current-code Stage-5 witness; r2 retained as
pre-hardening semantic baseline; r3-r6 rejected; all three source-format oracles accepted;
Stage-6 independent conservation complete at 7/7; Stage-8 base audit complete at 7/7;
product perfection and end-to-end evidence remain red  
Governing charter: [comparison-perfection-project.md](archive/comparison-perfection-project.md)  
Finding/fixture owner: CMP-AUD-035 in
[comparison-phase4-red-fixture-index.md](comparison-phase4-red-fixture-index.md)

## Purpose

This record re-establishes every vs-TSN comparison from the owner's deliberately
raw-only library at `C:\Users\Yunus\Downloads\TSMIS\tsn_library`. It distinguishes
comparison truth from evidence-only prints and binds every admitted member before a
normalizer, comparator, or evidence generator is trusted.

No generated `consolidated/` member is an input. Historical normalized workbooks and
comparison outputs are not source truth.

Resumed-state recheck on 2026-07-12: `rg --files` enumerated 54 ordinary library files
across only the declared `raw/` and `pdf/` dataset roles plus README placeholders. There
were zero `consolidated/` paths and zero `tsn_*_normalized.xlsx` members. Generated r7
artifacts remain isolated under the audit-artifact root, never inside this source library.

## Canonical manifest algorithm

For each admitted ordinary member:

1. compute the lower-case SHA-256 of its bytes;
2. express its path relative to the TSN-library root with `/` separators;
3. sort members by case-folded relative path; and
4. hash the UTF-8 concatenation of one line per member:

```text
<relative_path>\t<byte_length>\t<member_sha256>\n
```

Manifest hashes from another audit are comparable only if they use this exact
serialization. Member hashes remain directly comparable regardless of manifest format.

| Role | Members | Bytes | Canonical manifest SHA-256 |
|---|---:|---:|---|
| Authoritative comparison truth (`raw/`) | 29 | 52,670,235 | `c6c91c378c4010682df72f000212df26f9ed5caae89ba38bb6c6b226393a7c54` |
| Evidence-only TSN prints (`pdf/`) | 14 | 53,336,889 | `0f2f1edbb7c6eed04b203fdfd4e8941332f55501fae48c6a3daac404f4c3c048` |
| Combined admitted corpus | 43 | 106,007,124 | `bc39460e9769344183f66af419a2559a9c2236c412704ef27c8efa5f63515b9f` |

These values were independently recomputed from the supplied files after two parallel
inventories. A prior interim total of 118,017,124 bytes was rejected as arithmetic
error; the member sums and the independently recomputed total are 106,007,124 bytes.

## Dataset bindings and roles

| Dataset | Comparison-truth input | Core manifest | Evidence input | Matrix vs-TSN placements |
|---|---|---|---|---|
| Highway Log | 12 D01-D12 district PDFs | 12 / 27,911,991 / `6cee58a9eae6d056c47c6bd51a35b74c7a17c226e32030747432da1d5beb5468` | Same raw PDFs | `highway_log`, `highway_log_pdf` |
| Highway Sequence | 12 D01-D12 district PDFs | 12 / 3,866,949 / `83a683484f6a8819e07ea567df4f8096cbaab722aa88dada6867d28ee6c6ddb9` | Same raw PDFs | `highway_sequence`, `highway_sequence_pdf` |
| Ramp Detail | One statewide XLSX | 1 / 1,590,431 / `ad51daf95d1405e0f35a18162d4dee57e94c0b3bb0f9022771fa51d5a953150f` | One statewide TSN print PDF | `ramp_detail`, `ramp_detail_pdf` |
| Ramp Summary | One statewide PDF | 1 / 11,758 / `1983ae8865cd235b7a77ccc6fc8abe7f6f8f788d06bdf032aa4abdb807c6d408` | None | `ramp_summary` |
| Intersection Summary | One statewide PDF | 1 / 12,326 / `15766c79de1937b9e4ac06cf6244af6493988ce06d384a51bd1c8bf592c7ebc3` | None | `intersection_summary` |
| Intersection Detail | One statewide XLSX | 1 / 2,920,705 / `8b42a3dd43df09ba803fbe8c031673e0515254acbab5bcd935ec82038a58add7` | One statewide TSN print PDF | `intersection_detail`, `intersection_detail_pdf` |
| Highway Detail | One statewide XLSX | 1 / 16,356,075 / `22e2b6b270e722e567486b9ff1f6b15bf0434a573a24afa2e7cffaa299208926` | 12 D01-D12 district PDFs | `highway_detail`, `highway_detail_pdf` |

The five PDF-edition Matrix rows reuse their base dataset. They do not own a second TSN
comparison truth. For Ramp/Intersection/Highway Detail, `pdf/` is evidence-only and may
never replace the authoritative XLSX.

## Exact comparison-truth members

### Highway Log — raw district PDFs

The exact set contains 2,121 pages and identifies itself as the 2025 California State
Highway Log (OTM52010). The previously accepted production parser baseline is 60,083
rows / 263 routes; the isolated build and independent conservation oracle must re-prove
that count from these bytes.

| Member | Bytes | SHA-256 |
|---|---:|---|
| `D01 Highway Log TSN.pdf` | 1,633,209 | `0e26d5ef011891f0a77be774e3b655a18a7add616c5139676ab99950e54ddc34` |
| `D02 Highway Log TSN.pdf` | 2,045,757 | `d610f137d88c41cf61d239aa29c6ecad1c2621d307d4c984a8ea5aa15289b6a4` |
| `D03 Highway Log TSN.pdf` | 2,725,260 | `139b14eb4893ee6427153def005262589d1e2dc4bdb2766831579d284307081f` |
| `D04 Highway Log TSN.pdf` | 4,376,185 | `6046fd7a8f60cf3a85d497cd13278fc936d949221820b75235eaab1a263e8433` |
| `D05 Highway Log TSN.pdf` | 2,060,100 | `633ac80514b4791886ee58c8b41be166fd75a03ed0e8c974369fe521035799f5` |
| `D06 Highway Log TSN.pdf` | 2,226,816 | `ac6409f35047a0ecfac93ba00347cf355dbf99bb41e5da69788c3c4a4d387282` |
| `D07 Highway Log TSN.pdf` | 3,626,589 | `7d1151142d103df72e8b3f6ba9193001a88a2806c580ab4dda775053dd0a4371` |
| `D08 Highway Log TSN.pdf` | 2,744,102 | `e2efb38281e9bfcc18a02a54bdc4ad1068045fdcbd812f00584e6c6092109cd3` |
| `D09 Highway Log TSN.pdf` | 844,675 | `38470f27cc49ee1d2eb0813ef653a1348a17522a519a903155ef995ea8c63903` |
| `D10 Highway Log TSN.pdf` | 2,080,827 | `f6aff2dba133da9d66a46d81ffa5f723f38aab5e48a6d8b1824dbfb4a085c123` |
| `D11 Highway Log TSN.pdf` | 2,311,316 | `d7a1eba4ddf75d98874e42a379b7cf189699436dcebe557bffd140b287091a76` |
| `D12 Highway Log TSN.pdf` | 1,237,155 | `36e56bf834063a11be8f2c24cc1e3c93cfd89ac4bc745dd8a494ed6311b39a97` |

### Highway Sequence — raw district PDFs

The exact set contains 1,540 pages. Every document reports Reference Date 15-SEP-25
(OTM22025 Highway Locations). The accepted independent Stage-6 oracle proves 69,804
printed records (68,806 data plus 998 EQUATES TO claims), 69,758 projected rows, and 263
routes from this exact manifest; product losses remain separately red.

| Member | Bytes | SHA-256 |
|---|---:|---|
| `D01 HSL TSN.pdf` | 204,709 | `3a4cb30340a55edae2f72d758dcda62d30e21d919ecc862ec6955d6795252a4a` |
| `D02 HSL TSN.pdf` | 288,696 | `f32078eb79f38fa2e4799319bd10f661ecdff669dd7c4ade18a5326723ad5d85` |
| `D03 HSL TSN.pdf` | 373,387 | `8c5cd4638dd4901797f9c15e6fac7f998d5bc989749f874e6eedf52f72506fb0` |
| `D04 HSL TSN.pdf` | 625,052 | `5facc297fd7d28e8ad760cce8d7f4699b1ee4bc7582f2a007196c0bf739bcd5a` |
| `D05 HSL TSN.pdf` | 265,876 | `b8246f8c28e31d0c4acc352b7148988b6a6a0d7abaf56e810943e14816389e7b` |
| `D06 HSL TSN.pdf` | 327,246 | `e240f038390109ca02ceb012a5e8e5b82fc8845c49be718506acb56667db3dad` |
| `D07 HSL TSN.pdf` | 555,648 | `c791b99789e496efb83b52850aa54e142946aaa541a91b780489fe7e0bc7ec25` |
| `D08 HSL TSN.pdf` | 370,505 | `f23b8e3d5a90200cc1a6285ebb40480b828673f9e5a37b06f36fe30bc9697565` |
| `D09 HSL TSN.pdf` | 103,868 | `c6984a7e947ff600a450e4387f318aeed4826b05249361a694fbe507d0c7c5c3` |
| `D10 HSL TSN.pdf` | 298,313 | `e510a575c56c5af4404968d9fe51271f79cc23377df1e5c651b45b563dbf2ed6` |
| `D11 HSL TSN.pdf` | 315,238 | `920e3e352c1f24be415271c9819fc8bddce8ac6ef3095684e9fe06c87cf7378b` |
| `D12 HSL TSN.pdf` | 138,411 | `5583c0a0b94feeddaefda8bfa35bf34657cfb9f3b8e0a8d2b047c8fc27cbcc7a` |

### Statewide comparison truth

| Dataset/member | Rows x columns | Bytes | SHA-256 |
|---|---:|---:|---|
| Ramp Detail `TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx` | 15,410 x 18 | 1,590,431 | `3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856` |
| Ramp Summary `Ramp Summary Statewide_TSN.pdf` | 3 pages | 11,758 | `e09842e939af4bc0da82014cfd0de1f6670e7fed5e4c5f6441628bda818a118b` |
| Intersection Summary `Intersection Summary Statewide_TSN.pdf` | 3 pages | 12,326 | `c3ad85848764df1b6da53c0bba0f785b3c045e83675f5983555ef514688a7d46` |
| Intersection Detail `TSAR - INTERSECTION DETAIL_TSN.xlsx` | 16,626 x 36 | 2,920,705 | `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2` |
| Highway Detail `TSAR - HIGHWAY DETAIL_TSN.xlsx` | 60,083 x 56 | 16,356,075 | `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1` |

The two Summary PDFs report reference date 09/15/2025. Ramp Summary independently
reports 15,410 ramps and Intersection Summary reports 16,626 intersections, agreeing
with their corresponding detail-row cardinalities.

## Exact evidence-only members

### Ramp and Intersection statewide prints

| Member | Bytes | SHA-256 |
|---|---:|---|
| `ramp_detail/pdf/Ramp Detail Statewide_TSN.pdf` | 1,384,895 | `0d1e31054e8f866de3be924ba350a5bd77f9230d453e58d761dea079f4505a49` |
| `intersection_detail/pdf/Intersection Detail Statewide_TSN.pdf` | 9,284,543 | `1230b955176a1a34223ce8f79eeeed1b46970031372acc510ffb78a45c2f1f46` |

The Ramp print contains 500 pages. The Intersection print contains 1,111 pages.

### Highway Detail district prints

The 12-member evidence set contains 4,123 pages. These prints are evidence, not a
replacement for the statewide XLSX truth.

| Member | Bytes | SHA-256 |
|---|---:|---|
| `D01 Highway Detail_TSN.pdf` | 2,562,241 | `815ad64218ebcd262ceb75b8efa65c6173023f543ecef28beb33b096e7fb5ce4` |
| `D02 Highway Detail_TSN.pdf` | 3,196,667 | `7076f29147bc119cdf62398c99104ee7b7bfa05ee44663144a09303e805fd8ae` |
| `D03 Highway Detail_TSN.pdf` | 4,198,903 | `cdbfc4abda1e67cf16b46f43a3ae750e54aace7a0fa738b1cae66dedf30d3885` |
| `D04 Highway Detail_TSN.pdf` | 6,635,081 | `3fcb00d918b3cc2ce78043c50e01085e342c08cd9ba754a5ce9a7d074ae2ff5e` |
| `D05 Highway Detail_TSN.pdf` | 3,243,829 | `099460bc87ad6fb6c6fac00753be099e433cd54f7c77d636c7c8b97aebb42a04` |
| `D06 Highway Detail_TSN.pdf` | 3,408,172 | `7b4ec9888164c8ab2be424f13b6a77235dfd11a59e107183b1edbe2bc33d50d5` |
| `D07 Highway Detail_TSN.pdf` | 5,377,239 | `19538cc8569e7af578cc592d836a7f2cebfab99a2fc1b23498684fe92249c8ec` |
| `D08 Highway Detail_TSN.pdf` | 4,160,037 | `3507b0647a1a8851bb67b4a668a96c66697af2574da9eb68a7b66a8ea6aa8d46` |
| `D09 Highway Detail_TSN.pdf` | 1,333,655 | `d631142229b619bbadfe685aa6e944646757dc487e2e2051ed3891afacf25123` |
| `D10 Highway Detail_TSN.pdf` | 3,203,016 | `af0bc372674bbac9d6821a0f1faff246697523e02b67802f9a96bdfc637f05f6` |
| `D11 Highway Detail_TSN.pdf` | 3,491,150 | `a987c4a47e09a18462a16874780c3a06f0c3aa59ca71068e611b8e76b0979f25` |
| `D12 Highway Detail_TSN.pdf` | 1,857,461 | `381d895c242bf5606360477e4290383da7ac807b9bdd09b3818b33649b1d40a1` |

## Raw schema and identity facts already established

| Dataset | Raw universe | Adversarial identity result |
|---|---|---|
| Ramp Detail | 15,410 rows, 18 columns, 126 routes, 50 counties | Route + numeric PM collapses 81 cross-county keys / 163 county-specific identities. Complete PR+PM+PM_SFX still has 46 multi-county keys / 93 identities. PM_SFX is populated on 313 rows and must be retained. No current full-identity duplicate. |
| Intersection Detail | 16,626 rows, 36 columns, 216 routes, 58 counties | Route + numeric PM collapses 78 cross-county keys / 156 identities. Six real same-route/same-county/same-numeric-PM pairs differ only by prefix, so complete glued prefix+PM+suffix is mandatory. Fifteen full-identity duplicate groups remain for deterministic pairing. |
| Highway Detail | 60,083 rows, 56 columns, 273 routes, 58 counties | Production-shaped route-suffix + canonical PM still has 438 multi-county keys / 976 county identities. The weaker base-route + PP + PM probe has 453 multi-county keys / 1,008 identities. There are 86 full-identity duplicate groups and 433 within-county physical variants. |
| Highway Log | 12 raw PDFs, 2,121 pages; accepted parser baseline 60,083 rows / 263 routes | Raw group headers carry district, county, and route, but the current normalized row discards county. The earlier county exemption is not source-proved; retain the claim and run a full collision/count census before pairing semantics are accepted. |
| Highway Sequence | 12 raw PDFs, 1,540 pages; accepted independent census 69,804 source records / 69,758 projected rows / 263 routes | County plus complete printed PM still has 3,504 duplicate groups/7,044 rows; only the accepted district+route+direction+county+printed-PM occurrence-ordinal identity is unique. Other paths must use that complete physical identity; a route spanning district files is not itself a duplicate owner. |

No raw row in these three workbooks is currently missing or malformed in the fields
needed for the stated identity censuses. That fact is a bound observation, not license
for the loader to admit missing fields in a future source.

### Ramp Excel-to-print mapping fact — independently visualized

The Ramp evidence PDF is Oracle report OTM22260, created/modified 2025-09-15 09:58:34
PDT, 500 landscape-letter pages. Its internal Report Date and Reference Date are both
09/15/2025. Representative first, middle, final, and populated-suffix pages were
rendered and visually inspected under `tmp/pdfs/phase4-tsn-parity/ramp-detail/`.

The PDF prints one detail record per line with fixed columns for Location, PR, PM,
Date of Record, HG, Area 4, City Code, R/U, On/Off, ADT effective year, ADT, Ramp Type,
effective date, and Description. It does not print separate database identifiers,
Ramp Name, Segment Order ID, or a distinct PM_SFX column.

PM_SFX is nevertheless source-mappable in this exact pair, not assumable in general:
all 313 nonblank XLSX PM_SFX values equal HG (`L`: 165, `R`: 148), and zero blank-suffix
rows have HG L/R. Thus current print HG identifies both the printed HG attribute and
the XLSX suffix class with no residue. This invariant must be re-censused on every new
source pair and must not be converted into a universal rule. The normalized library
currently drops PM_SFX as an independent claim, and the evidence index keys only on
county/route/numeric PM; CMP-AUD-045 remains red until complete identity is retained
without depending on a potentially changing attribute coincidence.

## Detail XLSX-to-TSN-print oracle results

Ramp, Intersection, and Highway Detail are accepted source-format permanent gates after
adversarial review and fresh full-corpus reruns. They do not yet certify production
normalization, Comparison cells, or evidence images; their accepted mappings feed those
later gates.

### Ramp Detail and Ramp Summary

Accepted independent oracle: `build/phase4_ramp_tsn_pdf_oracle.py` version 3; no
production parser/comparator/schema imports. Script SHA-256
`c580336cb2aa5fceae51230fc037f712e8ab2908e68561aa4402728ed93ae8a5`.
Result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r1\ramp_cross_format_oracle-v3.json`,
SHA-256 `47383b5d00ed4b72fa72ed711d165c0ec633d2d7c8f86edd695f4f0a2e886ed1`.

- 15,410 XLSX rows = 15,410 PDF records = 15,410 unique physical identities; zero
  one-sided, ambiguous, or unresolved records.
- 15,404 records have exact extracted printed content. Six descriptions are exact
  visible equivalents under the hash-bound clip rectangle/font. The proof now reports
  the final PDF content character's endpoint and makes no claim about an absent
  character. Source dates classify zero values.
- The four `(cid:13)` extraction artifacts are bound by exact identity, physical/report
  page, row, and raw text. Missing, extra, moved, or changed artifacts fail closed.
- All Ramp Summary highway-group, on/off, population, Ramp Type, and total categories
  reproduce exactly from the 15,410 detail rows. The exact PM_SFX/HG invariant is
  313 = L165 + R148 with zero exceptions.
- All 18 XLSX columns have exactly one declared disposition: 14 printed/compared,
  PM_SFX relationally asserted, and three source-only fields census/digest-bound for
  Stage-6 raw-to-normalized conservation. Internal negative mutations all pass.

### Intersection Detail and Intersection Summary

Accepted independent oracle: `build/phase4_intersection_tsn_pdf_oracle.py` version 2;
no production parser/comparator/schema imports. Script SHA-256
`ffc364ceb8b6cdbbfb3bff680cc0f3ed77e12c1867978c86122d221de7c78441`.
Result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\intersection-tsn-cross-format-oracle-v2.json`,
SHA-256 `63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e`.

- 16,626 XLSX rows = 16,626 two-line PDF records; 598,536 field assertions, zero
  one-sided records, zero unresolved cells. All 36 XLSX columns map exactly once into
  PDF line 1/line 2 and the corresponding Report View layers.
- Relations are 578,432 raw-exact, 20,103 narrowly proven render equivalents, and one
  authorized pull-time delta. The sole delta is the Description at physical identity
  Route 001 / VEN / blank prefix / PM 23.907: later XLSX `SAN MIGUELITO RD-RT` versus
  earlier PDF `A LEASE CANYON RD`; the other 35 cells are clean and exact source hashes
  and PDF-before-XLSX timestamps are required.
- Any second changed detail cell revokes that authorization and becomes unresolved; a
  changed Summary count also becomes unresolved. All three source size/hash contracts
  and the negative mutation check are part of the passing result.
- Date-flag equivalence is directional: only a PDF-added `Y`/`*` on the same unflagged
  XLSX date is render-only. Description truncation requires the measured exact
  32-character cell boundary, including its narrowly handled character-32-space case;
  reverse flags, shorter prefixes, and wrong limits fail closed.
- The 62 raw printed Summary rows fold only the documented J/K/L/M/N/P control codes to
  S, yielding exactly 58 normalized categories including Total. The PDF taxonomy omits
  116 explicitly enumerated nonblank detail values; each section proves
  `printed categories + excluded values = 16,626` rather than coercing those rows to
  “no data.”

### Highway Detail

Accepted independent oracle: `build/phase4_highway_detail_tsn_pdf_oracle.py` version 1;
no production parser/comparator/evidence/constants imports. Script SHA-256
`34d7aceb7717d285b48d440e0e762564615be2f4de0fd0b4827fa568277fc45b`.
Result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\highway_detail_tsn_pdf_oracle_final.json`,
SHA-256 `540b1ce575be880f506ebc435acaabe253e238f4eba312a72a310129f4ecdc36`.

- All 12 frozen district PDFs / 4,123 pages parse to 60,081 records with zero residue or
  unsafe attribution. They pair against 60,083 frozen XLSX rows with exactly two
  D03/YUB/Route 020/L013.377 XLSX-only duplicate occurrences and zero PDF-only records.
- Pairing preserves multiplicity and uses maximum-cardinality/minimum-content-difference
  assignment. This closes the rejected ordinal-pairing defect across 77 physical-key
  collision groups, including the 4-to-2 D03 subset and tied-SEG reverse order in D11.
- The accepted projection has 3,003,609 exact printable cells and 127,455 narrowly proven
  render equivalents: `BEG_DATE` as `YY-01-01`, Description's first 23 source characters,
  three-character shoulder TO/TR cells, fixed three-decimal formatting, and composed
  median width/variance.
- The exact 443-item dated-delta allowlist has digest
  `d101bc1263188dcb436a9218bad6774ab047368e819c205d1e53b9b812b56d8a`:
  436 `LK_BACK_ADT`, three D07 descriptions, two D01 lengths, and the two exact XLSX-only
  occurrences. There are zero unresolved cells and zero SEG_ORDER inversions.
- Ten internal negative mutations pass. Any source hash, value, identity, field, count,
  allowlist digest, or field-count mutation fails closed. The audit also corrects the
  historical 57,647-record claim to 60,081, identifies `BREAK_DESC` as non-printing, and
  requires the five narrow projections above in evidence and layered Report View.

### Second-review disposition

All five Ramp/Intersection second-review defects are closed by the bound Ramp v3 and
Intersection v2 reruns above: directional date flags, the exact measured description
boundary, the four-item `(cid:13)` contract, the corrected clip-coordinate claim, and
all-18-field Ramp disposition. Highway Detail's independent duplicate-assignment and
delta-classification review is also closed by its final bound rerun. Zero unresolved
residue remains in any accepted source-format result.

## Raw admission disposition

- CMP-AUD-035 covers weak XLSX column admission, ambiguous raw member universes, and
  build-time source stability. The focused contracts now require exact-one statewide
  sources or one internally claimed D01-D12 set, immutable captured parsing, exact
  content-manifest reuse, coherent complete-only raw+normalized certificates, immutable
  normalized consumer capture, and source checks through comparison/evidence/cache
  publication. The r7 post-contract seven-family production witness is accepted.
- CMP-AUD-033 covers normalized readers that discard or weakly inspect headers.
- CMP-AUD-037 covers direct comparison of stale/unversioned normalized libraries.
- CMP-AUD-076/081 cover missing durable source/raw-manifest provenance in saved results
  and canonical Matrix freshness.
- CMP-AUD-019 through 022 cover incomplete, inconsistent, non-integral, and duplicate
  Summary categories/totals.
- CMP-AUD-049/066 cover route and role provenance for direct/PDF paths.

The remaining findings in this list stay red until their own gates close. CMP-AUD-035's
Stage-5 admission/lifecycle/certificate/consumer-token conditions are green with r7. The
pre-hardening r2 baseline remains useful semantic evidence, not the current-code witness.

## Accepted post-contract production-builder witness

Witness ID: `TSN-RAW-7-2026-07-12-R7`  
Runner: `build/run_phase4_tsn_source_rebaseline.py`  
Audit root:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r7`  
Result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r7\result.json`  
Result bytes / SHA-256: 173,124 /
`b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa`

Acceptance is `complete`: 7/7 families. The exact 29-member / 52,670,235-byte core
manifest remains
`c6c91c378c4010682df72f000212df26f9ed5caae89ba38bb6c6b226393a7c54`;
the 14-member / 53,336,889-byte evidence manifest remains
`0f2f1edbb7c6eed04b203fdfd4e8941332f55501fae48c6a3daac404f4c3c048`.
Both are byte-identical before/after. Operative code provenance is stable at 28 members /
867,593 bytes / `aee75325c5268e097c0fc389148b65a8ad97564ae314751e90e51062628dbfa7`.
The exact generated universe is seven workbooks plus seven sidecars: 14 artifacts /
20,794,592 bytes / `56fd098c268f14951ba5b860205ed5d9a40aad4aa809237726f5700fc951f3c4`.

Every family is `ok / complete / 0 skipped / 0 failed`, builder-certificate exact,
producer-complete, coherent-current, identity-token-current, and immediately reusable
without changing workbook or sidecar bytes.

| Dataset | Version | Rows | Distinct first-column values | Seconds | Output SHA-256 | Canonical token suffix |
|---|---:|---:|---:|---:|---|---|
| Highway Log | 4 | 60,083 | 263 | 883.578 | `fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa` | `dfd4c225…f92996` |
| Ramp Detail | 3 | 15,410 | 126 | 5.005 | `c121a9ca1bed2fad00bfc4b08bfc68fa01cd46da436d6bffa699c5579bb4f5f1` | `89326764…1d2d8c` |
| Ramp Summary | 2 | 31 | 31 | 0.158 | `15e5b9260b79618371d0378afa40f051a8912c7056c8fbf43cdbbde47b143356` | `7fd9bdf1…f61eb4` |
| Intersection Summary | 2 | 58 | 58 | 0.165 | `94befb313416a356a6e9f0363ffae0d065bd03c15ea1fce5bd8e93e0bf59a210` | `13714e19…50b7d` |
| Intersection Detail | 3 | 16,626 | 211 base routes | 9.129 | `d4609c3afb8663dd89e6e2e00103d41245a0213d7e4e08fb63e961bc4035b37b` | `fb78c4f1…47d8a` |
| Highway Sequence | 3 | 69,758 | 263 | 117.839 | `9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041` | `35a86d07…e5151` |
| Highway Detail | 2 | 60,083 | 273 | 41.602 | `46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5` | `48c0009b…bfbcc` |

An independent read-only stream compared every r2/r7 sheet name, cell data type, and
cell value: Highway Log 1,889,490; Ramp Detail 231,165; Ramp Summary 64; Intersection
Summary 118; Intersection Detail 598,572; Highway Sequence 544,604; Highway Detail
2,283,192; total **5,547,205 cells with zero differences**. Thus certificate, isolation,
normalizer-version, and consumer-hardening changes did not change normalized facts.

## Accepted pre-hardening production-builder baseline

Runner: `build/run_phase4_tsn_source_rebaseline.py`  
Audit root:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r2`

The runner directly invoked the seven catalogued builders against the raw-only source,
wrote each requested final output under an empty audit root, and recorded raw/evidence
member hashes, normalizer version, builder-source hash, producer outcome, output hash,
  sheets, headers, row counts, and route-like first-column cardinality. It is a
  production-path witness for the r2 code, not an independent semantic oracle and not a
  current-code witness after the HL/HSL version and raw-contract changes.

Final result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r2\result.json`  
Result SHA-256:
`1e9e6e689589f5a30eb32899ed163abffc00e73889806a2a8775179df9fd4e25`

The result independently reproduces the canonical 29-member/52,670,235-byte core
manifest and 14-member/53,336,889-byte evidence manifest above.

| Dataset | Version | Status / explicit completion | Rows | Distinct normalized first-column values | Seconds | Output SHA-256 |
|---|---:|---|---:|---:|---:|---|
| Highway Log | 3 | `ok / complete`; 0 skipped, 0 failed | 60,083 | 263 | 945.996 | `0547213f2a4c35878849c552acd543b7e525e8be6e851019d3c1461c8bf07398` |
| Ramp Detail | 3 | `ok / complete`; 0 skipped, 0 failed | 15,410 | 126 | 6.157 | `84e148e3840f23f32d10222abfd0d881e3abb85c7f9154c5c6febb5f8fc0ff75` |
| Ramp Summary | 2 | `ok / complete`; 0 skipped, 0 failed | 31 | 31 | 0.139 | `bd2df6b55fe8f158e7e4dd9cac196400263f919fead3d1de61aac33cd541c554` |
| Intersection Summary | 2 | `ok / complete`; 0 skipped, 0 failed | 58 | 58 | 0.148 | `47beed6caf7cd132a37ae51dd1cc20ace838da711df302c63bf63085cdb6ba3a` |
| Intersection Detail | 3 | `ok / complete`; 0 skipped, 0 failed | 16,626 | 211 base routes | 12.345 | `985a57f1df22f11a75ad49aa7ab97dccce423e97347c4e26fe505f70d9f588c2` |
| Highway Sequence | 2 | `ok / complete`; 0 skipped, 0 failed | 69,758 | 263 | 166.575 | `19eaa3226f933e4e5f6cdef2c2d37b88f4a7f1cc42363c8a4c9147138ff47135` |
| Highway Detail | 2 | `ok / complete`; 0 skipped, 0 failed | 60,083 | 273 | 50.961 | `cf4d24b7f1fba58579a2dcb6584b9593e1e47d543b7905e2514ec2be8535ab21` |

All captured events were scanned for warning/failure/skip/error/incomplete/duplicate
markers and returned zero suspicious lines. All seven producers in that baseline own
explicit `complete` state with zero skipped/failed inputs. The clean log remains useful
pre-hardening evidence, not proof of independent semantic conservation or current-code
acceptance.

Intersection's 216 raw route tokens intentionally normalize to 211 base routes: the
216 distinct `(base, suffix)` pairs include seven suffixed routes (`008U`, `010S`,
`014U`, `058U`, `101U`, `178S`, `210U`) whose bases overlap five unsuffixed route
families. The suffix remains a compared field; this exact 216-token/211-base mapping is
an oracle requirement, not unexplained row loss.

The r2 Highway Log build used an attempt-scoped scratch directory and an exact generated
member manifest. After the run, zero scratch directories remained and no file under the
former global `output/tsn_highway_log` boundary had changed after the r2 start. The
permanent overlap/cancel/failure/retry/sentinel fixture also passed. CMP-AUD-132 is
therefore resolved by focused proof plus this full 12-PDF / 60,083-row production
witness.

The rejected r1 run remains historical defect evidence: it wrote 369 intermediates to
the process-global directory and had implicit completion for RD/ID/HD. Although XLSX
ZIP hashes differ because workbook package timestamps changed, an independent streaming
reader compared every sheet name, cell type, and cell value across all seven r1/r2
outputs: 5,547,205 cells, zero differences. The r2 changes therefore corrected
isolation and producer claims without altering normalized cell semantics.

## Stage-6 independent conservation results

### Ramp Detail — corrected audit accepted; current normalized product red

Corrected result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase6_ramp_detail_conservation_r7_reissued.json`  
Result bytes / SHA-256: 64,727 /
`3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd`  
Detached acceptance bytes / SHA-256: 5,941 /
`2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb`  
Oracle: `build/phase6_ramp_detail_conservation.py`, 55,945 bytes, SHA-256
`c18f9d2a8422413fc1998dc1d57e3a312c3a4348cd93d54cf5edb5a1eb59c6ee`  
Permanent synthetic gate: `build/check_phase6_ramp_detail_conservation.py`, SHA-256
`673987c7d4a1acf3e0da6a8d9f30206cf0e4dd8210838fd548177f44fa8eae04`

The independent stdlib OOXML path binds the exact 18-column raw workbook and 15-column
`r7` normalized workbook before/during/after reading, explains every raw field, computes
ordered and multiset typed row digests plus every per-field digest, and proves exact
row/order/multiplicity/identity/anomaly/mutation facts across all 15,410 rows. The corrected
result has `stage6_family_audit_complete=true`, `projection_exact=false`, and
`normalized_full_conservation=false`. All 14 invariants and six semantic mutations pass;
two full authoritative replays reproduced identical result and acceptance bytes.

The complete physical identity is unique for all 15,410 rows. The weaker route+PM probe
has 81 cross-county keys / 163 county identities; route+PR+PM+suffix has 46 / 93.
All 246 district/county/route blocks are contiguous, all `SEG_ORDER_ID` values are typed
Decimal, and none decreases within its block. `PM_SFX` is populated 313 times
(`L` 165 / `R` 148), agrees with HG only in this frozen corpus, and remains absent as an
independent normalized claim. `ADT_EFF_YEAR` is `2023` on all rows and `EFF_DATE` equals
`DATE_OF_RECORD` on this frozen source, but both are fields in the accepted TSN print and
cannot inherit a universal derivation rule from that coincidence.

Direct raw-TSN/r7 plus same-pull TSMIS triangulation proves all 15 leading numeric
prefixes are source data, including nine whose token numerically equals the outer route.
The accepted projection classifies exactly the losses at raw worksheet rows 11, 12, 13,
14, 299, 300, 305, 588, 1998, 2001, 3243, 5684, 9519, 9603, and 10815, with zero other
residue. CMP-AUD-133 and CMP-AUD-135 retain these product gaps for remediation.

The first discovery result (SHA-256
`7fcaca163d2afa9d8842a67a77ebef2df4458d5192d27d7721d75b0f270dc8a6`)
is rejected audit-gate evidence, not an accepted result: adversarial review found its
missing final identity revalidation, conflated audit/product state, understated printed
field loss, and copied impossible-date acceptance into the oracle. The later 44,299-byte
`r7_final` candidate was also superseded after second review required private captured
parsing, error-cell refusal, contiguity invariants, full negative-gate coverage, and
detached post-write acceptance. The accepted oracle and permanent synthetic gate correct
those defects and keep the product findings red.

### Intersection Detail — audit complete, current normalized product red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase6_intersection_detail_conservation_r7_accepted.json`  
Result bytes / SHA-256: 453,532 /
`4d507661835cdd9e9267f05f7700777ba97b8a3948797ac3e436be8db8d21b88`  
Detached acceptance bytes / SHA-256: 3,353 /
`7077358da9ca016c12a4d1bc2cf8e09c95b20ac588272febf9b307f5856c7b43`  
Oracle: `build/phase6_intersection_detail_conservation.py`, 75,975 bytes,
SHA-256 `a3b19c4f4e04fdd0e9c8600ff029df4e9aa710bf902ea1002b34093d1d4187c4`

The independent stdlib audit reproduces all 16,626 normalized rows with zero projected
residue, gives all 36 raw fields one explicit disposition, executes and binds the shared
reader mutation gate, and passes all 24 acceptance invariants plus 25 semantic mutations.
Private captures own every worksheet/topology/error scan; the accepted `r7` workbook,
sidecar, lifecycle result, generator, reader, gate, final result bytes, and post-write
identities are one coherent detached acceptance unit.

Decimal-canonical physical identity yields 16,611 unique identities and 15 duplicate
groups / 30 rows. The exact six within-county prefix collisions are preserved at numeric
postmiles `5.45`, `9.54`, `15.34`, `15.62`, `0`, and `0.34`; weaker route+PM grouping
has 78 cross-county keys / 156 county identities, while complete PP+PM grouping has
71 / 142. A display-only trailing zero leaves all three numeric-PM diagnostics identical.

`projection_exact=true` and `stage6_family_audit_complete=true`, while
`normalized_full_conservation=false`: `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT`
remain authoritative omitted facts under CMP-AUD-133. CMP-AUD-139 and CMP-AUD-140 are
audit-gate remediations, not permission to discard those product findings.

### Highway Detail — audit complete, current normalized product red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation\highway_detail_conservation_r7.json`  
Result bytes / SHA-256: 122,006 /
`283315b30605461e748246444ea523542f61b0a205cd70131c73e1f6b77fb20b`  
Detached acceptance bytes / SHA-256: 3,802 /
`d26dee5d11517478312cde6361c4567c30a4f8d534d822539bb36388c170cf03`  
Oracle: `build/phase6_highway_detail_conservation.py`, 85,152 bytes,
SHA-256 `e957e6c0b8ff53f79c8641f53e7452af2fbd1492931f3b40ea828e90709d373a`

The independent full-corpus audit consumes the exact 56-column raw workbook and 38-column
`r7` normalized workbook, accepted `r7` lifecycle/sidecar, and accepted all-12 PDF oracle
from immutable captures. It executes and hash-binds the shared reader gate, revalidates
all eight source/code/provenance identities after the result write, and publishes
detached acceptance only when both identities are current and the family audit is
complete. Final independent review passed all 23 invariants and 22 mutations with zero
unexplained projection residue.

The exact collision/order facts remain: strong identity 77 duplicate groups / 156 rows
(76×2 plus 1×4), district-without-equation 83/168, legacy weak identity 86/174,
route+canonical-PM 438 multi-county keys / 976 county identities, and base
route+PP+PM 453/1008. DCR reconstruction is exact, SEG order has no inversion, and the
two source dates are exact singletons.

`stage6_family_audit_complete=true`, while `projection_exact=false` and
`normalized_full_conservation=false`. Three blocking product findings remain: omitted
DCR/ADT/change evidence facts, exact raw/PDF `000.014` versus r7 `000.013` at raw row
32565, and omitted printed `REFERENCE_DATE=2025-09-08` /
`EXTRACT_DATE=2025-09-15` snapshot metadata. CMP-AUD-141/CMP-AUD-143/CMP-AUD-147 are
audit-gate remediations; CMP-AUD-133/CMP-AUD-138/CMP-AUD-142 remain product-red.

### Ramp Summary — audit complete, exact comparison projection, printed provenance red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation\ramp_summary_conservation_r7.json`  
Result bytes / SHA-256: 384,147 /
`38b500489c8a310529c4c7b76bea3fe7461374d6c786b992caaa458e0ef65421`  
Detached acceptance bytes / SHA-256: 128,177 /
`55c43d501960d3ca3702e5eac1202f96ac6c9b3e1df2eb915b19c593669bf74c`  
Oracle: `build/phase6_ramp_summary_conservation.py`, 70,225 bytes,
SHA-256 `7a121136b959cbc3b6ccb095a0007bcd3849787bec7e526588994957af508d58`  
Permanent gate: `build/check_phase6_ramp_summary_conservation.py`, 7,657 bytes,
SHA-256 `309ba1af2a72cf827b2245efe08e4dd4c5d27de78d819bf30bccb9bf12841b45`

The independent PDF audit binds the exact three-page source, r7 normalized workbook,
sidecar/lifecycle witness, generator/reader/gates, and 95 loaded
`pdfplumber`/`pdfminer`/`pypdf` module files. All 103 acceptance-bound live identities
revalidated with zero drift. Exact source-role coverage is 13 observed = 13 unique
dispositions, including cover title and section headers; missing/duplicate/extra roles
fail closed. Detached acceptance is explicit and cannot survive audit-false,
unauthorized-open-finding, or post-write-drift paths.

The 30 comparison categories plus `Total` exactly reproduce all 31 normalized rows with
zero residue. Highway Group, On/Off, Population, and Ramp Type each sum independently to
15,410. All 18 invariants and 13 mutations pass. `projection_exact=true` and
`stage6_family_audit_complete=true`, while `normalized_full_conservation=false` only
because CMP-AUD-146's printed report/reference date, report ID, event, submitter,
scope/title, and generation time are absent from normalized artifacts. CMP-AUD-152/
CMP-AUD-153 are audit-harness remediations, not permission to omit that provenance.

### Intersection Summary — audit complete, exact comparison projection, raw granularity red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation\intersection_summary_conservation_r7.json`  
Result bytes / SHA-256: 245,040 /
`f3a0aa0dfb15cf2ca911ec98721c8dcc0d5d9b25c0ce3cc89184d2959aaf64de`  
Detached acceptance bytes / SHA-256: 44,337 /
`cdf63defdb62d2066a2cafb7229d0c1539a0c6d90f80ea1b96c07c77f609b703`  
Oracle: `build/phase6_intersection_summary_conservation.py`, 81,608 bytes,
SHA-256 `b5bd74920b4201d83a0d14a6b0a0a9c2f0635a84020d786b93c9d4c97bbba6f6`  
Permanent gate: `build/check_phase6_intersection_summary_conservation.py`, 11,023 bytes,
SHA-256 `0ceaa5090d20af75f5d3a3b2aef213d8cf30eb36f36582d7fdbc4bbfdf2ece68`

The independent audit visually inspected all three authoritative PDF pages and replayed
byte-identically. It binds 137 loaded executable parser/native module files (15,385,129
bytes; manifest SHA-256
`2e5ad10339dbb7a87ec8aec497f2adf0f9370bc795ab3bf564f01d5e5a140536`), exact source,
r7, sidecar/lifecycle, code, result, and post-write identities. All 19 invariants and 17
full-corpus mutations pass with zero unexplained residue.

All 62 printed source category rows have exactly one disposition. The 58 normalized
Category rows—including `Total Intersections`—each retain ordered and multiset typed
contribution digests, an exact typed target-row digest, and typed source-disposition
digests. Projected and normalized ordered digest is
`ce872ff02eecef92d4b92726e2c583e5d9257e0bbde6c5076c0658daab81ba64`;
multiset digest is
`c07cda6dc4e8ee5cd6597551b924ea040896db9b7161a4640fdc005aa3d28e72`.

`projection_exact=true`, `stage6_family_audit_complete=true`, and
`normalized_full_conservation=false`. The six printed J/K/L/M/N/P counts are correctly
derived into `S=2648` but cannot be reconstructed from normalized bytes; Control F is
relabelled `RED ON ALL`→`RED/MAINLINE`; and printed report provenance is omitted.
CMP-AUD-148/CMP-AUD-149/CMP-AUD-150/CMP-AUD-151/CMP-AUD-154 are audit-harness
remediations. CMP-AUD-144/CMP-AUD-145/CMP-AUD-146 remain product-red.

### Highway Sequence — audit complete, exact source dispositions, normalized product red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation\highway_sequence_conservation_r7.json`  
Result bytes / SHA-256: 1,276,684 /
`bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2`  
Detached acceptance bytes / SHA-256: 5,934 /
`71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2`  
Oracle: `build/phase6_highway_sequence_conservation.py`, 63,233 bytes,
SHA-256 `0d6cacfa5a4615a80381b077780b051127958bbf325979cf24b7a5c29eb8e17b`  
Permanent gate: `build/check_phase6_highway_sequence_conservation.py`, 12,131 bytes,
SHA-256 `5e61e9b422eb5497c8e07314cd21eaa797776ad86663bcdbafe53501c6612c2a`

The independent private-byte PDF parser consumes the exact 12 district members and
1,540 pages, records the named library placeholder only as a non-source role, and binds
every cover, data-page header, owner, report date/time, policy warning, and exact PDF
metadata claim. Thirty-six first/middle/final pages were rendered and visually inspected
across all districts. The final code/input state was then replayed twice from all 1,540
pages with byte-identical result and acceptance hashes. All 22 invariants and 14 semantic
mutations pass; 47 loaded parser modules have manifest SHA-256
`d9e0eaaf67b32611c7469f14a980a91c29ad329e2c927f3b9ff1cdd68953fe5d`.

The exact source census is 69,804 records: 68,806 ordinary data rows and 998 printed
`EQUATES TO` annotations. Of the equates, 952 retain known county ownership and project;
46 occur before county context and are classified source-only rather than guessed.
The independent projection and normalized workbook both contain 69,758 rows. Their 566
typed cell differences are fully classified: 283 `*P*` plus 282 `-------->` Distance
claims become blank, and D09/KER/014/018.365 gains one comma absent from its wrapped PDF
Description. Unexplained residue is exactly zero.

Identity remains occurrence-based, not merely value-based. Route+county+printed-PM has
3,504 duplicate groups / 7,044 rows / maximum multiplicity 4; numeric-PM has 3,651 /
7,378 / max 4; dropping county has 3,948 / 8,102 / max 11. The full physical
occurrence-ordinal identity has 69,758 distinct keys and zero duplicates. The source has
369 district-route-direction owners across 263 routes and 58 counties.

`stage6_family_audit_complete=true`, while `projection_exact=false` and
`normalized_full_conservation=false`. CMP-AUD-155/156/158/159 retain omitted
district/direction/report/PDF/policy provenance, the 565 distance tokens, the 46
pre-county equates, and the one invented comma as product-red facts. CMP-AUD-160 through
CMP-AUD-166 are resolved audit-gate defects, not exceptions to those source facts.

### Highway Log — audit complete, exact projection, normalized product red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation\highway_log_conservation_r1.json`  
Result bytes / SHA-256: 10,879,397 /
`f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4`  
Detached acceptance bytes / SHA-256: 6,502 /
`012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61`  
Oracle: `build/phase6_highway_log_conservation.py`, 129,944 bytes,
SHA-256 `986747344dc4c0884d0bfc2f5bf410bd923e021d7d984298919b409d5aadab4c`  
Permanent gate: `build/check_phase6_highway_log_conservation.py`, 27,692 bytes,
SHA-256 `ffc21351ae33de4f94365903184f6c7c12ea103e385e2c8311732c4822a07f17`

The independent private-byte PDF parser consumes the exact 12 D01-D12 members and all
2,121 pages, while recording the named library placeholder outside source truth. The
source census is 60,083 ordered records, 13,549 typed total claims, 23,094 Description
lines, and three exact Description-band blank markers. Every line is classified; no
total is unparsed. Thirty-six fresh first/middle/final source pages were rendered,
manifest-bound, and visually inspected with zero source-layout defects.

All 34 invariants and 53 semantic mutations pass. Eight decisive dataset contracts bind
raw rows, provenance, totals, separators, document metadata, both projections, and the
normalized workbook. All 12 page/owner/separator/total document manifests and all four
collision domains are exact. The full progression contract binds 5,451 assessable
intervals (4,675 exact plus 776 printed ±1 rounding), 79 explicit zero resets, eight
fragment-obscured intervals, all 2,905 complete mileage-to-DVMS pairs, and 35 separately
typed unassociated continuations. The 12 numeric fragments remain only in their proper
fragment ledger and cannot consume a continuation slot.

The exact pre/post 47-module parser manifest is stable at SHA-256
`d9e0eaaf67b32611c7469f14a980a91c29ad329e2c927f3b9ff1cdd68953fe5d`.
Fresh 822-second and 823-second full-corpus runs produced byte-identical result and
acceptance files. `stage6_family_audit_complete=true` and `projection_exact=true`, while
`normalized_full_conservation=false`: CMP-AUD-045/157 retain district/county ownership,
owner qualifier, three ADT fields, totals, and report provenance as product-red facts.
CMP-AUD-167 through CMP-AUD-182 are resolved audit-gate defects, not exceptions to those
source facts.

## Stage-8 base TSMIS-vs-TSN comparison results

Stage-8 base auditing is closed at 7/7 families. This accepts the bound source and
projection audits and records observed current-product behavior; it does not accept
product perfection, full physical-source conservation, workbook-cell evidence, or
end-to-end evidence. The remaining implementation boundary is recorded in
[comparison-implementation-handoff.md](archive/comparison-implementation-handoff.md).

### Ramp Summary — source truth/value projection accepted, product semantics red

Accepted result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\ramp_summary_base_r1.json`  
Result bytes / SHA-256: 491,099 /
`f05bad6e7442fd3f345f86c8b61f334f44bd6cbaced1341d4e24b277c2ef3ba2`  
Detached acceptance bytes / SHA-256: 11,568 /
`46ff47b2c73675b321ac88fc872767ef8446d7d09c3a3d1a36923a23fee782ca`

The independent oracle binds the exact accepted TSN raw→r7 chain plus four current
TSMIS trees: 126 Summary PDFs, 126 Summary Excel exports, 126 Detail Excel exports, and
126 Detail PDFs. Direct comparison of every audit-copy member to the authoritative
Downloads tree found zero differences. Canonical tree manifests are respectively
`81108f5b…8c444`, `d74c19b5…6281e`, `7c10fbf6…f7489`, and
`6e8a2b66…6c4c9` under the explicit name/bytes/member-hash serialization.

All 3,780 Summary PDF/Excel values agree. Every route total and the 15,216 statewide
total agree with both 15,216-row Detail forms. The nine-route printed Ramp-Type residual
is exactly the 22 same-pull Detail P/V records (P=2, V=20), with no residue. Independent
comparison truth is 29 shared / 0 TSMIS-only / 2 TSN-only, 24 differing shared / 5
identical, digest `a3cbf752…a2d63`; TSMIS/TSN totals are 15,216/15,410.

Production projects all source-backed values exactly, but its taxonomy/verdict is not
accepted: it fabricates TSMIS zeros for P/V, labels them shared, and injects the
59-point no-linework display metric as TSMIS-only. Accordingly
`source_truth_exact=true`, `production_value_projection_exact=true`, and
`stage8_base_oracle_complete=true`, while `production_comparison_semantics_exact=false`
and `comparison_end_to_end_perfect=false`. Two complete source-bound runs reproduced the
result and detached acceptance byte-for-byte. Existing CMP-AUD-019/020/024/025/071/076/
146 remain product-red; no semantic omission was excused.

## Required next gates

1. Keep the now-green exact-one/D01-D12 source, complete ordered schema, literal-cell,
   mandatory claim, immutable-snapshot parsing, content-manifest reuse, commit-time
   source/cancellation, explicit completion, and attempt-isolation gates permanent.
2. Keep the accepted r7 current-code production witness and r2 semantic baseline bound;
   r3/r4/r5/r6 directories remain rejected partial evidence.
3. Retain all seven accepted Stage-6 family audits and their exact raw/normalized,
   mutation, module, replay, and detached-acceptance bindings.
4. Retain the accepted Ramp/Intersection/Highway Detail XLSX-to-evidence-PDF permanent
   gates. Their explicit Excel-row-to-PDF-record, category, and layered-section maps,
   source dates, render equivalences, and exact delta classifications are the oracles for
   later normalization, evidence location, and Report View hierarchy.
5. Retain all seven accepted Stage-8 base audits and their independent cell/count/source
   bindings. Stage 9 must close the current companion PDF/Excel legs and version-pinned
   historical editions without mixing dates; product corrections remain Stage 11 work.
6. In Stage 10, reproduce every one of the five evidence families from both source PDFs
   and the Comparison sheet with zero unexplained discrepancy before evidence acceptance.
