# Stage 6 Intersection/Highway Detail conservation specification

This is an implementation hand-off for the independent Stage 6 oracles. It is
not a production schema and must not be imported by application code. The
oracles must use `phase3_xlsx_stream.py` and must not import any production
loader, normalizer, comparator, evidence adapter, or family constants.

## Frozen bindings

| Family | Raw source | Raw binding | Normalized r7 binding |
|---|---|---|---|
| Intersection Detail | `Sheet 1`, 36 columns, 16,626 rows | 2,920,705 bytes; `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2` | v3; sheet `Intersection Detail (TSN)`; 2,084,691 bytes; `d4609c3afb8663dd89e6e2e00103d41245a0213d7e4e08fb63e961bc4035b37b`; 16,626 rows x 36 columns |
| Highway Detail | `Sheet 1`, 56 columns, 60,083 rows | 16,356,075 bytes; `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1` | v2; sheet `Highway Detail (TSN)`; 8,478,589 bytes; `46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5`; 60,083 rows x 38 columns |

Each workbook must contain exactly the one visible sheet named above. Formula
or error cells in a required header or data cell are inadmissible. Bind exact
ordinary-file identity and SHA-256 before, during, and after both topology and
worksheet reads.

## Intersection Detail

### Exact schemas

Raw header, in order:

```text
PP, POST_MILE, LOCATION, DATE_REC, HG, CITY_CODE, RU,
EFF_DATE_INT, TY_INT, EFF_DATE_CT, TY_CT, EFF_DATE_LT, LT_TY,
EFF_DATE_ML, MAIN_SM, MAIN_LC, MAIN_RC, MAIN_TF, MAIN_NL,
X_CROSS_OVERRIDE, MAIN_EFF_DATE, MAIN_ADT, DESCRIPTION,
MAIN_OVERRIDE, CROSS_BEGIN_DATE, CS_SM, CS_LC, CS_RC, CS_TF,
CS_NL, EFF_DATE, CROSS_ADT, CROSS_ROUTE_NAME, CROSS_PM_PREFIX,
CROSS_POSTMILE, CROSS_PM_SUFFIX
```

Normalized header, in order:

```text
Route, PR, Route Suffix, PM, Date of Record, HG, City Code, R/U,
INT Type Eff-Date, INT Type, Control Type Eff-Date, Control Type,
Lighting Eff-Date, Lighting, ML Eff-Date, ML Mastarm, ML Left Chan,
ML Right Chan, ML Traffic Flow, ML Num Lanes, Description,
Main Line Length, CS Eff-Date, CS Mastarm, CS Left Chan,
CS Right Chan, CS Traffic Flow, CS Num Lanes, Int St Eff-Date,
Intrte Route, Intrte PM Prefix, Intrte Postmile, Intrte PM Suffix,
Xing Line Lgth, TSN District, TSN County
```

### Raw-field dispositions

Every raw field has one primary disposition. `source_only` means its typed
ordered/multiset digests remain mandatory even though the current normalized
workbook does not carry it.

