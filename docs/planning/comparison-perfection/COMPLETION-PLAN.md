# Comparison-perfection — plan to completion

**This is the single "you are here" surface for the project.** Read this first. The old
sprawl of status/handoff/reconciliation docs is retired to [archive/](archive/README.md);
the living data ledgers are listed under [Reference](#reference) below.

---

## 1. YOU ARE HERE

_Updated 2026-07-14._

```
Phase:  0 ── 1 ── 2 ── 3 ── 4 ── 5 ── 6 ── 7 ── 8 ── 9 ── 10
        ✅   ✅   ✅   🔨   ⬜   🟨   🟨   ⬜   🟨   ⬜   ⬜
        └───── done ─────┘  └── you are here ──┘        └ release ┘
        ✅ done   🔨 in progress   🟨 code built, proof incomplete   ⬜ not started
```

| | |
|---|---|
| **Branch** | `comparison-perfection` — pushed to origin, **CI green** |
| **Gate** | 121/121 offline checks + ruff(scripts) + byte-compile green; **4 identity contracts documented-red** under CMP-AUD-045 |
| **Audit floor** | Stage 6 (raw→normalized) **7/7**; Stage 8 base (TSMIS-vs-TSN) **7/7** — all seven witnesses hash-verified on disk |
| **Findings** | 238 total · **Resolved this takeover: CMP-AUD-238, 024, 025, 020, 021, 022, 023, 184, 183**; 115/035 partially remediated |
| **Next action** | **CMP-AUD-144 + 145 + 146** as ONE normalizer source-claim batch (single `normalization_version` bump); 076 folds into Wave 3 with 098 (see the RESUME block below) |

> ### ▶ RESUME HERE (2026-07-14, after the Summary-loader batch)
> **Done this batch — CMP-AUD-020/021/022/023 (aggregate Summary loader correctness):**
> `summary_layout.parse_count` (one strict count parser), `SectionRule` +
> `reconcile_counts` (censused per-side partition contracts, measured on the real
> corpus before encoding), duplicate key/column refusal, Rural/Urban parent-from-label
> + counted-orphan refusal, absent-vs-zero preserved end to end (loaders, `_rows`,
> and the TSN normalizers no longer fabricate zeros), bounded residuals EXPOSED as
> familiar-sheet notes via a per-run out-of-band channel (never warnings). Both
> oracles re-verified post-fix on the real corpus: **Ramp 29/0/2 · 5 identical ·
> 24 differing (15,216 vs 15,410)**; **Intersection 58/8/0 · 5 identical ·
> 53 differing (16,459 vs 16,626)** — and the ars-prod 7.9 re-consolidation stays
> 217/217 byte-identical.
>
> **Do this next: CMP-AUD-144 + 145 + 146** as ONE normalizer source-claim batch (a single
> `normalization_version` bump: preserve the six printed J–P control rows + the raw
> CONTROL F descriptor + printed report identity/timing/submitter in the normalized
> sidecar, exposed in Notes/evidence); **183 and 184 are Resolved**; **076** (durable
> cross-family provenance) folds into Wave 3 beside 098. Read each finding in
> `comparison-audit-findings.md` first. 183 follow-ups parked: matrix auto-rebuild when a
> consolidated workbook lacks a route census (then harden census-required), typed-contract
> census surfacing (Phase-5/7 overlay), and Ramp's own universe contract (CMP-AUD-071).
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
