# Comparison-perfection — plan to completion

**This is the single "you are here" surface for the project.** Read this first. The old
sprawl of status/handoff/reconciliation docs is retired to [archive/](archive/README.md);
the living data ledgers are listed under [Reference](#reference) below.

---

## 1. YOU ARE HERE

_Updated 2026-07-16._

```
Phase:  0 ── 1 ── 2 ── 3 ── 4 ── 5 ── 6 ── 7 ── 8 ── 9 ── 10
        ✅   ✅   ✅   🔨   ⬜   🟨   🟨   ⬜   🟨   ⬜   ⬜
        └───── done ─────┘  └── you are here ──┘        └ release ┘
        ✅ done   🔨 in progress   🟨 code built, proof incomplete   ⬜ not started
```

| | |
|---|---|
| **Branch** | `comparison-perfection` — pushed to origin, **CI green** |
| **Gate** | 121/121 offline checks + ruff(scripts) + byte-compile green; **identity gate 10 green / 0 known-red** (CMP-AUD-045 fully promoted) |
| **Audit floor** | Stage 6 (raw→normalized) **7/7**; Stage 8 base (TSMIS-vs-TSN) **7/7** — all seven witnesses hash-verified on disk |
| **Findings** | 238 total · **Resolved this takeover: 238, 024/025, 020–023, 184, 183, 144–146, 076, 135, 185, 155/156/158/159, 199, 204**; 045 RD+ID+HSL integrated & corpus-verified (HL/HD blocked); 098 pipeline half; 133/115/035 partial |
| **Next action** | **CMP-AUD-220 — owner-APPROVED 2026-07-16** (assignment/verdict split; approval recorded in the D3 gate doc; compare_core batch + all-family re-bless), then **218** (Spot Check independence, brief staged), then the 197 vs-TSN remainder. **DONE 2026-07-16: the same-source render-artifact fix** (owner-reported ID PDF↔Excel false positives; ID/RD/HSL corpus-verified). HL needs its county census first, HD-Excel vendor-pending |

> ### ▶ RESUME HERE (2026-07-16, after the Highway Sequence family batch)
> **DONE this batch — the whole HSL family in one commit
> (CMP-AUD-045-HSL / 155 / 156 / 158 / 159 / 199 / 204):**
> - **Normalizer v4** (`consolidate_tsn_highway_sequence`, catalog bump 3→4 + a
>   `TSN Normalization` marker sheet the loader gates on): pointer distance tokens
>   verbatim with a refusal on any foreign token (156), the 46 pre-county equates
>   conserved with their blank County (158), single-space wrap joins (159), and the
>   CMP-AUD-155 claims capture (cover NOTE policy + identity band exactly-once per
>   document; per-route directions with conflict refusal; `_cross_member_claims`
>   refuses a member from a different pull) riding `producer_extra` → sidecar →
>   per-run Notes via `_schema_with_claims`.
> - **Typed identity everywhere** (045): `_physical_pm_key` — canonical
>   (Route, County, complete GLUED postmile "R001.000E"; the one family whose
>   canonical keeps the suffix), reserved `"(county not printed)"` /
>   `"(no postmile printed)"` markers for the legitimately blank rows (46 TSN
>   annotations; 5 TSMIS PM-less rows per render — both corpus-proven), claims
>   lossless; wired into `_tsmis_row`, `_load_tsn` (v4-gated), the NEW same-source
>   loader, and `compare_env.HIGHWAY_SEQUENCE` via `physical_key_builder` (engages
>   only on the real shape: County named + PM flanked by the two UNNAMED columns;
>   else logs + falls back). **Both KNOWN_RED promoted → the identity gate is
>   10 green / 0 known-red.**
> - **CMP-AUD-199**: PDF-vs-Excel keys WITHOUT the suffix; "PM Suffix" is a compared
>   column; ALL columns asserted; descriptions verbatim both sides
>   (`compare_highway_sequence_pdf.SS_HEADER/_SS_SCHEMA/_tsmis_row_same_source`).
> - **CMP-AUD-204**: `_desc_plain` (TSN + same-source, verbatim) / `_desc_tsmis`
>   (own-route label only, canonical token compare, `.lstrip()` per 205's rule);
>   evidence projection side-aware.
> - **Corpus verify (ssor-prod 7.9 pair + the 12 bound raw PDFs)**: normalized
>   69,804 rows / 46 blank-county / 283+282 pointers / no comma / 154 prefixes /
>   directions {S-N 190, W-E 172, E-W 5, N-S 2}; all three leg SHAPES ==
>   `EXPECTED_CURRENT_LEGS` exactly; re-pairing the product-loaded rows under the
>   ORACLE's assignment objective reproduces every per-field count EXACTLY (+197's
>   four `_x000d_` cells unescaped) — and the live product's asserted deltas
>   (-7 = -10 Desc +3 FT Excel; -6 = -9 +3 PDF) equal CMP-AUD-220's own bound
>   reconciliation arithmetic digit for digit. Zero unexplained residue.
>
> **✅ CMP-AUD-220 UNBLOCKED (2026-07-16): the owner approved the recommendation**
> (*"Whatever you did is approved as long as it results in all correct
> comparisons"*) — the approval record is appended to the D3 gate doc
> (assignment/verdict split: the source-proven objective may drive ASSIGNMENT;
> counts/verdicts stay asserted-only). Implement it as the next compare_core
> batch per the memo below (all-family re-bless; the condition binds — every
> comparison must prove correct). The original memo, kept for its analysis:
> - **The conflict.** `comparison-phase3-decision-gates.md` fixed-architecture
>   item 5 (owner-approved 2026-07-12): *"Duplicate-pair cost is computed only from
>   the same asserting compared-cell equality state. Context/non-asserting cells
>   cannot influence assignment."* CMP-AUD-220 (verified Stage-8, AFTER that
>   approval) proves that objective changes WHICH physical occurrence pairs with
>   which relative to source truth in 445/448 Excel and 357/360 PDF HSL duplicate
>   groups, and its correction requirement mandates the source-proven objective —
>   the oracle's `(all-field diff count, character edit distance, |position gap|)`
>   for ASSIGNMENT while the VERDICT stays asserted-only ("pairing identity and
>   asserting verdict are separate decisions"). Both this batch's live measurement
>   and the finding's bound arithmetic agree digit-for-digit on the effect
>   (asserted −7 = −10 Desc +3 FT Excel; −6 = −9 +3 PDF vs the oracle).
> - **The options.** (A) Keep item 5 → the product's assignments stay a
>   permanently-attributed distance from source truth (the route-152-style
>   occurrence swaps stay possible wherever context distinguishes duplicates);
>   220 gets dispositioned "by approved design", contradicting its correction
>   requirement and the source-first rule. (B) Approve 220's split: context/source
>   fields MAY determine assignment (the oracle objective), counts stay
>   asserted-only — a compare_core-locked change + an all-family re-bless
>   (RD-79/ID-79 exact numbers, HL Route-1 969, all golden checks; HSL's asserted
>   counts MOVE to 5,589 / 5,001 / 3,721+4; this batch's scratchpad harnesses
>   `verify_hsl_corpus.py` / `verify_hsl_oracle_objective.py` are the re-verify
>   pattern). (C) Something narrower (e.g. per-family opt-in via CompareSchema).
> - **Recommendation: (B)** — the north star is "properly represent the data",
>   220's evidence is source-owned and exactly reconciled, and (B) preserves
>   item 5's real intent (context never inflates COUNTS) while fixing what it
>   got wrong (identity ≠ verdict). Costs: the Levenshtein cost component must be
>   profiled under the 100,000-cell cap; the typed trace/tie-break vocabulary
>   needs a deterministic extension (the oracle's position term already breaks
>   most ties); every family re-blesses.
> - **Until the owner appends an approval record to the D3 gate doc, do NOT touch
>   the pairing objective.** Work continues on the non-gated queue below.
>
> **Do this next: CMP-AUD-218 — Spot Check independence.** Censused 2026-07-16;
> implement as one fresh-context batch:
> - **The defect** (`compare_core._write_spot_check`, ~line 2074): Spot Check's
>   `$C$11` (status) and `$C$12`/`$F$12` (both data-sheet rows) are
>   `INDEX(Comparison!…, $C$6)` pulls, and EVERY field lookup rides those rows —
>   so a consistently-relinked wrong pair or a falsely one-sided status/link set
>   still shows six OKs (mutation-proven across all five legs in the finding).
> - **The design**: (1) add a hidden injective per-row TOKEN column to the
>   Comparison sheet (the row's `__CMP_E2_KEY_V1_<ordinal>` helper key as a
>   LITERAL, appended after the state chunks in BOTH twins —
>   `_write_comparison` ~1944 formulas branch AND values branch; the data
>   sheets' hidden `lay.key_col` column already carries the same tokens as
>   literals in both twins, which is what `_row_link` MATCHes, ~1435).
>   (2) Spot Check derives `T = INDEX(Comparison!<c_token>, $C$6)`, then the
>   INDEPENDENT rows `IFERROR(MATCH(T, <side>!$<key_col>:$<key_col>, 0), "")` —
>   `$C$12`/`$F$12` BECOME those independent cells (keep the addresses: golden
>   checks pin them; `check_compare_physical_identity` pins Spot `F7`), and
>   membership derives from `ISNUMBER(MATCH(...))` per side, NOT from
>   Comparison's status. (3) a new "Row integrity" line EXACT-compares
>   Comparison's claimed trow/nrow/status against the independent derivation
>   (OK/CHECK, loud CF); the one-sided callout + `independent_status` ride the
>   independent membership; the per-field K/L recomputation automatically
>   becomes truly independent once C12/F12 are.
> - **Blast radius to check while implementing**: `lay` construction
>   (~1178-1332) — append `c_token` cleanly after the state chunks (Comparison's
>   auto_filter/CF ranges end at `last_field_col`, so a hidden trailing column
>   is outside them, like the state chunks; keep it hidden);
>   `_write_snapshot_sheet` (~1905) + `_build_snapshot_freshness_expr` (~2665)
>   bind SOURCE sheets, not Comparison width — verify; Summary SELF-CHECK
>   COUNT formulas over Comparison columns (grep `SELF-CHECK`); `read_counts`
>   is label-based (safe); the Spot Check structural pins live in
>   `check_compare_audit` (~94) and `check_compare_equality_policy`
>   (~567-693 formula scans + ~762-886 the installed-Excel COM recalc model).
> - **The gate** (finding's acceptance): structural pins that C12/F12 MATCH the
>   token into the data sheets and never INDEX Comparison's row links; plus the
>   two mutation cases — a consistently RELINKED pair and a FALSE one-sided
>   status/link set — proven to say CHECK via installed-Excel
>   `CalculateFullRebuild` (the check_compare_equality_policy COM section is
>   the template, incl. its no-Excel skip behavior for CI).
> - **Canary discipline**: counts/status/display semantics must stay
>   byte-identical (Route-1 969; the RD/ID/HSL goldens; values↔formulas twin
>   parity) — this batch adds a hidden column + rewires Spot Check only.
>
> Then **CMP-AUD-197** (the `_x000d_` reader fix must be FAMILY-AWARE: HSL's
> oracle unescapes to CRLF≡space — the four Cactus City cells become equal — but
> RD-79's ACCEPTED oracle keeps its 4 `_x000d_` rows as honest PDF↔Excel
> differences; a blanket shared-reader unescape would break RD's re-bless).
> Then Wave 5 (127/130/131/118-120/214 + the unowned-findings triage).
> - HL stays BLOCKED on its raw county-retention + collision census; HD-Excel on
>   the vendor county answer. Do NOT infer either.
> - **CI discipline** (unchanged): verify the watched RUN ID belongs to the pushed
>   SHA; never `|| echo` over the exit code; fixture paths compare
>   RESOLVED-to-RESOLVED (8.3 short temp names); PYTHONIOENCODING=utf-8 for ` ≠ `.
>
> **DONE — Intersection Detail (2026-07-14): re-blessed against ID-79 EXACTLY** (all
> three legs incl. asserted cells; District+County asserted; v4 lib; identity gate
> 8 green / 2 known-red).
>
> **EARLIER — the ID brief (kept for its census):** (045-ID vs the accepted
> `ID-79` oracle). Tuple: **(base Route, County, complete PP, numeric Post Mile)** —
> unlike RD, the PREFIX is a key component (six within-county groups carry distinct PPs
> at one numeric PM); route SUFFIX / PR / District stay conserved claims. Re-bless
> targets (ars-prod 7.9 trees ×217 + raw `TSAR - INTERSECTION DETAIL_TSN.xlsx`):
> Excel vs raw TSN **16,199 / 260 / 427 · 146 identical / 16,053 differing / 21,676
> cells / 550,766 asserted**; PDF vs TSN same split / **21,683** cells; PDF↔Excel
> **16,459 · 16,450 / 9 · 9 cells** (8 tab-ending Excel Descriptions + the REAL
> `108/TUO/<blank>/5.87` HG defect — Excel `U` vs PDF+TSN `D`, stays visible);
> raw-vs-normalized 16,626 / 0. TSN has **15 exact duplicate groups (30 occurrences)**
> — the Hungarian pairing engages for real; persist the typed trace. NOTE the current
> product canary 21,675 ≠ the oracle's 21,676 (Excel) — expect the golden check's
> numbers to MOVE to the oracle's. Correct the ID KNOWN_RED glued expectation
> (`R1.000E` includes the suffix; the ID tuple has NO suffix — prefix+numeric-PM only)
> the same evidenced way as RD, then promote. Reuse the RD pattern: `_physical_pm_key`-
> style builder (canonical postmile = complete PP + numeric PM, e.g. `R1.000`?
> — derive the exact canonical string from the oracle script's identity, read
> `build/phase8_intersection_detail_comparison.py` FIRST — **census DONE
> 2026-07-14**: `physical_key = (route, county, complete_pp, numeric_pm)` with
> `_location` giving (district, county dot-stripped upper, base route `%03d`,
> suffix separate); `_numeric_pm` = Decimal canonical — `normalize_pm` →
> `Decimal.normalize()` `format 'f'`, trailing zeros + dot stripped, `0` for zero
> (so "005.870"→"5.87"); the engine's 3-component canonical postmile = complete
> PP + that Decimal form GLUED (e.g. "R5.87"; the ID KNOWN_RED's "R1.000E" is
> wrong twice: padded PM + suffix included). **NO edge-trimming in ID** — the 8
> trailing-tab Excel Descriptions are DATABASE data both Excel and raw TSN carry
> (equal on the Excel-vs-TSN leg without trimming; the 9 PDF↔Excel diffs = those
> 8 + the real 108/TUO HG defect, because the PDF render drops tabs) — do NOT
> copy RD's `_edge_text`. ID's normalizer is ALREADY conservation-exact
> (raw-vs-r7 16,626/0) and the v3 library already carries District/County
> sidecars + PR/Route Suffix in the shared width → likely NO
> `normalization_version` bump — the loaders just STOP SLICING the sidecar), the
> `EnvCompare.physical_key_builder` hook for the ID env adapter, and evidence
> adapter county-awareness (`evidence_intersection_detail`).
>
> **DONE — Ramp Detail (2026-07-14): re-blessed against RD-79 EXACTLY** (all three
> legs + every per-field count; 045-RD/135/185 resolved; 133 partial; lib v4).
>
> **EARLIER — the original Wave-4 brief (CMP-AUD-045 map):** Opening brief
> (censused 2026-07-14): the E2 typed-identity CORE is green; the four KNOWN_RED
> contracts in `check_compare_physical_identity` fail because projectors hand the engine
> plain route/PM strings. **Integration API:** each loader path emits its KEY CELL as a
> `comparison_contract.PhysicalKey` (with `physical_identity.canonical_components`, e.g.
> postmile/county) so `keys_for` keys become (route, PhysicalKey); the engine + Hungarian
> pairing already honor it (similarity pairing then runs only within genuine duplicates
> of the approved tuple). Promote each KNOWN_RED into TESTS as its family lands.
> **Approved tuples:** HSL route+county+complete glued PM (vs-TSN path already does this
> — the CROSS-ENV path doesn't); RD D4 `(Route, County, norm_pm(PM))` with PR/PM_SFX
> separately asserted; ID `(base Route, County, complete PP, numeric Post Mile)` with
> suffix/PR/District separately asserted. **Blocked (do NOT infer):** Highway Log needs
> its raw county claim retained + a collision census first; Highway Detail Excel is
> vendor-pending county. **Re-bless targets = the accepted Stage-8 oracles:** RD Excel
> 15,212 paired / 4 / 198 / 14,471 identical / 741 differing rows / 847 cells; RD PDF
> …774/998; PDF↔Excel 15,216 with exactly 4 Description renders; ID 16,199 / 260 / 427 /
> 16,053 / 21,675 cells / 518,368 asserting / 106 exact duplicate groups (production
> currently shows 15 false Description differences the oracle lacks). Real collision
> counts are bound in `comparison-phase4-red-fixture-index.md`. **Batch discipline (gate
> doc):** E2 runs focused adversarial fixtures + full gate + bound real-data canaries +
> installed-Excel `CalculateFullRebuild` parity before the next batch; test county
> resets, value swaps, prefix/suffix variants, real duplicate tuples, mid-list inserts
> on EVERY triangle edge. Start with **Ramp Detail** (smallest triangle, D4 approved,
> both oracle legs bound, County present in all its sources). **RD integration census
> (2026-07-14):** `PhysicalKey` is a str subclass (display = the source PM text; equality/
> hash/order ride `PhysicalIdentity(canonical_components=(("route",r),("county",c),
> ("postmile",norm_pm)), raw_claims=(RawIdentityClaim…,) non-empty, display auto)`) — the
> workbook writer + engine consume it transparently, and `check_compare_physical_identity`
> TESTS show green construction patterns. County per RD path: raw TSN `LOCATION`
> "01-DN-101" (the `_ROUTE_FROM_LOCATION` regex currently DISCARDS district+county);
> TSMIS consolidated position 1 Location "12 ORA 001" (currently unused in `_tsmis_row`);
> normalized library sidecar `["TSN District", "TSN County"]` after Route+SHARED_HEADER
> (indices 13/14 — `_normalized_row` currently slices to `[:13]`, exactly the finding's
> "loaders sliced them away"); the PDF flavor shares the positional consolidated shape
> (Location at 1). Cross-env RD is `EnvCompare(..., key_col="PM")` — generic, so the env
> path needs a per-report key-projection hook on EnvCompare (design carefully; it serves
> HSL too). Preserve PR/PM_SFX/District as raw claims, never key components. Re-bless =
> the RD Stage-8 oracle numbers above; also re-verify the RD evidence adapter (dual-row
> aware) after keys change, and promote the RD KNOWN_RED contract into TESTS.
>
> **DONE EARLIER — CMP-AUD-076 (durable cross-family comparison provenance).** 098's
> comparison half is DONE (2026-07-14: pre-read fingerprint capture recorded at all four
> record sites — Matrix env / vs-TSN+self / by-day / baseline; raced results
> auto-invalidate via `_fingerprint_for_record`; the formulas twin skips loudly on a
> mid-build change; CT-6d in `check_p2_freshness` locks it); 098's evidence-gate half
> rides Stage 10. **076 design notes (censused 2026-07-14):** the cited line numbers have
> drifted — the defects are (a) `run_files_compare`'s banner + `compare_core`'s Summary
> record only source BASENAMES (`A\same.xlsx` vs `B\same.xlsx` indistinguishable);
> (b) `compare_env` records folder basenames; (c) the outcome sidecar carries no recipe/
> selection/content identity. Build on what exists: `run_files_compare` already calls
> `artifact_store.capture_source_identities(...)` BEFORE loading (the capture seam), and
> the typed `ArtifactGeneration` already has `content_digests` + `producer_versions`
> mappings (FrozenMap since CMP-AUD-238) — the machine-readable home. Plan: persist
> {stable recipe key, role/side labels, canonical full selection, effective input
> identity + content fingerprint, producer metadata (input consolidation outcomes; the
> TSN sidecar identity/claims)} into (1) the typed generation record and (2) a small
> structured Provenance sheet appended to the comparison workbook (human-concise; NOTE:
> adds a sheet to EVERY comparison workbook — sweep golden checks that assert exact sheet
> lists, and mind `compare_core` correctness-locked semantics: content additive only).
> Mutation tests required: same basenames in different dirs, copies, aliases, moved
> files, folder discoveries with overlapping members. Seam facts (censused):
> `capture_source_identities` records INODE identity only (`_stat_identity` — no content
> digest; the exact gap 076 names), and `artifact_store.fingerprint(folder)` is a
> (name,size,mtime_ns) METADATA identity — for file-kind comparisons persist a real
> sha256 (the loaders read the whole file anyway); for folder-kind, the member census +
> metadata fingerprint is the proportionate record (state the distinction honestly in
> the ledger). 183/184 are Resolved. 183 follow-ups parked: matrix auto-rebuild when a consolidated
> workbook lacks a route census (then harden census-required), typed-contract census
> surfacing (Phase-5/7 overlay), and Ramp's own universe contract (CMP-AUD-071).
> - **Method (mandatory, proven):** (1) read the finding; (2) red fixture confirmed RED on
>   current code; (3) fix; (4) GREEN; (5) **verify against the real corpus** and, for anything
>   touching Ramp/Intersection Summary counts, **re-confirm the accepted oracles hold**
>   (Ramp Summary vs TSN MUST stay **29 shared / 2 TSN-only / 0 TSMIS-only / 5 identical /
>   24 differing**; Intersection Summary MUST stay **58 shared / 8 TSMIS-only / 0 TSN-only /
>   5 identical / 53 differing**, totals TSMIS 16,459 / TSN 16,626);
>   (6) local gate `build/.venv/Scripts/python.exe build/run_checks.py -j 4 -k` **AND**
>   `uvx ruff check scripts --select E9,F63,F7,F82,F811,F401`; (7) commit + push + `gh run watch`.
> - **Owner directive (2026-07-14):** *one-sided fields are EXPECTED and CORRECT.* Categories in
>   one summary but not the other (e.g. P/V only in TSN, TSMIS-only intersection codes) must be
>   represented as `Only in …`, **not** eliminated and **not** fabricated as zero-vs-count. Goal
>   is faithful representation, not forcing symmetry.
> - **Real inputs:** Ramp Summary — `Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ssor-prod\consolidated\tsar_ramp_summary_consolidated 2026-07-09 ssor-prod.xlsx`
>   vs `Downloads\TSMIS\tsn_library\ramp_summary\raw\Ramp Summary Statewide_TSN.pdf`.
>   Intersection Summary — consolidate the ars-prod 217-route tree
>   `Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ars-prod\intersection_summary\`
>   into a scratchpad workbook (the ground truth deliberately keeps no generated
>   consolidations) vs `Downloads\TSMIS\tsn_library\intersection_summary\raw\Intersection Summary Statewide_TSN.pdf`.
> - **Traps:** CI is Windows two-drive (D: checkout, C: temp) — no cross-drive `relpath`/cwd;
>   ruff is NOT in `build/.venv` (use `uvx`); `build/` has non-blocking F401s (ignore); the
>   `check_phase*` audit instruments are excluded from the gate on purpose; console prints of
>   comparison cells need `PYTHONIOENCODING=utf-8` (the ` ≠ ` marker breaks cp1252).
> - After the IS reds: the bigger structural findings (Wave 3: CMP-AUD-098 source-capture
>   digests; Wave 4: 045 PhysicalKey integration, 220, 218, 199, 197). Full sequence + external
>   gates in the sections below.

**What "you are here" means honestly:** the recovered engine rewrite already *implements*
much of the Phase 3–8 machinery (typed contracts, identity infra, ownership, transactional
publication), and it is committed and regression-green. What is **not** done is
*integration* (physical identity into the family projectors), *correction* (the open
semantic + contract findings), *proof* (per-finding red→green and evidence end-to-end),
and *acceptance* (the release gate). Regression-green ≠ comparison-perfect.

---

## 2. What "complete" means

Completion = **Phase 10, Tier 5 green** (from [comparison-remediation-plan.md](comparison-remediation-plan.md)):

- all 122 open findings resolved (red fixture before → green after → owning family gate green);
- all **29 classic recipes**, **30 Matrix placements**, **5 evidence families** green;
- both workbook modes, installed-Excel twins, cancellation/publication recovery;
- raw-source → normalized → comparison-cell → evidence-PDF conservation proven end-to-end;
- real-source canaries + **work-PC acceptance** pass.

Anything short of that is progress, not completion. "Audit complete" (where we are) means
source truth and current product projection were *classified* — the acceptances literally
record `stage8_family_accepted: false`.

---

## 3. The phase map

Detailed per-phase work is in [comparison-remediation-plan.md](comparison-remediation-plan.md); this is the state overlay.

| Phase | Scope | State | What remains |
|---:|---|---|---|
| 0 | Freeze reproductions, record decisions | ✅ done | — |
| 1 | Safety containment (S1–S5) | ✅ done | — |
| 2 | Typed contracts & truthful outcomes | ✅ done | — |
| 3 | One equality + identity engine (E1, E2) | 🔨 E1 done; **E2 infra built, 045 not integrated** | Integrate `PhysicalKey` into every family projector → **Wave 4** |
| 4 | Validated loaders, one family per batch (L0a–L7) | ⬜ not started | The bulk of family remediation → **Waves 2, 4** + later batches |
| 5 | One artifact-identity epoch | 🟨 code built, unproven | Prove/accept persisted schemas, migration, exact-generation evidence |
| 6 | Shared Matrix orchestration | 🟨 code built, partial | Attempt/ownership lifecycle, date/source truth, cache integration proof |
| 7 | Secondary views + **evidence** (Stage 10) | ⬜ not started | Evidence end-to-end proof for all 5 families; Report-View parity |
| 8 | Validation & evidence bundles | 🟨 partial | Coverage/readiness, truthful outcomes, bundle accounting |
| 9 | Classic UI, taxonomy, docs | ⬜ not started | **Most of the 78 unowned findings** live here |
| 10 | Acceptance & release gate (Tiers 1–5) | ⬜ not started | The final proof; needs the work PC + real corpus |

---

## 4. Codex review outcome (2026-07-14, verified against code)

An independent three-pass adversarial review of the engine diff. Every actionable claim
was re-verified against the source before acceptance.

| Finding | P | Status | Essence |
|---|---|---|---|
| CMP-AUD-045 | 1 | reconfirmed | `PhysicalKey` not integrated into any family projector — the 4 documented-red gate contracts |
| CMP-AUD-098 (+076/080) | 1 | verified | Generic source capture binds `(dev,inode)`, not bytes — same-inode / A→B→A edits pass "source-current" |
| CMP-AUD-115 | 1 | verified | Typed contract accepts impossible truth (asserted≠differing unchecked; a diff with no differences; trace indices unbounded by the source population) |
| CMP-AUD-220 | 1 | reconfirmed | Duplicate pairing optimizes asserted differences, not occurrence/source identity (the frozen objective) |
| CMP-AUD-218 | 1 | reconfirmed | Spot Check imports status + row links from Comparison — not independent |
| CMP-AUD-035 | 2 | **reopened** | Cert validation not type-exact (`1.0`/`True` alias ints); direct TSN builders lack a post-`os.replace` recheck |
| **CMP-AUD-238** | 2 | **new** | Public decoder permissive (`NaN`, dup keys, unknown fields); `frozen=True` objects shallowly mutable |
| ACL lease-leak | — | **disproved** | The 3 locked dirs are audit residue (protected DACLs omit the sandbox ACE); no product lease defect. Closes against CMP-AUD-203/236 |

Confirmed-still-open P2s: CMP-AUD-127, 130, 131, 118/119/120, 214. Qualified passes:
Hungarian solver, schema-v3 decode/chunk/generation binding, UTF-16 path limits, the TSN
library capture path.

---

## 5. Execution waves (the near term)

Ordered by dependency and risk. The principle: **harden the trust model before making
semantic corrections**, so every later red→green proof is enforced by a contract that
actually rejects impossible states.

### Wave 0 — record the review _(docs only, no code)_
Add CMP-AUD-238 (new) and reopen CMP-AUD-035 in [the ledger](comparison-audit-findings.md); record the ACL disproof against CMP-AUD-203/236. Update the [red-fixture index](comparison-phase4-red-fixture-index.md).

### Wave 1 — contract & validation hardening _(no count change, no canary re-bless · low risk)_
| Finding | Files | Fix | Guard |
|---|---|---|---|
| CMP-AUD-115 | `comparison_contract.py` | 3 missing invariants: asserted+context vs differing_cells; diff-requires-a-difference; trace indices bounded by source population | replay real persisted E2 traces + fix the gate's own out-of-range fixture first |
| CMP-AUD-238 | `comparison_contract.py` | strict `from_json`/`from_dict` (reject NaN/Inf, dup keys, unknown envelope fields); `MappingProxyType` for true immutability | round-trip existing sidecars through the stricter decoder |
| CMP-AUD-035a | `tsn_district_contract.py`, `tsn_library.py` | type-exact cert/manifest validation | replay accepted certs |
| CMP-AUD-035b | `consolidate_tsn_highway_sequence.py`, `consolidate_tsn_highway_log.py` | post-`os.replace` raw-source recheck (TOCTOU) | direct-builder fixture |

### Wave 2 — first semantic fix _(re-blesses 1 canary · low risk)_
**CMP-AUD-024/025 — Ramp Summary vs TSN.** Accepted, replayed oracle (29 shared / 2 TSN-only / 0 TSMIS-only / 5 identical / 24 differing). One comparator, 31 rows, no evidence family, no Report View. Pre: fabricated `0` for P/V + the 59-pt metric in the verdict universe → post: P/V as TSN-only, metric removed.

### Wave 3 — provenance / capture integrity _(medium risk)_
**CMP-AUD-098 (+076/080).** Generic source capture binds content digests, not just inode; thread `source_identities` through `run_compare`; update the gate that expects `source_identities == []`.

### Wave 4 — structural identity + pairing + spot-check _(re-blesses canaries across families · heaviest)_
**CMP-AUD-045** (PhysicalKey into all family projectors → promotes the 4 documented-red contracts to green) · **CMP-AUD-220** (pairing objective → occurrence/source identity) · **CMP-AUD-218** (Spot Check independence) · then **CMP-AUD-199** (HSL PDF↔Excel identity) · **CMP-AUD-197** (shared-reader CRLF, global). Done together with full oracle re-bless. This retires the "121/121 has 4 documented-red" asterisk.

### Wave 5 — confirmed-P2 cleanup + triage
CMP-AUD-127, 130, 131, 118/119/120, 214; then **triage the 78 unowned `Verified` findings** into owners and rewrite the ledger's status column (it currently conflates audit-harness "remediated" with product "remediated" — 48 strings against a declared 5).

---

## 6. The back half (Phases 5–10 → completion)

Beyond the waves, completion requires (further out, so less granular here):

- **Phase 4 (rest):** the remaining loader families L1–L7 (each: validated loader, red fixture → green, family gate).
- **Phase 5–6:** prove/accept the artifact-identity epoch and Matrix orchestration the recovered code already drafts.
- **Phase 7 / Stage 10 — evidence end-to-end:** all 5 evidence families proven raw→normalized→comparison-cell→image→Report-View with zero unexplained residue. **This defines what "correct evidence" is and must precede any evidence-image change** (CMP-AUD-208/209/210/214/218). Blocked findings wait here.
- **Phase 8:** validation & evidence bundles, coverage/readiness, bundle accounting.
- **Phase 9:** classic UI, taxonomy, docs — where most of the 78 unowned findings resolve.
- **Phase 10 — release gate (Tiers 1–5):** the final acceptance.

---

## 7. External dependencies — completion is not purely coding

These gate completion and are **not** in the implementer's control:

1. **Missing source files (Stage 9 / Phase 4).** Companion-format and historical-edition oracles need source pulls that may not all be on disk. Rule: *if a required source role is absent, stop and request the file* — never infer it.
2. **Highway Detail is vendor-provisional.** Its TSMIS layout is not vendor-finalized; it fail-closes on drift and may not reach "perfect-green" until Caltrans finalizes the format. External dependency, not a bug to code around.
3. **Work-PC-only acceptance (Phase 10 Tier 4/5).** Installed-Excel COM recalc, real-source canaries, and work-PC acceptance can only run on the locked-down Caltrans PC. The dev machine cannot self-certify these.

---

## 8. How we work (the discipline)

- **Per batch:** run the original red fixture *before* the change (record red) → apply → require green on the identical fixture → run the whole owning-family gate + all dependent placements. Never re-bless an unexplained count or cell delta.
- **Local gate before every push** (CI has bitten us twice): `build/run_checks.py -j 4 -k` **and** `uvx ruff check scripts --select E9,F63,F7,F82,F811,F401` **and** byte-compile. Ruff is not in `build/.venv` by design, so it must be run separately.
- **Honor the frozen invariants:** the approved semantics in [comparison-phase3-decision-gates.md](comparison-phase3-decision-gates.md) (D1–D7) and the correctness-locked `compare_core` contract. A confirmed global defect is fixed globally with exact evidence — never disguised as a per-report `CompareSchema` opt-in.
- **Source-first:** raw TSN under `Downloads\TSMIS\tsn_library` is truth; rebuild normalized inputs in isolation; a missing source fact is a hard stop.

---

## 9. Finding accounting

| Set | Count |
|---|---:|
| Total findings | 237 |
| Resolved | 53 |
| **Open (reproduced)** | **122** |
| — carried by the 7 family gates ("the 44") | 44 |
| — unowned `Verified` (mostly Phase 9) | 78 |

The "44" (7 gate sets, 51 with duplicates → 44 unique; CMP-AUD-045 alone spans 4 families)
is real but is **not** the whole debt — the 78 unowned findings are reproduced defects with
no family-gate owner yet. Wave 5 assigns them.

---

## <a id="reference"></a>10. Reference (living data — trust these over any prose)

| Document | Role |
|---|---|
| [comparison-audit-findings.md](comparison-audit-findings.md) | The 237-finding ledger (authoritative) |
| [comparison-canary-bindings.md](comparison-canary-bindings.md) | Exact sources, counts, result/acceptance hashes |
| [comparison-phase4-tsn-source-rebaseline.md](comparison-phase4-tsn-source-rebaseline.md) | Raw TSN roles, manifests, source facts |
| [comparison-phase3-decision-gates.md](comparison-phase3-decision-gates.md) | Approved comparison-engine semantics (D1–D7) |
| [comparison-phase4-red-fixture-index.md](comparison-phase4-red-fixture-index.md) | Finding → red-fixture / family-gate ownership |
| [comparison-remediation-plan.md](comparison-remediation-plan.md) | The detailed Phase 0–10 roadmap |
| [archive/](archive/README.md) | Retired status/handoff/reconciliation history |

---

## 11. Progress log (append-only — real progress, not recursion)

- **2026-07-16 — the same-source render-artifact fix (owner-reported; CMP-AUD-197's same-source half).** The owner reported eight "HILLCREST RD ≠ HILLCREST RD" Description false positives in an Intersection Detail PDF-vs-Excel workbook — byte inspection proved them the censused trailing-tab class (`'HILLCREST RD\t\t'`; Excel TRIM collapses spaces only, so tabs survived), which ID-79 had deliberately kept as honest byte differences. The owner ruled the class false positives; `compare_tsn_common.same_source_render_text` now applies render-artifact equivalence (OOXML `_xHHHH_` decode incl. `_x005F_` literals + edge-whitespace padding; PhysicalKey passthrough) at the load boundary of the three PDF-vs-Excel flavors ONLY — every vs-TSN leg keeps its oracle's byte semantics (pinned in `check_compare_tsn_common`). Corpus-verified: ID (ars-prod pair) 16,459/0/0 with exactly the one real 108/TUO HG defect left; RD (ssor-prod) 15,216/0/0 fully identical (the 4 `_x000d_` gone); HSL (ssor-prod) 1,410 rows / 3,721 cells == the Stage-8 oracle EXACTLY. The same owner reply approved the CMP-AUD-220 recommendation — the approval record (assignment/verdict split) is appended to the D3 gate doc; 220 is the next batch. Gate 121/121 + ruff clean.

- **2026-07-16 — Wave 4: the Highway Sequence family, one commit (CMP-AUD-045-HSL + 155 + 156 + 158 + 159 + 199 + 204 Resolved).** Normalizer v4 (catalog 3→4 + a `TSN Normalization` marker sheet the comparison loader gates on): the 565 printed pointer tokens conserved verbatim with a loud refusal on any foreign distance token; the 46 pre-county `EQUATES TO` annotations conserved with their blank County; wrapped descriptions joined on a single space (no invented comma); and the CMP-AUD-155 claims capture (cover reliability NOTE + identity fields exactly-once per document, per-route printed directions with conflict refusal, cross-member same-pull enforcement) riding `producer_extra` → the library sidecar → per-run Notes. Typed physical identity on every HSL path — canonical (Route, County, complete GLUED postmile "R001.000E"; verified against the Stage-8 oracle's `Row.identity` — HSL is the one family whose canonical keeps the equate suffix), with reserved `"(county not printed)"` / `"(no postmile printed)"` markers for the corpus-proven blank rows; both KNOWN_RED contracts promoted → **the CMP-AUD-045 identity gate is 10 green / 0 known-red**. CMP-AUD-199: PDF-vs-Excel got its own same-source profile (suffix OUT of identity, "PM Suffix" compared, every column asserted, descriptions verbatim) — 60,493/0/1 with PM Suffix 549 + HG 910 exact, the route-152 swap class structurally gone. CMP-AUD-204: TSN descriptions verbatim (154 numeric prefixes preserved); the TSMIS strip is own-route-token-only with 205's padding rule; evidence projection side-aware. Corpus verify: the v4 rebuild reproduced the bound census (69,804 rows; directions S-N 190 / W-E 172 / E-W 5 / N-S 2; one policy text), all three leg SHAPES equal `EXPECTED_CURRENT_LEGS` exactly, and re-pairing the product-loaded rows under the oracle's own assignment objective reproduces every per-field cell count EXACTLY — the live product's asserted deltas (-7 = -10 Desc + 3 FT Excel; -6 = -9 + 3 PDF) equal CMP-AUD-220's bound reconciliation arithmetic digit for digit, and the four `_x000d_` cells are 197's. Zero unexplained residue; next: 220 (shared assignment objective) → 218 → 197. Suite 121/121 + ruff clean.

- **2026-07-14 — Wave 4: the Intersection Detail family re-blessed against ID-79 EXACTLY (CMP-AUD-045-ID).** Every ID path keys on the accepted 4-part PhysicalKey (base route, county, complete PP inside the canonical postmile as PP+Decimal-PM, suffixes conserved as claims); District + County joined the compared header (the oracle's 34 asserted fields — the first re-bless attempt matched every diff count but the asserted denominators, which factored exactly to the two missing columns: 16,199×34=550,766); the v4 library reads its sidecars into the key (pre-v4 refused); the ID KNOWN_RED contracts were corrected from the glued-suffix expectation with oracle evidence and promoted (identity gate 8 green / 2 known-red — HSL only). All three legs equal the oracle exactly incl. asserted cells and exact pairing quality over TSN's 15 real duplicate groups; the 9 PDF↔Excel diffs stay honest (8 database trailing-tabs + the real 108/TUO HG defect). Gate 121/121 + ruff.

- **2026-07-14 — Wave 4: the Ramp Detail family re-blessed against RD-79 EXACTLY (CMP-AUD-045-RD + 135 + 185 resolved; 133 partial).** Every RD path keys on the owner-approved D4 `PhysicalKey` (route, county, norm_pm) — raw TSN, the v4 library (District/County/PM-Suffix sidecars read, v3 refused), Excel/PDF consolidated, and cross-env via the new `EnvCompare.physical_key_builder` → engine `key_normalizer` hook; prefix/suffix/Location/District ride as conserved raw claims (the KNOWN_RED contracts' glued-canonical expectation was corrected to D4 with corpus evidence — PR diffs 0, 313 unmatched TSN suffixes — and promoted into TESTS). District is compared everywhere (the 005/SD/72.366 12-vs-11 disagreement now surfaces); TSN Descriptions are preserved (edges trimmed per the accepted oracle's reading contract — two censused route-126 trailing-tab rows; internal whitespace per D2) and the TSMIS strip is route-matched. All three production legs + every per-field count equal the accepted oracle: 15,212/4/198 · 14,471/741/847 (Excel), …/774/998 (PDF, On/Off 95 + Ramp Type 60), 15,216 · 4/4 (PDF↔Excel). Gate 121/121 + ruff; identity gate 6 green / 3 known-red (HSL/ID pending).

- **2026-07-14 — Wave 3: CMP-AUD-076 Resolved (in-workbook Provenance sheet completes it).** `run_compare` gained the opt-in additive `provenance=` kwarg (None default keeps every caller byte-identical); both drivers pass the pre-read record, so every comparison workbook now displays what it compared — recipe, roles, full canonical selections, digests / member counts, producer completions — while the `.provenance.json` sidecar keeps the machine binding to the committed generation. Real-corpus verified; oracles unchanged; gate 121/121 (no sheet-list assertions broke). Only the schema-v4 fold-in remains, tracked under Phase 5.

- **2026-07-14 — Wave 3: CMP-AUD-076 folder-kind half (compare_env provenance).** Cross-environment comparisons persist the exact discovered member census per side (statted pre-read; the census is the effective identity — the discovery-set tripwire guards the read window), roles = derived side labels, full folder selections, recipe + generation binding, through the same tolerant sidecar writer. Hermetic e2e through the strict publication machinery. Remaining in 076: the in-workbook Provenance sheet + schema-v4 fold-in. Suite 121/121 + ruff clean.

- **2026-07-14 — Wave 3: CMP-AUD-076 file-kind half Resolved (durable comparison provenance).** Every file-kind comparison (the `run_files_compare` driver, all 12+ comparators) captures each input's full canonical selection + streaming sha256 + stat identity + coupled producer completion BEFORE the loaders read, logs the full selections under the banner, and persists the record (+ recipe + committed generation/member digests) as a tolerant guard-disciplined `.provenance.json` beside the workbook. Same-basename inputs are now durably distinguishable; copies keep their digest under their own selection; absence reads as an older comparison. Real-corpus verified (real sidecars beside both summary comparisons; oracles unchanged). Remainder: compare_env folder-kind + the in-workbook sheet + schema-v4 fold-in. Suite 121/121 + ruff clean.

- **2026-07-14 — Wave 3: CMP-AUD-098 comparison-pipeline half Resolved (mid-comparison mutation races).** All four comparison record sites (Matrix env / vs-TSN / self, by-day, baseline) capture the source-folder fingerprint BEFORE any read and record that capture, so a mid-build mutation auto-invalidates (the recorded binding mismatches the folders → `inputs_changed` stale, never a fresh 0/0) and is announced; the formulas twin skips loudly when inputs moved after the values build. CT-6d reproduces the finding's exact raced-fresh setup green + demonstrates the red mechanism. The evidence-gate half stays with Stage 10. Suite 121/121 + ruff clean.

- **2026-07-14 — Wave 2: CMP-AUD-144 + 145 + 146 Resolved (normalizer source-claim batch; summaries' `normalization_version` 2→3).** `parse_tsn_source_claims` captures the print identity (required exactly-once via `compare_tsn_common.tsn_print_identity`), all 62 printed pre-fold rows, the J–P components behind the derived Signalized 2,648 (cross-checked in the normalizer AND the raw compare path), and the declared TSNR-bound CONTROL F correction (printed-descriptor drift refuses). Claims ride `producer_extra` into the library sidecar and surface as familiar-sheet notes (identity · derived-S composition · declared correction) with an explicit no-claims diagnostic for older normalizations. Verified on both real statewide PDFs; both oracles unchanged. Suite 121/121 + ruff clean.

- **2026-07-14 — Wave 2: CMP-AUD-183 Resolved (Intersection Summary route universe).** The consolidator now refuses blank/malformed route identities, excludes every claimant of a duplicated route (loud FAILED ×2 + PARTIAL, never a silent double-count), and persists the ordered `route_census` through the new generic `ConsolidateResult.producer_extra` → `write_outcome(extra=…)` path (all four drivers pass it through). The comparison loader always validates internal universe soundness and, with a census beside the workbook, requires an EXACT ordered match — dropped/extra/renamed/reordered/suffix-collapsed rows refuse with the first divergence named; the census status is a familiar-sheet note + log line (census-less legacy workbooks keep internal checks + an explicit diagnostic). Real-corpus positive control bound in the canary ledger: 217 routes (008U/010S/014U/058U/178S/210U suffixed; 170 absent), oracle unchanged (58/8/0 · 5/53), and the finding's exact 905-deleted / 001-duplicated mutations now REFUSE. Suite 121/121 + ruff clean.
- **2026-07-14 — Wave 2: CMP-AUD-184 Resolved (familiar-view note contract).** The shared familiar-sheet note no longer claims one-sided categories "show 0" and no longer cites Ramp P/V on every family's sheet — it now states the truth (structural absence stays BLANK with no Δ, listed under 'Only in …'; an explicit 0 is a real source zero), with family detail in each spec's own notes. New mutation sweep: all 8 TSMIS-only Intersection categories agree across familiar cells (value/BLANK/BLANK), both formulas+values workbooks, and the generic 'TSMIS only' statuses. Oracles unchanged on the real corpus. Suite 121/121 + ruff clean.
- **2026-07-14 — Wave 2: CMP-AUD-020 + 021 + 022 + 023 Resolved (aggregate Summary loader correctness).** One strict count parser (`summary_layout.parse_count`) now feeds every aggregate read path (numeric text parses; fractions/booleans/negatives refuse with file+category context); duplicate exact normalized keys and duplicated consolidated columns refuse (distinct stale J–P/S keys still fold); the Rural/Urban parent binds from the LABEL (a count-less U parent no longer misfiles `-O` to Rural; a counted orphan refuses); and both `_load_pair`s independently validate each side against a **censused partition contract** (`SectionRule` + `reconcile_counts`) measured on the real corpus before encoding — exact blocks must reconcile, bounded blocks may only run SHORT with their residual EXPOSED as familiar-sheet notes (TSMIS ramp P/V residual 22; IS Highway Group −676; TSN IS untabulated classes −40/−40/−30/−3/−3), and all-zero-categories-under-a-total refuses even when both sides agree. Absent-vs-zero preserved end to end (the TSN normalizers no longer write fabricated `[key, 0]` rows). 12 defects probed RED pre-fix → all green post-fix; **both real-corpus oracles reproduce exactly** (Ramp 29/0/2·5·24, totals 15,216/15,410; IS 58/8/0·5·53, totals 16,459/16,626); ars-prod 7.9 re-consolidation 217/217 byte-identical. Suite 121/121 + ruff clean.
- **2026-07-14 — Wave 2: CMP-AUD-024 + CMP-AUD-025 Resolved (Ramp Summary vs TSN).** The `Ramp Points w/out linework` footnote is now display-only (out-of-band channel, never a compared row) and P/V are `Only in TSN` (not fabricated TSMIS zeros), mirroring the Intersection Summary recipe with no `compare_core` change. Proved red→green in the hermetic check **and verified on the real 7.9 SSOR-prod corpus — reproduces the accepted oracle exactly: 29 shared / 2 TSN-only / 0 TSMIS-only / 5 identical / 24 differing.** This is the first fully data-verified semantic fix; the Ramp Summary vs TSN comparison now represents the data correctly.
- **2026-07-14 — Wave 1: CMP-AUD-035 type-exactness fixed.** `version`/`member_count`/`byte_length`/`schema_version` now require exact `int` (rejecting `1.0`/`True` aliases) in the raw-manifest, normalized-identity, and certificate validators. Verified on 726 persisted objects + a real canonical manifest; guarded red→green in `check_tsn_district_source_contract`. The direct-builder post-`os.replace` TOCTOU recheck (part 2) remains open. Suite 121/121.
- **2026-07-14 — Wave 1: CMP-AUD-115 typed-contract invariants added.** Enforced `differing_cells <= asserted_cells` and "a complete diff must carry a difference" in `comparison_contract.py` (verified on 198 real persisted counts; 6 unrealistic test fixtures corrected). Declined Codex's trace-index-bound sub-claim — trace indices are global ordinals, not population-bounded. The finding's core (workbook-artifact schema enforcement) remains open. Suite 121/121.
- **2026-07-14 — Wave 1: CMP-AUD-238 Resolved.** Hardened the public comparison-contract decoder (rejects `NaN`/`Infinity`, duplicate keys, unknown envelope fields) and made the five frozen-contract mappings immutable via a `FrozenMap` `dict` subclass (asdict/json/deepcopy safe). Both halves proved red→green; suite 121/121, ruff clean, CI green.
- **2026-07-14 — Codex adversarial review complete.** Verified 4 actionable findings against code; added CMP-AUD-238, reopened CMP-AUD-035; disproved the lease-leak hypothesis. CI made green (fixed a cross-drive test bug + 3 ruff F401s the recovered work carried in).
- **2026-07-14 — Evidence base backed up + verified.** Two locations → `Desktop\AI Workspace\Claude\comparison-audit-evidence\` (`.codex` 4.28 GB / 19,017 files + repo `tmp/` 2.31 GB / 2,045 files), each with a SHA-256 manifest, 0 missing.
- **2026-07-14 — Stage 8 confirmed 7/7 on disk.** Owner unlocked the ACL-locked Highway Sequence gate roots; both replays hash byte-for-byte to the recorded values.
- **2026-07-14 — Batch 0 (custodial).** Rescued the ~11k-line uncommitted engine rewrite + 3 load-bearing modules + audit tooling + docs onto branch `comparison-perfection`. First gate run was red (11/140) → fixed 2 real bugs (`tsn_district_contract` missing from `APP_MODULES`; 14 silent swallows) + de-polluted the gate (19 audit instruments out of the blocking glob) → **121/121 green**. Frozen manifest `df7bb8fc…` deliberately superseded → source-only boundary `d87951b2…`.
- **≤2026-07-14 — Recovered audit (prior sessions).** Stages 0–8 as above; the full record is in [archive/reconciliation-report.md](archive/reconciliation-report.md) and the reference ledgers.