| Raw field | Disposition | Normalized target / independent rule |
|---|---|---|
| `PP` | projected | `PR`, type-preserving scalar |
| `POST_MILE` | composed | `PM`; trim, preserve sign, remove only leading zeroes, retain `0` and decimal fraction |
| `LOCATION` | composed | strict `DD COUNTY[.] RRR[SFX]`; emit 3-digit base `Route`, `Route Suffix`, two-digit `TSN District`, period-free `TSN County` |
| `DATE_REC` | composed | `Date of Record`, ISO `YYYY-MM-DD` |
| `HG` | projected | `HG` |
| `CITY_CODE` | projected | `City Code` |
| `RU` | projected | `R/U` |
| `EFF_DATE_INT` | composed | `INT Type Eff-Date`, ISO date |
| `TY_INT` | projected | `INT Type` |
| `EFF_DATE_CT` | composed | `Control Type Eff-Date`, ISO date |
| `TY_CT` | composed | `Control Type`; only J/K/L/M/N/P/S fold to `S` |
| `EFF_DATE_LT` | composed | `Lighting Eff-Date`, ISO date |
| `LT_TY` | composed | `Lighting`; Y/1 -> Y, N/0 -> N, numeric zero must not become blank |
| `EFF_DATE_ML` | composed | `ML Eff-Date`, ISO date |
| `MAIN_SM` | composed | `ML Mastarm`, Boolean fold above |
| `MAIN_LC` | projected | `ML Left Chan` |
| `MAIN_RC` | composed | `ML Right Chan`, Boolean fold above |
| `MAIN_TF` | projected | `ML Traffic Flow` |
| `MAIN_NL` | projected | `ML Num Lanes`; do not invent numeric coercion |
| `X_CROSS_OVERRIDE` | composed | `Xing Line Lgth`, canonical number with insignificant padding removed |
| `MAIN_EFF_DATE` | source_only | TSN-only second mainline effective date; currently absent from normalized bytes |
| `MAIN_ADT` | source_only | TSN-only mainline ADT; currently absent from normalized bytes |
| `DESCRIPTION` | projected | `Description`; preserve text/quotation characters |
| `MAIN_OVERRIDE` | composed | `Main Line Length`, canonical number |
| `CROSS_BEGIN_DATE` | composed | `CS Eff-Date`, ISO date |
| `CS_SM` | composed | `CS Mastarm`, Boolean fold above |
| `CS_LC` | projected | `CS Left Chan` |
| `CS_RC` | composed | `CS Right Chan`, Boolean fold above |
| `CS_TF` | projected | `CS Traffic Flow` |
| `CS_NL` | projected | `CS Num Lanes`; do not invent numeric coercion |
| `EFF_DATE` | composed | `Int St Eff-Date`, ISO date |
| `CROSS_ADT` | source_only | TSN-only cross-street ADT; currently absent from normalized bytes |
| `CROSS_ROUTE_NAME` | composed | `Intrte Route`, canonical number |
| `CROSS_PM_PREFIX` | projected | `Intrte PM Prefix` |
| `CROSS_POSTMILE` | composed | `Intrte Postmile`, canonical number |
| `CROSS_PM_SUFFIX` | projected | `Intrte PM Suffix` |

Numeric canon accepts only a signed decimal lexical value, removes leading
integer zeroes and trailing fractional zeroes, and preserves a real zero as
`0`. Date canon accepts typed dates, `MM/DD/YYYY`, `YYYY-MM-DD[ time]`, and
two-digit `YY-MM-DD` with the explicit 30-year window (00-29 -> 2000-2029;
30-99 -> 1930-1999). Unknown domains must be listed as anomalies rather than
silently generalized from production behavior.

### Identity, multiplicity, and order

- Source identity is base route + county + complete `PP` + numeric
  `POST_MILE`. District and route suffix are separately retained claims and
  participate in the lossless identity digest.
- The frozen source has 16,611 unique physical identities and 15
  same-identity/nonidentical duplicate groups (30 rows). Similarity pairing is
  not part of Stage 6: raw occurrence order must be preserved exactly in the
  normalized workbook.
- Six within-county weak-key collisions must remain distinct:
  `101/SF/5.450` (blank/M), `115/IMP/9.540` (blank/L),
  `132/STA/15.340` (blank/L), `132/STA/15.620` (blank/L),
  `184/KER/0.000` (blank/L), and `218/MON/0.340` (blank/L).
- Record weaker-key diagnostics: route+numeric-PM has 78 multi-county keys / 156
  county identities; complete PP+PM has 71 / 142.
- The independently projected row sequence must equal normalized rows both as
  an ordered typed digest and a typed multiset digest. The physical-identity
  multiplicity counter must also be exact.

### Product gap to report red

`compare_intersection_detail_tsn._tsn_onesided()` intentionally returns no data
when its input is the normalized library. Consequently `MAIN_EFF_DATE`,
`MAIN_ADT`, and `CROSS_ADT` appear blank in Report View on the canonical Matrix
path even though all three are present in the authoritative XLSX and its TSN
print. Exact projection may be green, but full Stage 6 conservation is not green
until these facts are retained in the normalized representation (hidden columns
are sufficient) or an equally immutable source-bound mechanism supplies them.

## Highway Detail

### Exact schemas

Raw header, in order:

```text
THY_ID, DIST, CNTY, RTE, RTE_SFX, DIST_CNTY_ROUTE, PP, POSTMILE,
E_IND, LENGTH, REC_DATE, HG, AC, ACC_SIG, ACC_EFF_DATE, CITY,
POP_CODE, BEG_DATE, ADT_AMT, PROFILE, BREAK_DESC, LK_BACK_ADT,
CHNGMILE, DVM, DESCRIPTION, NON_ADD, LT_SIG, L_EFF_DATE, L_ST,
L_NO_LANES, L_SF, L_OT_TOT, L_OT_TR, L_TR_WID, L_IN_TOT,
L_IN_TR, MED_SIG, M_EFF_DATE, M_TYPE_CODE, M_CL, M_BA, M_WID,
M_VA, RT_SIG, R_EFF_DATE, R_ST, R_NO_LANES, R_SF, R_IN_TOT,
R_IN_TR, R_TR_WID, R_OT_TOT, R_OT_TR, SEG_ORDER_ID,
REFERENCE_DATE, EXTRACT_DATE
```

Normalized header, in order:

```text
Route, Post Mile, PS, Length, Date of Rec, HG, AC, Acc-Cont Eff,
City, RU, RU Eff, Description, NA, LB Eff, LB S/T, LB #Ln,
LB S/F, LB OT-TO, LB OT-TR, LB Wid, LB IN-TO, LB IN-TR,
Med Eff, Med T, Med C, Med B, Med V/WDA, RB Eff, RB S/T,
RB #Ln, RB S/F, RB IN-TO, RB IN-TR, RB Wid, RB OT-TO,
RB OT-TR, TSN District, TSN County
```

### Raw-field dispositions

| Raw field(s) | Disposition | Normalized target / independent rule |
|---|---|---|
| `THY_ID` | source_only | database surrogate identifier |
| `DIST` | projected | `TSN District` |
| `CNTY` | projected | `TSN County`, trailing period removed only if present |
| `RTE` + `RTE_SFX` | composed | `Route`, 3-digit base plus uppercase suffix |
| `DIST_CNTY_ROUTE` | relational | assert exact consistency with DIST/CNTY/RTE/RTE_SFX and digest the raw literal |
| `PP` + `POSTMILE` | composed | `Post Mile` = prefix + fixed `MMM.mmm` + roadbed claim supplied by the separately retained `HG` field |
| `E_IND` | composed | `PS`; E -> E, otherwise blank |
| `LENGTH` | composed | `Length`, fixed `000.000` rounded to three decimals |
| `REC_DATE` | composed | `Date of Rec`, datetime -> `YY-MM-DD`, otherwise stripped source text |
| `HG` | projected + relational contributor | `HG`; L/R also supplies the roadbed claim in canonical `Post Mile` |
| `AC` | projected | `AC` |
| `ACC_SIG` | source_only | printed access-control change flag; absent from normalized bytes |
| `ACC_EFF_DATE` | composed | `Acc-Cont Eff`, date rule above |
| `CITY` | projected | `City` |
| `POP_CODE` | projected | `RU` |
| `BEG_DATE` | composed | `RU Eff`, date rule above; semantic slot is TSN ADT begin year |
| `ADT_AMT` | source_only | Report View/evidence `LK-AHD`; absent from normalized bytes |
| `PROFILE` | source_only | Report View/evidence `P`; absent from normalized bytes |
| `BREAK_DESC` | source_only | internal break helper; not separately printed |
| `LK_BACK_ADT` | source_only | Report View/evidence `LK-BACK`; absent from normalized bytes |
| `CHNGMILE` | source_only | Report View/evidence `CHG/MILE`; absent from normalized bytes |
| `DVM` | source_only | Report View/evidence `DVM`; absent from normalized bytes |
| `DESCRIPTION` | composed | `Description`, trim and collapse Unicode `\s` whitespace runs |
| `NON_ADD` | composed | `NA`; source `A` -> blank, other claims retained |
| `LT_SIG` | source_only | printed left-roadbed change flag; absent from normalized bytes |
| `L_EFF_DATE` | composed | `LB Eff`, date rule |
| `L_ST` | projected | `LB S/T` |
| `L_NO_LANES` | composed | `LB #Ln`, digit text -> unpadded integer text |
| `L_SF` | projected | `LB S/F` |
| `L_OT_TOT` | composed | `LB OT-TO`, unpadded numeric text |
| `L_OT_TR` | composed | `LB OT-TR`, unpadded numeric text |
| `L_TR_WID` | composed | `LB Wid`, unpadded numeric text |
| `L_IN_TOT` | composed | `LB IN-TO`, unpadded numeric text |
| `L_IN_TR` | composed | `LB IN-TR`, unpadded numeric text |
| `MED_SIG` | source_only | printed median change flag; absent from normalized bytes |
| `M_EFF_DATE` | composed | `Med Eff`, date rule |
| `M_TYPE_CODE` | projected | `Med T` |
| `M_CL` | projected | `Med C` |
| `M_BA` | projected | `Med B` |
| `M_WID` + `M_VA` | composed | `Med V/WDA`, two-digit width plus uppercase variance code |
| `RT_SIG` | source_only | printed right-roadbed change flag; absent from normalized bytes |
| `R_EFF_DATE` | composed | `RB Eff`, date rule |
| `R_ST` | projected | `RB S/T` |
| `R_NO_LANES` | composed | `RB #Ln`, unpadded numeric text |
| `R_SF` | projected | `RB S/F` |
| `R_IN_TOT` | composed | `RB IN-TO`, unpadded numeric text |
| `R_IN_TR` | composed | `RB IN-TR`, unpadded numeric text |
| `R_TR_WID` | composed | `RB Wid`, unpadded numeric text |
| `R_OT_TOT` | composed | `RB OT-TO`, unpadded numeric text |
| `R_OT_TR` | composed | `RB OT-TR`, unpadded numeric text |
| `SEG_ORDER_ID` | relational | bind typed value and assert normalized source order / within-DCR order; not printed as text |
| `REFERENCE_DATE` | source_only metadata | exact singleton `2025-09-08` |
| `EXTRACT_DATE` | source_only metadata | exact singleton `2025-09-15` |

All emitted Highway Detail normalized values are text claims; a real numeric zero
must become `0`, not blank. Unknown numeric/date/code shapes are anomalies and do
not receive a permissive new normalization automatically.

### Identity, multiplicity, and order

- Full source claim: district, county, route base, route suffix, PP, numeric
  postmile, equation claim, and roadbed claim (HG L/R). Retain a 1-based source
  occurrence for duplicate diagnostics.
- The accepted independent source-format oracle finds 77 nonidentical physical
  collision groups / 156 rows: 76 groups of two and one group of four. This is
  the stronger identity above. The older documentation phrase “86 full-identity
  duplicate groups” used county + route token + PP + numeric postmile + roadbed,
  omitting both district and equation claim; it produces 86 groups / 174 rows.
  Retaining district but still omitting equation produces 83 groups / 168 rows.
  These independently recomputed weaker probes must be named exactly rather than
  frozen as the full physical-identity count.
- Weaker diagnostics remain required: `(RTE+RTE_SFX, production canonical PM)`
  has 438 multi-county keys / 976 county identities; base RTE+PP+POSTMILE has
  453 / 1,008. Neither can pair rows safely without county.
- Raw row order must be reproduced exactly by normalized rows. Separately assert
  nondecreasing `SEG_ORDER_ID` within each DCR or emit every exception as an
  anomaly. A reordered duplicate group must fail the ordered digest even when
  its multiset remains equal.
- Ordered typed row digest, typed multiset row digest, per-field ordered and
  multiset typed digests, full identity multiplicity, route/county/district
  census, and anomaly manifest are all mandatory.

### Product gaps to report red/review

`compare_highway_detail_tsn._tsn_onesided()` returns no data for a normalized
library. The canonical Matrix path therefore blanks DCR plus `ADT_AMT`,
`PROFILE`, `LK_BACK_ADT`, `CHNGMILE`, and `DVM` in Report View. The normalized
schema also omits all four printed change flags. These are source/evidence facts,
not harmless database-only columns, so exact visible projection is not full
conservation. `THY_ID`, `BREAK_DESC`, uniform source dates, and `SEG_ORDER_ID`
may remain explicitly source-only if their typed digests and relational/order
assertions stay permanent; they may not silently disappear from the audit.

Highway Detail TSN is authoritative. No Stage 6 rule may infer a county for the
vendor-pending TSMIS Excel export; that later comparison flavor remains blocked
until it has an authoritative county claim.

## Required mutation probes for both families

1. Source SHA/size, sheet name/visibility, exact header order, extra/duplicate
   header, formula/error cell, and preserved-mtime source replacement.
2. Raw row deletion, insertion, duplicate, reorder, same-text cross-type change,
   and one projected-cell mutation.
3. Normalized row deletion, insertion, duplicate, reorder, header/tail-sidecar
   mutation, and a projected-cell mutation.
4. Source-only field mutation: raw typed digest must change while the visible
   projection remains blind; the result must report that blind spot rather than
   calling full conservation green.
5. County swap inside a known weak route/PM collision; ID PP-only variant;
   HD equation and HG-roadbed variants; duplicate occurrence insert/reorder.
6. Numeric zero versus blank, Boolean zero versus blank (ID), leading/trailing
   zeroes, two-digit date 29/30 boundary, malformed LOCATION/DCR relation, and
   HD M_WID/M_VA composition.
7. Token/source revalidation immediately before result acceptance and after the
   result bytes are written; A-to-B-to-A content interposition must fail.

Projection parity and full conservation are separate booleans. An oracle can
prove that production emitted exactly what its current schema requests while
still returning `stage6_family_complete = false` for a documented source fact
that the normalized representation loses.
