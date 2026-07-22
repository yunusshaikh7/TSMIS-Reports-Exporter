# Comparison audit findings ledger

Last updated: 2026-07-22 (index table reconciled against per-entry statuses — the table
rows for 042/138/144/145 were stale-open, 242 was missing; the per-entry Status line and
the table must be updated TOGETHER when a finding closes)  
Audit state: complete against executable behavior and available real data; Claude/Fable
claims independently reconciled; Phase 1 safety remediation verified 98/98; Phase-2
typed producer/publication/consumer contract closed offline 106/106; Matrix formula
twins remain Phase 5; D2/D3 are approved; the generic independent oracle, hardened
XLSX stream, corrected statewide oracle, installed-Excel E1 full-workbook gate,
build-freshness mutations, and opaque-helper collision gate are green; E1 typed state
masks, numeric/error safety, Spot Check, Summary/CF, both typed Detail Report Views,
exact/capped pairing, and cancellation are offline-green across all comparison-family
checks; E2's 41,000-trace schema-v3 persistence, bounded decode, crash-safe chunk
installation, and serialized exact-generation publication gates are green; the clean
production canary reproduced the corrected oracle with installed-Excel parity; Phase 3
is complete; Stage 6 conservation and the Stage 8 base audit are complete at 7/7.
Product perfection, companion/historical coverage, and end-to-end evidence remain red
and are deferred under the current product-code freeze. Live status and the handoff are
owned by `comparison-perfection-project.md`  
Finding ledger: continuous and authoritative through `CMP-AUD-242`  
Authoritative capability baseline: 29 classic comparison recipes, 12 matrix rows,
30 matrix row-mode placements, 7 canonical TSN datasets

This is the durable source of truth for defects found during the adversarial
comparison audit. Keep stable finding IDs when correcting issues. A finding moves to
`Resolved` only after its independent reproduction is red before the change, green
after the change, the relevant existing suite remains green, and any real-Excel gate
listed below passes.

## Executable comparison capability census

This list is generated conceptually from the executable catalog and was verified by
exact adapter identity at the UI/API and Matrix dispatch boundaries. It—not a prose
count in an older document—is the audit universe.

### Classic Compare recipes (29)

| Stable key | User-facing comparison | Inputs |
|---|---|---|
| `cmp:ramp_summary:env` | TSAR: Ramp Summary — between environments | folders |
| `cmp:ramp_detail:env` | TSAR: Ramp Detail — between environments | folders |
| `cmp:highway_sequence:env` | Highway Sequence Listing — between environments | folders |
| `cmp:highway_log:env` | Highway Log — between environments | folders |
| `cmp:intersection_summary:env` | Intersection Summary — between environments | folders |
| `cmp:intersection_detail:env` | Intersection Detail — between environments | folders |
| `cmp:highway_log_pdf:env` | Highway Log (PDF) — between environments | folders |
| `cmp:intersection_detail_pdf:env` | Intersection Detail (PDF) — between environments | folders |
| `cmp:highway_detail:env` | Highway Detail — between environments | folders |
| `cmp:highway_detail_pdf:env` | Highway Detail (PDF) — between environments | folders |
| `cmp:highway_sequence_pdf:env` | Highway Sequence Listing (PDF) — between environments | folders |
| `cmp:ramp_detail_pdf:env` | TSAR: Ramp Detail (PDF) — between environments | folders |
| `cmp:highway_log:tsn` | Highway Log — TSMIS vs TSN | files |
| `cmp:highway_log:pdf_vs_tsn` | Highway Log — TSMIS (PDF) vs TSN (PDF) | files |
| `cmp:highway_log:pdf_vs_excel` | Highway Log — TSMIS (PDF) vs TSMIS (Excel) | files |
| `cmp:ramp_detail:tsn` | TSAR: Ramp Detail — TSMIS vs TSN | files |
| `cmp:ramp_summary:tsn` | TSAR: Ramp Summary — TSMIS vs TSN | files |
| `cmp:intersection_summary:tsn` | Intersection Summary — TSMIS vs TSN | files |
| `cmp:intersection_detail:tsn` | Intersection Detail — TSMIS vs TSN | files |
| `cmp:intersection_detail:pdf_vs_tsn` | Intersection Detail — TSMIS (PDF) vs TSN | files |
| `cmp:intersection_detail:pdf_vs_excel` | Intersection Detail — TSMIS (PDF) vs TSMIS (Excel) | files |
| `cmp:highway_sequence:tsn` | Highway Sequence Listing — TSMIS vs TSN | files |
| `cmp:highway_detail:tsn` | Highway Detail — TSMIS vs TSN | files |
| `cmp:highway_detail:pdf_vs_tsn` | Highway Detail — TSMIS (PDF) vs TSN | files |
| `cmp:highway_detail:pdf_vs_excel` | Highway Detail — TSMIS (PDF) vs TSMIS (Excel) | files |
| `cmp:highway_sequence:pdf_vs_tsn` | Highway Sequence Listing — TSMIS (PDF) vs TSN | files |
| `cmp:highway_sequence:pdf_vs_excel` | Highway Sequence Listing — TSMIS (PDF) vs TSMIS (Excel) | files |
| `cmp:ramp_detail:pdf_vs_tsn` | TSAR: Ramp Detail — TSMIS (PDF) vs TSN | files |
| `cmp:ramp_detail:pdf_vs_excel` | TSAR: Ramp Detail — TSMIS (PDF) vs TSMIS (Excel) | files |

### Everything-Matrix placements (30)

| Row | Cross-environment | vs TSN | Same-source self-check |
|---|---|---|---|
| TSAR: Ramp Summary | yes | yes | — |
| TSAR: Ramp Detail | yes | yes | — |
| Highway Sequence Listing | yes | yes | — |
| Highway Log | yes | yes | vs TSMIS PDF |
| Intersection Summary | yes | yes | — |
| Intersection Detail | yes | yes | — |
| Highway Log (PDF) | yes | yes | vs TSMIS Excel |
| Intersection Detail (PDF) | yes | yes | vs TSMIS Excel |
| Highway Detail | yes | yes | — |
| Highway Detail (PDF) | yes | yes | vs TSMIS Excel |
| Highway Sequence Listing (PDF) | yes | yes | vs TSMIS Excel |
| TSAR: Ramp Detail (PDF) | yes | yes | vs TSMIS Excel |

The by-day matrix exposes the same 12 rows as date-specific TSMIS-vs-TSN
comparisons. The baseline matrix exposes the same 12 rows as same-format comparisons
between a selected day and an earlier day or Everything-store baseline. These are
additional orchestration surfaces over the audited direct adapters, not shadow
comparison implementations. Seven canonical TSN datasets feed the twelve TSN rows.

## Documentation oracles incorporated

The audit now treats the project's Claude-authored documentation as intended-behavior
evidence, while executable behavior remains the final authority. The routing order is:
the executable catalog/dispatch census first, the current capability table in
`docs/reports.md` second, report-specific canaries third, and historical planning files
only as design history. Contradictory documentation is never promoted into an oracle;
it is tracked in CMP-AUD-086.

The contracts imported from `CLAUDE.md`, `docs/comparison-engine.md`,
`docs/engine-and-reliability.md`, `docs/verification-and-testing.md`, and the v0.18
Claude close-out are:

- all 12 fully integrated report editions must remain reachable through direct and
  matrix comparison surfaces, including five PDF-to-Excel self-checks;
- comparison equality changes require cell-for-cell formulas/values proof;
- completeness is producer-owned and incomplete inputs must never look like a
  certified match. Current owning docs require persistent derived artifacts to keep a
  last-good truth state, while the historical v0.18 plan explicitly allowed a partial
  consolidation to remain comparable; that contradiction is now an implementation
  decision gate under CMP-AUD-085/086 rather than an assumed oracle;
- comparison counts are located by header label, not workbook position;
- TSN normalizer changes require a version bump and cached-library invalidation;
- evidence is a verified decoration of an already-current comparison, never a second
  source of counts; and
- canaries must be independently recomputed from raw sources rather than copied from
  an agent report or a pre-existing consolidated workbook.

The local-only development corpus is mapped by
`C:\Users\Yunus\Downloads\TSMIS\_INDEX.md` (15,890 files / about 5.8 GB at the
2026-07-11 inventory). Its `ground-truth/` directory is the acceptance source;
`report-samples/` supports parser spot checks; `comparison-outputs/` is historical
reference; and `_scratch/` is explicitly disposable and never an oracle. The corpus
contains real data and Caltrans-internal site captures and must never be copied into
the repository. Exact selected-input identities and unresolved canary ambiguities are
tracked in `docs/planning/comparison-perfection/comparison-canary-bindings.md`; Route-1 has a fully recorded
pre-Phase-3 input/code/output/real-Excel baseline there, while statewide/member-manifest
statewide bindings are input-bound and await the full independent typed-count run.

One historical decision is directly actionable in this audit: the v0.18 plan chose
`(relative_name, size, mtime_ns)` fingerprints and explicitly deferred content hashing
until a same-metadata replacement was proven
(`docs/planning/v0.18.0/05-claude-final-plan.md:303-306`). Chunk 10 has now produced
that counterexample (CMP-AUD-080).

## Independent reconciliation of Claude's second opinion

Claude's 2026-07-11 review is retained at
`docs/planning/comparison-perfection/claude-comparison-audit-second-opinion.md`. Its disputed and newly
sharpened claims were re-read against the implementation and reproduced independently
before being accepted here. The reconciliation found no false ledger finding and no
new defect requiring a new stable ID. It did produce the following corrections and
extensions:

- CMP-AUD-003 now records that openpyxl treats literal Excel error tokens such as
  `#N/A` as error-typed cells; the existing formula-injection guard does not stop it.
- CMP-AUD-004 now includes `matrix_state.read_counts` and conditional formatting,
  both of which repeat the ambiguous display-marker scan.
- CMP-AUD-006 now records that `norm_pm`'s docstring contradicts the executable
  normalizer, so that comment cannot be used as the domain contract.
- CMP-AUD-008 is stronger than “non-optimal”: a real, Hamming-distance 8x8 fixture
  scored 31 differences in file order and 32 through the production greedy branch.
  The implementation can therefore add a phantom difference despite its monotonicity
  claim. The true optimum for that fixture is 31.
- CMP-AUD-016 is narrowed: relative dropdown-selected folders do receive a report-
  membership preflight. File recipes and absolute Browse selections remain vulnerable,
  and selection state still leaks across recipes.
- CMP-AUD-085 is split internally into the unresolved partial-artifact publication
  policy and four independently defective truth surfaces: workbook wording, cache/
  retryability, day badge, and evidence publication.
- CMP-AUD-088's frozen queue-clear check covers only one same-kind ordering and does
  not exercise the mixed offline/auth-dependent queue it purports to protect.
- CMP-AUD-090 is reframed around `ensure_owned_dir` stamp-on-sight semantics. The day
  worker triggers the wrong-root case, but the Everything worker can also claim a
  pre-existing foreign `comparisons` or store directory.
- CMP-AUD-114's original golden fixture did entrench the defect: its sole complete
  comparison was unreadable and still required `comparisons_ok == 1`. Phase-2 validation
  fixtures now invert that expectation and require missing/untrusted generations to stay
  out of the OK bucket.
- CMP-AUD-116's reproduction includes both returned and raised failures. The Phase-2
  reducer now serializes explicit failed/cancelled completion for both shapes.

Two suggested severity/scope changes were rejected after checking this ledger's own
definitions. CMP-AUD-099 remains P2 because it is executable incorrect targeting and
can consume substantial rebuild time; P3 is reserved here for taxonomy/documentation/
presentation defects. CMP-AUD-101 already names only the generic folder shortcut; the
per-cell Open action is explicitly recognized as correct.

### Independent reconciliation of Fable 5's decision record

Fable 5's 2026-07-11 D1–D7 response is retained at
`docs/planning/comparison-perfection/fable5-comparison-remediation-decisions.md`. Its policy direction was
checked independently against the implementation rather than copied into the plan.
The review accepted D1's last-complete policy, D5's aggregate taxonomy, and D7's
capability facts, while recording these implementation-significant corrections:

- D2's proposed Boolean and universal non-ASCII/control-whitespace folding change
  current Python answers; they require semantic approval and real-data measurement.
- D3's 316-by-316 worst-case claim is false under the product cap, which permits a
  1-by-100,000 group. The implementation must be rectangular, prove tie-breaking, and
  retain an executable monotonicity fixture. Above-cap completion semantics remain a
  decision gate.
- D4 is proven for Highway Sequence, Ramp Detail, and Intersection Detail. Highway
  Detail still lacks an Excel-side county; the cited 453 count used a weaker key than
  `pm_canon` and is only an upper bound.
- D5 needs a display-only auxiliary metrics channel so removing the Ramp footnote from
  asserted rows does not erase it from the familiar presentation.
- D6's same-source principle is valid, but the proposed family profiles omit active
  transformations and miscount Highway Sequence's non-key fields. A complete
  five-family asserted/context/key/raw-claim table is required before coding.
- D7 changes catalog metadata, server-side recipe/role binding, and shape preflight in
  addition to picker/UI text.

The primary implementation index was recounted after these changes: all 185 stable IDs
appear exactly once, with no duplicate, omission, or extra ID. Secondary integration
gates remain explicit and do not close a finding by themselves.

## Status and severity

- `Verified`: reproduced through executable code or real Excel, not inferred only
  from comments.
- `Partially remediated`: one or more locked corrections landed, but an original or
  explicitly transferred closure requirement remains open; do not treat it as resolved.
- `Source-verified`: the faulty path is deterministic from the executable code, but
  its broader report-family fixture is still scheduled.
- `Candidate`: credible issue found during tracing; do not correct until independently
  reproduced.
- `P1`: can silently produce, hide, or certify the wrong comparison result, or make a
  trust workflow materially incomplete.
- `P2`: incorrect behavior with narrower inputs, incomplete reporting, or a broken
  supported action with a workaround.
- `P3`: taxonomy, drift-prevention, documentation, or presentation defect.

## Audit progress

- [x] Chunk 0: executable capability census and UI/API routing
- [x] Chunk 1: shared equality, keying, marker, and duplicate semantics
- [x] Chunk 2: formulas/values workbook parity in real Excel
- [x] Chunk 3: input discovery and completeness propagation
- [x] Chunk 4: Ramp/Intersection aggregate comparisons
- [x] Chunk 5: flat Excel report families
- [x] Chunk 6: Highway Log domain rules
- [x] Chunk 7: PDF parser integrity
- [x] Chunk 8: PDF/Excel/TSN triangles
- [x] Chunk 9: classic Compare UI/API
- [x] Chunk 10: Everything matrix
- [x] Chunk 11: day and baseline matrices
- [x] Chunk 12: evidence, validation, and available real-data acceptance; unavailable
  external canaries recorded below

## Phase-2 remediation checkpoint

The typed producer and strict-consumer contract is closed offline at 106/106. That is
not permission to collapse later findings into “done”; the following boundaries are
explicit transfers or later entry gates rather than unrecorded Phase-2 work:

- CMP-AUD-075/082: central classic `mode="both"` is one strict generation, while all
  three Matrix surfaces still build formulas in a second generation and can leave an
  older formulas twin.
- CMP-AUD-076/084: source identity, producer-version, and pairing-trace fields exist as
  validated schema slots, but producers do not universally populate them. A schema slot
  is not provenance or semantic invalidation by itself.
- CMP-AUD-080: strict readers intentionally hash workbook members on each snapshot.
  A faster stat-only process cache was adversarially rejected because it missed a
  same-size/same-mtime replacement on Windows. Source-folder fingerprints remain
  metadata-based.
- CMP-AUD-089: `AttemptState` is carried by the immediate comparison result, but Matrix
  workers do not yet persist a durable failed/cancelled attempt overlay separate from
  the last committed generation.
- CMP-AUD-098: Matrix source fingerprints are still recorded after comparison commit.
  A postcommit/precache mutation can therefore bind old output bytes to new source
  state; typed output generations do not solve input TOCTOU.
- CMP-AUD-100: loader fixes are in place, but the complete persisted cross-matrix
  envelope-swap/adversarial nested-JSON closure gate is still owed.
- CMP-AUD-106/109/110/112: evidence now requires a strict complete comparison and
  rechecks its generation, but comparison, source PDFs, evidence workbook/images, and
  retirement of old evidence are not one immutable transaction. A failure discovered
  after render can occur after evidence bytes were already published.
- CMP-AUD-115 remains the deep comparison-workbook schema boundary. CMP-AUD-114 is
  closed only for preventing absent/untrusted generations from being counted as OK.
- CMP-AUD-118/119/120 remain unchanged: raw-only first build, TSN-heal reporting truth,
  and pre-build cancellation still require their Phase-8 work.
- Real acceptance inputs are routed by the local corpus index but are not yet all bound
  by exact path/member manifest, SHA-256, and producer/parser/normalizer versions. Phase
  3 may not re-bless semantic counts from an unbound historical output.

## Findings summary

| ID | Priority | Status | Short description |
|---|---:|---|---|
| CMP-AUD-001 | P1 | Resolved | Python values and live Excel share one typed equality contract |
| CMP-AUD-002 | P1 | Resolved | Med-Wid normalization is exact and formula/value identical |
| CMP-AUD-003 | P1 | Resolved | Excel error text is literal-safe and counted through typed state |
| CMP-AUD-004 | P1 | Resolved | Literal ` != ` content is presentation-only, never discrepancy state |
| CMP-AUD-005 | P1 | Resolved | Opaque helper identities prevent delimiter collisions |
| CMP-AUD-006 | P1 | Remediated 2026-07-17 (the identity component is Decimal-canonical — compare_tsn_common.decimal_pm; zero partition merges statewide, pairing provably unchanged) | Ramp Detail PM normalization contradicts its identity contract |
| CMP-AUD-007 | P1 | Resolved 2026-07-18 (verify+pin) | Settings validation omits five PDF rows and selected TSN files |
| CMP-AUD-008 | P2 | Resolved | Duplicate pairing is exact in-cap and explicitly partial/capped above it |
| CMP-AUD-009 | P2 | Resolved 2026-07-18 (a numeric identity key now canonicalizes like its compared value — `_key_text` maps an integral float `5.0`→`'5'` so it aligns with its int/text twin instead of splitting into two false one-sided rows; whitespace/case stay significant by design — trim/casefold would merge distinct identities; typed PhysicalKey/roadbed paths untouched; census-proven byte-identical on 128,226 real key cells) | Row keys bypass ordinary trim and numeric coercion |
| CMP-AUD-010 | P2 | Resolved 2026-07-18 | Matrix Consolidate sends canonical TSN PDFs to a legacy-only path |
| CMP-AUD-011 | P2 | Resolved | ValidationWorker drops the partial-comparison count |
| CMP-AUD-012 | P2 | Resolved | Spot Check preserves typed blank/zero and full display parity |
| CMP-AUD-013 | P3 | Resolved | Matrix capability support is duplicated and hardcoded |
| CMP-AUD-014 | P3 | Resolved | PDF-versus-Excel checks are filed under Cross-environment |
| CMP-AUD-015 | P3 | Resolved 2026-07-18 (the four base Intersection comparison labels — summary/detail × env/tsn — dropped the wrong `TSAR:` prefix to match their export/consolidate entries and the already-correct PDF variants; the frozen catalog check + mock.js + architecture/reports docs updated in lockstep; `check_report_catalog` proves the derivation) | Four Intersection comparison labels incorrectly add `TSAR:` |
| CMP-AUD-016 | P2 | Resolved 2026-07-18 | Classic file/Browse inputs persist and launch across recipe changes |
| CMP-AUD-017 | P1 | Resolved | Skipped comparison inputs are cached and rendered as complete |
| CMP-AUD-018 | P1 | Resolved | Intersection cross-env bypasses its layout-drift validator |
| CMP-AUD-019 | P1 | Resolved 2026-07-17 (record_has_data requires Total + every printed section; per-route audit reconciliation connected to the producer outcome — unexplained → PARTIAL, explained P/V residual → typed note; matcher unknown/duplicate diagnostics; cross-env applies the same gate; 126-route real-data verified) | Ramp cross-env accepts a one-field partial parse as complete |
| CMP-AUD-020 | P1 | Resolved 2026-07-14 (censused per-side partition contract enforced; real-data verified) | Aggregate vs-TSN loaders do not reconcile section totals |
| CMP-AUD-021 | P1 | Resolved 2026-07-14 (one strict count parser through every aggregate read path) | Aggregate counts silently ignore text and truncate fractions |
| CMP-AUD-022 | P1 | Resolved 2026-07-18 (`counts_from_rows` — the raw block-walk feeding BOTH the TSN print parser and the TSMIS per-route consolidator — now keys each matched category by `(block, pre-fold code)` and refuses a repeat, closing the silent-double-count gap the normalized `_load_tsn`/consolidated `_load_tsmis` key-guards didn't cover; distinct J–P pre-fold codes still fold into Signalized; census: 437 real calls (3 TSN bands + 434 routes) carry 0 repeats and never mix a standalone S with the J–P fold, so the guard never false-fires) | Duplicate normalized categories overwrite or double-count silently |
| CMP-AUD-023 | P1 | Resolved 2026-07-14 (parent context from labels; counted orphans refuse) | Rural/Urban parent tracking can move counts to the wrong category |
| CMP-AUD-024 | P1 | Resolved | The `Ramp Points w/out linework` footnote is now display-only (out-of-band to the familiar sheet), never a compared row. Real 7.9 SSOR-prod run matches the oracle: 0 TSMIS-only |
| CMP-AUD-025 | P2 | Resolved | P/V are marked `sides="tsn"` and routed via `categories_for(side)`, so they are `Only in TSN`, not fabricated TSMIS zeros. Real run matches the oracle: 29 shared / 2 TSN-only / 0 TSMIS-only / 5 identical / 24 differing |
| CMP-AUD-026 | P1 | Resolved | PDF comparison paths discard producer partial outcomes |
| CMP-AUD-027 | P1 | Resolved | Header-only route files disappear from route coverage |
| CMP-AUD-028 | P1 | Remediated 2026-07-17 — a configured identity column is mandatory; `_resolve_key_field` fails closed instead of keying on column 0 | Missing configured key columns silently fall back to column zero |
| CMP-AUD-029 | P2 | Remediated 2026-07-17 — `_find_input_dir` excludes `~$` owner-lock stubs, so the generic cross-env XLSX path matches every other loader | Generic XLSX discovery includes Excel owner-lock files |
| CMP-AUD-030 | P2 | Remediated 2026-07-17 — `_load_xlsx_side` keeps a per-side seen-route set; a duplicate route is skipped into the incompleteness channel, never concatenated | Duplicate route files are silently merged |
| CMP-AUD-031 | P2 | Remediated 2026-07-17 — the flat XLSX route key is `_norm_route_key`-normalized and the `..._route_<n>` naming contract is required; a non-route file is skipped, never promoted from its stem | Flat report route keys do not normalize `1` and `001` |
| CMP-AUD-032 | P1 | Resolved 2026-07-18 (every flat cross-env family pins its EXACT export schema via a header_canonicalizer — RD/HSL/HD/ID XLSX + HSL-PDF/RD-PDF; census-verified on the 7.9 statewide exports + converted headers; two malformed/legacy/truncated/reordered sides refuse instead of matching) | Cross-env flat schemas trust the first file, not the report contract |
| CMP-AUD-033 | P1 | Remediated 2026-07-17 — all four normalized loaders bind the exact ["Route"]+SHARED_HEADER prefix + documented sidecars before reading positionally | Normalized TSN loaders ignore their declared headers |
| CMP-AUD-034 | P1 | Remediated 2026-07-17 — all four consolidated `_load_tsmis` loaders bind their EXACT documented header (the shared `exact_consolidated_header_ok`); relabels/shifts/insertions/deletions/wrong editions are refused | Consolidated TSMIS loaders accept semantically invalid layouts |
| CMP-AUD-035 | P1 | Resolved 2026-07-18 | Original raw-admission r7 accepted. Type-exact validation rejects float/bool aliases (2026-07-14). 2026-07-18: the direct HSL/HL builders now re-verify the raw source AFTER the os.replace (a change in the pre-replace-gate→replace window can no longer return success for stale bytes); HSL red→green in check_consolidate_toctou, HL symmetric |
| CMP-AUD-036 | P1 | Remediated 2026-07-17 — the RD-PDF source gate requires the exact PDF-consolidated width + the trailing On/Off/Ramp Type sentinels | Ramp PDF accepts a truncated four-column workbook |
| CMP-AUD-037 | P1 | Remediated 2026-07-17 — all five families gate the direct path (HSL v4 + HL v5 markers; RD v5 / ID v5 / HD v3 in-workbook markers + loader gates; marker-only bumps, rows byte-identical on the real corpus) | Direct comparisons trust stale normalized libraries |
| CMP-AUD-038 | P2 | Resolved 2026-07-18 (`iso_date` full-matches each documented form + calendar-validates via `date()`; trailing junk / impossible dates are preserved verbatim as a visible difference instead of truncated or faked; census-proven no-op — shipped == old on all 121,464 distinct real date cells across RD+ID, both editions) | Date normalization masks malformed and impossible dates |
| CMP-AUD-039 | P1 | Resolved 2026-07-18 (Report View slice remediated 2026-07-12; the last open slice — the shared `summary_layout._render` Summary-by-Category sheet — now flags each category from the SAME `compared_cell` verdict the Comparison sheet uses, never a re-derived numeric delta, so the two can't disagree; identical to the old delta styling for the integer counts CMP-AUD-021 guarantees, red→green on a text-different-numeric-equal fixture) | Detail Report View counts contradict the main comparison |
| CMP-AUD-040 | P1 | Resolved 2026-07-18 | File half closed by CMP-AUD-066 (2026-07-17). 2026-07-18: the FOLDER half — a run ROOT vs that run's `<report>` SUBFOLDER (or a junction/hardlinked tree) resolving to the same effective report dir / file set — now refuses before loading; census 0 false-rejections on the real 7.9 cross-env pairs, alias caught for every report with files |
| CMP-AUD-041 | P1 | Resolved | Selected or derived outputs can overwrite comparison sources |
| CMP-AUD-042 | P1 | Resolved 2026-07-21 (`06f2d85` — `_normalized_row` consumes the stored PS marker instead of re-deriving it from the already-normalized text) | Normalized Highway Detail erases every PS equation marker |
| CMP-AUD-043 | P1 | Resolved 2026-07-18 (both familiar secondary surfaces take the finding's accepted "unmistakable values-only snapshot label" path: the Report View was labeled a build-time snapshot in the 2026-07-12 remediation, and the shared Summary-by-Category sheet now carries an unmistakable "do NOT recalculate; regenerate after editing a source" disclosure, gated present in both family checks) | Formula Report View stays stale after live recalculation |
| CMP-AUD-044 | P1 | Resolved 2026-07-18 (both trim-and-slice loaders — `compare_env._load_xlsx_side` and `compare_highway_log._load_input` — now detect a nonblank cell beyond the declared width and refuse the file instead of slicing it off: compare_env skips loudly into the incompleteness channel, HL raises; census-proven no-op — 1,316 real flat exports carry 0 data beyond the trimmed header, confirmed end-to-end on 252 HD exports) | Data beneath trailing blank headers is silently discarded |
| CMP-AUD-045 | P1 | Partially remediated (HL integrated 2026-07-17; only HD-Excel stays blocked — HD is pre-release (owner 2026-07-21), its county question cannot be answered yet, never infer) | Shared typed identity core green; report-family integration remains red |
| CMP-AUD-046 | P2 | Resolved 2026-07-18 (RD Excel+PDF pin a position-authoritative `force_header`; ID Excel+PDF realign legacy→current via `_id_canonical_header`; census-verified per-position on the 7.9 exports; end-to-end proves a Description change shows under Description not R/U, an INT Type change under INT Type not INT Eff-Date) | Shifted exports report differences under the wrong fields |
| CMP-AUD-047 | P2 | Remediated: the env XLSX loader takes the report's own value projection (HL passes _hl_normalize; the HL-PDF conversion path too); red->green in check_compare_env_highway_log | Highway Log cross-env skips its whitespace normalization |
| CMP-AUD-048 | P2 | Remediated: per-side header canonicalization before layout equality (canonical/vendor editions compare with corrected labels; unrecognized same-width layouts refused by name); red->green in check_compare_env_highway_log | Two supported Highway Log header editions cannot compare |
| CMP-AUD-049 | P1 | Remediated 2026-07-17 (direct-compare, converter, and evidence halves) | Direct/PDF route provenance is not enforced |
| CMP-AUD-050 | P1 | Remediated (2026-07-17) | PDF routes can overwrite, double-count, or remain blank |
| CMP-AUD-051 | P1 | Resolved | Highway Detail PM spill creates phantom PDF records |
| CMP-AUD-052 | P1 | Resolved | Highway Detail header words swallow real line-two data |
| CMP-AUD-053 | P1 | Resolved | Highway Detail orphan reconciliation never fires |
| CMP-AUD-054 | P1 | Resolved | Highway Detail fallback grids corrupt real rows as complete |
| CMP-AUD-055 | P1 | Resolved | Damaged repeated headers silently drop later PDF data pages |
| CMP-AUD-056 | P1 | Resolved | Intersection wrapped rowB text is truncated as complete |
| CMP-AUD-057 | P1 | Resolved | Intersection orphan rowB lines are never counted |
| CMP-AUD-058 | P1 | Resolved | Intersection numeric furniture can consume a pending record |
| CMP-AUD-059 | P1 | Resolved | Mixed Intersection PDF editions silently lose legacy rows |
| CMP-AUD-060 | P1 | Resolved | Intersection vestigial-column drift is discarded as complete |
| CMP-AUD-061 | P2 | Resolved | Intersection grid scanning ignores cancellation |
| CMP-AUD-062 | P1 | Resolved | Intersection document-median geometry silently drops pages |
| CMP-AUD-063 | P2 | Resolved | Sequence/Ramp PDFs certify invalid post-mile code tokens |
| CMP-AUD-064 | P2 | Resolved 2026-07-18 (the HSL-PDF + RD-PDF consolidators no longer assign their unparsed-line count `loud` to the file-level `skipped_inputs`; like the already-correct `bad_tokens` path it escalates completion to PARTIAL only and now rides a structured `producer_extra['parse_anomalies']` diagnostic; a shared `pdf_table_lib._clamp_input_counts` caps skipped/failed to the discovered input count; real 3-route RD-PDF stays COMPLETE/skipped=0/no-anomalies; red→green in check_pm_code_vocabulary — 1 PDF / 3 bad lines → skipped_inputs 3→0 + unparsed_lines=3) | PDF parser anomaly counts masquerade as skipped input counts |
| CMP-AUD-065 | P1 | Remediated 2026-07-16 by CMP-AUD-199 (re-verified 2026-07-17: the same-source schema compares EVERY column — context_fields is empty) | Sequence PDF-vs-Excel suppresses three same-source fields |
| CMP-AUD-066 | P1 | Remediated 2026-07-17 (HL vs-TSN half via the v5 marker; the PDF-role halves via the PDF-conversion marker; RD structurally protected) | PDF comparison roles are not provenance-validated |
| CMP-AUD-067 | P1 | Remediated 2026-07-17 (same-source projections in all four families; HSL was fixed by 199/204, RD never had an instance) | TSN projections hide PDF-vs-Excel source differences |
| CMP-AUD-068 | P2 | Resolved 2026-07-18 (the ID PDF-vs-TSN half closed by CMP-AUD-239; the Highway Detail half now matches — `compare_highway_detail_tsn.add_report_view` extracted as the shared per-call composer and BOTH vs-TSN flavors ride it: the Excel-sourced `compare()` and the PDF-sourced `TSMIS_PDF_VS_TSN` (report_view=True + `_schema_for`); the same-source PDF-vs-Excel self-check keeps NO Report View — TSN-specific soft/ADT semantics don't apply to two TSMIS renders; real-corpus PDF-vs-TSN compare builds the Report View sheet with records, parity with Excel-vs-TSN; schema-parity + red→green in check_highway_detail_pdf) | PDF-vs-TSN Detail paths omit Report View |
| CMP-AUD-069 | P2 | Resolved 2026-07-18 (the Ramp Detail PDF wrapper now forwards its own `side_a`/`side_b` labels to `run_files_compare`, like the ID/HD wrappers — a missing PDF-vs-Excel second file names "TSMIS (Excel)" not the default "TSN", and a missing first file names "TSMIS (PDF)"; red→green existence-message test in check_compare_ramp_detail_pdf) | Ramp PDF comparisons mislabel their file roles in diagnostics |
| CMP-AUD-070 | P1 | Resolved 2026-07-17 — NOT A DEFECT: the loader correctly keys by the physical (Location) route, which TSN uses too (259/259 verified); the prescribed "use the file route" fix would introduce discrepancies | Intersection loader ignores explicit route and suffix fields |
| CMP-AUD-071 | P1 | Resolved 2026-07-18 (the comparator-side twin of CMP-AUD-050: Intersection Summary's route-universe validator promoted to the shared `compare_tsn_common.validate_route_universe` and wired into BOTH aggregate comparators — require ≥1 valid route, reject blank/duplicate, reconcile against the producer's ordered `route_census`; the Ramp Summary consolidator now records that census in its outcome sidecar so dropped/added/reordered/renamed rows are detectable; real 126-route consolidation records 001..980 and the comparator emits the verified note, total_ramps=15216; red→green route-universe suite: header-only/blank/dup-identical/dup-conflicting/dropped/reordered) | Ramp Summary comparison does not validate its route universe |
| CMP-AUD-072 | P2 | Resolved | Stale folder discovery can overwrite a newer recipe selection |
| CMP-AUD-073 | P2 | Resolved | Classic picker blocks two supported raw-PDF inputs |
| CMP-AUD-074 | P2 | Resolved | Universal file hint promises unsupported per-route inputs |
| CMP-AUD-075 | P1 | Resolved 2026-07-18 (closed by CMP-AUD-082) | Both-mode completion is persisted for only one output. Central path fixed 2026-07-11; the matrix twin residual (a values-only/failed formula refresh leaving STALE formula evidence) is closed by 082's `_settle_formulas_twin` (clears/refreshes the twin per values commit — all four matrix comparators). The "one generation id for both members" remainder is the deferred Phase-5 multi-artifact manifest (with 082), not a truth defect |
| CMP-AUD-076 | P2 | Resolved 2026-07-14 (durable provenance sidecar + in-workbook sheet; only the strict schema-v4 fold-in remains, Phase-5) | Saved comparisons lack durable source provenance |
| CMP-AUD-077 | P2 | Resolved | Comparison results discard their structured discrepancy counts |
| CMP-AUD-078 | P3 | Resolved | Comparison failures are titled as consolidation failures |
| CMP-AUD-079 | P2 | Resolved 2026-07-18 | Compare sub-tab switching can hide every Cancel control |
| CMP-AUD-080 | P1 | Partially remediated | Matrix artifact identity can miss changed source and output content |
| CMP-AUD-081 | P1 | Resolved | Matrix TSN freshness ignores source identity and library rebuild state |
| CMP-AUD-082 | P1 | Resolved | Matrix formula twins can survive as stale audit artifacts |
| CMP-AUD-083 | P2 | Resolved | Matrix presence and freshness count arbitrary non-report files |
| CMP-AUD-084 | P1 | Resolved | Matrix caches survive semantic comparator and parser changes |
| CMP-AUD-085 | P1 | Partially remediated | Partial-artifact policy conflicts while truth surfaces certify/reuse incomplete work |
| CMP-AUD-086 | P3 | Resolved | Comparison documentation contradicts the executable capability census |
| CMP-AUD-087 | P2 | Resolved | “Refresh stale” cannot rebuild cells whose count cache is unavailable |
| CMP-AUD-088 | P2 | Resolved | An authentication failure deletes queued offline comparisons |
| CMP-AUD-089 | P2 | Verified | Failed and cancelled rebuild attempts disappear behind prior results |
| CMP-AUD-090 | P1 | Resolved | Workers can mark pre-existing foreign folders as app-owned and deletable |
| CMP-AUD-091 | P1 | Resolved 2026-07-18 | Day exports and their chained comparisons can cross into different dates |
| CMP-AUD-092 | P2 | Resolved 2026-07-18 | Day discovery loses legacy folder identity and accepts impossible dates |
| CMP-AUD-093 | P2 | Resolved 2026-07-18 | Day consolidation status and refresh use incompatible target universes |
| CMP-AUD-094 | P2 | Resolved 2026-07-18 | Removing a running export day deletes its automatic comparison target |
| CMP-AUD-095 | P2 | Resolved 2026-07-18 | Source switches retain invalid source-scoped days and baselines |
| CMP-AUD-096 | P2 | Resolved 2026-07-18 | Invalid scoped rebuild filters silently broaden to the whole matrix |
| CMP-AUD-097 | P2 | Resolved 2026-07-18 | Unified matrix state cannot report that both inputs are missing |
| CMP-AUD-098 | P1 | Partially remediated 2026-07-14 (the comparison-pipeline half; the evidence-gate half remains Stage-10 work) | Inputs changed during comparison can be certified as the fresh sources |
| CMP-AUD-099 | P2 | Resolved 2026-07-18 | Baseline switching rebuilds baseline-independent Matrix modes |
| CMP-AUD-100 | P2 | Resolved | Matrix cache identity and nested record schemas are not validated |
| CMP-AUD-101 | P2 | Resolved 2026-07-18 | Open Comparisons opens the wrong tree for non-environment modes |
| CMP-AUD-102 | P2 | Resolved 2026-07-18 | “Show comparison for all” silently excludes hidden rows |
| CMP-AUD-103 | P2 | Resolved 2026-07-18 | Cell Build actions dispatch despite a known missing TSN input |
| CMP-AUD-104 | P3 | Resolved 2026-07-18 | One queue-capable day export action is uniquely disabled while busy |
| CMP-AUD-105 | P1 | Resolved | A missing explicit TSN source silently falls back to another dataset |
| CMP-AUD-106 | P1 | Partially remediated 2026-07-18 | Old red evidence survives beside a newly clean comparison |
| CMP-AUD-107 | P1 | Resolved 2026-07-18 | Highway Detail evidence invents differences the comparison treats as equal |
| CMP-AUD-108 | P2 | Verified | Duplicate-only differences disappear from evidence accounting |
| CMP-AUD-109 | P1 | Partially remediated 2026-07-19 | Evidence workbook and images are not one truthful transaction |
| CMP-AUD-110 | P2 | Resolved 2026-07-18 | Queued evidence actions silently retarget to current settings |
| CMP-AUD-111 | P1 | Resolved | Evidence summaries execute source values as Excel formulas |
| CMP-AUD-112 | P1 | Resolved 2026-07-18 | Evidence can verify old PDF records but rasterize replacement bytes |
| CMP-AUD-113 | P3 | Resolved | Evidence bundle member counts omit validation files |
| CMP-AUD-114 | P1 | Resolved | Unreadable comparison results are counted and shown as fully OK |
| CMP-AUD-115 | P1 | Partially remediated 2026-07-14 (typed-contract count/verdict invariants) | Comparison artifact validation accepts semantically empty workbooks |
| CMP-AUD-116 | P1 | Resolved | Failed validation records default to complete |
| CMP-AUD-117 | P1 | Resolved | Bearer credentials survive redaction into the evidence ZIP |
| CMP-AUD-118 | P2 | Remediated: _ensure_tsn_ready first-builds raw-only libraries (ensure_current None -> build_consolidated); raw-awaiting-build is a blocked capability in the digest | Validation skips imported raw-only TSN data instead of building it |
| CMP-AUD-119 | P2 | Remediated: _tsn_state_text renders the complete truth table (HEALED-to-current disclosed, heal-but-stale alarmed, HEAL FAILED/CANCELLED, awaiting-first-build, cancelled-before-heal); before/attempt/after preserved in JSON | Validation reports TSN healing with an inverted truth table |
| CMP-AUD-120 | P2 | Remediated: _tsn_stage polls should_cancel before every heal and records cancelled_before_heal; builders receive the events sink for mid-build cancellation | Pre-cancelled validation still mutates TSN libraries |
| CMP-AUD-121 | P2 | Resolved | Full exact duplicate traces can exceed the comparison-sidecar size ceiling |
| CMP-AUD-122 | P2 | Resolved | Duplicate pairing and typed counting ignored cancellation |
| CMP-AUD-123 | P1 | Resolved | Live workbook edits could certify stale build-time identity and pairing |
| CMP-AUD-124 | P2 | Resolved | Uppercase output basenames could not publish strict comparison metadata |
| CMP-AUD-125 | P1 | Resolved | Interrupted payload writes can permanently poison deterministic chunk names |
| CMP-AUD-126 | P1 | Resolved | Payload limits permit multi-gigabyte decode pressure and redundant peer decoding |
| CMP-AUD-127 | P2 | Remediated: post-publication reference-aware collection under the parent lease (sentinel/malformed-sibling/grace/mismatch all retain; identity-bound handle unlinks) | Superseded comparison payload chunks have no bounded lifecycle |
| CMP-AUD-128 | P1 | Resolved | Overlapping metadata publishers can both claim success for one persisted generation |
| CMP-AUD-129 | P2 | Resolved | Payload and sidecar names can exceed packaged Windows path limits |
| CMP-AUD-130 | P2 | Remediated: Windows deletions go through an identity-verified handle (delete-on-close bound to the checked inode); raced foreign replacements survive, gated in check_comparison_sidecars | Stat-then-unlink cleanup can delete a foreign same-path replacement |
| CMP-AUD-131 | P2 | Remediated via the sanctioned claims-narrowing option: every crash-safety claim now says process-interruption safety, power loss explicitly unproven, fail-closed reads named as the conservative sentinel | Publication is process-interruption safe but not proven power-loss durable |
| CMP-AUD-132 | P1 | Resolved | Highway Log intermediates are attempt-scoped and exact-manifest bound |
| CMP-AUD-133 | P1 | Partially remediated 2026-07-14 (RD PM_SFX conserved, v4 sidecar); the HD remainder is DEFERRED — HD is pre-release (owner 2026-07-21), resumes on the official HD delivery | Normalized Detail libraries discard source-backed identity, print, and Report View facts |
| CMP-AUD-134 | P1 | Remediated | The first Stage-6 Ramp oracle could certify without final source revalidation and understated printed-field loss |
| CMP-AUD-135 | P1 | Resolved 2026-07-14 (TSN Descriptions preserved; the TSMIS strip route-matched; re-blessed) | Ramp normalization deletes all 15 source-backed numeric Description prefixes |
| CMP-AUD-136 | P1 | Remediated | The independent XLSX reader can parse synchronized A-to-B-to-A bytes between equal live-file hashes |
| CMP-AUD-137 | P1 | Remediated | The independent XLSX reader folds error cells into ordinary strings instead of rejecting them |
| CMP-AUD-138 | P1 | Resolved 2026-07-21 (`d553fbd` — Length quantizes the exact source Decimal ROUND_HALF_UP; census 60,083 values, exactly one changes) | Highway Detail converts exact decimal Length through binary64 and rounds one source row downward |
| CMP-AUD-139 | P1 | Remediated | The first Intersection Stage-6 oracle has mutable auxiliary scans, split provenance, and permissive numeric admission |
| CMP-AUD-140 | P1 | Remediated | Intersection numeric-postmile collision censuses still group on display text and can split equivalent identities |
| CMP-AUD-141 | P1 | Remediated | The first Highway Detail Stage-6 artifact can report acceptance without one coherent immutable source/result transaction |
| CMP-AUD-142 | P1 | DEFERRED — HD is pre-release (owner 2026-07-21), resumes on the official HD delivery (library change → D2 version bump + re-bless when it does) | Highway Detail drops two PDF-printed snapshot dates and misdescribes them as database-only metadata |
| CMP-AUD-143 | P2 | Remediated | The Highway Detail audit's decisive Length projection inherits mutable ambient Decimal rounding context |
| CMP-AUD-144 | P1 | Resolved 2026-07-14 (printed J–P claims preserved + derived-S cross-checked; real-data verified) | Intersection Summary normalization irreversibly folds six authoritative printed control categories into one count |
| CMP-AUD-145 | P1 | Resolved 2026-07-14 (raw F descriptor retained as a declared TSNR-bound correction; drift refuses) | Intersection Summary drops the TSN PDF's erroneous raw CONTROL F label while applying the now-proven RED/MAINLINE canonical mapping |
| CMP-AUD-146 | P1 | Resolved 2026-07-14 (print identity/timing/submitter captured, typed, exactly-once; exposed in Notes) | Normalized Summary artifacts omit printed report identity, timing, and submitter provenance |
| CMP-AUD-147 | P1 | Remediated | Highway Detail detached acceptance can say accepted when audit invariants are false |
| CMP-AUD-148 | P2 | Remediated | Intersection Summary's J-component mutation probe treats the projector's correct fail-closed rejection as an audit failure |
| CMP-AUD-149 | P1 | Remediated | Summary PDF audits do not bind every loaded parser module and can miss same-version code drift |
| CMP-AUD-150 | P2 | Remediated | Intersection Summary's successful typed mutation diagnostic cannot be serialized into its result JSON |
| CMP-AUD-151 | P1 | Remediated | Intersection Summary's first green candidate lacks adversarial probes across total, geometry, raw-only, sidecar, and r7-output layers |
| CMP-AUD-152 | P1 | Remediated | Ramp Summary detached acceptance can be published for an audit-false result and has no explicit accepted Boolean |
| CMP-AUD-153 | P1 | Remediated | Ramp Summary claims complete PDF source-role disposition without exact observed-role coverage |
| CMP-AUD-154 | P2 | Remediated | Intersection Summary's per-category conservation omits multiset, target-row, and per-source-disposition typed digests |
| CMP-AUD-155 | P1 | Remediated 2026-07-16 (normalizer v4 claims capture; sidecar + Notes) | Highway Sequence normalization drops district, direction, report provenance, and source reliability policy facts |
| CMP-AUD-156 | P1 | Remediated 2026-07-16 (pointer tokens verbatim + foreign-token refusal, v4) | Highway Sequence's numeric-only distance parser erases a real printed landmark pointer |
| CMP-AUD-157 | P1 | Remediated (2026-07-17, HL normalizer v5) | Highway Log normalization drops group ownership, three printed ADT fields, totals, and report provenance |
| CMP-AUD-158 | P1 | Remediated 2026-07-16 (pre-county equates conserved with blank County, v4) | Highway Sequence drops EQUATES TO annotations that appear before county context exists |
| CMP-AUD-159 | P1 | Remediated 2026-07-16 (single-space wrap joins — no invented comma, v4) | Highway Sequence fabricates punctuation when joining one wrapped printed Description |
| CMP-AUD-160 | P1 | Resolved | The first Highway Sequence conservation gate misclassified the library placeholder as comparison truth |
| CMP-AUD-161 | P1 | Resolved | The Highway Sequence conservation gate asserted the wrong typed r7 acceptance vocabulary |
| CMP-AUD-162 | P1 | Resolved | The Highway Sequence conservation gate assumed printed and physical PDF page numbers were one-to-one |
| CMP-AUD-163 | P1 | Resolved | The first Highway Sequence detached acceptance serialized volatile output filesystem identity |
| CMP-AUD-164 | P1 | Resolved | The Highway Sequence conservation gate recorded partially asserted page-header and PDF-metadata claims |
| CMP-AUD-165 | P1 | Resolved | The Highway Sequence hardening draft generalized member-specific creation and generation times |
| CMP-AUD-166 | P1 | Resolved | The Highway Sequence hardening draft assumed every authentic PDF had identical creation and modification timestamps |
| CMP-AUD-167 | P1 | Resolved | The first Highway Log visual-sampling command silently omitted every midpoint page |
| CMP-AUD-168 | P1 | Resolved | The Highway Log visual-sample filename census admitted stale-prefix page overwrites |
| CMP-AUD-169 | P1 | Resolved | The independent XLSX reader's default XML-event ceiling rejects the authentic Highway Log normalized workbook |
| CMP-AUD-170 | P1 | Resolved | The first Highway Log synthetic negative conflated classified and unexplained projection residues |
| CMP-AUD-171 | P1 | Resolved | Highway Log invariant failures discard the completed full-corpus diagnostic before serialization |
| CMP-AUD-172 | P1 | Resolved | The Highway Log exact-total invariant retained the pre-hardening classifier census |
| CMP-AUD-173 | P1 | Resolved | The Highway Log audit's broad `LENGTH` fragment rule steals an authentic Description |
| CMP-AUD-174 | P1 | Resolved | The Highway Log audit attaches three printed dash separators as segment Descriptions |
| CMP-AUD-175 | P1 | Resolved | The Highway Log acceptance contract assumes a comma residue absent from the authoritative corpus |
| CMP-AUD-176 | P1 | Resolved | Highway Log totals reconciliation uses the wrong continuity and pairing boundaries |
| CMP-AUD-177 | P1 | Resolved | Highway Log raw-role disposition coverage is self-referential |
| CMP-AUD-178 | P2 | Resolved | Highway Log sidecar semantics under-assert the bound raw and normalized identity contract |
| CMP-AUD-179 | P1 | Resolved | Highway Log totals pairing mislabels and does not terminally bind 47 continuation/fragment claims |
| CMP-AUD-180 | P1 | Resolved | Highway Log records but does not terminally bind or stability-check its 47 loaded PDF parser modules |
| CMP-AUD-181 | P1 | Resolved | Highway Log displays but does not terminally bind its full physical-key collision census |
| CMP-AUD-182 | P1 | Resolved | Highway Log computes decisive source manifests without comparing them to frozen oracle values |
| CMP-AUD-183 | P1 | Resolved 2026-07-14 (route universe validated + producer census reconciled; real-data verified) | Intersection Summary aggregation accepts dropped and duplicate routes without validating its route universe |
| CMP-AUD-184 | P2 | Resolved 2026-07-14 (the shared note states the blank/one-sided truth) | Intersection Summary's familiar view note contradicts its structural-absence cells and cites Ramp categories |
| CMP-AUD-185 | P1 | Resolved 2026-07-14 (District compared on every RD leg; the 005/SD/72.366 disagreement surfaces; re-blessed) | Ramp Detail omits District and hides a real District disagreement as identical |
| CMP-AUD-186 | P1 | DEFERRED — HD is pre-release (owner 2026-07-21), resumes on the official HD delivery; parser rewrite, needs its own session | Highway Detail truncates multi-baseline line-two records and erases their attributes as complete |
| CMP-AUD-187 | P2 | Verified in audit harness | Independent oracle builds statewide key order quadratically |
| CMP-AUD-188 | P2 | Remediated in accepted audit artifact | Highway Detail product witness loses all returned evidence when its monolithic run exceeds the execution wrapper |
| CMP-AUD-189 | P2 | Remediated in accepted audit artifact | Highway Detail publication gate compares different duplicate-trace wire schemas byte-for-byte |
| CMP-AUD-190 | P2 | Remediated in accepted audit artifact | Highway Detail formula/value gate requires source-sheet counts both different and equal |
| CMP-AUD-191 | P1 | Remediated in accepted Stage-8 oracle | Highway Detail can classify but still leave 298 County-less Excel rows physically unattributed |
| CMP-AUD-192 | P1 | Verified source-export delta; version-separated in accepted oracle; DEFERRED — the 7.7/7.9 skew is inherent to HD's accidental pre-release window (owner 2026-07-21), resolves with the official HD delivery | Highway Detail route-005 Excel is a stale 7.7 payload beside a later PDF whose DCR owner changed on eight identical rows |
| CMP-AUD-193 | P1 | Current source correction proved; product publication and final replay pending | Highway Sequence current parity can inherit a stale cross-bundle residual and omit six July-9 Excel updates |
| CMP-AUD-194 | P2 | Remediated in independent source-oracle draft | Highway Sequence source oracle treats two visually composed legend labels as contiguous PDF text |
| CMP-AUD-195 | P2 | Remediated in independent source-oracle draft | Highway Sequence source oracle confuses harmless header-label width movement with a changed data grid |
| CMP-AUD-196 | P2 | Remediated and installed-Excel verified in source-oracle draft | Highway Sequence display projection recognizes only one case of the OOXML carriage-return escape |
| CMP-AUD-197 | P1 | Remediated for every current family: same-source flavors (owner-ruled render artifacts), the HSL vs-TSN loader, and the RD vs-TSN loader (family-censused; RD-79's Excel-vs-TSN leg amended 847→843 with source-first evidence) | Highway Sequence comparison reports four decoded carriage returns as literal `_x000d_` Description differences |
| CMP-AUD-198 | P2 | Remediated in source-bound installed-Excel artifact | Permanent installed-Excel escape probe over-specifies optional COM open arguments and cannot bind its proof artifact |
| CMP-AUD-199 | P1 | Remediated 2026-07-16 (suffix-less same-source keys; PM Suffix compared; corpus-exact) | Highway Sequence PDF-vs-Excel uses the changing equation suffix as identity, hiding moved-vs-missing semantics and forcing a route-152 cross-pair |
| CMP-AUD-200 | P2 | Remediated in source-bound current product witness | Highway Sequence product witness is externally terminated after 180 seconds and leaves a non-result partial conversion tree |
| CMP-AUD-201 | P2 | Remediated in exact product-source parity artifact | Highway Sequence parity probe requires worksheet dimensions that streaming product workbooks legitimately omit |
| CMP-AUD-202 | P2 | Remediated in three clean per-leg witnesses and independent twin audit | Highway Sequence comparison witness gives three large comparison legs one shared 600-second wrapper and is terminated during leg two |
| CMP-AUD-203 | P2 | Remediated in three clean per-leg witnesses and independent artifact-universe audit | Highway Sequence witness would reject the product's intentional permanent publication lease as unfinished output |
| CMP-AUD-204 | P1 | Remediated 2026-07-16 (TSN Descriptions verbatim incl. numeric prefixes; own-route strip only TSMIS-side) | Highway Sequence comparison deletes authoritative TSN numeric Description prefixes and false-cleans 81 current differences |
| CMP-AUD-205 | P2 | Remediated in corrected draft and direct-source r2 checkpoint; final acceptance replay pending | Highway Sequence audit projection removes a valid TSMIS outer route label but leaves its separator space on three rows |
| CMP-AUD-206 | P2 | Remediated in clean streaming-verified raw-TSN development twin | Highway Sequence raw-twin verifier requires optional worksheet dimensions from its own write-only XLSX |
| CMP-AUD-207 | P2 | Remediated in corrected draft and direct-source r2 checkpoint; final acceptance replay pending | Highway Sequence duplicate-cost projection recognizes only current TSMIS source names and treats historical Excel as TSN |
| CMP-AUD-208 | P1 | Verified in Highway Sequence evidence and Matrix publication path | Visual evidence never reads the Comparison cells it claims to verify |
| CMP-AUD-209 | P1 | Verified and quantified on both current Highway Sequence vs-normalized-TSN legs | Highway Sequence evidence excludes whole discrepancy classes before sampling |
| CMP-AUD-210 | P1 | Verified in Highway Sequence source routing, Matrix wiring, and current same-source truth | Highway Sequence Excel and PDF-vs-Excel comparisons have no source-faithful evidence path |
| CMP-AUD-211 | P2 | Remediated and independently verified in the raw-product development witness | Raw-product witness hashes a payload chunk and then separately reads different bytes for decompression |
| CMP-AUD-212 | P2 | Remediated and independently verified in the raw-product development witness | Raw-product witness accepts well-named comparison payload chunks that no sidecar references |
| CMP-AUD-213 | P2 | Remediated and verified in the five-leg development semantic oracle; direct-source permanent gate pending | Highway Sequence audit checks Summary and Spot Check formula quantity but not their cell semantics |
| CMP-AUD-214 | P2 | Remediated: banner row 15 / header row 16 / fields from 17; pins shifted atomically; exactly-one-banner gate on both twins | Spot Check immediately overwrites its intended field-by-field banner with the header row |
| CMP-AUD-215 | P2 | Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending | Source-core mutation probes prove that mutated objects differ instead of proving the real gate rejects them |
| CMP-AUD-216 | P1 | Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending | Raw semantic legs omit 46 blank-County TSN equates while labeling the 69,758-row subset as authoritative raw TSN |
| CMP-AUD-217 | P1 | Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending | Source-core hashes capture members and later reparses their paths instead of parsing the exact bytes whose identity was bound |
| CMP-AUD-218 | P1 | Remediated: Spot Check row matching rides the hidden Comparison key token + a Row-integrity line; both finding mutations proven CHECK under installed Excel | Spot Check calls its verdict independent while trusting Comparison's status and source-row pairing |
| CMP-AUD-219 | P2 | Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending | Historical TSMIS PDF rows are hardcoded with the current-PDF source role |
| CMP-AUD-220 | P1 | Remediated engine-wide via the owner-approved assignment/verdict split; the product is oracle-exact on every Highway Sequence leg | Duplicate matching ignores three source fields and changes hundreds of pair/one-sided assignments |
| CMP-AUD-221 | P1 | Remediated and verified in two byte-identical hardened classifier replays | Residual classifier declares every changed duplicate assignment explained without testing whether its asserted cause actually produced the assignment |
| CMP-AUD-222 | P2 | Remediated and verified with real Windows file/directory link mutations | Residual-classifier indirect-input guards resolve paths before checking for symlinks |
| CMP-AUD-223 | P1 | Remediated and verified with hardlink, lexical, and bound-input output rejections | Residual classifier can atomically overwrite one of its frozen inputs through an aliased `--output` after the final input guard |
| CMP-AUD-224 | P2 | Remediated and verified in direct-source raw-twin r6/r7; family acceptance pending | Raw equate topology checks every annotation forward but never proves every data-`E` row has a preceding annotation |
| CMP-AUD-225 | P2 | Remediated and verified in final direct legs and two family-gate replays | Highway Sequence one-leg witnesses allow their new output root inside a bound input-artifact directory |
| CMP-AUD-226 | P2 | Remediated and verified by delayed/full twin builds and final family replays | Direct raw-TSN twin canonicalizes ZIP timestamps but retains openpyxl's volatile core-property modified time |
| CMP-AUD-227 | P2 | Remediated and verified with real reparse mutations and final family replays | Direct raw-TSN twin calls files plain without checking Windows reparse attributes or redirected parent components |
| CMP-AUD-228 | P2 | Remediated and verified in final direct legs and two family-gate replays | Direct raw-product runner follows lexical components and final chunk aliases before its claimed non-following capture |
| CMP-AUD-229 | P1 | Remediated and verified in final direct legs and two family-gate replays | Direct raw-product runner persists terminal PASS before fallible post-result checks finish |
| CMP-AUD-230 | P1 | Remediated and verified across all 20 direct artifacts and two replays | Direct raw-product runner's final success rehashes only payload chunks, not every declared artifact |
| CMP-AUD-231 | P2 | Remediated and verified by exact-v1 mutations and final replays | Direct-v1 twin validation accepts undeclared top-level contract fields |
| CMP-AUD-232 | P1 | Remediated and verified with exact four-role code bindings and final replays | Direct raw-product completion does not bind the audit runner and build-helper bytes that produced it |
| CMP-AUD-233 | P1 | Remediated and verified with physical-distinctness controls and final replays | Direct raw-product final artifacts are not proved physically distinct from every bound input file |
| CMP-AUD-234 | P1 | Remediated and verified by 30 semantic mutations, final legs, and two replays | Detached completion publisher authenticates commit mechanics but accepts an arbitrary minimally shaped terminal payload |
| CMP-AUD-235 | P2 | Remediated and verified by retained-field/member mutations and final replays | Frozen-tree stability treats Windows' lazily populated directory `st_size` as source mutation |
| CMP-AUD-236 | P2 | Remediated; the interrupted attempt was rejected and a clean r2 completed | An external 20-minute audit wrapper interrupted Highway Log Excel publication and left incomplete temporary residue |
| CMP-AUD-237 | P2 | Remediated and verified by producer-format controls and two final-gate replays | The Highway Log audit consumer imposed a newline/canonical-format convention that identity-bound producer JSON did not promise |
| CMP-AUD-238 | P2 | Resolved | Decoder rejects `NaN`/`Infinity`, duplicate keys, and unknown envelope fields; the five frozen contract mappings are wrapped in an immutable `FrozenMap` (`dict` subclass — `asdict`/`json`/deepcopy safe) so validated invariants cannot be mutated away. Red→green in `check_comparison_contract`; suite 121/121, ruff clean |
| CMP-AUD-239 | P2 | Resolved | The Intersection Detail **TSMIS (PDF) vs TSN** comparison built no "Report View" replica though the Excel-vs-TSN one did — only the Excel `compare()` attached the Report-View `extra_sheet_writer`; the PDF flavors built a plain schema. Extracted a shared `add_report_view` helper (both vs-TSN legs project onto `SHARED_HEADER` + read the same TSN one-sided columns / TSMIS Location, so the replica is identical) and wired it into `TSMIS_PDF_VS_TSN` — NOT the same-source PDF-vs-Excel (its TSN-specific soft/structural date classification doesn't apply to two TSMIS renders). Statewide: the PDF-vs-TSN Report View renders identically (16,886 records). `check_intersection_detail_pdf` locks both (PDF-vs-TSN has it; PDF-vs-Excel does not) |
| CMP-AUD-240 | P2 | Resolved | Cross-env / baseline **Intersection Detail** refused to compare a current (2026-07-17) export against a pre-July-2026 one: the LABEL-ONLY edition change (`P`->`PP`, `S`->`PS`, INT Type/INT Eff-Date labels realigned, `Xing P/S`->`Int PS`) tripped the "different column layouts" guard even though every value stayed in an identical column position (proven cell-for-cell). Added `_id_canonical_header` to `compare_env.INTERSECTION_DETAIL` (the Highway Log CMP-AUD-048 pattern) mapping both editions to one canonical header; any OTHER header is returned UNCHANGED, so strict same-layout equality + genuine-column-move refusal are preserved (no `force_header`). Real-corpus: new-vs-old now aligns 16,459 intersections / 217 routes. Red→green in `check_compare_env_intersection` |
| CMP-AUD-241 | P2 | Resolved | The **TSMIS (PDF) vs TSN** Intersection Detail Description showed 8 trailing-tab-only false positives statewide (e.g. TSN `HILLCREST RD\t\t` vs PDF `HILLCREST RD`) that the Excel-vs-TSN leg did NOT — the TSN extract carries field-padding tabs the Excel export preserves (so Excel-vs-TSN matched) but the PDF print cannot render. Owner ruling (2026-07-17): showing two identical descriptions as a mismatch is NOT proper comparison — fix it. `_norm_text` now maps the extract's tab/CR/LF whitespace to spaces (compare_core's TRIM twin then collapses + edge-strips) on BOTH sides of the vs-TSN projection; interior content is untouched so genuine edits (incl. the KER 046 `''F''` vs `"F"` quote edit) still flag. Report-specific (NOT the shared engine, whose `_xl_trim` treats tabs as data by policy), and re-applied on read by `_normalized_row` so cached libraries need no rebuild. Real-corpus: PDF-vs-TSN Description 12->4 and total 5,100->5,092, now EQUAL to Excel-vs-TSN (unchanged 5,092/4). Red→green in `check_compare_intersection_detail_tsn` (`test_whitespace_normalization`) |
| CMP-AUD-242 | P1 | Resolved 2026-07-22 (chunk names 167→71 chars, legacy names read-compatible, two unconditional field-depth gates red→green, RD real-corpus canary-exact; rides the completion release per the owner's no-interim-release policy) | Payload chunk basename (167 chars) overran Windows MAX_PATH at the field install depth; on `LongPathsEnabled=0` machines publication failed and the matrix hid correctly-built comparisons |

The ` != ` text above represents the engine's spaced not-equal glyph. It is written
in ASCII in this ledger heading/table to keep terminals that use cp1252 from
corrupting the document; the detailed finding identifies the actual Unicode marker.

## Detailed findings

### CMP-AUD-001 — formulas and values use different equality semantics

Priority: P1  
Status: Resolved — current-code installed-Excel equality gate green 2026-07-12  
Primary code: `scripts/compare_core.py:319-325`, `376-391`, `687-714`,
`1129-1167`

The values model converts cells through `_xl_trim` and compares Python strings with
case-sensitive `==`. The live workbook uses Excel `=` over `TRIM(INDEX(...))`, which
is case-insensitive and applies Excel coercion/precision rules.

Verified examples:

| Inputs | Values/Python | Live Excel |
|---|---|---|
| `ABC` / `abc` | different | equal |
| Boolean `TRUE` / text `TRUE` | different | equal |
| integer `5` / text `5` | equal | equal |
| 17-digit number / same text | equal | rounded-number difference |
| high-precision decimal / same text | equal | rounded-number difference |

In the combined adversarial workbook, formula Summary reported 3 differing cells,
values Summary reported 4, and the values Comparison rows contained 6 marker-bearing
cells. Formula self-checks remained `OK`.

Correction requirements:

1. Define one explicit canonical equality contract.
2. Make formula cells, values cells, Spot Check, duplicate-pairing costs, Summary,
   Report View, and evidence enumeration consume that same contract.
3. Add real-Excel cases for casing, Boolean/text, 15+ digit numbers, precise decimals,
   numeric/text equivalence, and dates.

Remediation progress (2026-07-12): one frozen `ComparedCell` now owns raw values,
normalized operands, assertiveness, case-sensitive equality, display, and `E/D/N`
state. Values workbooks persist literal masks; formula workbooks independently derive
hidden, versioned, length-bounded `E/D/N/U` chunks with blank-safe `EXACT`. Displays,
Diffs, Summary, Spot Check, and conditional formatting project from state.

The adversarial post-implementation review caught two additional numeric seams.
openpyxl serializes float/Decimal NaN and infinity as deceptive blanks, so public runs
now reject all non-finite numerics before output guards/prompts or writes. Even finite
`Decimal('1.2300')`, `Decimal('1E+3')`, and exponent-form floats can be text-coerced
differently by Excel; copied source numerics are therefore exact `_xl_trim` text,
while engine counts/occurrences stay numeric and the shared helper retains its
>15-significant-digit backstop. Fixtures cover scale/exponent, small/large float
notation, and NaN/±infinity for float and Decimal. Broad ditto `.strip()` was also
replaced by ASCII-only trim.

All hermetic E1 policy checks are green. The optional `--excel` gate completed on the
current snapshot-enabled engine: formula masks, Diffs, displays, Summary counts, and
Spot Check equal the literal values twin after `CalculateFullRebuild`.

### CMP-AUD-002 — Med-Wid formula/value normalization diverges

Priority: P1  
Status: Resolved — production and installed-Excel formula/value gates green  
Primary code: `scripts/compare_core.py:339-355`, `665-669`

Python accepts only unsigned `digits[.digits]`, optionally followed by one suffix.
Excel `VALUE` also accepts signed and leading-decimal forms, while Excel equality
ignores suffix case.

Fixture pairs `06V/6V`, `-06V/-6V`, `.50/0.5`, and `06v/6V` produced three values
differences but zero live-formula differences.

Correction requirements: either implement Excel-compatible normalization in Python
and pin it, or stop using `VALUE` as a second semantic engine. Add all four pairs plus
invalid suffix/numeric controls to a real-Excel regression.

Remediation progress (2026-07-12): the approved grammar is now explicit and fail-
closed—ASCII unsigned decimal text plus at most one printable-ASCII non-digit/non-dot
suffix. Mixed Unicode-digit suffixes, non-ASCII lookalikes, and control suffixes stay
raw. The Python implementation and independent oracle are green. A five-stage hidden-
helper formula primitive (1,410 total formula characters; longest stage 598) passed
over 61,000 offline cases and installed Excel 16.0 across all 83 allowed suffixes,
canonical outputs, and case-sensitive `EXACT` pairs. Production workbook integration
now appends those live helpers after Key(helper), writes exact literal stages in the
values twin, derives state with `EXACT(CANON,CANON)`, and independently stages both
sides in Spot Check with a typed-blank wrapper before `INDEX` can coerce blank to zero.
Formula length, physical width, suffix fuzz, and all family gates are green. The full
workbook installed-Excel rebuild also proves the Med-Wid masks/displays and the
blank-versus-zero Spot Check against the literal twin.

### CMP-AUD-003 — Excel errors hide differences and invalidate Spot Check

Priority: P1  
Status: Resolved — literal-error and installed-Excel state gates green  
Primary code: `scripts/compare_core.py:634-714`, `921-924`, `1129-1167`

`TRIM(INDEX(...))` propagates Excel errors. Downstream difference counts search for
the rendered not-equal marker, so an error cell never creates that marker.

The source-data write guard does not prevent this. openpyxl classifies every member
of its `ERROR_CODES` set (`#NULL!`, `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#NUM!`,
and `#N/A`) as `data_type='e'`. `_styled(..., guard=True)` only forces strings that
start with `=`, `+`, `-`, or `@`, so all seven error tokens remain live error cells.

Verified:

- `#N/A` versus `OK`: values reports one difference; live formula cell is `#N/A`,
  Diffs is 0, and Summary certifies a match.
- `#N/A` versus `#N/A`: both Summary sheets certify a match, but the formula Spot
  Check raw cells are blank and its verdict/agreement cells are `#N/A`.

Correction requirements: define error-cell comparison policy, force recognized error-
code text to a literal string at the write boundary, represent errors without formula
propagation, and make an unusable Spot Check force a visible failed self-check rather
than coexist with a clean banner. Test all seven error tokens against ordinary text
and themselves in values/formulas/both modes with real Excel recalculation.

Additional evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_error_code_guard_93xuk5hx\result_pre_excel.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_error_code_guard_93xuk5hx\result_post_excel.json`

Remediation progress (2026-07-12): all seven Excel error tokens are forced to literal
string cells at every core and Report View source-display boundary. State formulas and
Spot Check compare those tokens without propagating Excel errors. Both Detail Report
View gates additionally freeze equal `#N/A`, equal `=1+1`/`-SAFE`, and unequal
`+LEFT/+RIGHT` and `@LEFT/@RIGHT` displays as exact string cells, closing a formula/
error-injection hole found during the E1 review. Hermetic and installed-Excel
integration gates are green.

### CMP-AUD-004 — literal difference-marker text corrupts counts

Priority: P1  
Status: Resolved — marker-independent state and installed-Excel gates green  
Primary code: `scripts/compare_core.py:67`, `888-904`, `921-939`, `1548`

The workbook infers semantic truth by searching rendered cell text for the spaced
Unicode not-equal marker. Equal source text containing that sequence is therefore
indistinguishable from generated difference text.

The ambiguity continues outside the workbook. `matrix_state.read_counts` locates the
labelled `Diffs` column but then ignores its values and rescans every displayed field
for the same marker. Matrix, day, baseline, and validation caches therefore inherit
the false count. Conditional formatting also searches the display text and paints an
equal marker-bearing value red.

Verified:

- Equal asserted value `North <not-equal> South`: Python count 0; Comparison Diffs 1;
  live Summary count 1.
- A non-asserting context value containing the marker: Python count 0; Comparison
  Diffs 1; live Summary count 1.
- Values Summary says everything matches while its Comparison says Diffs 1 and one
  Summary self-check reads `CHECK`; the live workbook says differences found and all
  self-checks read `OK`.

Correction requirements: store structured per-cell difference state. Display text,
conditional formatting, result-carried counts, `read_counts`, Matrix caches, and
validation must consume that state rather than rescan values. If `read_counts` remains
during migration, it must read validated labelled counts—not infer semantics from the
rendered fields.

Remediation progress (2026-07-12): `matrix_state.read_counts` now sums the unique,
validated numeric `Diffs` column and fails closed on missing/duplicate labels or
malformed matched rows. Its red/green fixture includes an equal source value containing
the literal marker and proves that displayed text no longer affects cached counts.
Comparison formulas, Summary field counts, Spot Check state/display agreement, and
conditional formatting now consume hidden `E/D/N/U` masks. Equal literal marker text
stays neutral and zero-diff in both workbook flavors and both typed Detail Report
Views. Offline and current-code installed-Excel gates are green.

Additional evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_read_counts_marker_clean_n1bowsrh\result.json`.

### CMP-AUD-005 — composite helper-key collision hides differences

Priority: P1  
Status: Resolved — opaque identity and installed-Excel collision gates green  
Primary code: `scripts/compare_core.py:622-652`, `1821-1838`

Consolidated helper keys flatten route, key, and occurrence with unescaped pipe
characters. Distinct tuples can become one string, and Excel `MATCH` returns the first
source row.

Fixture:

```text
A = [["R|X", "K",   "A1"], ["R", "X|K", "A2"]]
B = [["R|X", "K",   "A1"], ["R", "X|K", "B2"]]
```

Both tuple identities flatten to `R|X|K|1`. Values reports `A2` versus `B2`; live
Excel resolves both Comparison rows to the first source row, reports zero differences,
and all nine self-checks remain `OK`.

Correction requirements: use an injective encoding (for example length-prefixed
components) or independent helper columns. Regression must prove delimiter-containing
components remain distinct after Excel recalculation.

#### Remediation — 2026-07-12

The workbook no longer serializes route/key/occurrence components at all. One
versioned opaque ordinal (`__CMP_E2_KEY_V1_…`) is assigned injectively to every union
identity and reused by the Comparison and Only-in `MATCH` formulas in both flavors.
The pipe-bearing fixture now produces three distinct helpers, `Both/Both/A only`, one
real differing cell, and all Summary self-checks `OK` after installed Excel
`CalculateFullRebuild`. `check_compare_pairing_policy.py --excel` is the exit gate.

### CMP-AUD-006 — Ramp Detail PM canonicalization is incomplete

Priority: P1  
Status: Remediated 2026-07-17 (Decimal-canonical identity component)  
Primary code: `scripts/compare_tsn_common.py` (`decimal_pm`),
`scripts/compare_ramp_detail_tsn.py` (`_physical_pm_key`)

The notes explicitly state `9.6` and `009.600` identify the same ramp, but production
normalization returns `9.6` and `9.600`. Numeric/text zero variants also split: `0`,
`0.0`, and `000.000` become `0`, `0.0`, and `0.000`. End-to-end fixtures produced
one TSMIS-only plus one TSN-only row and zero matched rows for each supposedly equal
pair. Since the helper is shared with Intersection Detail and inherited by the Ramp
PDF variants, the blast radius is wider than the original boundary trace showed.

The helper's own docstring is not a usable specification: it says `0.606` remains
distinct from `000.606`, while the executable function maps both to `0.606`.

Correction requirements: first write one authoritative postmile identity contract;
then decide the permitted precision and canonical numeric representation without
binary-float rounding. Test text/numeric zero, leading and trailing zeros, signs,
prefixes/suffixes, invalid tokens, and the documented pair through both raw and
normalized-library loaders. Correct the docstring only after that decision.

**Remediation (2026-07-17).** The physical identity's postmile component is
now DECIMAL-canonical: the new shared `compare_tsn_common.decimal_pm`
(leading zeros stripped, then trailing fraction zeros and a bare dot —
`9.6` == `9.600` == `009.600` → `9.6`; `0`/`0.0`/`000.000` → `0`) feeds
`_physical_pm_key`'s `make_physical_identity`, while the norm_pm text stays
the display payload, so the two renders' printed forms remain visible where
physically identical rows now align. Intersection Detail already used this
canon (its `_decimal_pm` now delegates — byte-identical). Red→green in
`check_compare_ramp_detail_tsn.test_pm_identity_canon` (unit unification,
equal identities with distinct payloads, genuinely-different PMs still
differ) plus the deliberate re-bless of five identity-DISPLAY pins
(`1.000`-style → the canonical `1`) across that check and the
physical-identity gate (back to 11 green / 0 known-red). **Statewide
coincidence census (all three real sources — the 126 ssor-7.9 Excel
exports 15,216 rows, a fresh production PDF conversion 15,216, the raw TSN
extract 15,410; 244 route/county groups): ZERO norm-vs-decimal partition
merges — the pairing partition is IDENTICAL on the bound corpus, so every
count canary holds by construction; the visible delta is the canonical key
DISPLAY on 1,755 trailing-zero PM texts (`0.100` → `0.1`), with the PM
data cells unchanged.** Gate 127/127.


### CMP-AUD-007 — Settings validation silently omits supported comparisons

Priority: P1  
Status: Verified through executable registry and stubbed validation runs  
Primary code: `scripts/validation.py:141-163`, `194-245`,
`scripts/matrix_state.py:347-389`, `477-485`,
`scripts/gui_settings_api.py:357-359`

Validation passes each matrix export subdir directly to `_ensure_tsn_ready`. The five
PDF row subdirs are not TSN-registered; production matrix routing correctly maps them
to their base-family TSN dataset. Validation also fails to pass configured
`matrix_tsn_files` to `build_comparison`. Skipped rows do not enter
`comparisons_run`, so the UI can present `ok of ran` without revealing that five
capabilities were omitted.

Always-skipped rows:

- `highway_log_pdf`
- `intersection_detail_pdf`
- `highway_detail_pdf`
- `highway_sequence_pdf`
- `ramp_detail_pdf`

Chunk 12 reproduced both omission classes end to end. With distinct canonical and
explicit TSN workbooks, validation built from the canonical file, then the snapshot
advertised the explicit selection while rendering that canonical result fresh.
Executable census again found 12/12 TSN-capable rows but only seven validation-ready
row subdirs. Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_selected_tsn_snzyy4jm\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_coverage_census_cw4yikwk\result.json`

Correction requirements: drive validation through the row's real TSN mode mapping,
pass selected TSN files, count every expected capability in the denominator, and show
skipped/blocked totals separately. Test all 12 rows plus a selected-file-only source.

### CMP-AUD-008 — duplicate matching becomes non-optimal and non-monotonic

Priority: P2  
Status: Resolved — exact/capped typed policy and independent oracle gates green  
Primary code: `scripts/compare_core.py:372-373`, `406-494`

The matcher is exact only while the assignment permutation count is at most 5,040.
An eight-by-eight group switches to greedy selection with no warning. A reproduced
binary-field fixture scored positional 14, engine greedy 10, and true optimum 8.

The stronger advertised invariant is also false. The engine says similarity pairing
can only remove phantom differences, but an independently constructed eight-by-eight
fixture whose costs are genuine compared-field Hamming distances produced four
differences in file order and six through `pair_occurrences_by_similarity`; the exact
optimum was four. A second realizable cost fixture scored file order 31 versus greedy
32. Greedy can therefore create differences that the previous positional behavior did
not report, not merely miss the best reduction.

At the product cap, a `317 x 316` duplicate group is left in file order. Reversed
values produced 316 differences plus one A-only row; optimal matching produced zero
differences plus the same A-only row.

Correction requirements: decide a scalable optimal assignment or explicitly mark
the output incomplete when the engine cannot honor its advertised most-similar
pairing contract. At minimum, never accept a greedy score worse than positional.
Test sizes 7, 8, uneven groups, the cap boundary, ties, A/B reversal, context/Med-Wid
semantics, and formulas/values parity.

Additional evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_pairing_nonmonotone_4ozja9ro\result.json`.

#### Remediation — 2026-07-12

Every in-cap rectangular group now uses exact Hungarian assignment with the approved
two-level objective: minimum scalar cost, then lexicographically smallest smaller-side
assignment vector (side A on equal dimensions). The strict solver rejects malformed
matrices and remains rectangular at `1 × 100,000`. All retained 8×8 greedy traps and
both orientations equal an independent exhaustive oracle.

Above the 100,000-cell product cap, positional counts are explicitly partial/capped
diagnostics. Typed outcome, returned summary, workbook headline, Matrix state, and UI
can never certify a match or definitive differences. Complete traces persist original
indices, assignment vectors, pairs/costs, algorithm, dimensions, and quality; capped
groups require matching diagnostics. Lossy tuple unpacking is rejected for capped
results. Cancellation during source validation, cost construction, Hungarian scans,
capped fallback, trace construction, or typed counting returns cancelled/unknown with
no trace or workbook and preserves an existing output byte-for-byte. Locked by
`check_compare_pairing_policy.py` and `check_compare_cancellation.py`.

### CMP-AUD-009 — key identity bypasses comparison normalization

Priority: P2  
Status: Resolved 2026-07-18 — numeric identity parity added; whitespace/case deliberately significant  
Primary code: `scripts/compare_core.py` (`_key_text`, `keys_for`)

Raw route/key values are stringified without `_xl_trim` or integral-float
normalization. Verified outcomes:

```text
None / ""   -> matched
5 / "5"     -> matched
5.0 / 5     -> one-sided on each side
" K " / "K" -> one-sided on each side
"" / " "    -> one-sided on each side
```

Correction requirements: define identity normalization separately per domain; do not
blindly reuse display normalization. Add key tests for text/numeric types, spaces,
case, blanks, Unicode whitespace, and invalid-key warnings.

#### Remediation — 2026-07-18

The one genuine gap was numeric type parity: the value path already treats `5`, `"5"`,
and `5.0` as equal (`_xl_trim(5) == _xl_trim(5.0) == "5"`), but `keys_for` keyed on raw
`str()`, so a float `5.0` alignment key (`"5.0"`) never met its `"5"` twin — one physical
row split into two false one-sided rows *before* values were compared. New
`compare_core._key_text` mirrors `_xl_trim`'s numeric/bool canonicalization (integral
float → int, bool → literal) at the **bare-`str()` key branch only**. Whitespace and case
stay **significant** by deliberate design — identity must not be display-normalized;
trimming or case-folding keys would merge genuinely distinct identities, which the
finding itself cautions against. So `" K "` vs `"K"` and `""` vs `" "` remain distinct
identities, not merged.

Scope + safety: the typed `PhysicalKey` and roadbed-normalizer paths (RD/ID/HD/HSL/HL
vs-TSN, and cross-env RD/ID/HSL) never reach the `else` branch, so they are byte-identical;
the change only touches the flat bare-`str()` families (cross-env HD / HD-PDF / ID-PDF /
HSL-PDF). **Census (unreachable-on-real-data):** across 128,226 real key cells — HD 51,273
+ ID 16,459 + HSL 60,494 — the Post Mile / PM key columns are uniformly clean text with **0
numeric-typed and 0 whitespace-variant cells**, because both cross-env sides come from one
TSMIS export pipeline that formats the key identically. The shipped `_key_text` therefore
equals the old `str()` on **all 128,226** real key cells (alignment keys byte-identical);
only a hypothetical future numeric-typed key changes, and there it correctly fixes a
false-one-sided pairing (a postmile is never two distinct locations `5` and `5.0`).
Red→green in `check_compare_coercion` (`test_key_identity_numeric_parity`: float/int/text
parity, bool, whitespace + case stay significant, end-to-end 0 one-sided). Census:
scratchpad `census_009_keys.py`.

### CMP-AUD-010 — canonical raw TSN PDFs get a broken Consolidate action

Priority: P2  
Status: Verified through canonical resolver, snapshots, UI action, and endpoint  
Primary code: `scripts/tsn_library.py:622-633`,
`scripts/matrix_state.py:640-648`, `scripts/day_matrix.py:253-263`,
`scripts/ui/ui-matrix.js:363-404`, `scripts/gui_matrix.py:722-730`,
`scripts/matrix_build.py:294-305`

Canonical raw-library PDFs resolve as `kind=pdfs`, but both matrix snapshots advertise
the legacy `<dest>/_tsn_input/<report>` directory. The UI offers Consolidate for every
`pdfs` source. The endpoint rejects Ramp Summary, Intersection Summary, and Highway
Sequence; Highway Log is accepted but still reads the unrelated legacy folder.

Correction requirements: preserve source origin and real path in `tsn_meta`, route
canonical inputs through the registered TSN builder, and expose the legacy action only
for a legacy source. Test the button end to end for every PDF-backed TSN family and
both source origins.

### CMP-AUD-011 — successful validation payload drops partial count

Priority: P2  
Status: Resolved — Phase-2 validation payload gate passed 106/106  
Primary code: `scripts/validation.py:232-239`,
`scripts/gui_worker_maint.py:191-199`, `scripts/gui_settings_api.py:357-359`

The manifest correctly computes `comparisons_partial`; `ValidationWorker` omits it
from `validate_done`; the UI expects it and defaults the missing field to zero.

The same payload boundary drops a normal collector failure message. When
`evidence.collect` returned `{ok:false, message:"disk full"}`, the worker emitted an
unsuccessful terminal without `message`; the API reduced the actionable cause to
`unknown error`. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_bundle_failure_4jhd3sd6\result.json`.

Correction requirements: forward the count and add a successful-worker payload test
containing complete, partial, failed, skipped, and cancelled cells.

#### Remediation — 2026-07-11

`ValidationWorker` now forwards OK, partial, untrusted, failed, cancelled, and blocked
buckets, and preserves a false collector result's actionable message. The settings API
reports the same buckets without defaulting an omitted class to success. Locked by
`build/check_validation.py`, including the planted `disk full` collector result and
worker/API bucket parity; full runner 106/106.

### CMP-AUD-012 — values Spot Check turns blank into zero

Priority: P2  
Status: Resolved — full-display installed-Excel Spot Check gate green  
Primary code: `scripts/compare_core.py:967-1199`

In a clean values workbook, a genuinely blank Comparison cell was displayed as numeric
zero in Spot Check's Comparison-value column. The formula twin displayed blank.
`Agree?` still read `OK` because it checks marker presence rather than value parity.

Correction requirements: preserve blank display and make agreement compare the full
expected display value/status, not only the presence of a marker.

Remediation progress (2026-07-12): Spot Check independently recomputes typed state and
the complete expected display from the source sheets, projects Comparison's hidden
state, and uses `EXACT` on both state and display. Med-Wid staging tests `ISBLANK`
before `INDEX`, so a true blank remains distinct from numeric zero. Values/formulas
OOXML and installed-Excel cached evaluation gates are green.

### CMP-AUD-013 — capability support is duplicated outside the registry

Priority: P3  
Status: Resolved 2026-07-18 (`2b13df7`) — matrix mode + by-day support DERIVES from the registry; negative-mutation parity guard added  
Primary code: `scripts/day_matrix.py:53-75`,
`scripts/matrix_state.py:347-474`

Several special rows hardcode support instead of consulting `tsn_supported`, and TSN
and self comparators live in additional hand-written maps. Patching
`tsn_supported` false still left Highway Log and all five PDF rows supported.
Production identities currently match, but the claimed single source of truth is not
enforced.

Correction requirements: derive matrix mode adapters from the comparison registry or
add a blocking identity/parity test with negative support mutation.

### CMP-AUD-014 — self-consistency checks are grouped as Cross-environment

Priority: P3  
Status: Resolved 2026-07-18 (`d592462`) — new `self` (Self-consistency) sub-tab holds the five PDF-vs-Excel self-checks; keys unchanged; #mock-verified  
Primary code: `scripts/report_catalog.py:222-326`

The `env` group contains 12 folder-to-folder environment comparisons and five
same-environment PDF-versus-Excel file checks. This makes the sub-tab label inaccurate
and obscures the purpose of the self-checks.

Correction requirements: add a self-consistency group or rename/restructure the
overloaded group. Update mock, stable IDs, and UI routing tests without changing the
comparison operation keys.

### CMP-AUD-015 — Intersection comparison labels add the wrong family prefix

Priority: P3  
Status: Resolved 2026-07-18 (`af70443`) — dropped the wrong `TSAR:` prefix from the four base Intersection comparison labels; one-directional guard added (status line corrected 2026-07-18)  
Primary code: `scripts/report_catalog.py:118-130`, `241-254`, `290-301`

Export entries are `Intersection Summary` and `Intersection Detail` with no `TSAR:`
prefix. Four base comparison labels add `TSAR:` while PDF variants do not.

Correction requirements: normalize the four base labels and update the frozen catalog
and mock expectations.

### CMP-AUD-016 — classic file and Browse inputs survive recipe changes

Priority: P2  
Status: Verified with a classic-UI routing harness and all 29 endpoints  
Primary code: `scripts/ui/ui-compare.js:5,75-83,87-117,137-164,179-208`,
`scripts/gui_compare_api.py:185-203,222-267`

The classic file picker stores one global pair of paths. Switching from a Ramp
workbook recipe to PDF-vs-Excel changed the role labels but retained both old paths and
left Start enabled. The same leak exists for folders: custom report-subfolder paths
browsed under one recipe remained selected and launchable under another folder recipe.

All 17 file endpoints preflight only that both path strings are nonempty; they do not
check existence, file type, or recipe role before claiming the task and accepting the
Save selection. Absolute folders chosen with Browse likewise skip the server's report-
membership guard. With worker/Save boundaries captured, all 17 file recipes and all 12
folder recipes could be driven through those vulnerable file/Browse shapes with
deliberately nonexistent stale inputs; only later adapter execution rejects them.

Normal relative folder-dropdown selections are narrower and must not be included in
that backend claim: the dropdown is report-filtered and the endpoint rechecks that the
selected run contains a nonempty report subdirectory. That check is shallow rather
than semantic, but it does reject a missing report before Save.

Correction requirements: bind file and custom-folder selections to the stable recipe
key and role, or clear them whenever the recipe changes. Preflight existence,
file/folder type, supported role, and effective report membership before Save. Test
file-to-file and folder-to-family switches, relative dropdowns, absolute Browse paths,
deleted paths, run roots, custom report subfolders, and returning to a previously
selected recipe.

### CMP-AUD-017 — skipped inputs lose their partial completion state

Priority: P1  
Status: Resolved — Phase-2 typed-outcome/consumer gate passed 106/106  
Primary code: `scripts/compare_core.py:1913-1968`,
`scripts/matrix_build.py:175-179`, `scripts/baseline_matrix.py:409-427`,
`scripts/ui/ui-matrix.js:289-305`

`run_compare(..., warnings=[...])` correctly forces `verdict=diff` and writes an
incomplete banner, but the returned `ConsolidateResult` leaves `completion=None` and
the skipped/failed counters at zero. Matrix orchestration converts that missing value
to `complete`. The renderer ignores the cached verdict and decides from counts plus
completion, so zero counted differences and zero one-sided rows render as a green
`match / identical` cell.

Reproduction: both folders contained the same valid route plus the same unreadable
`~$...xlsx` lock file. The direct comparison logged two skipped files and returned
`verdict=diff`, but also returned `completion=None`; the readable rows had zero
differences. Recording this through the matrix path yields `completion=complete`,
which satisfies the renderer's green-match branch.

The baseline matrix reproduces the full false-green lifecycle rather than merely
inheriting it in theory. Two sides with the same valid route and an unreadable lock
file returned `verdict=diff` and `completion=None`; the baseline cache converted that
to complete, and the snapshot rendered 0/0 green even though the committed workbook
said `COULD NOT COMPARE EVERYTHING`. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_partial_xpmyff7_\result.json`.

Correction requirements: comparisons with warnings must return structured
`completion=partial`, `skipped_inputs`, and `failed_inputs`. Matrix presentation must
also honor the producer verdict as a consistency guard. Add a complete end-to-end
test from skipped folder input through cache, snapshot, and rendered cell.

#### Remediation — 2026-07-11

`run_compare` now determines typed completion and exact skipped/failed counts before
artifact commit. Matrix, day, baseline, validation, and classic UI accept state only
from the strict returned/persisted generation. Partial results are stale/retryable and
render amber without a checkmark or `match`; verdict/count contradictions fail closed.
Locked by `check_comparison_outcome.py`, `check_comparison_publication.py`,
`check_matrix.py`, `check_p2_freshness.py`, `check_mx_partial_render.js`, and
`check_classic_comparison_outcome.py`; full runner 106/106.

### CMP-AUD-018 — Intersection cross-env bypasses layout-drift validation

Priority: P1  
Status: **Resolved 2026-07-17** (census-first; one shared `record_problem`
validator gates the consolidation + cross-env paths, offline gate 130/130)  
Primary code: `scripts/consolidate_intersection_summary.py:114-126`, `263-267`,
`scripts/compare_env.py:290-327`

The consolidator owns a section-partition integrity gate, but the cross-environment
loader calls `parse_route` and emits rows without calling it. A fixture containing
Total=10 and only Highway Group R=10 made `_layout_drift` report that the
Rural/Urban/Suburban block summed 0 of 10. Two identical malformed sides nevertheless
returned `status=ok`, `verdict=match`, and `EVERYTHING MATCHES`.

Category data with a missing Total also passes: `record_has_data=True`, while
`_layout_drift(counts, None)` disables validation.

Correction requirements: share one strict parser validator across consolidation,
cross-env, and vs-TSN paths; require Total and all non-exempt partitions. Regressions
must prove two identically malformed inputs cannot match.

**Remediated 2026-07-17.** One shared validator
`consolidate_intersection_summary.record_problem(counts, total)` now owns the strict
parse-integrity rule: a data-bearing record REQUIRES a parsed Total (its absence, e.g. a
renamed/dropped "Total Intersections =" line, previously disabled `_layout_drift` since it
returns None on a falsy total) AND every non-exempt section must partition that total
exactly (Highway Group stays exempt — the site genuinely under-counts it). Both paths call
it: the **consolidator** replaced its bare `_layout_drift` call (gaining the missing-Total
case — a Total-less data route now FAILs, was silently included), and the **cross-env**
loader `_load_intersection_summary_side` now applies it after `record_has_data`, disclosing
a problem as a LOUD skip naming the route (the incompleteness channel) — so two identically
malformed sides are flagged incomplete, never a clean match. The **vs-TSN** path reads the
consolidated (already-gated) workbook and already shares the strict count parsing
(CMP-AUD-021/022) + route-universe gate (183), so it is protected transitively — no
per-route totals to re-validate.

- **Census (the false-fire guard):** a read-only sweep of all 434 real IS per-route exports
  (both environments, 217 each) found **0 layout-drift and 0 data-without-Total** — every
  real export has a valid Total with all non-exempt sections partitioning it exactly, so the
  gate never false-fires on real data.
- **Red→green:** pre-fix the cross-env loader silently INCLUDES a drifted and a Total-less
  record (would certify a clean match), and the consolidator accepts a Total-less data route;
  post-fix both disclose them. `check_consolidate_intersection` gains `record_problem` unit
  coverage + a no-Total end-to-end FAIL; `check_compare_env_intersection` gains a
  real-loader disclosure test (sound route contributes, drifted + Total-less routes named in
  `skipped`); the `check_consolidate_toctou` save-gate stub neutralizes the new validator
  like its sibling predicates (it forces an artificial empty record to isolate the TOCTOU
  behavior). Offline gate **130/130**; ruff clean.

### CMP-AUD-019 — Ramp cross-env accepts a one-field partial parse

Priority: P1  
Status: **Resolved 2026-07-17** — census-first, red→green, 126-route real-data verified  
Primary code: `scripts/consolidate_ramp_summary.py`, `scripts/compare_env.py`

**Remediation (2026-07-17).** Four coupled changes, all census-grounded on the
bound 126-route 7.9 ssor-prod corpus (0 unexplained, 0 unknown, 0 duplicate, 9
routes / 22 P/V-residual ramps = P2+V20 — matching the same-pull Detail evidence):

- `record_has_data` now requires the **Total Number of Ramps AND ≥1 populated
  category in every printed section** (Highway / On-Off / Population / printed
  Ramp Types). The `{route, total_ramps}` total-only phantom is rejected; none of
  the 126 real routes is dropped.
- New `reconcile_record` classifies each written route against the censused
  `_TSMIS_RULES` partition contract (mirrors `compare_ramp_summary_tsn`): the
  three exact blocks must sum to the route's own Total; Ramp Types is bounded. An
  **unexplained** gap (an exact block off, a Ramp-Types block over the total, or
  an unknown/duplicate matcher row) escalates the run to **PARTIAL** and names the
  route — the red in-workbook `Audit OK` cell is no longer disconnected from the
  producer result. The **explained** Ramp-Types shortfall (the TSN-only P/V dummy
  classes the Summary form never prints) is surfaced as a **typed structural-
  omission note** and stays COMPLETE. Real-corpus run: `complete`, 0 skipped/
  failed, note = "9 route(s) carry 22 ramp(s) in the TSN-only P/V dummy classes…".
- New `schema_diagnostics` surfaces the ordered, case-sensitive matcher's blind
  spots — a renamed/new label (`unknown`) or a second row for a filled category
  (`duplicate`, first-wins) — stored on internal keys and read by
  `reconcile_record`, so a silent drop can't hide behind an otherwise-reconciling
  table. `match_schema` is unchanged (still shared with the TSN parser).
- The cross-env `_load_ramp_summary_side` applies the SAME strengthened
  `record_has_data` + `reconcile_problem` gate (the sibling of the Intersection
  Summary CMP-AUD-018 gate), so two identically-malformed sides can't certify a
  clean match.

Controls (`build/check_ramp_summary_partial.py`, extended): total-only rejection,
renamed/duplicate/unknown category, explained P/V residual → COMPLETE + note,
unexplained exact-block → PARTIAL, plus `schema_diagnostics` unit coverage.
`check_compare_ramp_summary` + `check_pdf_route_universe` fixtures rebuilt to
fully-reconciling records (planted diff moved into a bounded Ramp-Types cell so
both sides still reconcile). Offline gate 130/130; ruff clean.

--- original finding ---

`record_has_data` accepts a Ramp Summary record when any one non-route value exists.
Two sides containing only `{route: 1, total_ramps: 10}`—one populated field out of 32
compared fields—returned a clean match.

The standalone consolidator uses the same predicate: a total-only or one-category
record is written and returned as `completion=complete`, even though the workbook's
other parsed sections are absent. Its red audit formulas are not reflected in the
producer result.

The source-bound Stage-8 Ramp Summary run proves the real-data consequence more
precisely. Production parsed all 126 current PDFs and projected all 3,780 source-backed
values exactly, but nine `Audit OK` formulas calculate a Ramp-Type warning while the
producer still returns `complete`, 0 skipped, 0 failed, and no warning. This is not a
parser undercount: the same-pull Detail Excel/PDF exports contain exactly 22 otherwise
unprinted P/V records across those nine routes (P=2, V=20), closing the residual to zero.
The product therefore needs a typed structural-omission disposition as well as strict
missing/duplicate/category coverage; a red formula must never be silently disconnected
from the returned producer outcome.

The raw category matcher is also case-sensitive, ordered, and first-wins:

```text
R - Right             -> recognized
R - RIGHT             -> silently missing
duplicate R - Right   -> first count retained, later count ignored
```

Correction requirements: return seen/missing/duplicate/unknown diagnostics, require
Total plus meaningful coverage of every section, and make unexplained integrity gaps
partial instead of green. Preserve the authentic P/V structural omission as an explicit
typed diagnostic rather than calling it parse loss or hiding it. Add total-only,
renamed-category, duplicate-category, unknown-category, and exact explained-residual
controls.

### CMP-AUD-020 — aggregate vs-TSN paths do not reconcile totals

Priority: P1  
Status: Resolved 2026-07-14 — censused per-side partition contract enforced; real-data verified  
Primary code: `scripts/compare_ramp_summary_tsn.py:197-209`,
`scripts/compare_intersection_summary_tsn.py:230-246`

Both recipes only check whether expected TSN keys are present. A complete universe
with every category explicitly zero and grand total 10 produced no warnings and equal
comparison rows when both sides carried the same invalid data.

Current source truth refines the Ramp rule. Across 126 current Summary routes, Highway
and Population each equal Total, while On/Off plus no-linework equals Total. The printed
14-row Ramp-Type block plus no-linework is short by 22 because the Summary form does not
print P/V; 15,216 same-pull Detail Excel rows and 15,216 Detail PDF rows prove those exact
22 records (P=2, V=20), with zero unexplained residue. Treating the printed Ramp-Type
subtotal as an unconditional equality would reject authentic source data; treating its
missing P/V as zero fabricates data.

Correction requirements: independently validate each input. Ramp must reconcile
Highway, On/Off plus no-linework, and Population exactly. It must expose the printed
Ramp-Type residual, permit it only under the explicit P/V-not-tabulated source contract,
and reconcile bound canaries to same-pull Detail P/V evidence; it must never zero-fill
those absent categories. Intersection must reconcile every partition except the
explicitly exempt Highway Group. All-zero categories plus Total=10 must be incomplete
even if both sides agree.

**Remediation (2026-07-14).** `summary_layout.SectionRule` + `reconcile_counts`
now validate each side independently in both `_load_pair`s, before any comparison
row is built: the grand total and every side-applicable category must be PRESENT
(hard stop, never a fabricated zero — `_rows` also refuses absent categories),
and every block must partition the total per a censused per-side contract.
Contracts were derived by measurement, not assumption (partition probe over the
real corpus): Ramp TSMIS = Highway/Population exact, On/Off+no-linework exact,
Ramp-Types+no-linework bounded by the P/V-not-tabulated residual (22 on the 7.9
pull, matching the Detail-proved P=2/V=20); Ramp TSN = all four blocks exact
(P/V included); Intersection TSMIS = every block exact except the bounded
site-under-counted Highway Group (−676 on ars-prod 7.9); Intersection TSN = five
blocks exact, five bounded with named censused reasons (untabulated TSMIS-only
codes −40/−40/−30; lanes >8 −3; right-channelization remainder −3 on the 2025-09
print). Bounded residuals may only run SHORT and are EXPOSED as familiar-sheet
notes + log lines via a per-run out-of-band channel (never a warning — warnings
mean unreadable inputs and would mark the run incomplete; never a fabricated
category value). A non-zero TSMIS P/V count trips a contract-change refusal.
All-zero-categories-plus-total now refuses on both sides even when they agree.
Red→green fixtures live in both `check_compare_*_tsn.py` (`test_validation_refusals`
+ the rebuilt arithmetically-consistent e2e fixtures); the accepted oracles
reproduce exactly on the real corpus post-fix (Ramp 29/0/2, 5 identical /
24 differing, totals 15,216 vs 15,410; Intersection 58/8/0, 5 identical /
53 differing, totals 16,459 vs 16,626), with the residual notes rendering as
censused. Same-pull Detail P/V canary reconciliation for the bound corpus remains
a Stage-9/10 oracle task; route-universe validation (dropped/duplicated route
detection) is NOT covered here and stays with the source-capture work (CMP-AUD-098).

### CMP-AUD-021 — aggregate count coercion silently changes data

Priority: P1  
Status: Resolved 2026-07-14 — one strict count parser promoted through every aggregate read path  
Primary code: `scripts/compare_ramp_summary_tsn.py:123-128`, `159-166`,
`scripts/compare_intersection_summary_tsn.py:170-175`, `204-222`,
`scripts/summary_layout.py:376-390`

Numeric text is ignored as missing/zero, while fractional numbers are truncated:

```text
Ramp TSMIS text "10"       -> 0
Intersection TSMIS "10"    -> absent
normalized TSN 1.9         -> 1
```

Different malformed values such as 1.1 and 1.9 can therefore compare equal. Missing
TSMIS category headers are also indistinguishable from explicit zero.

Correction requirements: promote one strict count parser. Accept integers,
comma-formatted integer strings, and integral floats; reject booleans, fractions, and
malformed text with source/category context. Preserve absent versus explicit zero.

**Remediation (2026-07-14).** `summary_layout.parse_count` is the one strict
parser: accepts ints, integral floats, and comma-formatted integer strings;
rejects booleans, fractions, negatives, and malformed text with a ValueError
naming the source file and category/column. It is now used by both `_load_tsmis`
loaders (per cell; blank cells contribute nothing — the never-tabulated P/V
columns), both `_load_tsn` normalized-workbook branches (a present row with no
count refuses), and the shared `counts_from_rows` block-walk (which the IS
consolidator now feeds RAW cell values, so a fractional per-route cell fails
that route loudly instead of silently truncating). Absent vs explicit zero is
preserved end to end: an absent column/row stays absent (reconcile_counts
decides whether it was required — CMP-AUD-020), and the two TSN normalizers
(`tsn_load_ramp_summary` / `tsn_load_intersection_summary`) now OMIT a category
the PDF didn't yield instead of writing a fabricated `[key, 0]` row (the PARTIAL
producer marking is unchanged; `check_tsn_normalizer` locks the omission).
Red→green: numeric text "10" now counts as 10 (was 0/absent), 1.9 refuses (was
1), True refuses (was 1), "1,234" parses as 1234 (was dropped). Real-corpus
oracles unchanged (see CMP-AUD-020). The pre-existing latent `str(v or "")`
antipattern note in `_norm_control_type` (Intersection Detail) is out of this
finding's scope and remains tracked in memory.

Priority: P1  
Status: Resolved 2026-07-14 — duplicate exact keys/columns refuse; only distinct legacy keys fold  
Primary code: `scripts/compare_ramp_summary_tsn.py:123-129`,
`scripts/compare_intersection_summary_tsn.py:170-176`

The same exact category repeated with counts 4 and 7 becomes 7 in Ramp Summary
(last row wins) and 11 in Intersection Summary (rows sum). Intersection legitimately
folds distinct legacy J–P/S signal keys, but that does not justify summing a repeated
identical original key.

Correction requirements: track original keys, reject duplicate exact keys, and allow
only distinct documented legacy signal keys to fold. Test repeated normal keys,
distinct J/P/S folding, and repeated J itself.

**Remediation (2026-07-14).** Both `_load_tsn` normalized-workbook branches track
ORIGINAL keys and refuse an exact repeat ("lists the category … twice"); the
Intersection fold still sums, but only across DISTINCT stale J–P/S keys (a
repeated J itself refuses). Both `_load_tsmis` loaders likewise refuse a
duplicated category COLUMN header (previously ramp last-wins / intersection
double-summed by column index). Fixtures: repeated normal key, repeated J,
distinct J/P/S fold (still 2235), and duplicated columns, in both
`check_compare_*_tsn.py`. Statewide-PDF band merging (the same block continuing
across column bands) is unaffected — duplicate detection applies where original
keys exist: the normalized workbooks and the consolidated columns.

### CMP-AUD-023 — Rural/Urban parent context can misclassify counts

Priority: P1  
Status: Resolved 2026-07-14 — parent context from labels; counted orphans refuse  
Primary code: `scripts/summary_layout.py:331-369`

A count-less `U-URBAN -I` parent row is skipped before updating parent state. The
following `-O OUTSIDE CITY=4` is then assigned to the previous Rural parent. An orphan
`-O` also defaults to Rural. The section total remains correct, so reconciliation can
pass while category values are wrong.

Correction requirements: update parent context from labels before numeric gating and
treat orphan children as ambiguous errors. A count-less U parent followed by U-O must
map correctly or fail loudly, never move to R-O.

**Remediation (2026-07-14).** `counts_from_rows` now updates the Rural/Urban
parent from the LABEL before any numeric gate, so a count-less `U-URBAN` parent
still binds its following `-O OUTSIDE CITY` to U-O; a COUNTED `-O` with no
parent in the block raises ("no preceding R-RURAL/U-URBAN parent") instead of
defaulting to Rural, while a count-less orphan label is ignored (no count to
misfile). The function is shared by the IS TSN PDF parser and the IS per-route
consolidator: the consolidator's per-file try/except turns the orphan error into
a loud per-route FAILED, and re-consolidating the real ars-prod 7.9 tree stays
217/217 with counts byte-identical to the pre-change output. Fixtures in
`check_compare_intersection_summary_tsn.test_block_walk`.

### CMP-AUD-024 — non-compared Ramp footnote forces a difference

Priority: P1  
Status: Verified in production rows and the existing end-to-end check  
Primary code: `scripts/summary_layout.py:79-88`, `159-167`,
`scripts/compare_ramp_summary_tsn.py:175-186`,
`build/check_compare_ramp_summary_tsn.py:152-170`

`Ramp Points w/out linework` is documented as displayed but not compared. The TSMIS
row builder nevertheless appends it to the comparison universe. Even value zero is a
TSMIS-only row, and any one-sided row forces `verdict=diff`. Ramp Summary vs TSN cannot
return match solely from its shared-category facts.

The accepted Stage-8 source binding fixes the current value at 59. Independent truth
contains 29 shared categories, two TSN-only Summary categories, and no TSMIS-only
comparison row. Current production instead reports 31 shared + one TSMIS-only row and
uses that 59-point display metric as a verdict input. The familiar sheet displays 59 in
the correct visual footer while its own prose says the metric is "never compared," so
the presentation and generic Comparison sheet directly contradict each other.

Correction requirements: pass footnote data separately to the familiar-sheet writer.
With all compared categories equal, footnote zero or nonzero must not change the
verdict while remaining visible on the display sheet.

### CMP-AUD-025 — Ramp P/V side taxonomy is contradictory

Priority: P2  
Status: Verified against spec metadata, emitted rows, and frozen checks  
Primary code: `scripts/summary_layout.py:159-167`,
`scripts/compare_ramp_summary_tsn.py:175-187`

P and V are described as TSN-only and one-sided by design, but their metadata defaults
to both sides and production emits TSMIS zero versus TSN count with status `Both`.

Stage-8 source evidence resolves the earlier business-decision uncertainty at the Ramp
Summary representation layer. Neither P nor V is printed in any of the 126 current
Summary PDFs or 126 Summary Excel exports. Same-pull Ramp Detail does contain 22 P/V
records (P=2, V=20), exactly explaining the Summary's unprinted residual, but those are
not Summary category counts and do not equal the TSN statewide P=122/V=81 values. The
base Summary comparison must therefore represent P and V as `Only in TSN`, with no
fabricated TSMIS zero. The familiar view may show a presentation placeholder only if it
is explicitly non-asserting and cannot change taxonomy or verdict.

Correction requirements: mark and emit P/V by side as TSN-only for this Summary recipe;
preserve absence separately from numeric zero; keep any display placeholder
non-asserting; and pin row status, counts, familiar-view text, and verdict behavior to
the accepted 29-shared/2-TSN-only contract.

**Remediation — 2026-07-14 (CMP-AUD-024 + CMP-AUD-025, both Resolved).** Mirrored the
Intersection Summary recipe, which already routes one-sided categories correctly:

- P/V categories are marked `sides="tsn"` in `summary_layout.RAMP_SUMMARY_SPEC`, and
  `compare_ramp_summary_tsn._rows` now emits `_SPEC.categories_for(side)` per side (TSMIS
  gets 29, TSN gets 31). P and V therefore land in `Only in TSN` — no fabricated TSMIS
  zero, no `Both` status.
- The `Ramp Points w/out linework` footnote no longer rides the compared rows. `compare()`
  binds a per-run `{footnote.key: value}` holder that the loader fills and
  `make_extra_sheet_writer(spec, footnote_values=…)` reads, so the value still shows on the
  familiar sheet but is never a comparison row (0 TSMIS-only). No `compare_core` change —
  the schema gets a per-run `extra_sheet_writer` via `dataclasses.replace`.

Proved red→green in `check_compare_ramp_summary_tsn` (the pre-fix engine fails on
`both==31`/`tsmis_only==1`/P-as-diff; the fix passes) **and verified on the real 7.9
SSOR-prod pair**: the fixed comparator reproduces the accepted Stage-8 oracle exactly —
**29 shared / 2 TSN-only (P, V) / 0 TSMIS-only / 5 identical / 24 differing**. Full suite
121/121, ruff clean.

### CMP-AUD-026 — PDF comparison paths discard producer completeness

Priority: P1  
Status: Resolved — exact direct/PDF input-outcome gate passed 106/106  
Primary code: `scripts/compare_env.py:330-489,659-669`,
`scripts/compare_tsn_common.py:210-222`

Highway Log, Highway Detail, Intersection Detail, Highway Sequence, and Ramp Detail
PDF consolidators correctly return usable `status=ok` workbooks with
`completion=partial`, `skipped_inputs`, and `failed_inputs`. Their environment loaders
check only `status`, discard all structured outcome data, and read whatever converted
XLSX files exist.

Verified for every family in formulas and values modes:

- Symmetric dropped lines or failed PDFs: both adapters return a clean match with no
  incomplete note.
- Same failed route on both sides: the missing route disappears and match is certified.
- Failure on only one side: the route is reported as an environment-only difference,
  with no disclosure that parsing failed.
- Clean controls correctly match.

A Highway-Log-specific producer stub returning `completion=partial`, seven skipped
inputs, and one failed input on both sides likewise became `ok/match`,
`completion=None`, and zero skipped/failed counts after the PDF environment adapter.

The direct recipes have the same trust break. Current valid outcome sidecars marked
selected Highway Log, Highway Sequence, Highway Detail, Intersection Detail, Ramp
Detail, and both Ramp Summary inputs partial; `consolidation_meta.read_completion`
read them as partial, but every comparison returned `status=ok` with
`completion=None`. The Detail pairs still returned match. The shared files driver
loads rows and optional warnings only and never reads or reduces persisted producer
completion.

All formula workbooks were recalculated in real Excel and agreed with the equally
incorrect values outputs.

Correction requirements: inspect producer completion in every environment and direct
file path, carry structured issues and counts into the comparison result, reconcile
original PDF identities against converted routes, and make incomplete state dominate
ordinary match/difference wording. Add parameterized both-mode checks over all PDF
families and triangle flavors for complete, partial-line, symmetric-failed-PDF, and
asymmetric-failed-PDF cases, including current, stale, malformed, and missing sidecars.

#### Remediation — 2026-07-11

Direct-file comparisons now consume coupled producer outcomes through
`consolidation_meta.read_outcome`. All five PDF environment families carry a typed
`LoadedSide` for each input, including completion, exact skipped/failed counters,
warnings/failures, and coverage diagnostics, into `run_compare` before commit. The
returned and persisted outcomes agree in formulas, values, and both modes under clean,
symmetric-partial, and asymmetric-partial fixtures. Locked by
`check_compare_input_outcomes.py` and `check_compare_env_pdf_completion.py`; full runner
106/106.

### CMP-AUD-027 — header-only routes silently disappear

Priority: P1  
Status: **Resolved 2026-07-17** (census-first; a header-only per-route file is
disclosed as an incomplete input, offline gate 128/128)  
Primary code: `scripts/compare_env.py:152-224`

A valid-header workbook contributing zero data rows is neither represented as an
empty route nor marked skipped. It errors only when the entire side has no rows.

Fixture: side A had matching route 001 plus header-only route 002; side B had only
matching route 001. The comparison returned `verdict=match`, said all rows matched,
and reported no route present only on A. Route 002 was erased from coverage.

Correction requirements: represent explicit empty-route presence or mark the file
incomplete; never silently discard its route identity. Test header-only on A, B, both,
and the only file on a side.

**Remediated 2026-07-17.** Census-first (the decision gate: is a data-less route
legitimate, or anomalous?). A read-only openpyxl sweep of every per-route XLSX export in
the bound 7.9 corpora — Ramp Detail 126, Highway Sequence 252, Highway Log 252 (ssor-prod),
Highway Detail 252 (ars-prod) = **756 real per-route exports; minimum data-row count
1/5/2/2; ZERO header-only files** — proves a header-only export is anomalous (likely a
truncated/interrupted export), so it must be surfaced, never silently accepted as
data-less-and-fine. Fix: in `_load_xlsx_side`, after the data-row loop, a file whose
`count == 0` appends a LOUD skip naming the route ("route NNN has a valid header but no
data rows (the export may be truncated)") into the same `skipped` incompleteness channel
the CMP-AUD-030/031 skips use — `_coerce_loaded_side` turns any non-empty `skipped` into
`completion="partial"`, so the comparison is flagged INCOMPLETE and the route is named,
never erased. The whole-empty-side case still raises loudly (unchanged); a route already
in `seen_routes` keeps a following real file for it an honest disclosed duplicate. Because
no real export is header-only, the disclosure never false-fires (every real comparison
stays complete). Proof: three tests in `check_compare_env_route_universe.py` — a
header-only file beside a real file is disclosed (real route still contributes; red→green:
pre-fix `skipped == []`), a sole header-only file errors loudly, and the finding's exact
end-to-end fixture (route 001 + header-only 002 vs route 001) now returns
`completion="partial"` with route 002 named, even though shared route 001 matches. Offline
gate 128/128; ruff clean.

### CMP-AUD-028 — missing identity columns fall back silently

Priority: P1  
Status: Verified with the real Ramp Detail adapter  
Primary code: `scripts/compare_env.py:543-557`

When configured `PM` or `Post Mile` is absent, `_resolve_key_field` logs and changes
identity semantics to column zero. The condition is absent from workbook warnings and
completion. Two identical malformed Ramp Detail workbooks missing PM returned a clean
match. Highway Sequence, Intersection Detail, and Highway Detail share the path.

Correction requirements: a configured identity column is mandatory. Reject the
layout or mark it incomplete. Add a fail-closed fixture for every keyed adapter and
prove case/whitespace-tolerant valid headers still resolve.

**Remediated 2026-07-17.** `_resolve_key_field` no longer falls back to column 0 when a CONFIGURED key column is absent — it raises a user-facing `ValueError` naming the missing column and the report, which the single `_schema` call site in `compare_folders` converts to a typed `ConsolidateResult(status="error")` (the `@comparison_result_boundary` types the return; it does not catch exceptions, so the raise is caught at the call site, matching the sibling layout gates). The legitimate no-key case (`key_col=None` — flat route-keyed reports like Highway Log use column 0) is untouched. All four keyed adapters (Ramp Detail + Highway Sequence + Intersection Detail + Highway Detail share the path) are covered. Proof (`build/check_compare_ramp_detail.py::test_missing_key_column_fails_closed`, red→green by git-stash — pre-fix `_resolve_key_field` returned 0 silently): the unit contract asserts every keyed adapter raises on a key-less header, resolves the key case/whitespace-tolerantly when present, and the unkeyed HIGHWAY_LOG still uses column 0; the end-to-end builds two IDENTICAL malformed Ramp Detail folders missing PM and asserts `compare_folders` returns an error with no workbook written (was a clean match). The downstream `_ramp_detail_env_keys` `key_field == 0` guard is now a redundant backstop. Offline gate 123/123.

### CMP-AUD-029 — Excel owner-lock files are treated as report inputs

Priority: P2  
Status: Verified  
Primary code: `scripts/compare_env.py:136-162`,
`scripts/consolidate_xlsx_base.py:116-121`

Generic cross-env discovery includes `~$*.xlsx`, unlike Intersection Summary and the
shared consolidator. Merely having a workbook open can turn identical inputs into an
incomplete comparison; CMP-AUD-017 can then render its matrix cache green.

Correction requirements: exclude owner-lock files before folder selection/loading in
every XLSX path. Identical exports plus a lock stub must remain complete with zero
skipped inputs.

**Remediated 2026-07-17.** `_find_input_dir` — the single discovery chokepoint the
generic cross-env `_load_xlsx_side` and Ramp Summary / Intersection Summary / PDF-side
loaders all glob through — now drops `~$`-prefixed names (`if not
p.name.startswith("~$")`), the same owner-lock filter the shared consolidator
(`consolidate_xlsx_base`), Intersection Summary, `baseline_matrix`, `day_matrix`,
`tsn_library`, and `validation` already applied. A lock stub can no longer open-fail
into a skip and mark identical exports incomplete. Output-safe: `~$` files exist only
transiently while Excel holds a file open, so the real corpus (which has none) globs an
identical member set. Proof
(`build/check_compare_env_route_universe.py::test_029_owner_lock_ignored`, red→green:
pre-fix a `~$hs_route_001.xlsx` stub beside the real export produced a "could not open"
skip; post-fix the stub is ignored and `skipped` is empty). The redundant `~$` re-filter
inside `_load_intersection_summary_side` is now a harmless no-op. Offline gate 125/125.

### CMP-AUD-030 — duplicate route files merge without disclosure

Priority: P2  
Status: Verified  
Primary code: `scripts/compare_env.py:205-214`

No seen-route set exists. Two route-001 workbooks on one side are concatenated. Side A
with split PM1/PM2 files and side B with one route-001 file containing both rows
returned a clean match. Stale copies and duplicate exports can therefore alter counts
without an input diagnostic.

Correction requirements: normalize and detect duplicate route tokens before reading
rows. Unless a report explicitly supports multi-file routes, duplicates must fail or
make the side incomplete.

**Remediated 2026-07-17** (with CMP-AUD-031 — one `_load_xlsx_side` batch). The loader
now keeps a per-side `seen_routes` set keyed on the NORMALIZED route (031). When a file
resolves to a route already seen on that side, it is skipped LOUDLY into the existing
`skipped` incompleteness channel (`"duplicate route <n> (already provided by another
file on this side)"`) instead of concatenating its rows — so a stale copy or split
export can never silently double a side's coverage or masquerade as a clean match. None
of the flat XLSX reports (Ramp Detail / Highway Sequence / Highway Detail / Highway Log)
supports multi-file routes, so the check is unconditional on that path. Proof
(`build/check_compare_env_route_universe.py::test_030_duplicate_route_flagged`, red→green
by git-stash — pre-fix both files' rows concatenated with an empty `skipped`): two files
resolving to route `001` on one side now yield exactly one file's rows plus a duplicate
disclosure. Output-safety: the real ssor-prod corpus loads byte-identically fixed vs
unfixed — Ramp Detail 15,216 rows / 126 routes / 0 skipped, Highway Sequence 60,494 rows
/ 252 routes / 0 skipped (each route appears once; `005` and `005S` stay distinct).
Offline gate 125/125.

### CMP-AUD-031 — flat report route padding creates false one-sided rows

Priority: P2  
Status: Verified  
Primary code: `scripts/compare_env.py:48-69`, `205-214`

Flat loaders keep the raw filename token while Summary loaders use the existing route
normalizer. Identical route data in `route_1.xlsx` and `route_001.xlsx` produced zero
matched rows plus one A-only and one B-only route. If the filename has no recognized
`route_<token>` pattern, `_route_from_name` silently uses the arbitrary stem as route
identity; a canonical Highway Detail workbook called `totally_unrelated.xlsx` was
accepted and cleanly matched. Highway Log's cross-environment XLSX path shares the
same route extraction behavior.

Correction requirements: normalize flat route tokens consistently before duplicate
detection and row construction. Test numeric and suffixed pairs such as `1/001` and
`1S/001S`. Require the route-export naming contract or reject an unrecognized name;
do not promote an arbitrary stem into a valid route.

**Remediated 2026-07-17** (with CMP-AUD-030 — one `_load_xlsx_side` batch). The flat
XLSX loader no longer keys a side off the raw filename token or an arbitrary stem. It
now (a) requires the `..._route_<n>.xlsx` export naming contract — a file without the
`_ROUTE_FROM_NAME` pattern is skipped LOUDLY (`"not a recognized '..._route_<n>.xlsx'
export name"`) rather than promoting its stem to a route identity, and (b) runs the
matched token through the same `_norm_route_key` zero-pad normalizer the Ramp Summary
path already used, so `route_1` and `route_001` resolve to the one route `001` (never
two one-sided rows) while suffixed routes stay distinct (`005S`→`005S`, `1S`→`001S`).
`_route_from_name` is untouched (still the Ramp Summary PDF fallback); only the flat
XLSX call site changed. Proof (`build/check_compare_env_route_universe.py`:
`test_031_route_token_normalized` + `test_031_non_route_name_rejected`, red→green by
git-stash — pre-fix `route_1` keyed as `"1"` and `totally_unrelated.xlsx` was promoted
to route `"TOTALLY_UNRELATED"`): the normalized token is `001`, and a non-route file is
skipped while the real route export beside it still contributes. The positive control
`test_030_031_canonical_side_unchanged` proves `005` vs `005S` stay separate with zero
skips. Output-safety: on canonical export names `_norm_route_key(m.group(1))` equals the
old `_route_from_name(p)` exactly, so the real ssor-prod corpus loads byte-identically
fixed vs unfixed (Ramp Detail routehash `fbbfdfc974e319d8`, Highway Sequence
`96808159b7c7d8d0`, both 0 skipped). Offline gate 125/125.

### CMP-AUD-032 — candidate discovery is filename-order dependent

Priority: P1  
Status: Verified  
Primary code: `scripts/compare_env.py:136-203,543-576,639-646,689-749`,
`scripts/intersection_detail_columns.py:1-41`,
`scripts/highway_detail_columns.py:72-87`

The loader globs every XLSX and, for unpinned reports, makes the alphabetically first
readable file's header canonical. A stray same-sheet workbook can cause valid files to
be skipped or make the two sides fail layout comparison. Renaming only the stray file
changes the result. Arbitrary browsed folders containing only same-sheet
`anything.xlsx` files can also return a match. Ramp Detail, Highway Sequence,
Intersection Detail, Highway Detail, and Highway Log all omit a canonical
`expected_header`, so
agreement between two malformed sides is treated as validity. The four non-Log flat
families returned `ok/match` for an identical two-column
`PM-or-Post Mile/Bogus` schema. Intersection
also cleanly matched the same obsolete 36-column layout on both sides, although its
vs-TSN loader correctly refuses that edition; Highway Detail never calls its existing
exact header recognizer. A missing key compounds this through CMP-AUD-028's column-zero
fallback. The Ramp/Highway-Sequence PDF conversion loaders are likewise unpinned;
the Intersection/Highway-Detail/Highway-Log PDF conversion loaders do carry canonical
headers. Highway Log is especially misleading: two identical 31-column `Bogus N`
headers pass the generic loader and are then force-labelled as the canonical Highway
Log fields in the output.

Correction requirements: pin every adapter to the report's canonical current schema,
then restrict candidates to the export naming contract. Reordering the same file set
must not change schema selection; two identically malformed or legacy inputs must fail,
and stray same-sheet workbooks must be ignored or make the side explicitly invalid.
Test current/current, legacy/legacy, current/legacy, missing/extra columns, and missing
keys for each family and its PDF conversion path.

**Remediation — XLSX cross-env (2026-07-18).** The naming-contract half was already
closed by CMP-AUD-031 (`_load_xlsx_side` requires `..._route_<n>.xlsx`, so a stray
`anything.xlsx` is skipped). The residual header-trust half is now pinned for all four
unprotected flat families via a `header_canonicalizer` (the pattern Highway Log already
used): a new shared `_flat_header_recognizer` factory recognizes a family's EXACT current
export header (the vs-TSN comparator's `_TSMIS_HEADER[1:]` for Ramp Detail / Highway
Sequence / Intersection Detail — unnamed columns included — and `highway_detail_columns
.HEADER` for Highway Detail) and returns None for anything else, which the config
composition turns into an "unrecognized column layout" refusal; Intersection Detail's
`_id_canonical_header` now refuses a non-edition layout instead of returning it unchanged
(it still bridges the current↔legacy label editions). So two identically-malformed,
truncated, reordered, or legacy-non-edition sides refuse instead of pairing on a
trusted-first-readable header. **Census** (bound 7.9 statewide exports: 126 RD / 252 HSL /
252 HD / 217 ID) proved each family has ONE consistent header shape, none carrying a
leading Route — so pinning drops no real file. Controls: new
`build/check_compare_env_flat_schema.py` (the per-family recognizer matrix +
current/current OK, bogus/bogus refuse, current/bogus refuse end-to-end); five existing
fixtures (`check_compare_ramp_detail`, `check_compare_highway_sequence`,
`check_compare_env_intersection`, `check_baseline_matrix`, `check_matrix`) rebuilt from
fake short headers onto the real layouts (red→green).

**Remediation — PDF-conversion path (2026-07-18, completes the finding).** The two
remaining unpinned PDF-conversion loaders now pin via the config `header_canonicalizer`
too (the config `_load` flat path applies it to `flat_pdf_loader` families exactly as to
XLSX): `HIGHWAY_SEQUENCE_PDF` reuses `_highway_sequence_canonical_header` (the PDF
conversion reproduces the Excel header verbatim — censused), and `RAMP_DETAIL_PDF` pins a
new `_ramp_detail_pdf_canonical_header` against `consolidate_tsmis_ramp_detail_pdf.HEADER`
(the 13-column print layout with the On/Off + Ramp Type sentinels the Excel export drops —
so the PDF path correctly refuses the Excel-only 11-column header). Converted-header census
ran both consolidators on real 7.9 PDFs and confirmed the exact shapes. All five PDF
loaders now pin (HL/HD/ID already did via `expected_header`). `check_compare_env_flat_schema`
gains the PDF-recognizer coverage. Offline gate 131/131; ruff clean.

### CMP-AUD-033 — normalized TSN headers are skipped, not validated

Priority: P1  
Status: Verified through reordered semantic workbooks and end-to-end comparisons  
Primary code: `scripts/compare_ramp_detail_tsn.py:175-193`,
`scripts/compare_highway_sequence_tsn.py:152-179`,
`scripts/compare_intersection_detail_tsn.py:313-329`,
`scripts/compare_highway_detail_tsn.py:336-352`

Every flat normalized-library loader selects a specially named sheet, discards its
header, and reads the remaining cells positionally. Workbooks whose headers and data
were semantically reordered were accepted in all four families. The declared Ramp
`PM=1.000` loaded as `R`; Highway Sequence `PM=1.000` loaded as `ORA`;
Intersection `PM=1.000` loaded as `R`; and Highway Detail `Post Mile=1.000` loaded
as `E`. Tagged end-to-end swaps produced exactly two false differences in Ramp
PR/HG and Highway Sequence FT/Description rather than an invalid-input result.

Correction requirements: bind each normalized sheet to an exact, versioned shared
header prefix; permit only documented sidecar columns after that prefix. Reject
missing, duplicated, reordered, or renamed shared columns before reading any row.
Exercise the raw, current-library, legacy-library, and adversarial reordered paths.

**Remediated 2026-07-17.** All four normalized-library loaders (`_load_tsn` in Ramp Detail / Highway Sequence / Intersection Detail / Highway Detail) now call the shared `compare_tsn_common.require_shared_header_prefix(header, ['Route'] + SHARED_HEADER, sidecars, name, report)` BEFORE reading any row. It binds the header to the EXACT ordered `['Route'] + SHARED_HEADER` prefix (rejecting missing, renamed, reordered, or duplicated shared columns — cell whitespace tolerated) and requires the trailing columns to be exactly the documented sidecars (RD: TSN District/County/PM Suffix; ID + HD: TSN District/County; HSL: none), rejecting an undocumented or missing sidecar. This subsumes the ad-hoc pre-county-aware shape checks it replaced in RD/ID and gives HD/HSL (which validated nothing) a real contract. The comparator owns the documented sidecar list (`_NORMALIZED_SIDECARS`), which `check_tsn_normalization_marker` proves equals the loader's `SIDECAR_HEADER` (the same mirror discipline as `NORMALIZATION_VERSION`). Because the loaders read the shared width positionally, the validator runs alongside the CMP-AUD-037 marker gate — a reordered header is refused whether or not it also carries a marker.

Proof: red→green by git-stash — pre-fix all four loaders ACCEPTED a header with its first two shared columns swapped (reading them positionally, one mis-mapped row returned); post-fix all four REFUSE. `check_tsn_normalization_marker` locks the helper unit contract (exact accepts; reordered / renamed / missing-sidecar / undocumented-trailing / duplicated all refuse), the per-loader reorder refusal for all four families, and the sidecar mirror. Each family check's own current-library fixture (with the exact header + sidecars) still loads, and the pre-county-aware fixtures now refuse through this gate. Real-corpus: the rebuilt statewide RD/ID/HD libraries (exact `['Route'] + SHARED_HEADER + sidecars` headers) are still accepted by `_load_tsn`; HSL's consolidator writes `['Route'] + SHARED_HEADER` verbatim. Offline gate 123/123.

### CMP-AUD-034 — consolidated TSMIS layout gates do not establish semantics

Priority: P1  
Status: Verified with superficially valid junk headers  
Primary code: `scripts/compare_tsn_common.py:58-84`,
`scripts/compare_ramp_detail_tsn.py:212-226`,
`scripts/compare_highway_sequence_tsn.py:143-149`,
`scripts/compare_intersection_detail_tsn.py:176-177,339-350`,
`scripts/compare_highway_detail_tsn.py:370-376`

The shared loader requires only a leading `Route`; each family then adds either no
guard, a weak width/sentinel test, or only an exact width plus final label. All four
loaders accepted headers made almost entirely of `JUNK` and projected the row by
position. Highway Sequence and Highway Detail need only `Route`; Ramp needs `PM`
somewhere in the first five cells and eleven cells total; Intersection accepts any
36-cell header ending in `Xing Line Lgth`. A shifted or wrong report can therefore
be interpreted as the intended schema and yield false differences, false one-sided
rows, or a false match.

Correction requirements: define a versioned positional-layout contract per source
edition, including enough immutable sentinels to prove every positional block. Reject
insertions, deletions, and block shifts. Where the upstream export's labels are known
to be shifted, validate the documented shifted signature rather than weakening the
gate to width alone.

**Prep 2026-07-17 (next-safe C-gate; the CONSOLIDATED-side analog of CMP-AUD-033).**
This is a safe-by-construction refusal gate: bind each `_load_tsmis` loader to the
EXACT documented consolidated header (which, for the label-shifted families, IS the
"documented shifted signature") instead of the current weak width/last-label checks.
The exact headers captured from the real ssor-prod 7.9 corpus (each carrying fixed
None cells at the header-less export columns — part of the signature, not noise):
- **Ramp Detail** (w12, None at 2/5/8): `['Route','Location',None,'PM','Date of
  Record',None,'HG','Area 4',None,'City Code','R/U','Description']`
- **Highway Sequence** (w10, None at 3/5): `['Route','County','City',None,'PM',None,
  'HG','FT','Distance To Next Point','Description']`
- **Intersection Detail** (w36, no blanks): `['Route','P','Post Mile','S','Location',
  'Date of Record','H/G','City Code','R/U','INT Type','INT Eff-Date','Ctrl T','Ctrl
  Type','Light Eff-Date','Light T/Y','ML Eff-Date','ML S/M','ML L/C','ML R/C','ML
  T/P','ML N/L','Description','Main Line Lgth','Inter Eff-Date','Inter S','Inter L',
  'Inter R','Inter T','Inter N','Int St Eff-Date','Intrte S','Intrte Route','Intrte
  Post','Intrte Mile','Xing P/S','Xing Line Lgth']`
- **Highway Detail**: capture still owed — the quick 2-route consolidation via
  `consolidate_highway_detail.consolidate` did not emit a workbook (path/signature to
  debug); capture it before binding.
**Safety DE-RISKED 2026-07-17 — the exact bind is proven source/edition-independent.**
The two prerequisites are now retired:
- **Full-statewide single-header stability** (per-route header read directly, all routes):
  RD 126/126 routes → 1 header (ssor 7.9), HSL 252/252 → 1 (ssor 7.9), ID 217/217 → 1
  (ars 7.9), HD 252/252 → 1 (ars 7.9). Every family carries exactly ONE header across its
  whole statewide corpus. HD's header is captured (`stability_034.py`): per-route w34
  `['Post Mile','Length','Date of Rec','HG','AC','Acc-Cont Eff','City','RU','RU Eff',
  'Description','NA','LB Eff','LB S/T','LB #Ln','LB S/F','LB OT-TO','LB OT-TR','LB Wid',
  'LB IN-TO','LB IN-TR','Med Eff','Med T','Med C','Med B','Med V/WDA','RB Eff','RB S/T',
  'RB #Ln','RB S/F','RB IN-TO','RB IN-TR','RB Wid','RB OT-TO','RB OT-TR']` (consolidated =
  `['Route']` + this).
- **Cross-source/env/edition equality** (`crosssource_034.py`): RD and HSL headers are
  BYTE-IDENTICAL across all six data-source/env combos (ars/ssor × dev/prod/test in the
  6-env batch) AND the 7.9 edition — 7 samples each, 1 distinct header. This confirms the
  CLAUDE.md fact that one TSMIS page serves every source/env with an identical FORMAT, so
  the header is data-source-independent (only the site EDITION changes it — exactly what
  an exact bind SHOULD refuse, matching the existing pre-July-2026 ID refusal).

**Implementation path (remaining — a large but mechanical 4-family batch, not yet done).**
Bind each `_load_tsmis` `header_ok` to `h == ['Route'] + <per-route header>`. `header_ok`
receives the loader's `[str(c).strip() if c is not None else "" for c in row]` (no
trailing-trim; `header[0]=='Route'` is checked separately). Current weak gates to replace:
RD `"PM" in h[:5] and len(h) >= 11`; ID `len==36 and h[-1]=='Xing Line Lgth'`; **HSL + HD
have NO `header_ok` at all.** Cross-cutting caveats to trace BEFORE binding: (a) **ID's
`_header_ok` is shared by the PDF-vs-Excel self-check** (`compare_intersection_detail_pdf
._load_tsmis_same_source`, line 54) — confirm the PDF-consolidated header equals the
Excel-consolidated one before binding, or the self-check's loader breaks; (b) HD/HSL PDF
loaders — verify none reuse the bound `header_ok` with a different shape; (c) the quick
`consolidate_highway_detail.consolidate()` 2-route call did not emit a workbook — reading
per-route headers directly worked, but debug the consolidate seam if the real-corpus test
consolidates. Then red→green per family (junk-middle / wrong-width / shifted refused —
proving the old gate accepted them — real header passes) + real-corpus per family.
Scripts: session scratchpad `capture_034_headers.py` / `stability_034.py` /
`crosssource_034.py`.

**Remediated 2026-07-17.** Shared `compare_tsn_common.exact_consolidated_header_ok(expected)`
builds the `header_ok` predicate that binds the CONSOLIDATED header EXACTLY (each cell
`str(c).strip()`, None→`""`, matching how `load_consolidated_rows` presents it). All four
`_load_tsmis` loaders now use it against a documented `_TSMIS_HEADER` constant, replacing
the weak gates (RD `PM in h[:5] and len>=11`; ID `len==36 and h[-1]=='Xing Line Lgth'`;
HSL + HD had none). **Caller-trace completed**: `_load_tsmis` is polymorphic — the
Highway Sequence PDF-vs-TSN, Highway Detail PDF-vs-Excel, and Intersection Detail
PDF-vs-Excel flavors load the PDF-consolidated workbook through the SAME `_load_tsmis` —
and the PDF consolidator's header was verified byte-identical to the Excel one for each
(`consolidate_tsmis_highway_sequence_pdf.HEADER`, `…_highway_detail_pdf.HD_HEADER`,
`…_intersection_detail_pdf.INTD_HEADER` all == the Excel per-route header), so one exact
bind is valid for both shapes; Ramp Detail's `_load_tsmis` is Excel-only (RD-PDF keeps its
own 14-col `_pdf_header_ok`). Proof: NEW `check_compare_consolidated_layout.py` (the exact
header + its loader-normalized form accepted; a relabelled middle column, block shift,
insertion, deletion, and route-only header refused; the OLD ID/RD gates shown accepting
the junk the exact bind refuses; an end-to-end shifted-workbook refusal per family).
Real-corpus (no false rejection): consolidating the statewide corpus per family, each
`_load_tsmis` ACCEPTS — RD 472 / HSL 3,362 / ID 1,670 / HD 2,642 rows — and the ID
PDF-consolidated workbook is accepted too (1,423 rows, polymorphic path). Five existing
fixtures that used synthetic `c1..cN` headers (valid only under the old position-only
gates) were updated to the real header (rows are positional, so no assertion changed).
Offline gate 126/126.

### CMP-AUD-035 — raw TSN admission can certify incomplete or ambiguous truth

Priority: P1  
Status: Partially remediated — original r7 admission witness accepted; **reopened
2026-07-14** for two related TSN defects (below)  

**Reopened 2026-07-14 (Codex review, verified against code).** The original raw-admission
remediation stands, but two related defects in the same TSN-admission domain are open:

1. **Certificate validation is not type-exact.** ~~`tsn_district_contract.validate_raw_manifest`
   (and the `tsn_library` sidecar checks) compare with Python `==`/`!=`, so `version=1.0`,
   `member_count=True`, or `byte_length=1.0` alias the required ints and pass.~~ **Fixed
   2026-07-14:** `validate_raw_manifest` now requires exact `int` (rejecting `bool`) for
   `version`/`member_count`/`byte_length` before the canonical dict-equality (which would
   otherwise admit `1.0==1`/`True==1`); `validate_normalized_workbook_identity` and the
   `tsn_library` certificate `schema_version` check are hardened the same way. Verified
   against 726 persisted objects (0 floats) and a real canonical manifest; guarded red→green
   in `check_tsn_district_source_contract`.
2. **Direct TSN builders lack a post-`os.replace` raw-source recheck.** The direct Highway
   Sequence and Highway Log consolidators run their last source check *before*
   `atomic_save_if` performs `os.replace`, so a source change in that interval can return
   success for stale bytes. The canonical `tsn_library.build_consolidated` path already
   rehashes post-builder; the gap is limited to direct builder/CLI use. Correct by
   re-verifying the raw source after the replace.

Both are scheduled in Wave 1 (contract & validation hardening).

**Resolved (2026-07-18) — the post-`os.replace` recheck.** Both direct builders now
re-verify the raw source AFTER the commit: `consolidate_tsn_highway_sequence.consolidate`
re-checks `source_current()` after `_write_workbook` returns committed, and
`consolidate_tsn_highway_log.consolidate` re-checks after `consolidate_xlsx` returns
`ok` — a change in the window between the pre-replace gate (`may_publish` /
`publish_guard`) and the actual `os.replace` now turns the result into an error, so the
direct/CLI path can never return a success-shaped result for a source that changed
during the final commit (mirroring the canonical wrapper's post-builder rehash).
Red→green in `check_consolidate_toctou.tsn_highway_sequence_post_replace_source_change`
(the source PDF is mutated right after the real replace via a patched `atomic_save_if`;
the recheck returns error, and an unchanged source still commits OK — the recheck is a
no-op on the happy path). HL is the symmetric application, gate-covered. Files:
`consolidate_tsn_highway_sequence.py`, `consolidate_tsn_highway_log.py`, that check.


Primary code: `scripts/compare_ramp_detail_tsn.py:136-149`,
`scripts/compare_intersection_detail_tsn.py:281-295`,
`scripts/compare_highway_detail_tsn.py:298-312`

The three statewide-XLSX raw loaders validate only the columns used to derive row
identity: `LOCATION/PM`, `LOCATION/POST_MILE`, or `RTE/POSTMILE`. Every absent
compared field is silently projected as blank. A real two-column workbook for each
family, paired with a row whose other side was blank, produced one matched row, zero
differing cells, and zero one-sided rows. The output therefore certifies equality
even though the selected TSN source contains none of the attributes being audited.

Correction requirements: require every source column used by a compared field and
explicitly classify truly optional/context columns. A missing optional column must
make completeness partial and be visible in the result; it must never silently
participate in a clean verdict. Add missing-one, missing-many, and identity-only
fixtures for all raw schemas.

#### Source-universe extension — 2026-07-12

The owner's deliberately raw-only seven-family TSN library exposed the same admission
defect one boundary earlier. `tsn_library.build_normalized` chooses the newest matching
file by filesystem mtime for every statewide source, so two ordinary XLSX/PDF candidates
silently change which authoritative truth is normalized. The Highway Log and Highway
Sequence builders accept whatever `*.pdf` members are present; they do not establish one
and only one source for each district D01-D12. Eleven districts, a duplicated district,
or a mixed-report PDF set can therefore produce success-shaped normalized data without
proving the required source universe.

The exact current raw contract is seven datasets / 29 comparison-truth members: exactly
one statewide source for Ramp Detail, Ramp Summary, Intersection Summary, Intersection
Detail, and Highway Detail, plus exactly twelve uniquely claimed D01-D12 district PDFs
for each of Highway Log and Highway Sequence. Evidence-only PDFs are a separate role and
must not enter this selector. This extends CMP-AUD-035's raw-source admission boundary;
it does not create a second finding for every family.

Correction requirements additionally include exact candidate cardinality, unique
district-role claims, filename/document/report-family agreement, and deterministic
diagnostics for missing, duplicate, extra, and wrong-role members. A malformed or
ambiguous member universe must fail before projection, even when every present member
parses cleanly. The retained red gate must cover 0/1/2 statewide candidates and all
missing/duplicate/unknown-district permutations before the current 29-member positive
manifest is allowed to pass.

The same production witness showed that the three statewide detail projectors (Ramp,
Intersection, and Highway Detail) return `status=ok` with zero skipped/failed inputs but
leave producer `completion=None`. The production library wrapper later infers complete
when it writes metadata; the builder itself never owns that truth claim. Source-first
acceptance requires an explicit complete/partial/failed producer result with admitted,
emitted, and rejected counts. A legacy inference cannot promote these three normalized
outputs by itself.

#### First admission remediation review — 2026-07-12

The exact-one statewide selector, exact ordered 18/36/56-column headers, explicit detail
completion, and stale-reuse invalidation are now focused-green and passed the real raw
workbooks. CMP-AUD-035 remains open: each real workbook has exactly one worksheet named
`Sheet 1`, but all three loaders still fall back to the first sheet when that name is
absent and ignore additional visible/hidden worksheets. A renamed first sheet with the
same header or an extra populated sheet can therefore be admitted without establishing
the complete workbook role/universe. Add exact single-sheet/name, extra-sheet,
hidden-sheet, formula/error-cell, and required per-row identity-claim controls before
promoting raw XLSX admission. HL/HSL exact D01-D12 document-claim admission also remains
red under this finding.

#### Second admission remediation review — 2026-07-12

Both raw projector paths for Ramp Detail, Intersection Detail, and Highway Detail now
require exactly one visible worksheet named `Sheet 1`, the complete ordered 18/36/56
column schema, literal non-error cells, and the mandatory nonblank identity claims that
the real sources guarantee. Renamed sheets, extra visible or hidden sheets, formulas,
Excel error cells, missing identities, 0/2-source ambiguity, stale reuse, and implicit
producer completion are permanent focused fixtures. The three authoritative real
workbooks pass with exactly 15,410 / 16,626 / 60,083 rows.

The first implementation deliberately received a real-corpus adversarial correction:
Ramp `PR` is legitimately blank on some rows, so blank PR is retained as an exact
identity component instead of being rejected or invented. Required nonblank claims are
therefore source-proved (`LOCATION+PM`, `LOCATION+POST_MILE`, and
`DIST+CNTY+RTE+POSTMILE` respectively); optional prefix/suffix components remain present
and literal.

The remaining HL/HSL gate is now implemented and focused-green in
`build/check_tsn_district_source_contract.py`: every document must claim exactly one
internal D01-D12 value; all title/group claims must agree; a Dnn filename claim, when
present, must agree but can never substitute for missing document identity; and the
source universe must contain exactly one document for every D01-D12. Missing, duplicate,
extra, out-of-domain, mixed-claim, filename-disagreeing, and failed documents return
error without publishing partial truth. That first focused pass did not close the
finding: r3 was terminated on the reuse/version bypass and r4 was later stopped on the
additional adversarial issues below. Neither partial directory is a witness.

#### District reuse review — 2026-07-12

The first district-gate implementation closed the builders but not reuse:
`tsn_library.status()` still defined district raw admission as merely `bool(raws)`, and
HL/HSL retained their prior normalization versions. An existing newer consolidated
workbook could therefore remain `current` after a district was removed and could avoid
ever passing the new document contract after upgrade. Correction requires exact
12-member cardinality in the reusable-source predicate and normalization-version bumps
for both families, forcing every existing library through the strict builder once.

Implemented and focused-green: district `raw_admissible` now means exactly 12 members;
11 and 13 members both make an otherwise newer last-good workbook non-current. Highway
Log is normalization version 4 and Highway Sequence version 3. The permanent district
contract fixture proves both version bumps and 11/12/13 reuse states.

#### Adversarial district-contract review — 2026-07-12

The first r4 run was stopped and rejected before completion after an independent review
found five remaining holes; neither the partial r3 nor partial r4 directory is evidence:

1. P1 — cardinality/version/mtime freshness is not content identity. `import_raw` uses
   `copy2`, so replacing one of 12 members with different bytes/internal district while
   preserving an older mtime can leave `status.current=True` and reuse a consolidated
   workbook without running the document parser. A successful build must persist a
   canonical raw-member content manifest and reuse must require its exact match. The
   preserved-mtime byte-replacement bypass also applies to each exact-one statewide
   source, so the reusable manifest contract is seven-family, not district-only.
2. P1 — both parsers currently log and skip a recognizable data row seen before any
   route header, then may still publish `complete`. A missed later group header can also
   leave the prior route active and misattribute rows. Recognizable unowned rows and
   unresolved header/route ownership must fail with zero rejected candidates required.
3. P2 — the first filename-token regex accepted only its first Dnn-looking token and
   tolerated trailing letters/ambiguous names such as `D01-D02`. Filename claims must
   use exact alphanumeric boundaries, enumerate all tokens, and either be absent or form
   the same singleton as the internal claim.
4. P2 — Highway Sequence could observe cancellation during the final parse and still
   publish because it did not recheck before/inside atomic commit. Cancellation must be
   checked before writing and included in the final `proceed` predicate.
5. P1 — neither builder binds source bytes before/after its long sequential parse. A
   member can be replaced mid-build and produce a mixed generation. The same canonical
   manifest must be captured before parsing, verified immediately before commit, and
   persisted beside the successful normalized artifact for future reuse.
6. P1 — the same generic manifest will close preserved-mtime reuse for all seven
   datasets, but the five statewide builders still need an immutable-snapshot or
   pre/post-at-commit stability contract. Hashing after they have already replaced the
   normalized destination cannot prove which bytes were read or preserve a last-good
   artifact on a concurrent source mutation.

#### Final focused disposition — 2026-07-12

All six review issues are now permanent green gates. Every registered dataset persists
and revalidates the exact canonical raw content manifest, so preserved-mtime replacement
cannot reuse a workbook. HL/HSL parse immutable captured PDF bytes, reject recognizable
unowned data and malformed group carry-over, require exact internal D01-D12, and check
source stability/cancellation inside final publication. The five statewide builders now
parse a private captured snapshot, re-hash the live exact-one source after projection and
  inside `atomic_save_if`, preserve last-good on detected pre-commit mutation, and return
  the exact manifest certificate consumed by the parser. A post-replace check now owns
  the narrower predicate-to-replace window. The focused fixture includes a
transient A→B→A mutation, persistent mutation, commit-time mutation, snapshot cleanup,
and certificate validation.

CMP-AUD-035 was then reopened by the witness/consumer review below. The clean r2 baseline
predates these changes; partial r3/r4 remain rejected.

#### Witness and consumer adversarial review — 2026-07-12

The first r5 run was stopped and rejected in Highway Log before any canonical family
workbook was accepted. A second independent review found these additional gaps:

1. P1 — `status()` correctly marks a normalized TSN workbook non-current when raw files
   are absent/unreadable, but `ensure_current()` returns `None`; Matrix and by-day then
   proceed with the already-resolved consolidated path. Raw deletion therefore bypasses
   the manifest contract and can still compare stale truth.
2. P1 — generic `consolidation_meta.write_outcome()` deliberately treats an absent
   sidecar as harmless for a complete ordinary consolidation. TSN now requires the
   `tsn_raw_manifest`, so a real sidecar `PermissionError` can return build success even
   though `status()` is non-current and no durable certificate exists.
3. P1 — the witness runner checks each family only around its own builder, then never
   re-discovers/re-hashes the entire raw/evidence universe. A completed early family or
   a late-added member can drift during later builds without invalidating the run.
4. P2 — the runner directly invokes thin builders rather than the production
   `tsn_library.build_consolidated()` boundary, so it does not prove durable sidecar
   publication, `status().current`, or certified reuse.
5. P2 — mutation after `atomic_save_if`'s predicate returns but before `os.replace` can
   replace the previous workbook with a complete snapshot for source A while live source
   B is present. This cannot create a mixed workbook, but the direct builder can falsely
   return success and the existing negative test overstates last-good preservation.
6. P2 — the accepted freshness test was stale: its stub lacks the now-required builder
   certificate and it explicitly regression-locks the raw-missing fail-open behavior.
7. P2 — witness provenance hashes only thin loader modules, omits shared normalizer,
   projector/raw-contract/publication code, uses a weaker stat-then-hash helper for some
   records, and writes the final result non-atomically.

Correction requirements: comparisons must require a certified current TSN source or
return a typed blocking error; TSN builds must verify durable certificate sidecars even
for complete results; the witness must exercise the production library boundary and
prove current/reuse; a final whole-run source/evidence rescan and code manifest must be
stable; direct builders must post-check the source after replacement and describe the
narrow race truthfully; permanent fixtures must cover real sidecar failure, raw removal,
post-predicate mutation, and successful certified auto-heal before another full run.

#### Second-review remediation disposition — 2026-07-12

All reopened focused gates are now green:

- `status()` preserves empty versus unreadable versus ambiguous raw admission facts;
  `ensure_current()` returns a typed failed result for any existing non-current artifact
  it cannot certify/rebuild, and rejects legacy/foreign consolidated paths. Everything
  and by-day Matrix consumers pass that resolved source into the gate and stop before the
  comparator. The first-use no-output/no-raw UX remains unchanged.
- `build_consolidated()` no longer trusts the generic complete-without-sidecar fallback:
  it re-reads the durable TSN normalization version/raw manifest through `status()` and
  returns error when the certificate cannot be verified.
- `build_normalized()` rechecks after `os.replace`; mutation in the narrow post-predicate
  window cannot return success. The fixture truthfully proves non-certification rather
  than claiming the previous bytes always survive that irreducible external-writer race.
- `build/check_tsn_freshness.py` now emits an exact builder certificate and proves
  deleted, unreadable, ambiguous, and legacy/foreign sources never reach either
  comparator; its complete suite is green.
- The phase-4 runner uses `build_consolidated(force=True)`, requires complete/0/0,
  builder certificate equality, durable sidecar, `status.current`, and unchanged
  certified reuse for every family; then it re-discovers/re-hashes the entire raw and
  evidence universe, rechecks operative code provenance, requires the exact workbook+
  sidecar universe, and atomically accepts only a complete payload.

The combined 13-check CMP-AUD-035 compatibility sweep plus compileall was green, but the
next independent probe below found two missing scenarios before r6 completed.

#### Normalized identity and post-ensure drift review — 2026-07-12

The first r6 run was stopped and rejected during Highway Log. Two high-severity
false-green paths remained outside the focused suite:

1. P1 — the raw manifest is certified only before comparison. Canonical `resolve()` does
   not return an identity token, so comparison/evidence publication and Matrix caches
   track only normalized workbook mtime. A preserved-mtime raw change after
   `ensure_current()` allowed a complete/match comparison to publish; `status()` correctly
   became non-current, but the Matrix snapshot still rendered that result fresh/match.
   Evidence-only paths can likewise use a stale canonical or legacy fallback after their
   mtime checks.
2. P1 — the required sidecar binds raw manifest, normalizer version, and normalized
   workbook mtime, but not the normalized workbook bytes/file identity. Replacing a
   certified canonical workbook with different valid bytes and restoring its mtime left
   `status.current=True`; `build_consolidated()` then reused the foreign bytes under the
   old raw certificate.

Correction requirements: the durable certificate must bind the normalized workbook's
stable content identity; canonical resolution must expose one current identity token
covering raw manifest/certification plus normalized bytes; comparison and evidence must
revalidate that token before and after work and at publication; cached Matrix/by-day
state must persist the token and require its current exact match. Permanent probes must
cover preserved-mtime normalized replacement, raw drift after `ensure_current`, stale
cached verdicts, and both evidence-only entry points before another lifecycle witness.

#### Coherent certificate-snapshot review — 2026-07-12

The normalized-workbook digest correction closed direct preserved-mtime replacement,
but an independent boundary-injection probe found a third P1 false-green path before a
new witness was started. `status()` reads the strict sidecar, raw manifest, and normalized
workbook identity sequentially and did not final-recheck earlier components. Three
separate persistent, preserved-mtime mutations were injected immediately after each
component's bound read: raw A-to-B after the raw hash, workbook A-to-B after the workbook
hash, and sidecar replacement after its bound read. In all three cases that status call
returned `current=True`, while the immediate unpatched call returned `current=False`.
The fast reuse path could therefore certify a live stale generation during the practical
raw/workbook hashing window.

Correction requirement: `current=True` must come from one coherent certificate snapshot.
After calculating the candidate token, final-re-read/re-hash the sidecar payload, exact
raw member universe/manifest, and normalized workbook identity and require exact equality
with the candidate observations. Any changed, unreadable, missing, extra, replaced, or
malformed component fails the status call closed. Preserve the permanent three-boundary
mutation fixture in addition to consumer publication guards; the latter do not repair a
false-green `status()` fast path.

The same review found a separate producer-outcome false green. A valid identity-bound
sidecar with `completion=partial` and `skipped_inputs=1` still produced
`status.current=True`; Settings therefore displayed the green/current state, and
`build_consolidated(force=False)` returned a newly synthesized `ok/complete/0/0` reuse
result. `resolve().completion` remained partial, so later comparison reduction could be
amber, but producer status and direct reuse contradicted the rule that partial truth is
never fresh/green/complete.

Correction requirement: distinguish mere byte/provenance agreement from a reusable
complete generation. Green/current and the non-force reuse fast path require the strict
persisted outcome `completion=complete`, `skipped_inputs=0`, and `failed_inputs=0` in
addition to the coherent identity snapshot. If partial artifacts remain visible for
diagnosis, preserve and return their exact persisted state; never manufacture a complete
result. Add a permanent identity-bound partial-sidecar fixture covering status, Settings,
resolve, and reuse.

#### Consumer target-lease composition review — 2026-07-12

The canonical token implementation reached comparison, formulas, evidence, Everything/
by-day caches, and both evidence-only entry points, but an independent guard-composition
probe found one P1 bypass before promotion. `_compose_source_guard()` first calls the
existing target guard as `guard(path, **binding)`. On `TypeError`, it retried
`guard(path)` even when `binding` contained `anchor_path`, `anchor_identity`, or
`directory_identity`. A legacy one-argument guard therefore returned true for an
identity-bearing descendant that `visual_evidence`'s direct fail-closed boundary would
reject. The initial permanent check covered a permissive `**kwargs` guard and missed the
fallback branch.

Correction requirement: identity-bearing bindings are mandatory lease evidence. If any
binding is present, `TypeError`, unsupported keywords, or any other exception must deny;
never retry after dropping them. The path-only compatibility fallback is permitted only
when the original call carried no binding. Add a permanent legacy one-argument negative
fixture alongside the modern target-aware positive fixture, then rerun comparison,
evidence, ownership, and consumer-token suites.

The target-binding fallback was corrected and its negative fixture turned green, but the
same review found a second P1 consumer gap. Both comparison and evidence still open the
live normalized TSN pathname after validating token A. An injected A-to-B-to-A sequence
can move A aside, put a valid workbook B at the pathname for the loader/generator, and
restore the original A before publication. The output then reflects B while the final
canonical hash again sees A and `artifact_store` again sees A's original file identity;
all persistent-drift guards pass. Evidence has the same read-by-path/revalidate-after
shape. The existing fixture only left B in place and therefore did not exercise this.

Correction requirement: comparison and evidence must consume one immutable captured
workbook generation, not reopen the mutable canonical/explicit pathname. Capture the
input through a stable descriptor into attempt-local storage, hash the captured bytes,
require exact equality with the resolved workbook-content identity/token, and use only
that captured path throughout loading/rendering. Revalidate the live generation before
and after capture and at publication, but do not treat live A's restoration as proof that
the loader read A. The capture must be owned, cleaned on every terminal path, and must not
make the published comparison sidecar depend on a deleted temporary source. Preserve a
synchronized A-to-B-to-A loader/generator fixture for comparison and evidence.

Capture design review found one additional false-complete trap that the implementation
must avoid: `compare_tsn_common._merge_input_outcomes()` reads producer completion from a
sidecar beside the path it loads. A private captured workbook has no trusted sidecar, so
an explicit selected workbook with a valid PARTIAL producer outcome would silently become
complete if the snapshot path simply replaces the semantic source path. Carry the
original trusted producer outcome structurally into the comparator, or create an internal
snapshot-bound outcome record derived from that exact trusted state; never copy/reuse the
original path-bound sidecar blindly. A permanent explicit-PARTIAL-through-capture fixture
must remain partial, and comparison metadata/workbook labels/cache must contain no
temporary pathname after safe capture cleanup.

#### Remediation closure and accepted r7 witness — 2026-07-12

The final implementation closes every CMP-AUD-035 boundary described above. A reusable
TSN generation now requires an exact complete/zero-skipped/zero-failed producer outcome,
two-pass coherent agreement among the strict sidecar, admitted raw manifest, and
normalized-workbook byte identity, and one canonical token covering that entire
generation. Matrix, by-day, formulas, evidence, and cache acceptance retain the target
lease while revalidating the source token. Comparison and normalized-workbook evidence
read one identity-checked attempt-local capture, including a capture-local structured
copy of a trusted explicit producer outcome; synchronized A-to-B-to-A path interposition
therefore cannot substitute workbook B while live workbook A is restored for publication.

The permanent adversarial gates are `build/check_tsn_status_coherence.py` and
`build/check_tsn_canonical_consumer_identity.py`. Together they cover preserved-mtime
raw/workbook/sidecar mutations after each status read, partial-sidecar non-promotion,
Settings and reuse behavior, synchronized and persistent workbook drift, explicit
PARTIAL-through-capture, identity-bound cleanup, target-lease composition, evidence
entry points, and Everything/by-day cache binding. The surrounding raw-source,
district-source, freshness, normalization, runner, Matrix, evidence, and ownership
suites also passed after the final change.

The accepted production-lifecycle result is
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r7\result.json`,
SHA-256 `b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa`.
It records schema-v2 `acceptance=complete`, all seven families complete with zero
skipped/failed inputs, stable 29-member comparison-truth and 14-member evidence source
manifests, stable 28-member code provenance, exactly 14 generated workbook/sidecar
artifacts, current coherent identity tokens, and certified unchanged immediate reuse for
every family. An independent read-only r2/r7 stream compared all sheet names, cell types,
and 5,547,205 cell values and found zero differences. Thus the hardening altered the
admission/certification/consumption contract without changing normalized source facts.

The rejected r3-r6 attempts remain retained as audit history and are not witnesses.
Immutable capture and exact manifests for the *PDF files* read by visual evidence remain
a separate Stage-10 evidence-provenance requirement: this closure covers the normalized
TSN workbook generation and does not claim that live TSMIS/TSN PDF path sets are already
immune to same-object or A-to-B-to-A content interposition. That later PDF boundary does
not reopen CMP-AUD-035.

### CMP-AUD-036 — Ramp PDF accepts a fabricated four-column shape

Priority: P1  
Status: Verified through the production PDF loader  
Primary code: `scripts/compare_ramp_detail_pdf.py:97-109`

The PDF source gate claims to require the print-only `On/Off` and `Ramp Type`
columns, but its executable test only looks for `PM` among the first five cells and
`On/Off` anywhere. A four-column `Route/Location/PM/On-Off` workbook was accepted
and expanded into the full Ramp comparison row with every absent field fabricated as
blank. Both PDF-vs-TSN and PDF-vs-Excel inherit this source loader.

Correction requirements: require the exact PDF-consolidated width, order, and all
print-only sentinels, including `Ramp Type`. Refuse truncated and Excel-shaped inputs;
test every prefix truncation and a valid PDF-consolidated control.

**Remediated 2026-07-17.** `compare_ramp_detail_pdf._load_tsmis_pdf` now gates on `_pdf_header_ok`: after trimming trailing blank cells, the header must be EXACTLY `_PDF_WIDTH` (14 = `['Route']` + the RD-PDF consolidator's 13-column print HEADER) columns, carry `PM` among the first five, and END in the two print-only sentinels `('On/Off', 'Ramp Type')` — the columns the Excel export drops. This refuses the fabricated four-column `Route/Location/PM/On-Off` shape (and every prefix truncation, which the old `PM in first five + On/Off anywhere` gate expanded with blank fields) and an Excel-consolidated pick (no print-only columns). Proof (`build/check_compare_ramp_detail_pdf.py`, red→green by git-stash — pre-fix the four-column workbook loaded one fabricated row): the full PDF-consolidated control loads; the four-column shape, a truncated shape that still carries both sentinels, an Excel-consolidated pick, and every prefix truncation all refuse; `_PDF_WIDTH` is pinned equal to `1 + len(consolidator.HEADER)` and the sentinels equal its last two labels (drift guard). Real-corpus: a fresh two-route consolidation of the bound 7.9 ssor-prod RD PDFs (324 rows) still loads through the tightened gate. Offline gate 124/124.

### CMP-AUD-037 — direct comparison bypasses normalized-library freshness

Priority: P1  
Status: Verified with legacy-normalized representations  
Primary code: `scripts/compare_ramp_detail_tsn.py:154-193`,
`scripts/compare_highway_sequence_tsn.py:152-179`,
`scripts/report_catalog.py:356-378`, `scripts/tsn_library.py:348-365`

Matrix flows can rebuild a library whose `tsn_normalization_version` is stale, but a
classic direct file comparison trusts any workbook containing the normalized sheet.
Ramp reprojects PM/date only, leaving legacy Route and Description forms; Highway
Sequence reprojects County/Description only, leaving legacy Route and PM forms. An
otherwise identical row became two one-sided rows for `005` versus `5` and
`LA 000.500` versus `LA 0.5`. The code comments promise stale-library repair, but
the direct path neither validates the version stamp nor fully re-applies identity
normalization.

Correction requirements: make direct compare validate the library sidecar/version or
fully and idempotently reproject every identity and compared field. Legacy libraries
must be rebuilt or rejected with an actionable message, never partially repaired.

**Remediated 2026-07-17 (the bucket-A sweep completed).** HSL (v4, 2026-07-16) and Highway Log (v5, 2026-07-17) already refused pre-current normalized TSN workbooks on the DIRECT path via their consolidators' in-workbook markers. The three XLSX-sourced families now do the same. Their normalized workbooks carry an in-workbook **"TSN Normalization"** marker sheet — the shared `compare_tsn_common.write_normalization_marker` / `normalization_marker_version` / `require_current_normalization` helpers, written by `tsn_library.build_normalized(marker_version=…)` on the write-only workbook — and each direct loader (`_load_tsn`) refuses a pre-current library with a rebuild hint before it trusts the normalized sheet. **Highway Detail's loader had NO freshness gate at all before this**; Ramp Detail and Intersection Detail keep their prior shape refusals for the truly-old (sidecar-less) libraries, with the marker version now catching the newer shape-valid-but-stale case the shape check cannot see. The version constant lives in each comparator (`NORMALIZATION_VERSION` — RD 5, ID 5, HD 3; the `tsn_load_*` loader already imports the comparator, so this direction avoids an import cycle) and the catalog `normalization_version` MIRRORS it (RD 4→5, ID 4→5, HD 2→3) — a drift the new `check_tsn_normalization_marker` gate rejects. Each is a MARKER-ONLY bump: the normalized rows are byte-identical to the prior version, so the D2 rebuild that adds the marker to stored libraries moves no comparison count.

Proof: red→green by git-stash (all three loaders ACCEPT a marker-less normalized library pre-fix, REFUSE it with a rebuild hint post-fix). NEW `check_tsn_normalization_marker` — the helper round-trip incl. the write-only path and the malformed-marker→0 fail-safe, the catalog-mirror invariant, and the real `build_normalized` writer seam (stamps the requested version, leaves the data sheet intact, writes nothing when asked not to). Per-family refusal/acceptance flows added to each family's own check. Real-corpus rebuild of all three statewide libraries from their bound raw XLSX — RD 15,410 rows, ID 16,626, HD 60,083 — each carrying the marker at the new version, `_load_tsn` accepting the marked build and refusing a marker-stripped copy; an RD unmarked-vs-marked rebuild proved the data rows byte-identical (additive-only). Offline gate 123/123 (full CI 128 with the JS checks).

### CMP-AUD-038 — date normalization hides malformed input

Priority: P2  
Status: Resolved 2026-07-18 — full-match + calendar-aware, invalid text preserved  
Primary code: `scripts/compare_tsn_common.py` (`iso_date`, `_valid_ymd`)

The shared Ramp/Intersection date normalizer uses prefix `re.match` and constructs a
date string without calendar validation. `02/25/1976 junk` becomes the same
`1976-02-25` as a valid source cell, while impossible `02/31/1976` becomes the
plausible-looking `1976-02-31`. Trailing corruption can therefore be erased before
comparison and invalid dates can be presented as normalized data.

Correction requirements: full-match only the documented date/time forms, parse with
calendar-aware date construction, and reject or explicitly preserve invalid source
text as a difference. Cover leap days, impossible months/days, trailing text, typed
Excel dates, timestamps, and the documented two-digit-year window.

#### Remediation — 2026-07-18

`iso_date` now `re.fullmatch`-es each documented form — TSMIS `MM/DD/YYYY`, TSN
`YYYY-MM-DD` with an optional ` HH:MM:SS[.f]` time, TSN 2-digit `YY-MM-DD` — and
constructs the ISO result only when the shared `_valid_ymd` helper (a `datetime.date`
calendar probe) confirms the date is real. Trailing corruption (`02/25/1976 junk`),
impossible dates (`02/31/1976`, `13/01/2000`), and non-leap Feb-29 (`02/29/1900`) are
returned **verbatim**, so they surface as a visible difference against a clean value
rather than being silently truncated to a plausible date or faked into an ISO string.

Discrepancy-safe by construction and by census: the strict full-match set is a strict
subset of the old prefix-match set (a `fullmatch` implies the old `match`), so no value
the old code left alone can newly normalize; and the **shipped** `iso_date` equals the
old behavior on **all 121,464 distinct date-shaped cells** harvested from the real RD +
ID corpora (TSMIS Excel exports + raw TSN extracts, both the 7.9 and 2026-07-17 ID
editions) — 0 changed normalizations, 0 valid dates moved. The only inputs whose result
changes are the trailing-junk/impossible forms, which do not occur in the corpus, so the
fix moves no real diff count. Red→green in `check_compare_tsn_common` covers leap days,
impossible months/days, trailing text on both date shapes, timestamps, the impossible
2-digit-year and impossible-ISO-timestamp cases, and the two-digit window. The
`except ValueError` in `_valid_ymd` is the sanctioned validity probe (in-place
`# silent-ok`). Census: scratchpad `census_038_dates.py` / `census_038_reverify.py`.

### CMP-AUD-039 — Report View uses a second equality model

Priority: P1  
Status: Report View slice remediated 2026-07-12; familiar category-summary slice verified/open  
Primary code: `scripts/compare_core.py:319-325,376-391`,
`scripts/compare_intersection_detail_tsn.py:692-696,738-741`,
`scripts/compare_highway_detail_tsn.py:650-654,685-688`,
`scripts/summary_layout.py:384-407,451-473`

The main comparison judges cells through `compared_cell`, whose Excel-TRIM mirror
collapses internal ASCII-space runs. Both two-line Report View writers instead call
`str(value).strip()` and compare the strings directly. For Intersection Description
`ALPHA  BETA` versus `ALPHA BETA`, the main comparison returned equal/zero diffs
while Report View displayed a red inequality and Major=1/Diffs=1. Highway Detail did
the same end to end for City `LOS  ANGELES` versus `LOS ANGELES`, including a Summary
total of zero beside Report View Major=1/Diffs=1.

Correction requirements: Report View must consume `compared_cell` results (including
context, Med-Wid, and future normalization semantics) rather than reimplementing
equality. Assert per-record Report View `Diffs` against the corresponding Comparison
row and Summary totals for formulas and values outputs.

#### Remediation and secondary-surface extension — 2026-07-12

Both Detail Report View writers now consume the public typed `compared_cell` result.
Their focused gates prove ASCII-space equality, case-sensitive differences, equal
literal ` ≠ ` content, blank-versus-zero, non-asserting context, hard/soft styling,
complete asserting-field coverage with no duplicate grid slots, and the full typed
Major/Diffs totals repeated on exactly two physical rows. The generic Summary now adds
one live aggregate invariant:
`SUM('Report View'!B:B) = 2 * SUM(Comparison!Diffs)`. Both family gates prove the
formula is present. Summary also labels Report View as a build-time snapshot and says
to regenerate after any source edit: the aggregate catches count drift, but a
same-count value/field change can remain stale and is still owned by CMP-AUD-043/
Phase 7. Formula/error-leading Report View literals now use the shared safe-cell seam.

The adversarial exit sweep found the same architectural defect in the Ramp and
Intersection `Summary by Category` extra sheet. `summary_layout._render` independently
coerces counts through `_as_int`, derives equality from a numeric delta, and chooses
red/non-red styling without consuming the typed comparison state. Existing family
checks assert only labels and presence. This remaining secondary surface stays open
under this finding and Phase 7 V1; it needs typed-state parity fixtures before it can be
called corrected.

#### Remediation — 2026-07-18 (the Summary-by-Category slice — closes the finding)

`summary_layout._render` now derives each category's flag from `compared_cell` — the
**same typed verdict** the Comparison sheet builds — instead of an independently
re-derived numeric delta. A new `typed_differ(key)` looks up the category's paired rows
and returns `compared_cell(sc, count_field, ra, rb, off).state_code == "D"`; `value_row`
and the grand-total row style red on that verdict (falling back to the numeric-delta
heuristic only when a category is one-sided or absent, exactly as before). The displayed
Δ stays numeric as a reader aid.

Agreement is by construction, not by sampling: `typed_differ` issues the identical
`compared_cell(sc, count_field, ra, rb, off)` call that `count_diffs` already made on
those same rows to produce the Comparison verdict — so the familiar sheet's flag *is*
that verdict, and there is no new failure mode (every such call already succeeded when
the comparison ran). It is also a no-op on real output: the strict aggregate count parser
(CMP-AUD-021) guarantees integer counts, for which `compared_cell` returns `D` iff
`delta != 0`, so the styling is unchanged on every real comparison. The change is proven
by a discriminating red→green fixture — a count that is text-different but numeric-equal
(`5` vs `"05"`): the numeric delta says equal while the typed verdict says different, and
the sheet now follows the verdict — in `check_compare_ramp_summary_tsn`
(`test_summary_by_category_typed_parity`), with the shared `_render` thereby covering the
Intersection Summary sheet too. This closes the last open 039 slice; see CMP-AUD-043 for
the paired staleness disclosure.

### CMP-AUD-040 — distinct labels can resolve to the same effective input

Priority: P1  
Status: Verified through file and folder adapters  
Primary code: `scripts/compare_tsn_common.py:194-204`,
`scripts/compare_env.py:136-145,598-608`,
`scripts/gui_compare_api.py:180-203,222-266`

File comparisons have no same-input check. Highway Sequence PDF-vs-Excel accepted
the exact same resolved workbook for both labels and returned `ok` with one identical
row and zero differences. Folder comparisons reject exactly equal selected roots,
but compare that selection rather than each side's effective report directory. A run
root on side A and that same run's `highway_detail` subfolder on side B passed the
guard, resolved to the same XLSX set, and returned a clean match. The alias applies
to every environment adapter that accepts either a run root or report subfolder.

Correction requirements: resolve the effective inputs before launching and reject
same-file identities (`samefile`, not just path text), equal effective report roots,
and overlapping/identical discovered file sets. Keep a deliberate internal self-test
escape hatch separate from user-facing comparison recipes if one is needed.

**Partially remediated (2026-07-17, the bucket-A sweep).** The FILE half is closed by CMP-AUD-066: the same resolved workbook can no longer satisfy both labels of a PDF-vs-Excel flavor — marked it refuses the Excel role, unmarked it refuses the PDF role (probe: both directions error on the exact original case). The FOLDER half — a run root on one side aliasing its own report subfolder on the other through compare_env — remains open (bucket D/E).

**Resolved — folder half (2026-07-18).** `compare_env.EnvCompare.compare_folders` now compares the two sides' EFFECTIVE report directories (and discovered file sets), not just the selected roots. New `_effective_input_dir(folder)` resolves `<folder>/<subdir>` when that holds the files else `<folder>` (via `_find_input_dir`, `.resolve()`-canonical). The guard refuses when the two effective dirs are equal OR (with files present) the two canonical file sets are identical — catching a run ROOT vs that run's `<report>` SUBFOLDER, and a junction/hardlinked tree aliasing the same files, both of which the plain selected-root equality missed. **Census** (real 7.9 `ssor-prod`/`ars-prod` cross-env, HD/RD/ID/HSL): 0 false-rejections — every legitimate pair resolves to different effective dirs — and the root-vs-subfolder alias is caught for every report that has files (HD 252 / ID 217 on ars, RD 126 / HSL 252 on ssor). Red→green in `check_compare_env_sidelabel.test_040_folder_root_subfolder_alias` (alias rejected before loading; two different run folders proceed). Files: `compare_env.py`, that check.

### CMP-AUD-041 — selected or derived output aliasing can destroy a source

Priority: P1  
Status: Resolved — Phase-1 alias/consent/transaction gate passed 98/98  
Primary code: `scripts/gui_compare_api.py:146-177`,
`scripts/artifact_store.py:221-303`, `scripts/compare_tsn_common.py:194-204`,
`scripts/matrix_build.py:471-521`, `scripts/day_matrix.py:408-433`,
`scripts/visual_evidence.py:179-184,592-649`

Neither the classic API, adapter driver, nor transactional artifact commit receives
or checks the input identities when validating the chosen output. In a temp fixture,
the output was set to the selected Highway Sequence source workbook. The normal UI
commit flow built a valid comparison in a sibling temp file and atomically replaced
the source; its original report sheet disappeared and was replaced by Summary,
Comparison, Only-in, and input-copy sheets. Overwrite confirmation does not establish
that destroying an input is a valid comparison operation.

Both mode expands the destructive surface to an unselected derived destination. The
native Save dialog confirms only the picked formulas path; `_launch_compare` does not
pass a confirmation callback to `commit_workbook`, whose default approves both the
picked file and its derived ` (values)` twin. A pre-existing twin containing a
`UserData` sheet was silently replaced by a Comparison workbook, and a `UserRace` twin
created during production was also overwritten. The derived twin can itself be either
comparison source, so a safe picked output path can still destroy an input.

The shared and day Matrix paths have the same alias class. Selecting the exact TSN
workbook path that the Matrix will use as its comparison destination let the adapter
read the original source and then atomically replace it with the generated Comparison
workbook. Formula siblings can likewise alias a selected source. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_matrix_tsn_alias_gukunz5m\result.json`.

Visual-evidence publication adds a third derived destination with no alias guard.
Selecting `<comparison> (evidence).xlsx` as the TSN source let evidence generation
load that workbook and then replace it with an evidence Summary workbook. The main
comparison destination itself was safe; its undisclosed evidence sibling destroyed
the source afterward. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_alias_9aioh1el\result.json`.

Correction requirements: resolve both final output paths before production; reject
either one if it aliases an input, and explicitly disclose/confirm every existing
destination. Pass the real decision through transactional commit and re-confirm a
destination that appears during production. Enforce the guard in both the API and the
lower-level driver/commit contract. Test canonical paths, symlinks/junctions,
case-insensitive aliases, pre-existing/late twins, locked twins, declines, and all
output modes.

#### Remediation — 2026-07-11

`artifact_store.ensure_outputs_do_not_alias_sources` now binds every selected/effective
source and rejects direct, canonical, case-folded, hardlink, linked-directory, nested,
and derived-twin aliases before production and again before publication. Direct folder
and file drivers enforce the same contract, including their discovered file set.
Classic both-mode parks the request behind a single-use server token bound to the exact
derived values path; decline, mismatch, replay, or a late unapproved destination cannot
launch/overwrite. Workbooks and visual evidence use unpredictable, exclusively created,
identity-bound temps/quarantines/fallbacks and retain uncertain replacements.

Locked by `check_artifact_store.py`, `check_compare_env_sidelabel.py`,
`check_compare_tsn_common.py`, `check_gui_bridge.py`,
`check_compare_overwrite_consent.js`, `check_formulas_twin_guard.py`, and
`check_visual_evidence.py`; full runner: 98/98. Residual: the native Save dialog does
not expose whether its own overwrite prompt was accepted, so the return-to-first-
`exists()` interval remains the smallest observable dialog gap. Every later boundary is
rechecked and transactional.

### CMP-AUD-042 — normalized Highway Detail erases the PS marker

Priority: P1  
Status: **Resolved 2026-07-21 (`06f2d85`)** — `_normalized_row` consumes the stored PS
value; only the RAW paths call `pm_suffix`.  
Primary code: `scripts/compare_highway_detail_tsn.py:176-182,321-332`,
`scripts/tsn_load_highway_detail.py:34-68,81-94`

#### Remediation — 2026-07-21

`_normalized_row` re-projects an already-projected library row and its docstring
promises every projection is idempotent on already-normalized values. PS was the
exception: it re-ran `pm_suffix()` over the STORED marker, which parsed `E` as a
glued postmile token, found no trailing letters, and returned `""`. A row whose PS
genuinely differed from TSMIS therefore reported a clean zero-difference match on
Comparison, Summary and Report View — an invented match, the worst failure class in
this engine. Highway Detail PDF-vs-TSN inherited the same loader.

The stored value is now consumed directly (`_project`), which is idempotent by
construction. `pm_suffix` remains correct and unchanged on the RAW paths, which see
a real postmile token plus `E_IND`.

Proved idempotent — raw → normalized → re-projected is stable for BOTH PS and the
roadbed-aware Post Mile key — across every blank/E × roadbed/equation combination the
finding required: `044.236`/E, `044.236`/blank, `R044.236R`/E, `R044.236L`/blank,
`044.236R`/E, `012.500R`/blank, `L012.500`/E. Red→green: with the change reverted a
stored `E` re-projects to `''` and both new pins fail. Suite 144/144.

No `normalization_version` bump or user rebuild: the library CONTENT is unchanged —
only its re-projection at comparison time was wrong.

The current library builder stores the already-projected `PS` cell as blank or `E`.
The normalized-library reader incorrectly treats that cell as a glued postmile token
and calls `pm_suffix` again; `pm_suffix("E")` returns blank. Against an identical
TSMIS row whose PS was blank, the valid raw TSN fixture reported `(blank) != E`, one
different cell, and Report View Diffs=1/Major=0. The canonical normalized fixture
silently erased `E` and returned a clean zero-difference match on Comparison,
Summary, and Report View. Highway Detail PDF-vs-TSN inherits the same TSN loader.

Correction requirements: make normalized reprojection idempotent: consume the stored
PS value directly (or store/reconstruct the source token unambiguously). Prove raw and
current normalized libraries project every row identically, with explicit blank/E and
roadbed/equation combinations.

### CMP-AUD-043 — live formulas do not drive Report View

Priority: P1  
Status: Verified in installed Excel with `CalculateFullRebuild()`  
Primary code: `scripts/compare_intersection_detail_tsn.py:731-741,848-866`,
`scripts/compare_highway_detail_tsn.py:680-697,772-788`,
`scripts/summary_layout.py:391-482`,
`scripts/compare_ramp_summary_tsn.py:58`,
`scripts/compare_intersection_summary_tsn.py:88`

Both Report View writers emit literal snapshot values even in the live-formulas
workbook. Starting from clean comparisons, the copied TSN input sheet was edited in
Excel and fully recalculated. In Intersection Detail, Description changed; in Highway
Detail, City changed. Comparison, Summary, and Spot Check all updated to one
difference and every self-check stayed `OK`, while each Report View remained
Major=0/Diffs=0 with its old text. A workbook advertised as live can therefore show
two mutually incompatible answers after its supported recalculation workflow.

Correction requirements: either make Report View formulas reference the live input
and pairing cells, or mark/remove it from formulas output and make the snapshot limit
unmistakable. Acceptance must edit both sides, add/remove differences, recalculate in
real Excel, and assert Report View against Comparison/Summary for both families.

The 2026-07-12 exit sweep extended this finding to the familiar Ramp/Intersection
`Summary by Category` sheets. The shared extra writer emits literal counts, deltas, and
styling in both workbook modes. After a supported formulas-mode edit/recalculation,
the generic Comparison, Summary, and Spot Check can update while this sheet remains at
its build-time answer. Phase 7 V1 therefore covers every familiar secondary sheet, not
only sheets literally named `Report View`; each must become live or carry an
unmistakable values-only generation/snapshot label and an installed-Excel edit gate.

#### Remediation — 2026-07-18

Both familiar secondary surfaces take the finding's accepted second path — "carry an
unmistakable values-only generation/snapshot label." The Report View was labeled a
build-time snapshot in the 2026-07-12 remediation (with the live `SUM('Report View'!B:B)
= 2 * SUM(Comparison!Diffs)` aggregate invariant catching count drift). The shared
`summary_layout._render` Summary-by-Category sheet now carries an unmistakable disclosure
line — "These counts are a build-time snapshot and do NOT recalculate; regenerate the
comparison after editing a source file" — so a reader cannot mistake its literal counts
for live values after a formulas-mode recalculation. The static edit gate is the
label-presence assertion in both family checks (`check_compare_ramp_summary_tsn` and
`check_compare_intersection_summary_tsn`), matching how the Report View slice's gate
proves its snapshot label / invariant formula is present. The paired CMP-AUD-039
remediation makes the same sheet's flags consume the typed verdict, so what the snapshot
shows is exactly the Comparison verdict at build time.

### CMP-AUD-044 — trailing blank headers truncate real data

Priority: P1  
Status: Verified end to end in the flat cross-environment loader  
Primary code: `scripts/compare_env.py:188-190,208-211`,
`scripts/compare_highway_log.py:94-124`

The loader removes blank cells from the end of the selected header and then slices
every row to that shortened width without checking the discarded cells. With header
`[Post Mile, V, blank]`, side A row `[1, same, A-ONLY]`, and side B row
`[1, same, B-ONLY]`, Highway Detail returned `ok/match` with zero differences. The
only differing evidence existed beneath the blank header and never reached the
comparison. The same shared path serves all flat cross-environment families. Highway
Log's direct file loader independently repeats the trim-and-slice pattern; a canonical
31-column header plus a blank 32nd header hid `A-ONLY` versus `B-ONLY` data and also
returned zero differences.

#### Remediation — 2026-07-18

Both trim-and-slice loaders now reject data outside the declared width instead of
silently truncating it. In the row loop, before slicing to `r[:n]`, each checks
`any(v is not None and str(v).strip() != "" for v in r[n:])` — a nonblank cell beyond
the trimmed header is real data under a trailing blank header. `compare_env
._load_xlsx_side` refuses the file into the existing incompleteness channel (a loud
`skipped` entry naming it, exactly like the CMP-AUD-027/030/031 skips, so the whole
comparison is marked partial rather than certifying a clean match); the file's rows are
accumulated locally and discarded on overflow so no partial rows leak. `compare_highway
_log._load_input` raises its user-safe `ValueError` (its raise-on-bad-shape contract).
The blank-labelled column is not preserved-and-compared (the finding's alternative)
because no real export uses one — refusing keeps a would-be data-loss loud without
adding a speculative compared column.

Census-proven no-op on real data: the census computes exactly the fix's trigger — a
nonblank cell beyond the trimmed header width — across 1,316 real flat exports (HD 252,
HSL 252, RD 126, HL 252, ID 217×2); every file has a uniform trimmed-header width (HD
34, HSL 9, RD 11, HL 31, ID 35) and **0** carry any data beyond it, so the new refusal
branch never fires. Confirmed end-to-end by loading all 252 real HD exports through the
fixed `_load_xlsx_side` (51,273 rows, 0 skips, 0 overflow refusals). Red→green in
`check_compare_env_route_universe` (the overflow file is refused while a clean file
beside it still contributes) and `check_compare_highway_log` (the loader raises
"beyond … header"). Census: scratchpad `census_044_trailing.py`.

Correction requirements: after binding the canonical schema, reject any nonblank cell
outside its declared width. If an upstream blank-labelled position is legitimate,
preserve it under a stable positional label and compare it; never truncate data solely
because its header is blank.

### CMP-AUD-045 — PM-only identity is too weak

Priority: P1  
Status: Partially remediated — core green; **Ramp Detail + Intersection Detail (2026-07-14), Highway Sequence (2026-07-16), and Highway Log (2026-07-17) integrated + corpus-verified; the identity gate is 11 green / 0 known-red**; only HD-Excel remains blocked pending the vendor county answer  
Primary code: `scripts/compare_env.py:689-719`,
`scripts/compare_core.py:445-490`,
`scripts/consolidate_tsn_highway_log.py:280-361,459-495`,
`scripts/compare_highway_sequence_tsn.py:63-65,104-123`,
`scripts/compare_ramp_detail_tsn.py:43-49,71-86,120-133,199-209`,
`scripts/compare_intersection_detail_tsn.py:183-202,273-279,331-350,472-488`

Highway Sequence, Ramp Detail, and Intersection Detail cross-environment adapters key
only on raw PM/Post Mile. Duplicate-key similarity pairing can then match the most
similar payloads across different physical locations, masking changes. Controlled
fixtures compared the current output with the domain-correct composite identity:

- Highway Sequence county reset: 2 reported differences versus 10 correct.
- Highway Sequence blank versus `E` PM suffix: 2 versus 10.
- Ramp Detail identical PM under two county-bearing Location tokens: 2 versus 10.
- Intersection Detail identical PM under two Location tokens: 2 versus 6.

The direct triangle recipes repeat the weak identity. A two-county fixture placed the
same route+PM in both counties, then swapped ALPHA/BETA descriptions between physical
locations. The correct county-aware result is two Description differences. PDF-vs-
Excel, PDF-vs-raw-TSN, and Excel-vs-raw-TSN returned match with two Both rows and zero
differences in both Ramp and Intersection. Excel-vs-normalized-TSN did too, even when
the normalized libraries retained district/county sidecars, because the loaders sliced
them away. Similarity pairing matched the most alike descriptions across county
boundaries and erased the physical changes on every triangle edge.

Highway Sequence's vs-TSN comparator already implements normalized County plus glued
prefix/PM/suffix identity, but its other paths do not. The source-first reset also
invalidated two earlier exemptions:

- Highway Log raw group headers carry `<district> <county> <route>`, but `parse_pdf`
  stores only `route` and rows; its normalized workbook therefore discards county before
  duplicate pairing. No complete raw collision census had justified calling Highway Log
  county-independent. Its historical Route-1 count remains engine evidence, not a
  physical-identity oracle, until the exact 12-PDF source is re-oracled with county.
- Highway Detail's glued postmile retains prefix/suffix/roadbed but not county. The raw
  XLSX proves hundreds of route+canonical-PM keys spanning counties. Because the TSMIS
  Excel export currently has no authoritative county field and remains vendor-pending,
  that flavor is blocked rather than repaired by inference.

Correction requirements: preserve the complete source-backed identity and every asserted
identity-adjacent claim in every environment, PDF, Excel, raw-TSN, and normalized-library
path. Highway Sequence uses route + county + complete printed/glued PM. The owner-approved
D4 Ramp tuple is exactly `(Route, County, norm_pm(PM))`; `PR` and `PM_SFX` remain separately
asserted and conserved source claims, not extra pairing-key components. The accepted
Intersection source oracle supersedes the earlier numeric-PM shorthand: its physical tuple
is `(base Route, County, complete PP, numeric Post Mile)`. Route suffix, PR, District, and
the other source claims remain separately asserted fields. Highway Log must first retain
its raw county claim and complete a collision census; Highway Detail Excel remains blocked
without a source-backed county derivation.
Similarity pairing may run only within genuine duplicates of the approved family tuple.
Test county resets, value swaps, prefix/suffix-only field variants, real duplicate tuples,
and mid-list inserts on every triangle edge.

**Ramp Detail remediation (2026-07-14).** Every RD path — raw TSN, the v4
normalized library (District/County/PM-Suffix sidecars now READ, not sliced),
the Excel and PDF consolidated loaders, and the cross-env adapter (a new
`EnvCompare.physical_key_builder` hook producing the engine `key_normalizer`) —
keys rows with the owner-approved D4 `PhysicalKey`
`(Route, County, norm_pm(PM))`; PR/PM_SFX/Location/District ride as conserved
raw claims, never key components (the original KNOWN_RED contracts expected a
glued `R1.000E` canonical, which contradicts the accepted RD-79 oracle — PR
differs on zero paired rows and TSN's 313 print suffixes have no TSMIS
counterpart, so gluing would fabricate one-sided rows; the contracts were
corrected to D4 with this evidence and PROMOTED into TESTS, 6 green / 3
known-red remaining for HSL/ID). Similarity pairing now runs only within
genuine D4 duplicates (the one real TSMIS group, 101/LA/1.284). The Comparison
sheet's key column shows the side-independent canonical
"route / county / postmile" display. **Re-blessed against the accepted RD-79
oracle EXACTLY, all three legs and every per-field count** — Excel vs raw TSN
15,212/4/198 · 14,471/741/847 (District 1, Description 185, PR 0); PDF vs raw
TSN …/774/998 (On/Off 95, Ramp Type 60); PDF vs Excel 15,216 · 4/4. Blocked
families unchanged: HL needs its county census, HD-Excel is vendor-pending.

**Intersection Detail remediation (2026-07-14, same day).** Every ID path —
raw TSN, the v4 normalized library (District/County sidecars read into the
key; pre-v4 refused with a rebuild hint), the shared consolidated loader both
flavors ride, and the cross-env adapter via the same `physical_key_builder`
hook — keys rows with the accepted ID-79 PhysicalKey `(base Route, County,
complete PP, numeric Post Mile)`: the complete PP is INSIDE the canonical
postmile (`PP + Decimal-canonical PM`, e.g. "R5.87" — six real within-county
groups carry distinct PPs at one numeric PM), while the route/PM suffixes and
Location ride as conserved claims. The ID KNOWN_RED contracts' glued
`R1.000E` expectation was corrected (the accepted tuple has NO suffix and a
Decimal-canonical PM) and both promoted into TESTS — the identity gate is now
8 green / 2 known-red (HSL only). District + County joined `SHARED_HEADER` as
asserted compared fields (the oracle asserts 34 fields per paired row —
construction-equal, zero difference cells, visible provenance; the Report View
shows them inside its LOCATION cell). No edge-trimming (unlike RD): ID's 8
trailing-tab Excel Descriptions are database data both Excel and raw TSN
carry — the 9 PDF↔Excel differences stay honest, including the REAL
`108/TUO/<blank>/5.87` HG defect (Excel `U` vs PDF+TSN `D`).
**Re-blessed against the accepted ID-79 oracle EXACTLY, all three legs**:
Excel vs raw TSN 16,199/260/427 · 146/16,053 · 21,676 cells · 550,766
asserted; PDF vs raw TSN … · 21,683 · 550,766; PDF vs Excel 16,459 ·
16,450/9 · 9 · 559,606 — all with exact pairing quality across TSN's 15 real
duplicate groups (the Hungarian assignment's first statewide engagement).

**Highway Sequence remediation (2026-07-16).** Every HSL path — the v4 normalized
TSN loader (marker-sheet gated; pre-v4 refused with a rebuild hint), the shared
consolidated loader both TSMIS flavors ride, the new PDF-vs-Excel same-source
loader, and the cross-env adapter via the same `physical_key_builder` hook
(engaging only on the real export shape: County named, PM flanked by the two
UNNAMED prefix/suffix columns; anything else logs and falls back) — keys rows
with the oracle-approved PhysicalKey `(Route, County, complete glued postmile)`:
zero padding, realignment prefix, and equate suffix exactly as printed
("R001.000E" — the ONE family whose canonical keeps the suffix; the
PDF-vs-Excel leg alone excludes it per CMP-AUD-199 and compares it as the
"PM Suffix" column). The raw prefix/PM/suffix (and County text with its
TSMIS-only trailing period) ride as conserved claims. Rows printing NO county
(the 46 CMP-AUD-158 annotations) or NO postmile (five TSMIS rows per render)
key under the reserved `"(county not printed)"` / `"(no postmile printed)"`
markers — disclosed, unpairable with real geometry, never fabricated. Both
KNOWN_RED contracts were verified against the Stage-8 oracle's `Row.identity`
(the glued expectation is CORRECT for HSL, unlike RD/ID) and PROMOTED —
**the CMP-AUD-045 identity gate is now 10 green / 0 known-red; every
unblocked family is integrated**. Corpus-verified on the current ssor-prod 7.9
pair vs the oracle's `EXPECTED_CURRENT_LEGS`: all three leg SHAPES exact
(60,494/69,804/57,072/3,422/12,732 · 60,493/69,804/57,505/2,988/12,299 ·
60,493/60,494/60,493/0/1), and re-pairing the product-loaded rows under the
oracle's assignment objective reproduces every per-field cell count EXACTLY
(the residual product deltas are precisely CMP-AUD-220's objective + the four
CMP-AUD-197 `_x000d_` cells — no other residue). HL still needs its raw county
retention + collision census; HD-Excel remains vendor-pending — do NOT infer
either.

**Highway Log remediation (2026-07-17).** The 2026-07-16 county/collision census
plus a same-day owner-qualifier census settled the honest HL identity:
**(Route, roadbed-canonical Location)** — county can never be a two-sided key
component because the TSMIS Highway Log export has NO County column (the numeric
"Cnty Odom" IS compared and feeds the CMP-AUD-220 assignment objective), so the
TSN print's district/county/route group ownership is conserved as a per-document
sidecar CLAIM (`tsn_source_claims.documents[].ownership`, one entry per printed
group header with page/district/county/route token/suffix/row count). The
qualifier census resolved CMP-AUD-157's open token-4 question with a decisive
source correspondence: exactly 19 four-token headers statewide, and their
(route, letter) combinations are exactly TSMIS's ten suffixed routes (005S 008U
010S 014U 015S 058U 101U 178S 210U 880S) — row-verified (TSMIS 101U's 8 rows
are postmile-for-postmile a subset of the "01 MEN 101 U" section, equate
included) and confirmed by the print's own accounting (every suffixed section's
COUNTY/ROUTE totals print all-zero, excluding those rows from the base route).
The detached suffix therefore JOINS the route identity: normalizer v5 keys
"07 LA 005 S" rows as route 005S, un-misattributing **317 rows statewide**
that v4 merged into base routes (previously: every TSMIS suffixed-route row was
falsely "Only in TSMIS" while the 317 TSN rows inflated the base routes).
Gates: the identity gate grew to **11 green / 0 known-red**
(`test_highway_log_route_and_location_identity` — suffix separation through
the production pdfplumber pipeline on hand-rolled fixture PDFs, county-as-claim,
`_SCHEMA.key_normalizer is roadbed_canonical_location`), the v5 marker sheet +
loader gate refuse pre-v5 TSN workbooks in both vs-TSN flavors (PDF-vs-Excel
ungated — no TSN side), and the locked Route-1 canary re-blessed EXACTLY
(299/18/69/221/969, all 30 per-field counts identical, 8,970 asserted; the v5
per-route TSN Route-001 rows are byte-equal to the frozen HL-R1-E1 input).
Only HD-Excel remains blocked (vendor county answer) — do NOT infer it.

Raw-source re-verification on 2026-07-12 bound the user-provided, raw-only TSN library
before implementation:

- Ramp SHA-256 `3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856`:
  15,410 rows; 81 route+normalized-PM keys span multiple counties (163
  county-specific identities). PM_SFX is populated on 313 rows. Independent XLSX/PDF
  inspection proved that this exact print has no separate PM_SFX column, but all 313
  nonblank suffixes equal HG (`L` 165 / `R` 148) and no blank-suffix row has HG L/R.
  That source-pair invariant explains the current print mapping but is not a universal
  identity rule; preserve the raw suffix claim and re-census each source pair.
- Intersection SHA-256
  `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2`:
  16,626 rows; 78 weak numeric-PM keys span multiple counties (156 identities),
  while the complete PP+PM key has 71/142. Six real within-county groups contain
  distinct prefix variants at the same numeric PM: 101/SF 5.450, 115/IMP 9.540,
  132/STA 15.340 and 15.620, 184/KER 0.000, and 218/MON 0.340. The current TSMIS
  7.9 exports independently contain both rows in each checked group (for example,
  Route 101 `M005.450` MARKET/OCTAVIA versus blank-prefix `005.450` WILLOW).
- Highway Detail SHA-256
  `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1`:
  the Fable count reproduces as 453 multi-county *keys* only under its weaker base
  `RTE + PP + POSTMILE` probe (1,008 county identities). The production-shaped
  `(RTE+RTE_SFX, pm_canon)` exposure is 438 keys / 976 identities. Highway Detail's
  TSN shape is authoritative, while its TSMIS output remains vendor-review-pending;
  TSMIS schema drift must fail closed and no Excel-side county source will be invented.
- Highway Log's 12 raw PDFs bind to the core family manifest recorded in
  `comparison-phase4-tsn-source-rebaseline.md`. The parser visibly recognizes county in
  each group header and then drops it. A full county-aware collision/count oracle is now
  required before its previous exemption or canary can be retained.

This real evidence confirms that county cannot be omitted. Stage-8 Intersection Detail
then resolved the remaining identity question against all four current sources: six real
within-county route+numeric-PM groups contain distinct complete-PP values, so complete PP
is part of the Intersection physical key. That evidence supersedes the earlier shorthand;
it is not an inferred convenience. Ramp keeps its separately approved numeric-PM tuple.
Route suffix, PR, District, and all other populated claims still must be retained,
compared or explicitly dispositioned, and mutation-tested rather than silently folded.

Stage-8 Intersection Detail acceptance binds the exact impact. The current raw TSN has
16,611 unique physical identities and 15 exact duplicate groups / 30 occurrences under
`(base Route, County, complete PP, numeric Post Mile)`. Route+numeric-PM has 78
cross-county keys / 156 county identities; Route+complete-PP+numeric-PM still has 71 / 142.
Production declares only Route+PM in all five legs and exposes neither County nor complete
PP as identity. Its current-corpus counts happen to match the strong oracle—16,199 paired
and 260/427 one-sided—because the present values do not trigger every ambiguity, but the
31-assertion permanent gate's county and complete-PP swap fixtures reproduce the masked
change. This keeps the finding product-red even though the accepted result proves all
overlapping cells and one-sided inventories for the unmutated corpus.

#### Structured-seam implementation audit — 2026-07-12

The first shared `PhysicalIdentity`/`PhysicalKey` seam was reviewed adversarially before
family integration and is not accepted yet. Independent executable probes confirmed:

- `LoadedSide -> JSON -> LoadedSide` flattens `PhysicalKey` to plain `str`, losing the
  canonical identity and raw claims.
- The outer consolidated Route and the identity's canonical Route are two unchecked
  authorities. A `001` outer route versus canonical `002` silently becomes two one-sided
  rows; traces omit the disagreeing outer authority.
- A typed side compared with a legacy-string side silently becomes one row only on each
  side instead of failing the incomplete migration.
- `RawIdentityClaim.value: Any` is not lossless: tuples return as lists, non-string
  mapping keys are stringified, and dates cannot JSON-serialize.
- The red projector fixture itself expected numeric-only Ramp/Intersection postmiles
  even when source prefixes were populated, scanned the whole row rather than the
  engine-consumed key field, and asserted only that some raw claim existed. It could
  bless the exact prefix/suffix loss this finding prohibits.
- Equal typed identities may carry different display strings; side order then changes
  the visible Comparison location. Ordering is inherited from `str` even though equality
  uses physical identity, so two equal keys can also compare less-than by display.

Correction requirements for the shared seam: tagged round-trip serialization; one
validated canonical Route authority; fail-closed uniform typed mode once any typed key
is present; an exact serializable raw-claim domain; schema-aware key-field assertions
using real `PhysicalKey`; full glued PM and exact raw-claim fixtures; deterministic
canonical display and ordering consistent with equality. The all-legacy path must remain
unchanged. No family may integrate this seam until these gates are green.

#### Structured-seam hardening review — 2026-07-12

The shared core now passes tagged `PhysicalKey` round trips, a scalar-only exact raw
claim domain (including finite-float and signed-zero behavior), deterministic canonical
display/ordering, outer-route equality with the canonical route, and fail-closed uniform
typed mode across both sides. Its permanent fixture uses real `PhysicalKey` instances,
full Ramp/Intersection prefix+normalized-PM+suffix tokens, and exact per-source claims.
The all-legacy engine behavior and pairing-policy gate remain green.

This does not resolve the finding: the family projector portion of
`build/check_compare_physical_identity.py` remains intentionally red for Highway
Sequence, Ramp Detail, Intersection Detail, and the direct/PDF projectors. Those paths
must retain and emit the source-backed typed identity before similarity pairing is
allowed to operate within the remaining genuine duplicate groups.

### CMP-AUD-046 — position-shifted exports are labelled as the wrong fields

Priority: P2  
Status: Verified with one planted difference per affected family  
Primary code: `scripts/compare_env.py:559-576,689-719`,
`scripts/compare_ramp_detail_tsn.py:199-224`,
`scripts/compare_intersection_detail_tsn.py:153-177`

Ramp and Intersection exports have documented cases where header labels are shifted
relative to the value positions. Their cross-environment adapters display the raw
loaded header and do not configure a corrected `force_header`. A real Ramp Description
change was reported under `R/U`; an Intersection `INT Type` change was reported under
`INT Eff-Date`. Difference detection fires, but field summaries and remediation point
the user to the wrong business attribute. The PDF cross-environment variants inherit
the same display schema.

Correction requirements: project values onto one position-authoritative semantic
header before comparison. Plant a unique change in every physical position and assert
the displayed field name, per-field count, and source-cell link for Excel and PDF
variants.

**Remediation (2026-07-18).** Per-position census of the real 7.9 exports (RD Excel +
converted PDF, ID Excel + converted PDF) pinned the exact shift and the corrected label
for every value position:

- **Ramp Detail (Excel + PDF)** now carries a position-authoritative `force_header`
  (`compare_env._RD_ENV_HEADER = ["Location","PR","PM","Date of Record","PM Suffix","HG",
  "Area 4","City Code","R/U","Description","(unused)"]`, + `On/Off`/`Ramp Type` for the
  PDF's two print-only columns), applied exactly like Highway Log's corrected labels —
  the export's labels shift right of their values from City Code onward (value pos8=R/U
  under "City Code", pos9=Description under "R/U"), and force_header relabels each
  position to its true field. The PDF conversion carries the identical shift, censused.
- **Intersection Detail** — the current site edition realigned its labels over their
  values (the INT Type / INT Eff-Date swap, etc.); the Excel cross-env was already fixed
  by CMP-AUD-032/048's `_id_canonical_header` (legacy→current), and the **PDF** variant,
  which had no canonicalizer and displayed the shifted legacy labels, now pins the same
  `_id_canonical_header`.

Values are compared BY POSITION, so no difference COUNT changes — display only. New
`build/check_compare_env_field_labels.py` proves it end-to-end: a planted Ramp
Description change is shown under **Description** (not R/U), a planted Intersection INT
Type change under **INT Type** (not INT Eff-Date), for the pinned families; plus the
force_header / canonicalizer wiring per variant. Offline gate 132/132; ruff clean.

### CMP-AUD-047 — Highway Log environment comparison skips normalization

Priority: P2  
Status: Verified end to end  
Primary code: `scripts/compare_highway_log.py:78-91`,
`scripts/compare_env.py:208-211`

The dedicated Highway Log loader replaces tabs/newlines with spaces before the shared
Excel-TRIM semantics, specifically because the vendor export pads Description with
tabs. The cross-environment adapter uses the generic XLSX loader and calls only
`normalize_value`, bypassing that report rule. Identical descriptions except for three
trailing tabs returned `ok/diff` under Highway Log cross-env; the dedicated loader
correctly judged them equal.

Correction requirements: every Highway Log entry point must use the same projection
function before keying/comparison. Run a field-by-field projection parity suite across
direct Excel, direct PDF variants, Excel cross-env, and PDF cross-env.

Execution disposition (2026-07-16): `compare_env._load_xlsx_side` accepts a
per-report `value_normalizer` (CMP-AUD-047) and `EnvCompare` carries it; the
Highway Log registration passes `_hl_normalize` (the dedicated comparator's
tab/newline collapse) and the Highway Log (PDF) conversion path passes the
same projection to its converted-XLSX read, so every Highway Log entry point
now projects identically. Red->green in `check_compare_env_highway_log`: a
Description identical but for trailing tab padding compared ok/diff pre-fix
and compares clean (0 cells) post-fix.

### CMP-AUD-048 — supported Highway Log header editions conflict

Priority: P2  
Status: Verified with canonical-versus-vendor headers  
Primary code: `scripts/highway_log_columns.py:103-118`,
`scripts/compare_env.py:559-576,639-646`

`highway_log_columns.recognize` deliberately supports both the corrected canonical
31-column header and the old vendor-labelled 31-column header because their positions
are equivalent. Direct comparison accepts that pair. Cross-environment loading instead
compares the two raw header texts before applying `force_header`, so identical rows
using one supported edition on each side fail with `different column layouts`.

Correction requirements: recognize and canonicalize each side independently before
layout equality. Reject an unrecognized same-width header, while accepting every
documented canonical/vendor pairing and displaying only the corrected semantic names.

Execution disposition (2026-07-16): `EnvCompare` carries a
`header_canonicalizer` applied to EACH side before layout equality; Highway
Log's maps either documented edition (canonical or vendor labels, with or
without a leading Route) to the corrected canonical header via
`highway_log_columns.recognize`, and an unrecognized same-width layout is now
REFUSED by name ('do not use a recognized … column layout') instead of being
compared positionally on faith. Red->green in `check_compare_env_highway_log`
(canonical-vs-vendor compares clean with corrected display labels; the
supported pairing no longer errors; the fake 31-column layout errors).

### CMP-AUD-049 — Direct and PDF route identity is not enforced

Priority: P1  
Status: Verified in direct-file and five PDF-conversion paths  
Primary code: `scripts/compare_highway_log.py:94-151`,
`scripts/consolidate_tsmis_highway_log_pdf.py:443-470`,
`scripts/consolidate_tsmis_highway_detail_pdf.py:448-486`,
`scripts/consolidate_tsmis_highway_sequence_pdf.py:341-348`,
`scripts/consolidate_tsmis_ramp_detail_pdf.py:355-362`,
`scripts/consolidate_tsmis_intersection_detail_pdf.py:341-371`,
`scripts/visual_evidence.py:248-286,390-444`

Per-route direct comparisons do not establish which route either workbook represents.
Two identically populated files named Route 001 and Route 002 were accepted as the
same one-row universe and returned zero differences. In the PDF converter, a filename
route that disagrees with the in-document cover route only emits a warning and the
filename wins; a Route 001 Highway Log PDF whose cover says Route 002 is emitted and
certified as Route 001. Highway Detail likewise emitted filename Route 001 when its
DCR content identified `11 IMP 007`. Highway Sequence and Ramp Detail PDFs whose
visible page banners both said Route 099 were emitted as Route 007 solely because of
their filenames. Intersection Detail emitted filename Route 001 while its Location
field identified route 780. Every mismatch producer returned complete with zero
failed/skipped inputs. Duplicate-route consequences are tracked separately in
CMP-AUD-050.

Visual evidence repeats the relabelling risk after comparison. Every TSMIS evidence
adapter constructs the requested PDF path from the expected route filename; the
engine does not reconcile an in-document route identity before captioning the image.
A foreign-route PDF renamed to the expected route, with the same key/value, can be
verified and captioned as that requested route.

Correction requirements: require normalized per-route identity on both direct inputs
and require filename, document cover/banner/DCR, and emitted route to agree wherever
the report carries route provenance. A mismatch must set structured partial/failure
state rather than merely warn or silently relabel. Test numeric/suffixed padding,
content mismatch, and distinct per-route selections across every direct and PDF
report family.

**2026-07-17 partial (the direct-compare half).** Per-route Highway Log pairs —
the one direct per-route comparison family, all three flavors (vs-TSN and both
PDF-sourced) — now require a normalized route token in BOTH filenames and exact
agreement (`compare_tsn_common.require_per_route_identity`, wired in
`compare_highway_log._load_pair`): "Route 001" vs "Route 002" refuses naming
both files and routes; a token-less per-route file refuses with rename/
consolidated guidance (per-route workbooks carry no Route column, so the
filename is the only verifiable identity; every export and conversion this app
writes carries the token). Consolidated pairs stay content-keyed and
unaffected; the Route-1 canary re-verified 299/18/69/221/969 under the rule.
Red→green pinned in `check_compare_highway_log` (3 pre-fix failures by
git-stash).

**2026-07-17 (the converter half — the finding's producer core).** The five
PDF converters now treat the DOCUMENT's own route claim as the authoritative
identity; the filename token merely corroborates
(`pdf_table_lib.reconcile_route_identity`, called from every family's
convert_one): a missing claim, conflicting claims, or a filename that
disagrees is a NAMED FAILED input (each family's finalize escalates PARTIAL —
never a silent relabel), and a token-less filename now converts under the
document's route instead of being skipped. Per-family in-document sources
(censused on the bound 7.9 statewide sets before coding): Highway Sequence
and Ramp Detail read every data page's banner ("District: 10 Route: 004
Direction: W – E" / "Route: 004 Direction: W – E") in the band the parsers
previously skipped (`BANNER_ROUTE_RE`; claims returned as
`stats["doc_routes"]`); Highway Detail matches the data pages' "Ref Date: …
Route NNN Page N" banner on the SPACELESS group text, captured BEFORE the
geometry gate so a grid-less document still identifies itself; Intersection
Detail (no page banner) reads its cover's REPORT-PARAMETERS "ROUTE : 020"
line (`COVER_ROUTE_RE`, captured before the geometry gate) — NOT the
per-record Location cells: the census proved an intersection OF the subject
route WITH another route prints the OTHER route's mainline in Location
(118 of 217 real per-route prints carry multi-route Location sets, e.g.
route_009 claims {001, 009}), so rows are data and only the cover parameter
is the document's claim about itself; Highway Log's already-parsed cover
"Route NNN" line is now authoritative instead of losing to the filename
WARN. Ramp Summary needs no converter change — its route already comes from
the document's own parsed content (CMP-AUD-050 added its blank/duplicate
refusals).

**2026-07-17 (the evidence half — the finding's captioning core).** Every
evidence adapter's `locate_tsmis` now captures the same in-document claims
in LOCKSTEP with its consolidator twin and raises
`pdf_table_lib.RouteIdentityError` (via `require_document_route`) when the
document does not confirm the route the filename names; the engine's
extracted `visual_evidence._locate_tsmis_sources` catches that error
DISTINCTLY — the PDF is excluded from evidence with a loud ⚠ note and its
examples become misses, while merely-unreadable PDFs keep their separate
path. A renamed foreign-route PDF can no longer be verified or captioned as
the requested route.

**Proof.** Red→green: the new `check_pdf_route_identity` (the helper
contract; all five families' mismatch/missing/conflict/token-less/agreement
flows through the real consolidate() with parse_pdf stubbed; REAL-parser
banner/cover capture on hand-rolled fixture PDFs incl. suffixed routes, the
geometry-less Highway Detail document, and the record-less Intersection
Detail cover; all five adapters' refusal + agreement twins; the engine
exclusion; the ID cover-regex shapes incl. the ROUTE:ALL non-claim) — 34
rule/parser pins failed pre-fix and every adapter pin failed "did not
raise" pre-fix; the whole check passes post-fix and joined the gate (125).
Statewide census through the PRODUCTION parsers over the bound 7.9 sets —
every real per-route document's claims equal its filename route with ZERO
refusals: RD 126/126 (15,216 rows), HSL 252/252 (60,493), HD 252/252
(51,206), HL 252/252 (51,886), ID 217/217 under the cover parameter
(16,459; the superseded rows-based census leg is what MEASURED the 118
multi-route-Location documents and forced the cover redesign — the census
did its job before the wrong rule could ship). Real end-to-end: three real
Ramp Detail PDFs (004, 051, suffixed 880S) convert COMPLETE, and a REAL
renamed print (880S content saved as `tsar_ramp_detail_route_002.pdf`)
refuses loudly — named FAILED input, PARTIAL, both routes in the log; all
five adapters locate real per-route PDFs (incl. 008U/178S/020) with zero
refusals.

### CMP-AUD-050 — PDF conversion does not enforce a route universe

Priority: P1  
Status: Remediated 2026-07-17  
Primary code: `scripts/pdf_table_lib.py:276-307`,
`scripts/consolidate_ramp_summary.py:260-295,690-780`

All five table-PDF consolidators use the shared conversion driver. When two PDFs
normalize to the same route, it logs a warning but writes the later payload over the
earlier route workbook, increments the converted count twice, and can return complete;
the earlier data vanishes. Ramp Summary uses a separate path with the opposite
corruption: two parsed PDFs both claiming Route 001 are appended as two records, the
producer returns complete, and the aggregate vs-TSN loader sums both. A 5-count and a
7-count duplicate became statewide count 12. Ramp Summary also accepted a populated
record with `route=None` and returned a complete workbook containing a blank Route.

Correction requirements: require a nonblank normalized route for every parsed PDF and
maintain a route-to-source map before writing. A duplicate must fail or produce an
explicitly reconciled partial result; it must never overwrite or double-count by file
order. Summary counts must report unique emitted routes, and route provenance must be
retained in the workbook/result.

**Remediation (2026-07-17).** Both paths now keep a route→source-PDF map and
refuse instead of absorbing by file order. The shared driver
(`run_pdf_conversion`, all five table-PDF consolidators): a blank/None route
identity or a second PDF converting to an already-claimed route returns an
error NAMING both source PDFs — the combined workbook is not written and
last-good is preserved (the old warn-overwrite-double-count path is gone, so
`converted` counts unique emitted routes by construction). Ramp Summary's
collection loop: a duplicate route refuses the same way before anything is
written; a POPULATED record with no parseable route becomes a named FAILED
input — the run publishes without it under the existing loud
"⚠ INCOMPLETE" banner with `completion=PARTIAL` and `failed_inputs`
counted, never a complete workbook with a blank Route row. Red→green pinned
in the new `check_pdf_route_universe` (fake-converter driver runs + patched
Ramp Summary collection: duplicate names both sources / blank refuses or
fails loudly / distinct routes still publish COMPLETE; 8 pre-fix failures
under git-stash). All three CMP-AUD-049 halves (direct per-route comparison
identity, filename-vs-document route agreement in the converters, evidence
adapters) closed the same day — see that finding's record.

### CMP-AUD-051 — Highway Detail line-one spill creates phantom records

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `ab8d103`) — already closed by the
054 `_is_line1` hardening: the statewide 7.9 census found exactly 3 equate-spill
shapes (`R42.401 LT EQ …` on 101 ×2, `14.752 LT EQU 14.760 RT` on 280), and
`_is_line1` correctly rejects ALL 3 (**0 residual phantoms** — it requires the
post-mile ALONE, or post-mile+Length with window 1 empty; an equate description's
text runs on as words). Each rejected spill is then attached to its pending record
as the line-2 (the finding's required behavior), never a phantom row. The 3 shapes
are pinned in `check_highway_detail_pdf.test_line1_classifier`.  
Primary code: `scripts/consolidate_tsmis_highway_detail_pdf.py:271-291,310-420`

The parser accepts an exact-looking post mile in the first grid window as a new
line-one record without validating the remainder of that physical line. When a
wrapped line-two value spilled `R42.401` into window zero and `LT EQ 43.185` into
window one, two intended records became three emitted records. The original record
lost its line-two fields, while the invented `R42.401` record received
`LT EQ 43.185` as its Length. The parser reported zero orphans, the producer returned
complete, and the corrupt row reached the consolidated workbook.

Correction requirements: validate the full line-one token shape, field occupancy,
and overflow before starting a record. A post-mile-like token inside line-two spill
must be attached to the pending record or make the source explicitly partial; it must
not create a row. Add row-count, key-set, and no-phantom-record assertions around
wrapped descriptions and post-mile-shaped text.

### CMP-AUD-052 — Highway Detail header words swallow real line-two data

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `ab8d103`) — the reprinted-header
detector no longer keys on the bare words `ROADBED`/`MEDIAN` (which a real date-less
Description like "OLD ROADBED" / "BEGIN MEDIAN" could carry). `THEAD_RE` now anchors
the roadbed header on the header-ONLY `LEFTROADBED`/`RIGHTROADBED` compounds —
censused present on every one of the 516 statewide roadbed-header lines, so all
headers are still recognized, and byte-identical on the corpus (0 rows moved). A
date-less "BEGIN MEDIAN" description now parses as data instead of being swallowed.
Pinned in `check_highway_detail_pdf.test_line2_furniture`.  
Primary code: `scripts/consolidate_tsmis_highway_detail_pdf.py:152-155,388-410`

The table-furniture detector treats any line containing a bare header word such as
`DESCRIPTION`, `ROADBED`, `MEDIAN`, `T-W`, or `WDA` as a header before it attempts
line-two mapping. A legitimate date-less description beginning `BEGIN MEDIAN` was
discarded as furniture. The record was still emitted with blank description/tail
fields, the following record survived, orphan and single-line counters stayed zero,
and the producer returned complete.

Correction requirements: identify a table header from its ordered set of anchors,
page position, and geometry rather than a substring anywhere in a data line. Exercise
every header-vocabulary word in sparse and populated descriptions, including records
whose line two has no date.

### CMP-AUD-053 — Highway Detail orphan reconciliation never fires

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, **a real correctness fix**, `ab8d103`)
— the investigation surfaced a 054-missed CORRUPTION: the reprinted "Acc-Cont Eff"
header wraps as "ACC-" then a bare "CONT" line, which the parser consumed as a
record's line-2, emitting a garbage record ("C"/"ONT" in the roadbed columns, NO
Description/attributes) while the record's REAL line-2 was ORPHANED. "CONT" (and a
dashed-district group header) are now recognized as furniture (`_is_header_residue`),
so each line-1 pairs with its real line-2: **7 records across 5 routes
(018/101/110/152/395) corrected** from garbage to the printed Description + roadbed
data (cell-for-cell verified — "44TH STREET", "FIGUEROA ST OFF RAMP , UC 53-533",
"RT ON LAKE FROM LINCOLN", "WESTLAKE VILLAGE SCL", "BEGIN R REALIGNMENT"). The 2
genuinely-unreconcilable leading orphans (route 395 alignment/wrap fragments) are now
COUNTED (`leading_orphans`) and escalate the producer to PARTIAL with a structured
`parse_anomalies` diagnostic, never silently ignored. Old-vs-new (git-stash, 252
PDFs): count unchanged (51,201); the ONLY content delta is the 7 corrections (rows
sha256 83fd8fb7→f8cf36d0). Red→green + e2e escalation in
`check_highway_detail_pdf.test_053_leading_orphans`.  
Primary code: `scripts/consolidate_tsmis_highway_detail_pdf.py:336-353,382-420,488-506`

The `orphans` statistic is initialized but never incremented, even though it is one of
the few conditions that can make the producer partial. A leading non-furniture
line-two payload on a gridded data page was silently ignored; the next record survived,
`orphans=0`, and the run returned complete. Separately, end-of-file after line one and
a footer was accepted as an ordinary single-line record with a blank tail, so a
truncated pair is indistinguishable from a valid source single-line record.

Correction requirements: account for every non-furniture text group that cannot be
reconciled to a line-one record, reconcile the two bands explicitly, and distinguish
source-proven single-line rows from broken/truncated pairs. Unexplained or truncated
payload must make the producer partial or failed and remain visible in structured
diagnostics.

### CMP-AUD-054 — Highway Detail fallback grids can certify corrupted rows

Priority: P1  
Status: **Resolved 2026-07-18** — a band-less-line-1 page recovers its line-1 grid from its own line-2 band (census: exact merge on 3,664/3,664 both-band pages); rect-less data pages escalate to PARTIAL instead of the corrupting document median. The named 005.009 record + 16 more recover faithfully; 15 routes' final unshaded records now go PARTIAL. **HD-PDF comparison consequence flagged for the owner** (see remediation note)  
Primary code: `scripts/consolidate_tsmis_highway_detail_pdf.py:363-420,477-506`

When a page lacks a detectable grid, the parser reuses document-median column windows
without validating token fit, boundary crossings, or the shapes of the extracted
fields. A shifted page was emitted with values such as Length=`000.010 26-01-01`,
Date=`R`, and Description=`SHIFTEDDESC N`. The run recorded a fallback page only in a
live log, returned complete with zero skipped/failed inputs, and did not preserve that
fallback outcome in the durable summary.

Correction requirements: validate character/token crossings and per-field shapes on
fallback pages, as the Highway Log parser does. An incompatible fallback must be
partial rather than converted, and every validated fallback must remain in structured
producer/consolidation diagnostics. Track fallback use when either half of a
cross-page record relies on it.

The frozen current `All Reports 7.9 / 2026-07-09 ars-prod` sources now prove the
same defect without mutation. `highway_detail_route_005.pdf` has 226 physical pages:
three front-matter pages and 223 data pages. An independent word/topology census finds
219 data pages with both exact grids and four continuation pages with only the 25-cell
line-two grid. Physical pages 6-7 are one printed-page layout block and share the same
25-cell base grid; its 10-cell line-one grid is exactly and uniquely the merge at base
edges `(0,1,3,5,6,7,9,11,12,14,25)`. Page 7 therefore has source-backed local geometry,
but production treats the missing 10-rectangle band as a reason to use the unrelated
document median.

The consequence is visible in the unmodified source. On physical page 7 the printed
record is Post Mile `005.009`, Length `000.083`, Date of Record `64-01-01`, HG `D`,
AC `F`, Acc-Cont Eff `64-01-01`, City `SD`, RU `U`, and RU Eff `64-01-01`. Direct
production parsing emitted Post Mile `005.009`, blank Length, Date of Record
`000.083`, blank HG, AC `64-0`, Acc-Cont Eff `1-01 D F`, City `64-01-01`, RU `SD`,
and RU Eff `U 64-`, then reported no orphan/failure. The rendered page and the
independent local-grid parser both retain the source columns. This is a product parser
corruption, not an Excel/PDF source delta and not merely a synthetic hardening case.

**Remediated 2026-07-18.** Census-first on the bound 7.9/ARS set (252 PDFs / 4,452
pages; `census_054_hd_grids.py` + `census_054b_fullparse.py`). The parser now parses
data ONLY on source-backed geometry — a page's own shaded band, or (when the line-1
record is unshaded but the line-2 band is present) its line-1 grid DERIVED from that
page's own line-2 base edges. Two-line records share one auto-layout table, so the
10-cell line-1 grid is exactly the 25-cell line-2 grid merged at
`_L1_FROM_L2_EDGES = (0,1,3,5,6,7,9,11,12,14,25)` — proven EXACT on all **3,664**
both-band pages statewide, 0 exceptions. So the 17 fallback pages (13 routes) recover
their records faithfully (the named `005.009` record parses `005.009 / 000.083 /
64-01-01 / D / F / …` digit-for-digit as printed; the old median gave blank Length /
`Date=000.083`). The document median is no longer used for data at all; a rect-less
page carrying data (no derivable geometry — 15 routes' single final UNSHADED record)
escalates the producer to PARTIAL and drops the un-parseable row rather than emitting
the median's shifted parse ("incompatible fallback must be partial rather than
converted"). `fallback_pages` is now a durable summary diagnostic; `unresolved_pages`
drives the PARTIAL. Hermetic guard: `check_highway_detail_pdf.test_fallback_recovery`.
Exact re-bless numbers + census bindings: comparison-canary-bindings.md.

> **Owner decision — ACCEPT HONEST AMBER (2026-07-18; SUBJECT TO CHANGE).** Because the
> day's HD-PDF consolidation is ONE workbook for all 252 routes, and 15 routes each
> carry a band-less final record with no recoverable geometry, the statewide HD-PDF
> consolidation reports **PARTIAL** (its vs-TSN / vs-Excel comparison shows amber,
> never "green"). This is strictly more honest than the prior state (the median
> silently emitted 15 CORRUPT final records under a COMPLETE result) and is
> discrepancy-safe (a dropped record is one-sided/visible, never a wrong value). **The
> owner ACCEPTS the amber** rather than investing now in a field-type-tokenisation
> recovery of those 15 records. **⚠ EXPLICITLY SUBJECT TO CHANGE:** Highway Detail is
> **not yet vendor-approved**, and the owner will eventually supply a NEW statewide
> batch; if the band-less-final-record problem still occurs on that batch it will be
> re-evaluated then (recover vs. keep amber). Everything in this project is subject to
> revision on new source data, but this decision especially — do not treat the accepted
> amber as permanent. The named 005.009-class recovery (the finding's core corruption)
> is shipped unconditionally.

### CMP-AUD-055 — Damaged repeated headers silently drop later PDF data pages

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `874b8d5`) — once a document has
entered its data section, a headerless page (missing/damaged column-header anchors)
that still carries a postmile-shaped data token is flagged (`damaged_pages`) and
escalates the producer to PARTIAL with a structured `parse_anomalies` diagnostic
(the finding's "rejected as partial" path), instead of being skipped wholesale as a
cover/legend and silently dropping its data. **Census (statewide 7.9, HSL 252 + RD
126 PDFs): every real headerless page is a genuine cover/legend/trailer page
carrying 0-1 anchor words and ZERO postmile tokens** — so the detection is a no-op
on real data (a clean render stays COMPLETE) and never trips on a legitimate cover.
Shared `pdf_table_lib.page_has_postmile`; anomalies escalate completion only, never
the file-count fields (CMP-AUD-064). Red→green + clean multi-page no-op in
`check_pm_code_vocabulary.test_damaged_header_data_page`.  
Primary code: `scripts/consolidate_tsmis_highway_sequence_pdf.py:142-149,258-262`,
`scripts/consolidate_tsmis_ramp_detail_pdf.py:149-170,275-279`

Both parsers require every data page to repeat a full set of header anchors. A later
page that loses only the `DESCRIPTION` anchor is classified like a cover/legend page
and skipped wholesale, even after earlier data pages established the table. In each
three-page fixture, post mile `002.000` and its row were visibly present on page three,
but direct parsing returned only the first of two rows with no unclassified-line or
stray-fragment count. Consolidation wrote only the first row and returned complete
with zero skipped/failed inputs and no warning.

Correction requirements: once a document has entered its data section, a page with
data-shaped rows but missing or damaged header anchors must be recovered from verified
document geometry or rejected as partial. Reconcile expected/observed data pages and
row-shaped text, and test removal/corruption of every individual anchor on first,
middle, and final data pages.

### CMP-AUD-056 — Intersection wrapped rowB text is truncated as complete

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — a Description
continuation baseline within a wrap gap below a rowB (desc-window text, no
intersection number) is now counted (`wrapped_rowb`) and escalates the producer to
PARTIAL rather than being silently truncated. Census (217 statewide 7.9 PDFs): 0
wrapped rowBs; the hardened parser emits byte-identical rows (16,459/16,459, sha256
unchanged) — a discrepancy-safe no-op. A full row-grouping recovery is unneeded at
0 occurrence; the escalation is the honest signal. Red→green + clean no-op in
`check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:279-300`

Intersection Detail treats each physical baseline as a complete logical line. A rowB
whose Description wrapped from `LONG DESCRIPTION FIRST` to `SECOND HALF` caused the
first baseline to consume the pending rowA; the continuation baseline was then
ignored. Only the first half reached the workbook, while emitted/orphan/vestigial
statistics remained clean and consolidation returned complete.

Correction requirements: group continuation baselines into one logical rowB using
cell geometry and record boundaries, and account for every data-area character before
emitting. Test multi-line values in each mergeable cell, multiple simultaneous wraps,
page-boundary wrapping, and continuation text that resembles a header or post mile.

### CMP-AUD-057 — Intersection orphan rowB lines are never counted

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — a complete rowB
(`_is_rowB`: integer intersection number AND Description) is now classified
INDEPENDENT of the pending state; one arriving with no rowA pending is counted
(`leading_orphan_b`) and escalates to PARTIAL, never silently treated as furniture.
Census: 0 leading orphans statewide (byte-identical 16,459/16,459) — no-op on real
data. Red→green in `check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:279-305`

The parser attempts rowB classification only while a rowA is pending. A complete
rowB at the start of a data stream is silently treated as furniture, so it does not
increment `orphans` or any unclassified statistic. A later valid pair is emitted and
the producer certifies the input as complete despite the unexplained record payload.

Correction requirements: classify rowB-shaped lines independently of pending state
and count an unmatched rowB as an orphan. Every data-area line must end in an emitted
record, an explicit furniture category, or a structured partial/failure diagnostic.

### CMP-AUD-058 — Intersection numeric furniture can consume a pending record

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — rowB acceptance now
requires the integer intersection number AND a populated Description window
(`_is_rowB`), so a numeric-furniture line (a page number, a year like `2026`) can
no longer be consumed as a mostly-blank rowB and orphan the real one. Census: every
one of the 16,459 statewide rowB records carries a Description, so the tightening
rejects 0 real records (byte-identical output) while rejecting bare-integer
furniture. Red→green (the real rowB pairs instead of a blank record) in
`check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:296-300`

With a rowA pending, the only rowB discriminator is an integer in window one. A
furniture line containing `2026` there was accepted as rowB, prematurely emitted a
mostly blank record, and cleared the pending rowA. The real rowB that followed was
then ignored under CMP-AUD-057. All reconciliation statistics stayed clean and the
producer returned complete.

Correction requirements: validate the complete rowB shape, required populated cells,
and plausible relationship to its rowA rather than a single integer. Keep furniture
classification separate and add adversarial numeric years, page numbers, route
numbers, and intersection labels in every window.

### CMP-AUD-059 — Mixed Intersection PDF editions silently lose legacy rows

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — a PRE-July-2026
unpadded-postmile hit (`old_pm_hits`) now escalates the producer to PARTIAL
whenever current rows also exist (a mixed/transitional/page-drifted file), not only
in the homogeneous-old case (which still fails outright). The legacy rows are named
in the log and can no longer drop silently under a COMPLETE result. Census: 0 mixed
files statewide (byte-identical 16,459/16,459) — no-op on real data. Red→green in
`check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:293-305`

The parser counts legacy unpadded post miles, but declares `old_layout` only when no
current row was emitted. A fixture containing legacy `0.204` followed by current
`000.205` silently discarded the legacy row, set `old_layout=false`, emitted the
current row, and returned complete. Thus the edition safeguard works only for a
homogeneous old file, not for concatenated, transitional, or page-drifted input.

Correction requirements: any legacy-layout hit must be reconciled or make the source
partial/failed regardless of whether current rows also exist. Preserve counts and
source pages by edition, and test both orderings plus layout transitions between and
within pages.

### CMP-AUD-060 — Intersection vestigial-column drift is discarded as complete

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — detected data in the
dropped 21st rowA column now BLOCKS complete status (escalates to PARTIAL, was
warn-only), and the raw value + source page ride the structured
`parse_anomalies.vestigial_samples` diagnostic. The affected row is neither mapped
nor silently emitted with the value discarded; a schema decision is required before
the column can be used. Census: 0 vestigial hits statewide (byte-identical
16,459/16,459) — no-op on real data. Red→green e2e (COMPLETE→PARTIAL) in
`check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:290-291,356-389`

The parser correctly detects data in rowA's supposedly vestigial 21st column, then
`_make_row` discards that value. Finalization adds a warning line but does not include
`vestigial` in the conditions that make the producer partial. A `DRIFT` value was
therefore removed from the output while the result remained complete.

Correction requirements: detected schema drift that would discard populated data
must block complete status. Retain the raw value and source coordinates in structured
diagnostics, fail or quarantine the affected row, and require an explicit schema
decision before the new column can be mapped or intentionally ignored.

### CMP-AUD-061 — Intersection grid scanning ignores cancellation

Priority: P2  
Status: **Resolved 2026-07-18** (`7e16fea`) — the correction requirements (cancel
the document grid scan, poll between pages, propagate a distinct cancelled outcome
before the no-grid/error handling) are met: `_doc_windows` now derives BOTH grids in
ONE pass and polls `events.is_cancelled()` between pages, and `parse_pdf`
distinguishes a cancelled `(None, None)` from a no-grid result. Byte-identical
(statewide 7.9 ID: 16,459 rows, same sha256 `5104861d…`) — a pure polling addition;
`_shaded_column_windows` removed. Test in `check_intersection_detail_pdf`
(`test_061_cancellation`). **Bounded follow-up (not required by the correction, and
already bounded today):** the evidence locators `locate_tsmis`/`locate_tsn` scan one
PDF's pages without an internal poll, but `visual_evidence` already polls cancellation
per-route (`_locate_tsmis_sources`) and per-district before each call, so the
uninterruptible window is a single PDF; threading per-page polling into the 5
adapters is a clean future improvement.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:159-187,273-279`
(the grid scan); evidence-locator follow-up in `scripts/evidence_*.py`
(`locate_tsmis`/`locate_tsn`) + `scripts/visual_evidence.py`

Cancellation is checked only after `_doc_windows` has scanned every page and every
rectangle. Cancelling during a no-grid scan is therefore reported as an unreadable/no-
data error rather than cancelled, and a large document remains unresponsive through
the entire geometry pass.

The evidence locators add another long uninterruptible surface. Intersection and Ramp
build their statewide TSN indexes across every page without polling cancellation;
Highway Log and Highway Sequence discard the supplied events object and scan every
district print inside one locator call. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_cancel_poll_3upbrxej\result.json`.

Correction requirements: pass cancellation into both grid scans, check it between
pages, and propagate a distinct cancelled outcome before any error/no-grid handling.
Test cancellation before open, during each grid type, during line parsing, and just
before workbook emission.

### CMP-AUD-062 — Intersection document-median geometry silently drops pages

Priority: P1  
Status: **Resolved 2026-07-18** (census-first, `c6f72a6`) — the parser still
derives one document-median grid (census proves it is correct — see below), but
each page whose OWN band grid diverges from that median past `_PAGE_GEOM_TOL`
(6pt) is now flagged (`geom_divergent_pages`) and escalates the producer to
PARTIAL, so a shifted page can no longer silently stop classifying. **Census (217
statewide 7.9 PDFs): max per-page boundary delta 0.000pt on BOTH grids, 0
classification/value divergences** — the ID print layout is genuinely uniform
across every page, so per-page recovery (the HD-054 approach) is unneeded here and
the detection is a no-op on real data (byte-identical 16,459/16,459). A future
mixed-paper build escalates to amber instead of dropping pages. Red→green
(shifted-page fixture flagged) in `check_intersection_detail_pdf`.  
Primary code: `scripts/consolidate_tsmis_intersection_detail_pdf.py:159-204,273-300`

The parser derives one document-wide median grid for all pages. In a two-page fixture
whose second page shifted 60 points, the chosen shifted geometry parsed page two but
caused page one's valid row to stop classifying. The first row (`PAGE ONE LOST`)
vanished; only page two (`PAGE TWO KEPT`) was emitted, with two pages reported but
zero orphans, no-grid, old-layout, or vestigial anomalies. Consolidation returned
complete.

Correction requirements: derive and validate geometry per page or cluster compatible
page families, then reconcile every page carrying data bands or data-shaped text. A
page incompatible with all validated grids must be partial/error, never silently
ignored. Test shifts, scaling, rotation, mixed paper sizes, and layout changes in both
page orders.

### CMP-AUD-063 — Sequence and Ramp PDFs certify invalid post-mile code tokens

Priority: P2  
Status: **Resolved 2026-07-17** (census-first; both consolidators escalate an
unexpected token to PARTIAL, offline gate 128/128)  
Primary code: `scripts/consolidate_tsmis_highway_sequence_pdf.py:276-280`,
`scripts/consolidate_tsmis_ramp_detail_pdf.py:287-292`

Both parsers know the supported post-mile prefix vocabulary, but an unexpected `Q`
only produces a live warning and is retained under a complete producer outcome.
Highway Sequence also accepted an undocumented `Z` suffix silently because the suffix
is never validated; its documented nonblank suffix is `E`. These tokens alter the
canonical post-mile key and can turn a schema/extraction anomaly into ordinary
one-sided comparison rows without any durable indication that the source was suspect.

Correction requirements: version the accepted prefix/suffix vocabularies, count every
unexpected key token in structured parser diagnostics, and make the result at least
partial until the token is supported. Test every known code, blank, lowercase, joined
tokens, multiple characters, and unknown values on both sides of the PM.

**Scope 2026-07-17 (next C-gate; census-first, output/completion-affecting).** The
accepted vocabulary already exists: `PREFIX_SET = frozenset("CDGHLMNRST")` in BOTH
`consolidate_tsmis_highway_sequence_pdf.py` and `consolidate_tsmis_ramp_detail_pdf.py`;
HSL's documented nonblank equate SUFFIX is `E`. The two defect sites: (1) an unexpected
PREFIX is logged but KEPT under a complete outcome — `…_highway_sequence_pdf.py:290`
(`if vals["prefix"] and vals["prefix"] not in PREFIX_SET: … (kept)`) and
`…_ramp_detail_pdf.py:301` (the `vals["pr"]` equivalent); (2) HSL never validates the
equate suffix at all (a `Z` is silently accepted). Fix: version the vocab, add a
structured unexpected-token DIAGNOSTIC count, and escalate the producer outcome to at
least PARTIAL when an unknown prefix/suffix appears (never silently complete). This is
output/completion-affecting, so it is **census-first, like CMP-AUD-070/034**: parse the
statewide HSL-PDF + RD-PDF corpora and confirm ONLY `PREFIX_SET` prefixes and `{blank,
E}` suffixes appear, so the escalation never false-fires on real data (every current
statewide consolidation must stay COMPLETE). The census is a SLOW, RAM-heavy pdfplumber
sweep — serialize it (the memory lesson: 3 concurrent statewide pdfplumber jobs starved
RAM). If any unknown token appears on real data, it becomes a data question, not an
autonomous escalation. Remains open.

**Remediated 2026-07-17.** Census-first, exactly as scoped. A shared
`pdf_table_lib.unexpected_pm_tokens(prefix, suffix, *, prefix_set, suffix_set)`
owns the membership rule (a non-empty window that is not an EXACT member of its
accepted set is unexpected — lowercase, joined, multi-char, and unknown tokens
all qualify; a blank window never does); the two parsers own their censused,
VERSIONED vocabularies (`PREFIX_SET = frozenset("CDGHLMNRST")` both;
`SUFFIX_SET = frozenset("E")` for Highway Sequence, which has the suffix window;
Ramp Detail has no suffix column; `PM_VOCAB_VERSION = 1` each). Each `parse_pdf`
now counts every unexpected prefix/suffix into a structured `stats["bad_tokens"]`
diagnostic and logs it (naming the window + `vocab v1`); `convert_one`
accumulates `ctx["bad_tokens"]`; `finalize` escalates `result.completion` to
PARTIAL and adds a ⚠ note. Highway Sequence now validates the suffix it never
checked (a stray `Z` escalates). `bad_tokens` drives COMPLETION only — never
`skipped_inputs`/`failed_inputs` (those stay the file-level channels; the
separate CMP-AUD-064 defect is untouched).

- **Census (the hard requirement — the escalation must never false-fire on real
  data).** A read-only serialized pdfplumber sweep of the bound 7.9 ssor-prod
  corpus (`ground-truth/All Reports 7.9/2026-07-09 ssor-prod/`): Highway
  Sequence 252 PDFs → 60,493 rows, prefixes `{C,D,G,H,L,M,N,R,S,T}` (all ten
  codes appear), suffixes `{E: 1132}`; Ramp Detail 126 PDFs → 15,216 rows,
  prefixes `{C,L,M,R,S,T}`; both 0 unclassified / 0 stray. Every token ⊆ the
  accepted vocabulary, so **both statewide consolidations stay COMPLETE** — the
  escalation adds no false PARTIAL. (Numbers bound in the canary-bindings doc.)
- **Red→green on the SAME defect input**: a bad HSL fixture (unexpected `Q`
  prefix + `Z` suffix) and a bad RD fixture (unexpected `Q` prefix) through the
  real consolidators returned `('ok', 'complete')` PRE-fix (the defect), `('ok',
  'partial')` POST-fix. NEW `build/check_pm_code_vocabulary.py` (30+ pins):
  the membership rule exhaustively (every known code, blank, lowercase, joined,
  multi-char, unknown, both PM sides, the RD no-suffix case), and hermetic
  positioned-Helvetica fixture PDFs driving BOTH consolidators end to end — an
  unexpected token escalates to PARTIAL with the note, and a clean render stays
  COMPLETE (the census invariant in miniature). The `check_pdf_route_identity`
  parse-stub base dicts gained `bad_tokens: 0` to match the widened contract.
- Offline gate **128/128**; `ruff check scripts` clean.

### CMP-AUD-064 — PDF parser anomaly counts masquerade as skipped input counts

Priority: P2  
Status: Verified with one PDF containing three malformed lines  
Primary code: `scripts/consolidate_tsmis_highway_sequence_pdf.py:351-375`,
`scripts/consolidate_tsmis_ramp_detail_pdf.py:365-389`, `scripts/events.py:138-141`

The result contract defines `skipped_inputs` as the number of input files left out.
The two parsers instead assign their count of unclassified lines/fragments directly to
that field. One affected PDF with three malformed lines therefore reports three
skipped inputs even though only one input exists. Completion is correctly partial,
but the structured evidence and every consumer using it overstate the affected source
count.

Correction requirements: track parse anomalies in a separate field/diagnostic and set
`skipped_inputs` to the count of distinct affected or omitted PDFs. Lock invariants
that skipped/failed input counts cannot exceed discovered inputs and that per-file
line counts remain available without changing file-level totals.

### CMP-AUD-065 — Highway Sequence PDF-vs-Excel suppresses three same-source fields

Priority: P1  
Status: Verified end to end in a values workbook  
Primary code: `scripts/compare_highway_sequence_tsn.py:49-62,214-229`,
`scripts/compare_highway_sequence_pdf.py:101-105`

The base Highway Sequence schema treats HG, City, and Distance To Next Point as TSN
context because the two systems populate them at different granularity. The PDF-vs-
Excel self-check clones that schema without clearing those exclusions even though both
sides are TSMIS renderings of the same report. At the same Route+County+PM, PDF values
`CITYA`/`D`/`000.500` versus Excel `CITYB`/`U`/`000.999` returned `verdict=match` and
Comparison Diffs=0. The differing originals survived only on the side sheets; the
Comparison row displayed the PDF values as if shared.

Correction requirements: give PDF-vs-Excel a self-comparison schema with no TSN-only
context suppression. Mutate each of all seven shared fields independently and require
the intended field label, one counted difference, and a diff verdict in both output
modes.

**Remediated 2026-07-16 by CMP-AUD-199 (re-verified 2026-07-17, the bucket-A sweep).** The same-source schema (SS_HEADER/_SS_SCHEMA) compares County, PM, PM Suffix, City, HG, FT, Distance To Next Point, and Description with context_fields EMPTY — the three previously-suppressed fields are ordinary compared cells, and the 2026-07-16 corpus proof asserts every cell (oracle-exact 1,410/3,721).

### CMP-AUD-066 — PDF comparison roles are not provenance-validated

Priority: P1  
Status: Verified with physically distinct same-content workbooks  
Primary code: `scripts/compare_highway_log_pdf.py:53-63`,
`scripts/compare_highway_sequence_pdf.py:110-138`,
`scripts/compare_highway_detail_pdf.py:54-80`,
`scripts/compare_intersection_detail_pdf.py:57-85`

The PDF-vs-Excel recipes label the first picker as PDF but validate only a workbook
shape that the Excel rendering also has. Two distinct copies of an Excel-consolidated
workbook were accepted as `TSMIS (PDF)` and `TSMIS (Excel)` for Highway Log, Highway
Sequence, and Highway Detail and certified as matches. Highway Log PDF-vs-TSN also
accepted two TSMIS Excel copies under `TSMIS (PDF)` and `TSN (PDF)`. This is broader
than CMP-AUD-040's same-file alias. Intersection Detail behaved the same with two
native-Excel copies, while Ramp Detail's richer PDF header correctly rejected its
native-Excel control. The paths and file identities were different, so path
de-duplication cannot establish that either required source was ever compared.

**2026-07-17 partial:** the Highway Log v5 marker gate (CMP-AUD-157/045-HL) closes
this finding's HL PDF-vs-TSN instance as a side effect — the TSN side must now carry
the "TSN Normalization" marker sheet, so a TSMIS workbook (which never has one) can
no longer stand in as `TSN (PDF)`.

Correction requirements: persist durable producer/report/source-role metadata and
validate it against each picker role before loading rows. Distinct copies, renamed
files, wrong producer editions, and missing/stale/malformed metadata must not certify a
source-specific comparison. Provide an explicit legacy-import workflow if unmarked
historical workbooks must remain usable.

**Remediation (2026-07-17, the PDF-role halves — the finding closed).** Every
workbook this app writes FROM PDFs now carries a very-hidden versioned
`TSMIS PDF Conversion` marker sheet: the five per-route converted files
(`pdf_table_lib.write_route_workbook(pdf_source_marker=True)` — an OPT-IN
seam, because the TSN Highway Log consolidator shares that writer and must
stay unmarked) and every combined conversion workbook (`run_pdf_conversion`
wraps the report's `decorate_workbook`, append()-based so the write-only
combine path works). The four vulnerable families' flavors enforce roles at
load: the `TSMIS (PDF)` side REQUIRES a valid marker
(`compare_tsn_common.require_pdf_source` — unmarked and pre-marker picks
refuse with a re-consolidate hint, the explicit legacy path: re-consolidate
once and the workbook re-earns its role), the `TSMIS (Excel)` side REJECTS
any marker presence (`reject_pdf_source` — valid OR malformed: a corrupted
marker still says PDF-sourced), and the vs-TSN flavors' `TSMIS (PDF)` sides
gate identically while their TSN sides keep their own normalization-marker
gates. `pdf_source_marker_state` fails CLOSED both ways (-1 for
present-but-malformed is never valid for the PDF role and never clean for
the Excel role). Unmarked HISTORICAL EXCEL workbooks stay fully usable — no
migration needed on the Excel role. Ramp Detail needs no gate: its
13-column PDF-only header (On/Off + Ramp Type) already rejects the Excel
shape structurally, as this finding itself verified. Red→green: the new
`check_pdf_role_provenance` (writer/opt-in/fail-closed pins + all four
families' require/reject/honest-pair flows + the three vs-TSN PDF-side
refusals; 15 red pre-fix — every mismatched-role run returned ok) and the
gate grew to 126/126 (one check-fixture update: check_compare_highway_log's
PDF-side fixtures now carry the marker like every real conversion). Real
corpus: converting the real ssor-prod 7.9 route-051 Highway Log PDF stamps
BOTH artifacts (per-route + combined, marker state 1); the honest real pair
(that conversion vs the real vendor Excel export) compares — 82/82
locations identical; the SWAPPED roles refuse with the exact hint.
Operational note: PDF-sourced consolidated workbooks written BEFORE this
change (stores, old run folders) refuse on the PDF role until
re-consolidated once — the refusal message says exactly that.

### CMP-AUD-067 — TSN projections hide PDF-vs-Excel source differences

Priority: P1  
Status: Verified across four PDF-vs-Excel self-check families  
Primary code: `scripts/compare_highway_log.py:66-69`,
`scripts/highway_log_columns.py:246-257`,
`scripts/compare_highway_log_pdf.py:41-46`,
`scripts/compare_highway_sequence_tsn.py:89-101,129-140`,
`scripts/compare_highway_sequence_pdf.py:110-138`,
`scripts/compare_highway_detail_tsn.py:156-173,215-220,246-261,354-376`,
`scripts/compare_highway_detail_pdf.py:54-80`,
`scripts/compare_intersection_detail_tsn.py:241-267,331-350`,
`scripts/compare_intersection_detail_pdf.py:57-85`

The self-check adapters reuse projectors designed to reconcile unlike TSMIS and TSN
encodings. That erases discrepancies which PDF-vs-Excel exists to detect:

- Highway Log inferred Excel Location `000.100` as `000.100R` from its roadbed block
  and matched it to PDF `000.100R`.
- Highway Detail's `pm_canon` likewise filled a missing R/L from HG, and its TSN-only
  NA crosswalk made PDF blank equal Excel `A`.
- Highway Sequence stripped a lost `001/` Description prefix, making `001/JCT 5`
  equal `JCT 5`.
- Intersection Detail folded raw control type `J` to combined `S`, making PDF `J`
  equal Excel `S`; a `J`-versus-`A` control did flag, but displayed rewritten `S ≠ A`.

Every isolated mutation returned match with zero differences. For the roadbed cases,
the projected token is also the key, so the lost source text cannot appear as an
ordinary compared field.

Correction requirements: define same-source projectors and identity separately from
cross-system normalization. Preserve original values and apply only explicitly
documented PDF/Excel render equivalences; surface canonical and raw identity separately
when canonical pairing is still required. Add a per-family mutation matrix for every
crosswalk/normalizer, proving each non-approved source difference changes the verdict
and retains the raw values in output.

**Remediation (2026-07-17).** The finding's exact isolated mutations were first
REPLAYED against the then-current flavors (fixtures under the CMP-AUD-066
marker): HSL's instance was already fixed by CMP-AUD-199/204 ("001/JCT 5" vs
"JCT 5" flags), Ramp Detail never had one (verbatim loader — a Description
mutation flags raw), and the ID/HD/HL instances all REPRODUCED verbatim
("EVERYTHING MATCHES" / the rewritten "S ≠ A"). Each family then got a
same-source projection that separates PAIRING identity from cross-system value
reconciliation:
  * **Intersection Detail** — `_tsmis_row_with(r, project)` (one row body, two
    projections) + `_load_tsmis_same_source`: the 045 physical pairing key and
    Location-derived provenance are IDENTICAL to the vs-TSN projection, but
    every value cell is verbatim — the control-type J→S crosswalk (and the
    boolean/date/numeric folds) exist to bridge TSN's encodings and no longer
    touch two TSMIS renders. PDF `J` vs Excel `S` now FLAGS and a J-vs-A cell
    displays the RAW "J ≠ A".
  * **Highway Detail** — the same `_tsmis_row_with` seam + `SS_HEADER` =
    SHARED_HEADER + "PM (raw)": the canonical roadbed-aware Post Mile stays the
    PAIRING key (the vendor Excel genuinely drops roadbed letters, so verbatim
    keys would explode one-sided rows), the RAW printed token is its own
    compared trailing cell (a dropped R/L SURFACES instead of hiding inside the
    key), NA and every other value cell compare verbatim (the TSN-only
    'A'→blank fold no longer applies), and the one kept normalization is the
    typed-date render equivalence (openpyxl cell typing, value-identical).
  * **Highway Log** — after re-reading the locked
    docs/highway_log/comparison-study.md + the Phase-3 decision gates: the §7b
    roadbed-canonical key and the ditto non-asserting convention are UNTOUCHED
    (pairing semantics correctness-locked), and the same-source flavor appends
    "Location (raw)" as its own compared cell (`_load_pair_same_source` +
    `_SS_HEADER`, a flavor-scoped schema — no shared-engine edit): an Excel
    "1.000" whose dittoed block implies R used to match the PDF's explicit
    "1.000R" with zero differences. (The stale highway_log_columns comment
    claiming PDF-vs-Excel is "unaffected" by the key normalizer was
    probe-refuted — the flavor inherits it from the shared schema.)
Red→green: the new `check_compare_same_source` mutation matrix (HSL/RD pinned
green as permanent guards; ID two pins, HD two pins, HL one pin all red
pre-fix; identical-render MATCH pins hold everywhere); gate 127/127.
**Statewide re-verifies (fresh consolidations from the bound 7.9 sets, under
the full 049+066+067 stack — zero identity/role refusals anywhere):**
  * ID (ars-prod): **16,459 / 0 / 0 with exactly ONE differing cell — HG
    "D ≠ U", the known real 108/TUO defect** — the verbatim projector surfaced
    ZERO new classes statewide (a no-delta re-bless; the crosswalk's statewide
    reach was nil, which is exactly why the mutation matrix, not the corpus,
    is the guard).
  * HD (ars-prod): **the row TOPOLOGY is exactly the v0.26.0 reference —
    50,730 matched / 50,171 fully identical / 559 differing rows / 476 + 543 =
    1,019 one-sided — pairing unchanged as designed**, while the cell
    accounting is now verbatim: 1,622 differing cells, including the
    previously-INVISIBLE classes the fix exists to surface — "PM (raw)" 5 (the
    vendor Excel's dropped roadbed letters), NA 6 (the A-vs-blank class the
    TSN fold hid), PS 5 — beside the known real render classes (Length 374,
    the LB block ~148 each, dates/HG/AC/City…), all within the SAME 559 rows
    the old projector already flagged.
  * HL (ssor-prod): **51,884 matched / 51,261 fully identical / 623 differing
    rows / 624 differing cells / 2 PDF-only, 0 Excel-only** — the classes are
    the flavor DOING ITS JOB: "LB T-W Wid" 608 (the known vendor-Excel
    blanked-width bug), "Sig Chg. Date" 11, Description 5. "Location (raw)"
    contributed ZERO cells statewide — the dropped-roadbed class is LATENT on
    this pull (like ID's crosswalk). NEW FINDING surfaced by the verbatim
    Description class: the TSMIS-PDF parser DROPS asterisk-leading printed
    Descriptions ("(blank) ≠ *" ×2, "(blank) ≠ **** CODE ACCIDENTS TO") — the
    exact mirror of the TSN v5 star-recovery (CMP-AUD-157), bound as a
    follow-up work item in the plan; a "— MER 059" Description tail on one PDF
    row is censused there too.

### CMP-AUD-068 — PDF-vs-TSN Detail paths omit Report View

Priority: P2  
Status: Verified for Highway and source-bound end-to-end for current Intersection Detail  
Primary code: `scripts/compare_highway_detail_tsn.py:838-855`,
`scripts/compare_highway_detail_pdf.py:42-49,59-67`,
`scripts/compare_intersection_detail_tsn.py:917-936`,
`scripts/compare_intersection_detail_pdf.py:45,62-70`

The ordinary Highway and Intersection Detail vs TSN entry points add their two-line
domain Report Views at call time. Both PDF-vs-TSN adapters invoke the static base
schemas directly, so the same semantic comparisons omit that sheet and its TSN-only
diagnostics. Clean controls produced Report View on each Excel leg and no such sheet on
the corresponding PDF leg. This is capability loss, independent of the Report View
equality defects tracked in CMP-AUD-039 and CMP-AUD-043.

Correction requirements: compose the report-specific extra writer into every
applicable source flavor, then assert sheet/field parity across Excel-vs-TSN and PDF-
vs-TSN. Apply the unified equality model before treating Report View as trustworthy.

Current Intersection Detail Stage-8 evidence is exact on both raw and normalized inputs.
Each Excel-vs-TSN workbook has `Report View`; each PDF-vs-TSN workbook omits it. The raw
Excel leg's view contains 16,886 logical records / 33,772 physical data rows and maps all
16,626 nonblank `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT` claims. The normalized Excel
leg has the same record universe but blanks all three fields under CMP-AUD-133. The PDF
legs therefore lose the entire layered view rather than only those three normalized
values. All four exact sheet universes are acceptance-bound in the 1,059,072-byte
Stage-8 result; this finding remains product-red.

### CMP-AUD-069 — Ramp PDF comparisons mislabel their file roles in diagnostics

Priority: P2  
Status: Verified through missing-file diagnostics and event logs  
Primary code: `scripts/compare_ramp_detail_pdf.py:215-223`,
`scripts/compare_tsn_common.py:172-176,197-207`

Ramp Detail's PDF wrapper builds the correct schema and banner labels but does not pass
them to the shared file driver. The driver therefore uses its default `TSMIS`/`TSN`
roles: PDF-vs-Excel reports a missing second workbook as “The TSN file doesn't exist”
and logs the selected Excel input as TSN. The Intersection wrapper provides the
correct control by forwarding both role labels.

Correction requirements: pass the schema's side labels to the shared driver, or make
the driver derive them from one authoritative schema. Test existence messages, log
lines, picker labels, workbook labels, and banners for every PDF triangle flavor.

### CMP-AUD-070 — Intersection loader ignores explicit route and suffix fields

Priority: P1  
Status: Verified through fixtures and the current 434-member source-bound triangle  
Primary code: `scripts/compare_intersection_detail_tsn.py:153-202,331-350`,
`scripts/compare_intersection_detail_pdf.py:57-85`

The consolidated Intersection row contains an explicit Route at position zero and an
explicit source `S` suffix field, but `_tsmis_row` derives both compared Route and
Route Suffix solely from the route token embedded in Location. PDF Route 001 versus
Excel Route 002 returned match when both Location cells said route 002; both loaded
rows were relabelled 002. Likewise, explicit source `S` values `U` versus blank
returned match when both Location values lacked a suffix; both loaded suffixes became
blank. Thus two authoritative source disagreements are discarded before comparison,
and an upstream route conflict such as CMP-AUD-049 can be laundered into a clean row.

Correction requirements: retain and validate the consolidated Route, Location route,
and explicit suffix as separate source claims. Require their normalized identities to
agree within each input, use the authoritative route for grouping, and compare the raw
suffix field rather than reconstructing it from another cell. Test every pairwise
conflict, blank claim, suffixed route, and both input directions.

The Stage-8 production consolidations narrow the defect boundary. Across all 217 Excel
and 217 PDF members, every explicit member Route and physical `S` value is preserved
exactly into the consolidated workbooks; there are zero Route mismatches and zero `S`
mismatches. Every nonblank typed cell is exact. The Excel consolidator's only permitted
representation change is 125,152 explicit empty strings serialized as physical blanks;
the PDF consolidation is raw-representation exact. The comparison then re-derives Route
and Route Suffix from Location and omits both source claims, proving the loss occurs in
the loader/comparison projection rather than the exporter or consolidator. The exact
source-claim ledger SHA-256 on both TSMIS forms is
`a7fc8d1617b03d19258ce5455c0b847697c755f5ef911b65e3de9b484a3dcfa8`.

**Census 2026-07-17 — OWNER-GATED: the prescribed fix is output-affecting, NOT
safe-by-construction.** A read-only agreement census consolidated the real ID corpus
(`Intersection Detail Bundle 7.8`, 16,459 rows; column semantics
`['Route','P','Post Mile','S','Location',…]` — explicit Route at col 0, explicit `S`
at col 3, Location at col 4) and compared the explicit source fields against the
Location-derived values the comparison currently uses (base-split so `008U`/`010S`
suffixed routes are correctly excluded):
- **259 rows** carry a genuine mainline-route-vs-Location-route disagreement — e.g. a
  `route_009` file row whose Location reads `05 SCR 001` (base `001`). The comparison
  currently keys these by the Location route (`001`); switching to the authoritative
  col-0 route (`009`), as the correction requires, would **re-group all 259 rows** and
  move the pairing, one-sided classification, and the ID canary (21,675/687).
- The compared **Route Suffix** switch (Location-derived → raw col-3) shows a
  None-vs-`""` representation gap on all 16,459 rows plus **33 rows** where the raw col-3
  `S` genuinely differs from the Location-derived suffix — so it too would change output.

Therefore this finding is **not an autonomous safe-by-construction change** under the
owner directive (changes that "can lead to discrepancies" are not pre-approved). The
core question — *when the mainline route (col 0) and the Location-embedded route disagree
on 259 rows, which is authoritative for the comparison key?* — is a source-truth / domain
ruling that needs the owner and an investigation into what the Location column encodes on
those rows (a genuine cross-reference vs a data anomaly). The finding's earlier Stage-8
"zero Route mismatches / zero S mismatches" measured consolidation PRESERVATION of the
explicit fields, not this col-0-vs-Location relationship. Census script:
`_scratch`-equivalent `census_070.py` (session scratchpad; results recorded here).
Remains **open, re-classified from "lighter C-gate" to owner-gated output-affecting.**

**RESOLVED 2026-07-17 — NOT A DEFECT; the current loader is correct (owner-endorsed
direction).** A row-by-row comparison of all 259 against the raw TSN extract settled it:
the 259 are **route-origin / junction rows** (descriptions: `BEG RTE 20`, `JCT 9-RIVER
ST`, `JCT 12/29`) — the FILE route is the report the row appears in, but the intersection
physically sits on the CROSSING route, so the Location names the crossing route. **TSN
represents them identically by route: for 259/259 TSN carries the same physical route +
county as TSMIS's Location (NOT the file route), and 259/259 have a byte-exact TSN
description twin** at a DIFFERENT postmile (TSMIS stamps the mainline's PM, e.g. `000.000`;
TSN stamps the crossing route's actual PM, e.g. `059.803`). So the current loader — which
keys by the Location (physical) route on BOTH sides — is CORRECT and matches TSN; the
prescribed fix (key by the FILE route) would make TSMIS DISAGREE with TSN on all 259 rows,
introducing discrepancies. The "require file route == Location route" half would falsely
flag 259 legitimate equate rows. The one-sidedness of these rows is a mainline-PM vs
crossing-PM difference, already reflected in the accepted one-sided counts. Key validated:
the same physical key matched 16,200/16,200 (100%) agreeing rows and 0/259 disagreeing.
Evidence sheet: session scratchpad `CMP-AUD-070 route-vs-location (7.8).xlsx`.

**Audit spillover (owner-requested): no OTHER report has this trap live.** Ramp Detail's
comparison IS code-asymmetric (TSMIS keys by the file route at col 0; TSN by the Location
route) but BENIGN — ramps are always physically on their own mainline route, so file route
== Location route on all 15,216 statewide rows (0 disagreements); it's latent fragility
only. Highway Detail (explicit `RTE` col) and Highway Sequence (parsed route) have no
crossing-route-in-Location duality; Highway Log keys by district/county/route-group
ownership. The forthcoming per-row "source file" provenance column (owner-requested) will
make this class of file-vs-physical divergence visible on every TSMIS-only comparison tab.

### CMP-AUD-071 — Ramp Summary comparison does not validate its route universe

Priority: P1  
Status: Verified with empty and duplicate-route consolidated workbooks  
Primary code: `scripts/compare_ramp_summary_tsn.py:128-166,197-209`

The TSMIS loader validates only a shaped header, then sums category cells without
requiring any route rows or checking route identity/uniqueness. A header-only workbook
produced a complete zero universe with no warnings and 31 ordinary Both/zero-diff
categories. Two Route 001 rows carrying 5 each were silently summed to TSN 10, again
with no warnings and all 31 compared categories aligned. CMP-AUD-024's unrelated
TSMIS-only zero footnote currently forces the overall verdict to diff, but the route
coverage corruption is invisible and would become a false clean once that footnote
bug is corrected.

The accepted current corpus establishes the exact positive control the product must
enforce: 126 unique ordered routes, including `005S`, `010S`, `015S`, and `880S`.
Production happened to emit that exact route order and all 3,780 values on the accepted
run, but completion still has no route-universe assertion; the empty/duplicate fixtures
above remain valid red reproductions.

Correction requirements: require at least one valid normalized route, reject blank or
duplicate routes, and reconcile discovered route counts/identities with producer
metadata before aggregation. Preserve the route universe in structured diagnostics;
test empty, header-only, duplicate-identical, duplicate-conflicting, padded aliases,
and partial statewide inputs.

**Re-verified still OPEN (2026-07-17, the bucket-A sweep).** NOT closed by CMP-AUD-050: that remediation fixed the CONSOLIDATION-side collection loop (duplicate/blank route refusals when building the Ramp Summary workbook). This finding is the COMPARATOR side — compare_ramp_summary_tsn accepting a header-only or duplicate-route CONSOLIDATED workbook and summing without route-universe validation. Remains bucket C (loader/validation contracts).

### CMP-AUD-072 — stale folder discovery can overwrite a newer recipe selection

Priority: P2  
Status: REMEDIATED 2026-07-18 (`c244fc4`, CI SHA-verified) — generation token +
recipe-key snapshot + Start-disabled-while-loading  
Primary code: `scripts/ui/ui-compare.js:119-142`, `scripts/ui/app.js:755-765`

Each folder-recipe render starts an asynchronous `get_compare_folders` request without
a generation token, current-key check, or sequencing. In the harness, recipe A's
request was delayed 60 ms, the UI switched to B whose request returned in 5 ms, then
A's stale response arrived last. The selected key remained B while both final folder
lists contained A's runs (`expected_prefix=B`, `actual_prefix=A`). Start is not held
disabled while discovery is unresolved, so the wrong run choices can be launched
through the newer adapter.

Correction requirements: snapshot the recipe key and request generation, discard any
response that is not still current/latest, and clear/disable Start while options are
loading. Test both response orders, rejection/fallback, state-push rerenders, custom
paths, and rapid A→B→A switching.

#### Remediation — 2026-07-18

`renderCompareDirs` now mirrors `refreshConsDest`'s `consDestSeq` guard: it
increments a `compareDirsSeq` generation token AND snapshots the recipe key before
awaiting, then discards any response that is not still the latest (`seq !==
compareDirsSeq`) or whose recipe changed under it (`key !== compareChoice()`) — so a
slow response for an abandoned recipe can no longer stomp the current folder lists.
A `compareDirsLoading` flag holds Start disabled (via `syncCompareButton`, with a
"Finding the run folders…" tooltip) while a discovery is unresolved. New
`build/check_compare_dirs_race.js` drives the real functions in a `vm` sandbox with
DEFERRED, out-of-order `get_compare_folders` promises: it proves the A→B→A stale
response is discarded (B's folders stand), Start is held disabled while loading, a
clean single discovery applies + enables, and a rejected discovery falls back to the
seed list. Red→green: the stale-A-wins and Start-not-disabled checks both fail
without the fix. #mock confirms the normal folders path still populates the dropdowns
(ssor-prod vs ars-prod defaults) and enables Start.

### CMP-AUD-073 — the classic picker blocks supported raw-PDF inputs

Priority: P2  
Status: Verified at the native-dialog boundary and both raw parsers  
Primary code: `scripts/gui_compare_api.py:92-102`,
`scripts/ui/ui-compare.js:179-184`,
`scripts/compare_ramp_summary_tsn.py:97-112,212-221`,
`scripts/compare_intersection_summary_tsn.py:147-160,249-257`

The only classic file picker always supplies the native dialog with
`Excel workbook (*.xlsx)`. Ramp Summary vs TSN and Intersection Summary vs TSN both
explicitly support a raw statewide TSN PDF as their second input, but the UI sends
neither recipe key nor side role and cannot offer that extension. Captured dialog
arguments were XLSX-only, while isolated `.pdf` calls exercised both production parser
branches successfully. A normalized XLSX is a workaround, not the advertised raw-PDF
path.

Correction requirements: declare accepted extensions per recipe role in the registry,
pass key and role into the picker, and render the matching native filters/help. Assert
raw PDF and normalized XLSX selection for both Summary recipes plus XLSX-only controls
for every other role.

### CMP-AUD-074 — the universal file hint promises unsupported per-route inputs

Priority: P2  
Status: Verified by executable recipe census and rejection fixture  
Primary code: `scripts/ui/ui-compare.js:144-153`,
`scripts/compare_highway_log.py:94-145`

Every file recipe is told it accepts either two per-route workbooks or two consolidated
workbooks. Only the three Highway Log recipes accept both shapes. The other 14 file
recipes require consolidated TSMIS/PDF workbooks and statewide/raw/normalized TSN
inputs. A per-route Ramp Summary workbook offered under that guidance was rejected as
not consolidated; the two Summary recipes do not even take two workbooks when their
raw PDF path is used.

Correction requirements: make accepted shape and per-role guidance registry-owned and
render it for the selected recipe. Lock every hint against positive and negative
loader fixtures, including per-route, consolidated, statewide PDF, raw XLSX, and
normalized-library forms.

### CMP-AUD-075 — both-mode completion is persisted for only one output

Priority: P1  
Status: Partially remediated — central both-mode generation fixed; Matrix formula twins remain split  
Primary code: `scripts/gui_worker_export.py:581-597`,
`scripts/compare_core.py:1960-1968`, `scripts/consolidation_meta.py:229-255`

A successful both-mode comparison commits formulas and values workbooks, but returns
only the formulas path. `ConsolidateWorker` writes one outcome sidecar beside that path.
A synthetic partial result with one skipped input therefore produced a formulas
sidecar that read `partial`, while the equally partial values workbook had no sidecar;
`read_completion` returned `None`, which legacy consumers infer as complete. If the
formulas best-effort commit fails the chosen path flips, demonstrating that publication
depends on commit order rather than both deliverables' shared truth state.

Correction requirements: return a structured map of every committed output and
publish the same validated outcome beside each artifact. Sidecar publication must be
all-artifact safe: no twin may remain reusable as complete if another write fails.
Test complete/partial, formulas best-effort failure, locked sidecars, rollback, and
both artifact-opening orders.

#### Remediation progress — 2026-07-11

The central `artifact_store.commit_workbook` path now returns every committed member.
Classic/direct `mode="both"` publishes values and optional formulas as one UUID
generation with identical typed truth, peer membership, SHA-256 binding, conservative
sentinels, and all-member-safe interruption behavior. Generic workers no longer race a
second comparison sidecar write. `check_comparison_sidecars.py` and
`check_comparison_publication.py` lock both opening orders, tamper, locks, partial state,
formulas best-effort failure, and recovery.

The finding is not resolved: Everything, day, and baseline Matrix `also_formulas`
still run values and formulas as two comparator calls. Each commit creates a fresh
generation ID, so the twins are not one generation and a later values-only/failed
formula refresh can leave stale formula evidence. This residual is the Phase-5
CMP-AUD-082 integration gate; it must not be hidden by the central publisher fix.

### CMP-AUD-076 — saved comparisons lack durable source provenance

Priority: P2  
Status: Resolved 2026-07-14 — durable provenance in a sidecar + in-workbook sheet for every comparison; only the strict schema-v4 fold-in remains (Phase-5 artifact epoch)  
Primary code: `scripts/compare_tsn_common.py:219-222`,
`scripts/compare_env.py:666-669`, `scripts/compare_core.py:1503-1504`,
`scripts/consolidation_meta.py:157-163`

File comparisons pass only input basenames into the workbook; environment adapters
pass only folder basenames, and the outcome sidecar records no recipe or source
identity. Distinct `A\same.xlsx` and `B\same.xlsx` consequently produced the ambiguous
provenance line `TSMIS: same.xlsx    TSN: same.xlsx`; neither full selection nor a
fingerprint survived in the workbook or sidecar. Renames, run-root/report-subfolder
aliases, and later file replacement cannot be audited from the saved artifact.

Stage-8 Ramp Summary adds a real source example. The 126 TSMIS PDFs print report date
07/09/2026, reference date 07/10/2026, route/title claims, and submitter
`Yunus.Shaikh@dot.ca.gov`; their Excel siblings also retain per-route generated times.
The production consolidated/comparison workbooks preserve only source basenames and
lose those printed claims. All source-backed numeric values are exact, but the saved
comparison cannot independently identify the pull/snapshot that supplied them.

Chunk 12 exposed the operational consequence on real statewide Highway Log data. A
fresh PDF-vs-TSN values build found 46,919 paired rows—164 more than the older
documented canary—while the TSN universe remained 60,083. The arithmetic is consistent
with TSMIS source drift, but the retained artifacts do not carry enough durable source
identity to prove exactly which pull/generation changed or exclude a semantic producer
change after the fact. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_hl_pdf_vs_tsn.xlsx`.

Correction requirements: persist the stable recipe key, role, canonical selection and
effective input identity, content fingerprint, and producer metadata in a structured
workbook sheet and sidecar. Keep human display concise while retaining unambiguous
machine-readable evidence. Test same basenames, copies, aliases, moved files, and
folder discoveries with overlapping members.

**Remediation, file-kind half (2026-07-14).** `run_files_compare` — the shared
driver behind every file-kind comparator — now captures each input's identity
BEFORE any loader reads it (`capture_input_provenance`: role, basename, FULL
canonical selection, streaming sha256, size, mtime_ns, and the producer
completion read through the coupled mtime-validated outcome reader) and, after
a successful commit, persists the record as a tolerant `.provenance.json`
sidecar beside the workbook (`write_comparison_provenance`, the write_outcome
pattern: guard-disciplined temp+replace; a write failure logs and never fails
the comparison; absence reads as an older comparison). The record binds the
recipe (report + banner), both inputs, the committed `generation_id`, and the
member digests. The run log now prints both FULL selections + digest prefixes
under the concise banner names. `artifact_store.fingerprint` excludes the new
sidecar. Fixtures: `test_provenance_sidecar` (same basenames in different
directories disambiguated; a byte-copy keeps the digest under its own
selection; absent/corrupt sidecars read None), the updated 8-line driver
banner lock, and the coupled-reader read-twice lock. Real-corpus: both summary
comparisons persist real records (full Downloads selections, real digests, the
ssor-prod consolidated workbook's `complete` producer completion) with both
oracles unchanged. **Still open in this finding:** compare_env's folder-kind
provenance (member census + metadata fingerprint — `fingerprint()` is
(name,size,mtime_ns) metadata, stated honestly), the in-workbook structured
Provenance sheet, moved-file/alias mutation coverage beyond copies, and folding
the sidecar into the strict schema-v4 payload (Phase-5 artifact epoch).

**Folder-kind half (2026-07-14, same day).** `compare_env.compare_folders` now
captures the exact discovered member census per side (name/size/mtime_ns,
statted BEFORE any loader reads — the census is the effective input identity;
a per-member content digest would re-read hundreds of files, and the existing
discovery-set tripwire + captured identities already guard the read window)
and persists {folder-kind roles = the derived side labels, full canonical
folder selections, member counts + census, recipe, committed generation} via
the same `.provenance.json` writer. Both kinds carry an explicit `kind` field.
Fixture: the Intersection Detail env e2e asserts the folder record end to end
through the strict publication machinery. Folder-kind real-corpus exercise
rides the next work-PC visit (with the owed baseline-matrix two-day run).

**Final piece (2026-07-14, same day).** `run_compare` gained an opt-in additive
`provenance=` kwarg (default None → every direct caller byte-identical, honoring
the correctness lock): both drivers now pass the pre-read record, and the
workbook itself carries a concise human-facing **Provenance sheet** — the
recipe, each input's role/kind, FULL canonical selection, content digest (file)
or discovered member count (folder), and the producer completion — with the
note that the machine binding (committed generation) lives in the sidecar.
Verified on the real corpus (the regenerated summary comparisons carry the
sheet with the real Downloads selections + digests; oracles unchanged) and the
full gate (no sheet-list assertion anywhere broke). Moved files and aliases are
covered by construction: the record persists the resolved compare-time
selection (a later move cannot retroactively alter it) and `resolve()`
canonicalizes aliases at capture. The only remainder is folding the sidecar
into the strict schema-v4 payload — Phase-5 artifact-epoch work, tracked there.

### CMP-AUD-077 — comparison results discard structured discrepancy counts

Priority: P2  
Status: Resolved — Phase-2 typed-count gate passed 106/106  
Primary code: `scripts/compare_core.py:1909-1937,1964-1968`,
`scripts/events.py:110-141`

The engine computes matched, side-only, differing-row, and differing-cell counts, then
returns only a coarse verdict plus human summary strings. A one-difference result had
`verdict=diff` but no structured discrepancy fields; API, sidecar, validation, and
matrix consumers must reopen/scrape a workbook or recompute the comparison. That makes
cross-surface consistency difficult to assert and helped the partial-count drift in
CMP-AUD-011 and CMP-AUD-017 survive.

Correction requirements: add typed comparison counts to the result and outcome
sidecar, with invariants against workbook Summary/Comparison/Only-in totals. Test all
output modes, match, differences, one-sided rows, zero rows, warnings, partial state,
and cancellation.

#### Remediation — 2026-07-11

`ComparisonCounts` now carries paired, side-only, differing-row/cell, per-field,
asserted, and context counts. The same validated count object travels through the
returned result, strict sidecar, Matrix caches, classic UI, and validation without
workbook prose scraping. Locked by `check_comparison_contract.py`,
`check_comparison_outcome.py`, and `check_comparison_sidecars.py`; full runner 106/106.

### CMP-AUD-078 — comparison failures are titled as consolidation failures

Priority: P3  
Status: Resolved — classic typed-terminal gate passed 106/106  
Primary code: `scripts/gui_api.py:919-957`

A classic comparison returning `status=error` is handled by the consolidation terminal
path and opens a modal titled “Consolidation failed”. The reproduced body correctly
said the selected TSMIS file did not exist, but the operation title was wrong. This can
send users toward the wrong workflow while debugging an ordinary comparison input.

Correction requirements: carry the active operation kind/label into terminal handling
or branch on the ending task before it is cleared. Assert comparison error, cancel,
match, diff, and incomplete titles separately from consolidation outcomes.

#### Remediation — 2026-07-11

Classic comparison dispatch now marks the operation kind even for early returned
errors. The terminal handler titles those results `Comparison failed` and uses trusted
typed completion/verdict for successful and incomplete comparisons; ordinary
consolidation failures retain their own title. Locked by
`check_classic_comparison_outcome.py`; full runner 106/106.

### CMP-AUD-079 — Compare sub-tab switching can hide every Cancel control

Priority: P2  
Status: Verified with the actual UI visibility/task predicates  
Primary code: `scripts/ui/app.js:182-211,387-465`,
`scripts/ui/ui-compare.js:36-52`, `scripts/ui/index.html:541-549`,
`scripts/ui/ui-matrix.js:1125-1130,1421-1426`

Compare sub-tabs remain enabled during a classic `task=compare`. Switching to the day
or baseline matrix hides the entire classic section, including `btnCancelCompare`.
Those matrix sections show their own Cancel buttons only for `task=matrix`, so no
usable cancellation control remains even though the comparison continues. The user
must discover that returning to the classic sub-tab restores it.

Correction requirements: expose one global task-aware Cancel in the activity card or
lock sub-tab navigation while a classic comparison is active. Test classic→day,
classic→baseline, and tab-away during every comparison epoch; Cancel must stay visible,
enabled, and bound to the live task without affecting later runs.

### CMP-AUD-080 — Matrix artifact identity can miss changed content

Priority: P1  
Status: Partially remediated — output generation identity fixed; source identity and performance remain open  
Primary code: `scripts/artifact_store.py:324-358`,
`scripts/matrix_state.py:205-260`, `scripts/matrix_build.py:389-431`,
`scripts/visual_evidence.py:190-225`

The Matrix source fingerprint hashes only file name, size, and `mtime_ns`. Replacing a
source file with different same-length bytes and restoring its timestamp produced the
same fingerprint, so the old cached `match / 0 differences` remained fresh. This is the
exact same-metadata case for which the v0.18 Claude plan deferred content hashing.

Cached output identity is weaker still: a result record is trusted when its stored
`built_at_mtime` is within one second of the workbook. Replacing a 3-byte output with
36 different bytes and an mtime only 0.5 seconds later preserved the old match verdict
and counts. Size, workbook structure, content, and a transactional generation ID are
not checked.

Visual-evidence currentness inherits both weaknesses. The on-demand gate uses only
store metadata plus relative mtimes; same-metadata consolidated, TSN, and comparison
replacements passed. Intersection and Ramp evidence also cache parsed TSN print
records by `(size, mtime_ns)`, so changed same-metadata PDFs returned the exact old
parsed object without reopening the file.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_same_meta_hydtqmjy\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_cache_contract_huac_oin\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_midrun_mutation_d0s18cwx\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_index_cache_0ja91pca\result.json`

Correction requirements: use a durable content identity for every effective source
and cached output (with incremental hashing if needed), and bind the result record to
the exact committed workbook generation rather than an mtime tolerance. Migrate old
metadata-only records to stale once. Test same-size/timestamp replacements, rapid
successive commits, copy/restore tools that preserve timestamps, and cache-write
failure after a new workbook commit.

#### Remediation progress — 2026-07-11

Strict comparison sidecars now bind every output member by SHA-256 and peer generation,
and Matrix cache records must name that exact generation. Same-size/same-mtime workbook
replacement therefore fails strict validation. The source-folder fingerprint still
uses relative name, size, and `mtime_ns`, so the original same-metadata source
replacement remains possible; evidence PDF parse caches retain related metadata-only
keys.

Strict Matrix snapshots currently re-hash each workbook member to preserve this
correctness. A process-local stat cache was tested and rejected because Windows did not
provide a reliable change signal for the planted same-size/same-mtime tamper. Any Phase-5
performance cache must use a trustworthy file-ID/change token or equivalent validated
manifest; stat-only memoization is prohibited.

### CMP-AUD-081 — Matrix TSN freshness ignores the effective source identity

Priority: P1  
Status: REMEDIATED 2026-07-18 — the canonical-library residual is closed by the
consumer identity token being nulled whenever the library is not current; pinned by a
regression test (see Remediation — 2026-07-18)  
Primary code: `scripts/tsn_library.py:593-631`,
`scripts/matrix_state.py:641-669`, `scripts/matrix_build.py:603-631,672-680`,
`scripts/gui_matrix.py:689-719`

The TSN side contributes only presence and mtime to Matrix freshness; its selected
path, content identity, canonical-library raw fingerprint, and normalization version
are not persisted in the cell cache. Switching a cell from `tsn_A.xlsx` to a different
older `tsn_B.xlsx` left the prior match fresh. The same failure occurs when canonical
raw input is newer than both its consolidated workbook and the comparison: `resolve`
still returns the consolidated mtime and the snapshot reports fresh.

`build_comparison` can call `ensure_current`, but only after the cell is scheduled.
Because “Refresh stale” sees neither a selected-source change nor pending library
rebuild as stale, that auto-heal path is never reached without a forced/single-cell
rebuild.

The same identity failure is inherited by both day and baseline matrices: switching
to a different older selected TSN workbook retained a fresh prior result. Their
executable reproductions are recorded under the Chunk 11 verification log.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_tsn_switch_cg3ypj31\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_stale_tsn_library_t12oang3\result.json`

Correction requirements: persist and compare the effective canonical TSN path,
content fingerprint, raw-input fingerprint, producer completion, and normalization
version. Changing/clearing/importing a selection must invalidate every dependent cell;
a canonical library that `ensure_current` would rebuild must already read stale in the
snapshot. Test newer, older, same-mtime, moved, missing, and fallback sources plus every
normalization-version transition.

#### Remediation progress — 2026-07-11

Versioned explicit TSN selections now bind canonical path, SHA-backed identity token,
size/mtime, and file identity; switching, deleting, or replacing that selection blocks
or invalidates dependent cells instead of falling through. Canonical consolidated TSN
resolution still lacks a comparable identity token/raw-input/normalizer generation in
the cell record, so stale-library and semantic-version parts of this finding remain
open with CMP-AUD-084.

#### Remediation — 2026-07-18

The canonical-library residual was re-examined and found already closed by the
CMP-AUD-105 work — verified and pinned rather than re-fixed. When consolidated TSN
resolution gained an identity token (CMP-AUD-105), it inherited `tsn_library.status`'s
deliberate contract: `"identity_token": expected_identity_token if current else None`.
So a canonical library that `ensure_current` WOULD rebuild — raw newer than its
consolidated, a `normalization_version` bump, or any raw-manifest / normalized-bytes
mismatch — resolves `current=False`, and `resolve()` hands the matrix snapshot
`identity=None`. A cell built against the prior *current* token then reads stale through
the existing identity gate (`source_identity_changed`) even though the consolidated
bytes and mtime are unchanged — which is exactly the finding's "resolve returns the
consolidated mtime and the snapshot reports fresh" case, now closed. This single token
comparison subsumes the raw-input and normalization-version signals the finding lists
separately (all three drive `current=False` → a nulled token). A comparison can never be
built against a stale library in the first place (`tsn_identity_check_for` raises on a
non-current consolidated), so a cell's recorded token is always a valid current one.

Because this is an incidental consequence of a deliberate contract, it is now PINNED:
`check_tsn_freshness` builds a current library, drifts the raw newer than the
consolidated, and proves `status().current` flips false, `resolve()` nulls the consumer
token (consolidated bytes/mtime unchanged), and the dependent cell reads stale — with a
RED leg showing that a RETAINED token would read fresh (the defect) and a git-stash
confirmation that neutralizing the nulling collapses the coverage. The `_staleness`
identity branch, the two snapshot TSN-source builders, and `resolve()` carry
CMP-AUD-081 comments documenting the mechanism (no behavior change). The `by-day` matrix
inherits it through the shared `matrix._cmp_state`. Gate 135/135 (the new leg rides the
existing check).

### CMP-AUD-082 — Matrix formula twins can remain stale

Priority: P1  
Status: REMEDIATED 2026-07-18 — every values commit now refreshes the twin or clears
a stale prior one; a `(formulas)` sibling can no longer outlive its generation (see
Remediation)  
Primary code: `scripts/matrix_build.py:42-121,149-162,512-521,645-655`,
`scripts/ui/index.html:971-978`

The values workbook is canonical, while the optional `(formulas)` sibling has no
manifest or freshness state. Once a formulas sibling exists, a later values-only
refresh leaves it untouched. A failed formulas refresh also preserves it, and the
12,000-row bulk limit returns without removing it. In all three cases the stale file
keeps its ordinary audit-looking name beside a newer values comparison.

The executable harness planted `STALE FORMULAS`; that marker survived a successful
values-only Matrix rebuild, a formulas commit failure, and an over-limit skip. The UI
checkbox says it will write a live-formulas copy, but no cell state identifies the
surviving sibling as belonging to an older comparison generation.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_formula_toggle_qi2yx17_\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_stale_formulas_n_kc72t1\result.json`

Correction requirements: publish a multi-artifact manifest binding values and formulas
to one input/result generation. Whenever the formulas twin is not refreshed, remove or
quarantine the prior sibling, or mark it durably stale in both filename/metadata and UI.
Expose the large-report skip before execution and test toggle-off reruns, row-cap skips,
commit/validation failures, cancellation, locked twins, and recovery after a later
successful formulas build.

#### Remediation — 2026-07-18

Took the "remove the prior sibling" resolution (the safest of the offered options — the
values workbook is canonical and holds every value, so a genuine live-formulas copy is
one explicit rebuild away; a stale one that misrepresents the current comparison is
worse than none). Every matrix comparator now settles the twin on EVERY successful
values commit through one shared `matrix_build._settle_formulas_twin(compare_call,
out_path, do_write, …)`: when `do_write` (the toggle is on AND the inputs are
unchanged AND it is under the row cap) it refreshes the twin; otherwise it clears any
prior `(formulas)` sibling. `_try_formulas` now RETURNS whether it committed a fresh
twin, so an over-limit skip or a failed/validation-error formulas commit also falls
through to the clear. The clear (`_clear_stale_formulas_twin`) is
ownership/alias-guarded and best-effort: a twin still open in Excel (locked) is
announced, not silently trusted. All four not-refreshed paths are covered — the
toggle-off (values-only) refresh, the inputs-changed skip, the row-cap skip, and the
failed formulas commit — across the cross-environment, TSN, self (PDF-vs-Excel), and
baseline builders (the by-day matrix rides the shared TSN path). A later successful
formulas build re-commits the fresh twin. The row-cap skip stays announced (events +
log) at decision time.

`check_formulas_twin_guard` gains the CMP-AUD-082 matrix: each not-refreshed path clears
a seeded prior twin, a successful refresh keeps the fresh one, clearing is a no-op when
none exists, and a RED leg proves the bare `_try_formulas` path leaves the stale twin
(git-stash confirmed: neutralizing the clear reddens the three clearing legs). The
multi-artifact manifest and a UI-level durable-stale marker remain the heavier Phase-5
option not taken; removal fully closes the "stale file masquerading as current"
defect. Gate 135/135.

### CMP-AUD-083 — Matrix source presence counts arbitrary files

Priority: P2  
Status: REMEDIATED 2026-07-18 (`05cd0d8`, CI SHA-verified) — one shared
accepted-data-file predicate powers presence/mtime/discovery; fingerprint keeps
its conservative inclusion by design (see below)  
Primary code: `scripts/report_library.py:64-102`,
`scripts/artifact_store.py:324-358`, `scripts/day_matrix.py:157-204`,
`scripts/baseline_matrix.py:187-257`

#### Remediation — 2026-07-18

New `artifact_store.is_report_data_file(name)` (a `.xlsx`/`.pdf` that isn't a
lock/temp/comparison-payload/publication-lock/sidecar) is the ONE predicate wired
into all four presence/mtime/discovery scanners: `report_library.newest_mtime` +
`_newest_in`, and `day_matrix` + `baseline_matrix._folder_newest_mtime` (which
previously excluded only `~$`). A lock-only / `notes.txt`-only / sidecar-only
folder no longer reads as an export, and a newer lock/sidecar no longer inflates a
folder's freshness. **Census** over the real 7.9 corpus (6912 files / 53 folders):
6897/6897 real report files kept; only `.gitkeep` stubs + our JSON sidecars/markers
drop (never a real export). **`fingerprint` deliberately KEEPS its conservative
`_is_excluded` inclusion** — a change-detection hash must count a stray/near-match
file so nothing hides from freshness (guarded by `check_artifact_store`'s near-match
`.zlib`); the extension allowlist answers "is this an export?", not "did anything
change?", so unifying them there would REGRESS that property. New
`check_matrix_presence_predicate.py` pins the predicate, all four scanners, and that
deliberate asymmetry (red→green: 6 defect-scenario checks fail without the fix).

`report_library._newest_in` treats every direct child file as report data. A folder
containing only `~$route.xlsx` therefore appears exported, while a newer lock file can
make an otherwise current comparison stale. This disagrees with both the consolidators
and `artifact_store.fingerprint`, which exclude owner-lock/temp/sidecar files. The same
logic also accepts arbitrary text, metadata, and unsupported extensions as presence and
freshness signals.

Day and baseline discovery repeat the defect through `_folder_newest_mtime`. A folder
containing only `notes.txt`, `README`, or `.fingerprint.json` is offered as an export;
the baseline picker can accept it and derive comparison targets even though it contains
zero supported report files.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_lock_freshness_4r8n6quh\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_audit_f6qbdpa0\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_inherited_identity_m9qagv5k\result.json`

Correction requirements: make Matrix presence, newest-data mtime, fingerprinting, and
adapter discovery share each report's accepted data-file predicate. Exclude locks,
temporary files, sidecars, ownership markers, and unsupported extensions. Test XLSX
and PDF rows with empty, lock-only, metadata-only, mixed, and unreadable folders.

### CMP-AUD-084 — semantic code changes do not invalidate Matrix artifacts

Priority: P1  
Status: REMEDIATED 2026-07-18 — a semantic producer version is persisted in every
matrix cache record AND consolidation sidecar, and any mismatch reads stale before
target selection (see Remediation)  
Primary code: `scripts/cache_envelope.py:29-64`,
`scripts/matrix_state.py:228-260`, `scripts/matrix_build.py:363-371`,
`scripts/artifact_store.py:466-481`, `version.py:7`

The cache envelope's version 2 describes only the JSON record shape. Neither a Matrix
result record nor a persistent TSMIS consolidation records the comparator, parser,
normalizer, consolidator, or app semantic version that produced it. Replacing the live
Ramp Summary comparator function with a different implementation left the existing
cell fresh with its old match verdict. The current app is v0.26.2, but caches introduced
at v0.18 can still pass the same schema and input-metadata checks after years of parser
and comparison fixes.

The same omission affects persistent PDF/Excel consolidations: unchanged raw files
keep an old parsed workbook fresh after a parser correction, so the updated comparator
can continue reading pre-fix rows unless the user knows to force consolidation.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk10_cache_contract_huac_oin\result.json`.

Correction requirements: define explicit semantic producer versions for each
row/mode's consolidation and comparison pipeline, persist them with artifacts and cache
records, and make any mismatch stale before target selection. Separate record-shape
migration from semantic invalidation. Add an upgrade test that changes comparator,
normalizer, and PDF-parser versions with unchanged source files and proves all affected
cells/consolidations rebuild once.

#### Remediation — 2026-07-18

A semantic producer version now rides both freshness surfaces, keyed on the app's
released `MAJOR.MINOR.PATCH` (`version.__version__`) — a shipped comparator / parser /
normalizer / consolidator fix always rides a new release, so the app version is the
release-granular signal for all of them, auto-bumping (never a forgotten manual
version) so a cache built by an older pipeline can never survive an upgrade:

* **Comparison cache** — `matrix_state.producer_identity()` (`{"app": …}`, one place
  the Everything / by-day / baseline caches share) is recorded in every cache record
  (`record_result` / `record_tsn_result` + the day and baseline `record_result`s) and
  compared in the shared `matrix_state._staleness`: a record whose `producer_versions`
  differs from the running pipeline reads stale with reason `producer_version_changed`,
  even when mtime, input fingerprint, output generation, and TSN identity all still
  match. A legacy record (no field) reads stale once, then rebuilds.
* **Persistent consolidation** — `consolidation_meta.write_outcome` stamps
  `producer_app_version` in every outcome sidecar (uniform across the matrix store
  consolidation, the Consolidate tab, auto-consolidate, and the TSN builders), and
  `matrix._consolidated_stale` rebuilds a workbook whose stamp trails the running app —
  so a corrected parser re-parses instead of feeding pre-fix rows to the fixed
  comparator. A legacy sidecar (no stamp) rebuilds once.
* The **TSN normalizer** path stays covered by its existing finer signal: a
  `normalization_version` bump rebuilds the canonical TSN library (D2) → a new TSN
  identity token → dependent cells already read stale via `source_identities`.
* **Separation preserved** — the `cache_envelope` schema version remains the record
  SHAPE migration; `producer_versions` is the independent ongoing semantic gate. The
  version accessor resolves `version.py` even under a scripts-only `sys.path` (isolated
  checks) by reading it via `ast` when the import is unavailable, so freshness never
  silently degrades.

New `check_matrix_producer_version.py` is the upgrade test: with every other freshness
signal held equal, a simulated app upgrade reads both a comparison cell and a
persistent consolidation stale (`producer_version_changed`), a rebuild re-stamps and
reads fresh exactly once, and a legacy record/sidecar migrates once. Gate 135/135.

### CMP-AUD-085 — partial-artifact policy conflicts while truth surfaces certify incomplete work

Priority: P1  
Status: Partially remediated — policy recorded and truth surfaces fixed; last-good publication remains open  
Primary code: `scripts/matrix_build.py:238-290,500-532,662-680`,
`scripts/artifact_store.py:397-481`, `scripts/matrix_state.py:228-260`,
`scripts/matrix_build.py:183-205`, `scripts/day_matrix.py:288-308,329-346`,
`scripts/matrix_build.py:389-433,538-552`, `scripts/visual_evidence.py:592-626`,
`scripts/ui/ui-matrix.js:268-305`

A complete persistent Highway Sequence consolidation initially contained routes 001
and 002. After route 002 was replaced by a workbook missing the required sheet, the
real Matrix consolidation returned `partial`, overwrote the complete canonical
workbook with a one-route artifact, wrote a matching input fingerprint, and reported
that reduced artifact fresh. The prior complete bytes and route 002 were gone.

#### Contract arbitration

That overwrite and the persistence of a partial comparison record are deliberate
under the historical v0.18 design, not clearly accidental omissions. The plan makes
export-store promotion complete-only, but separately allows `complete|partial`
consolidation cache records and says `partial` should “compare but flag.” Production
code follows that replace-and-flag model and deliberately recovers partial completion
when reusing the canonical consolidation.

Current `CLAUDE.md` and `docs/engine-and-reliability.md` state the stricter opposite:
a partial persistent refresh keeps last-good and a partial is never cached. History and
code cannot establish whether those newer words are an intentional policy change or
documentation drift. Therefore these two behaviors are decision-gated rather than
unconditionally condemned:

1. whether the canonical consolidation represents the latest attempted generation,
   even when partial, or the last complete generation; and
2. whether the comparison cache represents the latest attempted result or only the
   last complete result.

#### OWNER DECISION — 2026-07-21: **LAST-COMPLETE**

Both gates resolve the same way. The canonical consolidation and the comparison cache
represent the **last COMPLETE** generation. A partial refresh must **keep last-good**: it is
reported and retryable, but it never overwrites verified bytes and is never promoted to
canonical. This matches `CLAUDE.md` and `docs/engine-and-reliability.md` — those words were the
intended policy, and the shipped replace-and-flag behavior is the drift. Losing a verified
two-route workbook to one broken export is unacceptable for comparison ground truth.

The defects listed below are **independent of this decision** and are wrong under either
policy — a partial run caching `partial` while its own Summary certifies `✓ EVERYTHING
MATCHES`, a partial zero-difference cell rendering primary `✓ match`, partials having no
first-class retry state, and evidence rendering off a partial run with no warning. Fix those
as false-green regardless.

#### Defects under either policy

- Partial completion is applied only after the comparison workbook is committed. A
  comparison over incomplete input can therefore cache `completion=partial` while its
  own Summary certifies `✓ EVERYTHING MATCHES`.
- A partial zero-difference cache record renders with class `mx-partial` but primary
  text `✓ match`; incompleteness is demoted to subtext.
- Partial records have no first-class retry state. “Refresh stale” excludes them, and
  the day-wide consolidation badge can turn green because fingerprint freshness is
  treated as completeness.
- Automatic evidence runs on any `status=ok`, the camera path does not read completion,
  and the evidence workbook contains no partial/incomplete warning.

The sidecar/cache, workbook, Matrix cell, day badge, and evidence can consequently
present different truth levels for one generation.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_partial_overwrite_iuu8p2x7\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_cache_contract_huac_oin\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_cache_contract_huac_oin\render.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_partial_match_artifact_1j9g2igi\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_targets_fxbljqey\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_partial_8u1k2bnt\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_partial_camera_ttweni2l\result.json`

Correction requirements: record the policy decision before coding. The recommended
strict model keeps the last complete canonical generation and publishes a useful
partial attempt under a distinct unpromoted identity; comparisons must not silently
substitute the stale complete generation for current inputs. If the historical latest-
attempt model is retained, every persisted artifact and surface must loudly carry
partial truth. Under either model, partial attempts must be explicitly retryable, no
primary label may use a checkmark or match claim, and workbook/cache/evidence truth
must be generation-consistent through later successful recovery.

#### Remediation progress — 2026-07-11

D1 now selects last-complete canonical state plus a distinct unpromoted partial attempt;
the Phase-2 compatibility path temporarily keeps the stable comparison pathname with
explicit partial truth. The unconditional cross-surface defects are corrected:
completion enters before comparison publication, strict typed outcomes own every
consumer, partial cells are amber/retryable with no match/checkmark, consolidated
freshness requires a trusted comparable outcome, and evidence rejects partial
comparisons.

The finding remains open because persistent consolidations and comparison artifacts do
not yet implement last-complete plus a durable attempt overlay. A partial generation can
still replace the canonical artifact, and evidence is not yet a member of one exact
generation transaction. Those are Phase-5/7 closure requirements, not Phase-2 truth-
surface regressions.

**M9 assessment (2026-07-18) — DEFERRED (owner-gated policy + Phase-5/7 overlay).**
Closing 085 needs BOTH: (a) an OWNER DECISION on the arbitrated policy — does the
canonical consolidation / comparison cache represent the *last complete* generation or
the *latest attempted* one (the two decision-gates in "Contract arbitration" above; the
current `CLAUDE.md`/`docs/engine-and-reliability.md` state "keeps last-good" but history
and code cannot establish whether that is intentional policy or drift) — AND (b) a
DURABLE ATTEMPT OVERLAY that persists the useful partial attempt under a distinct
unpromoted identity without clobbering the last-complete canonical bytes, which
`CLAUDE.md` conventions explicitly assign to Phase-5/7 ("durable attempt overlays/
provenance remain their assigned Phase-5/7 work"). The unconditional cross-surface truth
defects are already corrected (Phase-2); the remainder is a decision + a full-stack
persistence change, so it is deferred to a Phase-5/7 session ALONGSIDE CMP-AUD-089/085
(same durable-attempt-overlay family). The owner decision is surfaced in the session
summary; note the decision ALONE does not unblock the finding — the overlay work is
required under either policy.

### CMP-AUD-086 — comparison documentation contradicts current capability

Priority: P3  
Status: REMEDIATED 2026-07-18 — the cited contradictions fixed + a durable
catalog-derived doc guard added (see Remediation)  
Primary documentation: `CLAUDE.md:55-65,184-192`,
`docs/reports.md:32-56,535-566`, `docs/comparison-engine.md:726-745,798-805`,
`docs/gui.md:146-149,212-218`, `docs/verification-and-testing.md:74-76,104-114`,
`docs/tsn-parsers.md:247-253`

The current capability table correctly describes 12 integrated rows and five PDF-to-
Excel self-checks, but nearby owning docs still describe 7, 8, or 10 rows and only
three self-checks. Root `CLAUDE.md` says Highway Detail is integrated, then says the
Highway pair remains absent from comparisons/matrices. Other current text says the
disabled export set is empty despite disabled Route History, lists Ramp Detail TSN
normalization v2 where its report oracle says v3, and places obsolete Intersection
Summary one-sided counts directly beneath the current 58/8/0 canary.

These contradictions are not harmless history: they can cause future audits to omit
live placements, bless obsolete canaries, or skip required version invalidation.

The generated work-PC evidence manifest also declares a 16-item “live-verify set”
derived from all export registry rows, including disabled/non-exportable Route
History; only 15 rows are enabled. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_scope_px8vkpqv\result.json`.

The Stage-8 Ramp Detail reconciliation found another concrete instance: §9c of
`docs/comparison-engine.md` described Ramp Detail with Highway Detail's 49,699/50,455
row, roadbed/median, route-041/046, and 21-route-only statistics. Those facts are
impossible for the 15,216/15,410-row Ramp sources. The section was corrected on
2026-07-12 to the accepted Ramp oracle and explicitly labels current product semantics
red; this documentation repair does not resolve the broader generated-catalog and
cross-file consistency requirements below.

Correction requirements: regenerate all comparison capability tables from the catalog,
keep one canonical canary/version table per report, and add documentation checks for
row count, mode count, self-check count, stable keys, normalizer versions, disabled
reports, and cross-file canary duplication. Historical planning files should be clearly
labelled immutable history; current owning docs and `CLAUDE.md` must be updated together.

#### Remediation — 2026-07-18

Re-censused the cited contradictions: most had already been fixed in prior sessions
(the "3 self-checks" text, comparison-engine §9c's Ramp/Highway-Detail mix-up, the RD
normalization version, and the obsolete IS one-sided counts are all gone). The ones
STILL present were fixed and guarded:

* **`docs/reports.md` COMPARE_REPORTS table** — was incomplete (20 of 29 rows) and
  still labelled the PDF-vs-Excel rows `env` after CMP-AUD-014 moved them to `self`.
  Regenerated verbatim from `report_catalog.COMPARE` (all 29 rows, correct groups).
* **The "10"→"12" counts** in reports.md (env-matrix rows; vs-TSN comparators — the
  list was missing Highway Sequence (PDF) + Ramp Detail (PDF)).
* **The "disabled export set is empty" drift** — `DISABLED_EXPORT_SUBDIRS` is
  `{'route_history'}` (the reserved id-15 placeholder), but reports.md:256,
  architecture.md ×2, and CLAUDE.md still claimed the gate was empty. Corrected all
  four to name Route History.
* **The work-PC evidence manifest's live-verify set** (`evidence._report_set`) was
  built from ALL 16 export rows incl. the disabled Route History; now uses
  `reports.enabled_export_reports()` (15). Pinned in `check_evidence_bundle`.

New **`check_docs_capability.py`** keeps reports.md from drifting again: it parses the
COMPARE_REPORTS table and asserts (label, kind, group) == the catalog in order +
complete, the env/vs-TSN/self prose counts == the catalog tallies, and the disabled-
export prose == `DISABLED_EXPORT_SUBDIRS` (fail-loud on a false "empty" claim).
Red→green proven (a self→env row and a false "empty" claim both fail). DEFERRED (P3,
lower value): an exhaustive cross-file canary-duplication / per-report normalizer-
version doc checker — the count/group/disabled guards cover the drift classes the
finding's evidence actually exhibited.

### CMP-AUD-087 — unavailable count caches cannot be refreshed as stale

Priority: P2  
Status: Resolved — shared stale/rebuildability gate passed 106/106  
Primary code: `scripts/cache_envelope.py:47-64`,
`scripts/matrix_state.py:228-260`, `scripts/matrix_build.py:183-205`,
`scripts/day_matrix.py:116-148,329-346`,
`scripts/baseline_matrix.py:140-178,343-361`, `scripts/ui/ui-matrix.js:283-287`

When a comparison workbook exists but its result-cache record is absent or untrusted,
the snapshot has `built=true`, `stale=false`, and null verdict/counts. The renderer calls
that state `re-run / stale — refresh`, but `cells_to_rebuild(scope="stale")` checks only
the false `stale` flag and selects nothing. “Refresh all” is the only workaround.

This is also the cache-envelope migration path: an old, corrupt, or schema-mismatched
cache intentionally unwraps to empty, but the documented “simply recomputes” behavior
does not occur through the ordinary Refresh-stale action.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_missing_cache_refresh_xwwbx7tp\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_cache_envelope_tq5v8fop\result.json`

Correction requirements: define one rebuildability predicate shared by state,
renderer, target selection, and pending counts. A built cell with untrusted/missing
counts or verdict must be stale/rebuildable. Test absent, corrupt, truncated,
wrong-schema, wrong-output-identity, and workbook-mtime-mismatch caches across all
three matrices.

#### Remediation — 2026-07-11

A missing, malformed, untrusted, partial, or wrong-generation cache record now becomes
stale with `cache_missing_or_mismatched` (or the explicit partial reason), so Refresh
stale selects it across Everything, day, and baseline matrices. Cache identity,
generation, mtime, fingerprint, and strict sidecar truth must all agree. Locked by
`check_matrix.py`, `check_p2_freshness.py`, and `check_day_matrix.py`; full runner
106/106.

### CMP-AUD-088 — authentication failure clears offline comparison work

Priority: P2  
Status: REMEDIATED 2026-07-18 — an auth/browser failure now drops only the
auth-dependent export jobs; local comparison/evidence jobs on the shared queue
survive and continue (see Remediation)  
Primary code: `scripts/gui_api.py:1122-1144`,
`scripts/gui_matrix.py:276-343`, `build/check_matrix_bridge.py:351-358`

An auth/browser failure in a Matrix export clears every pending job because `_on_error`
assumes all queued Matrix work would hit the same prerequisite. The queue is shared,
however, and Everything/day/baseline comparison jobs are local workbook operations that
do not authenticate or launch a browser. In the executable reproduction, a failed live
export deleted one queued day-vs-TSN comparison and one queued baseline comparison.

The current golden Matrix bridge check expects queue clearing, but its fixture queues
only an export behind an export. It never exercises a mixed auth-dependent/offline
queue, so it both normalizes the broad behavior and fails to cover the loss described
here.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk10_auth_queue_clear_eja9rhch\result.json`.

Correction requirements: classify each queued job's prerequisites. On auth/browser
failure, retain and continue runnable local comparison/evidence jobs; suspend or remove
only jobs requiring the failed prerequisite, with an explicit recoverable state. Test
every ordering of export, consolidation, evidence, Everything comparison, day comparison,
and baseline comparison around auth and browser-not-found failures.

#### Remediation — 2026-07-18

The matrix queue holds four job kinds and only the **export** re-authenticates and
launches a browser; **compare** (Everything / day / baseline), **evidence**, and
**tsn_consolidate** are local workbook/PDF operations that never authenticate. A single
classifier `_matrix_job_needs_auth` (over the frozen
`_AUTH_DEPENDENT_MATRIX_KINDS = {"export"}`) captures that, and `_on_error` now calls
`TaskCoordinator.drop_matching(self._matrix_job_needs_auth)` instead of
`self._queue.clear()`: only the export jobs (which would hit the same failure) are
removed, the local jobs are retained in FIFO order, and `_end_task`'s existing
auto-advance then continues them — an auth failure no longer erases queued offline
comparison/evidence work. `drop_matching` is fail-safe (an unclassifiable job is kept,
never dropped) and returns `(removed, retained)` so the handler tells the user both what
was cleared (re-queue after sign-in) and what continues. An export-only queue still
fully clears (unchanged). The golden `check_matrix_bridge` fixture — which previously
queued only an export behind an export and normalized the broad clear — gains the mixed
queue: `drop_matching` removes exactly the export jobs and keeps compare/evidence/
tsn_consolidate in order, `_matrix_job_needs_auth` classifies each kind, and the
end-to-end `_on_error` on a running-export + queued-compare keeps the compare and frees
the gate (RED: the pre-fix `_queue.clear()` empties it, the finding's exact defect).
Gate 135/135.

### CMP-AUD-089 — failed rebuild attempts are not durable cell state

Priority: P2  
Status: Verified with comparator failure and cancellation workers  
Primary code: `scripts/gui_worker_matrix.py:156-195,221-260,285-322`,
`scripts/gui_matrix.py:1373-1398`, `scripts/ui/ui-matrix.js:268-305`

All three comparison workers emit per-cell `error`/`cancelled` statuses, but the bridge
discards `payload.status`; the terminal handler emits only transient log text. No durable
last-attempt state overlays the prior cache. A forced rebuild that crashed therefore
returned to the unchanged old `mx-match / ✓ match / identical` cell as soon as the grid
refreshed, with no indication that the requested verification failed.

Workers also increment `done` for a cancelled result. A one-cell cancellation emitted
`status=cancelled`, `errors=1`, and the terminal message “1 of 1 done” even though no new
artifact was built. “Attempted,” “succeeded,” “failed,” and “cancelled” are collapsed.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk10_failed_rebuild_wad37jg4\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk10_cancel_count_c8s0y2eu\result.json`

Correction requirements: persist a per-cell last-attempt record separate from the
last-good artifact/cache, render failed/cancelled refreshes without erasing the prior
result, and count attempted/succeeded/failed/cancelled independently. Test exceptions,
error results, cancellation before/during/after a cell, partial results, app restart,
and successful recovery across all three matrices.

### CMP-AUD-090 — workers can claim and expose foreign folders to Reset

Priority: P1  
Status: Resolved — Phase-1 ownership/lease/Reset gate passed 98/98  
Primary code: `scripts/owned_dir.py:34-69`,
`scripts/gui_worker_matrix.py:156-163,221-228`,
`scripts/gui_worker_export.py:229-235`, `scripts/day_matrix.py:98-113`,
`scripts/gui_worker_maint.py:65-97`

`DayMatrixCompareWorker` stamps `<batch_dest>/comparisons` as app-owned, although day
comparison outputs are actually written to the global
`OUTPUT_ROOT/comparisons/tsn-by-day` tree. The worker does this even when it has no
cells to build and even when the destination already exists with unrelated content.

The shared root cause is broader than that wrong path. `ensure_owned_dir` calls
`mkdir(..., exist_ok=True)` and then unconditionally stamps whatever directory is at
the path. The Everything Matrix uses the same helper for `<batch_dest>/comparisons`,
and Export Everything uses it for environment-store directories. A pre-existing user
directory can therefore be converted into “proof” that the app created it even on an
empty, cancelled, or failed worker run.

The executable reproduction began with an unowned foreign `comparisons` folder
containing `personal-budget.xlsx`. An empty day worker changed it to owned; the real
Reset selector then included that entire foreign folder in its deletion set. The
comparison operation has therefore converted user data outside its output tree into
data the maintenance workflow is authorized to remove.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_day_wrong_ownership__mcn7a80\result.json`.

Independent shared-caller evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_owned_shared_root_r834t0vq\result.json`.

Correction requirements: change the ownership primitive, not only the day caller.
Stamp only a directory atomically created by the operation or one that already carries
a valid, purpose-bound marker. A pre-existing unowned directory—empty or nonempty—must
fail closed. Remove the day worker's wrong-root stamp. Reset must validate marker kind,
path provenance, and expected app-owned structure rather than marker presence alone.
Test new versus pre-existing directories, empty/cancelled/failed workers, all three
callers, corrupt/wrong-kind markers, replacement races, and Windows junctions/symlinks.

#### Remediation — 2026-07-11

`owned_dir` now uses create-only, purpose-bound schema-1 markers with a versioned
`creation_claim`; it never adopts a pre-existing directory. `OwnershipLease` binds an
exact root and reparse-free descendants. Export staging, route saves, consolidation,
PDF scratch, outcome/fingerprint/cache/evidence writes, promotion journals/recovery,
and cleanup recheck the lease and created-object identities at mutation boundaries.
Everything Matrix owns a comparisons lease and lazily requires the existing cell-store
lease for TSN/self work; Day/Baseline remain app-private. Reset operates only on its
immutable preview set, atomically quarantines the exact entry under an unpredictable
same-parent name, revalidates identity/marker, and restores or retains on uncertainty.
Legacy markers are retained with guidance rather than migrated into delete authority.

Locked by `check_owned_dir.py`, `check_reset_safety.py`, `check_artifact_store.py`,
`check_matrix_ownership.py`, export/consolidation/PDF checks, and real Windows junction
fixtures; full runner: 98/98. Residual: ordinary Windows pathname APIs retain a final
identity-check-to-filesystem-syscall race. Closing that last instruction-sized interval
would require native handle-relative operations; portable code fails closed at every
surrounding boundary.

### CMP-AUD-091 — one day export job can write and compare different dates

Priority: P1  
Status: RESOLVED 2026-07-18 (`b107c32`) — the by-day export binds its captured run date (`job["env"]`) end to end: `MatrixBatchExportWorker.day` -> `_run_matrix_export_step(day=)` -> `ExportWorker.day`; `_prep_edition` names `output_run_dir(src, env, day)/subdir` for the captured day (single/fast/coalesced). Additive `day=None` keeps store + normal dated exports byte-identical; the auto-compare already targets that date. Red->green in `check_worker_lifecycle` + `check_day_matrix`.
Primary code: `scripts/gui_matrix.py:426-480,1044-1055,1400-1433`,
`scripts/gui_worker_matrix.py:23-43,74-128`, `scripts/paths.py:98-106`,
`scripts/exporter.py:992-1000`

The queue captures day D1, but its export worker receives only `dated=True`. Each
lower export step independently resolves “today” when it determines the output base.
The completion callback later chains the day comparison against the originally queued
D1. In the reproduction, a 12-report job queued on `2026-07-10`, the exporter resolved
`2026-07-11`, and the automatic comparison still targeted `2026-07-10`.

A real job crossing midnight can split its reports across two dated folders, claim
success, and compare an older or incomplete D1 instead of the bytes it just exported.
System-clock correction and DST transitions expose the same missing run identity.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_day_rollover_5k4g907c\result.json`.

Correction requirements: capture one canonical run date and resolved output directory
at enqueue or dispatch, pass it explicitly through every export step, and bind the
automatic comparison to that exact directory identity. Test midnight between every
pair of steps, clock changes, DST boundaries, retry/resume, and queued jobs that start
on a later date.

### CMP-AUD-092 — day discovery reconstructs the wrong folder and accepts fake dates

Priority: P2  
Status: RESOLVED 2026-07-18 (`1400516`) — `paths.valid_calendar_date` gates `parse_run_folder` (impossible tokens like `2026-99-99` rejected at discovery) and `paths.day_source_dir` resolves the REAL run folder (pre-v0.10 legacy bare-date included; suffixed wins deterministically), wired through `day_matrix`/`baseline_matrix`. Census: 0 real corpus folders newly rejected. Red->green in `check_day_matrix`.
Primary code: `scripts/paths.py:91,109-116`,
`scripts/day_matrix.py:175-204,269-284,388-410`,
`scripts/baseline_matrix.py:89-101,205-255`, `scripts/gui_matrix.py:990-1000`

Discovery returns only a date token and later reconstructs the directory using the
current suffixed naming convention. A valid legacy folder such as
`output/2025-12-31/highway_log` is offered, then resolved as the nonexistent
`output/2025-12-31 ssor-prod/highway_log`. The baseline picker inherits the same
identity loss and can show that legacy day as 0/12 present.

The date regex also accepts impossible tokens such as `2026-99-99`. The picker offers
them, the API persists them, and the day core dispatches them. A text pattern is being
treated as both a calendar date and a durable folder identity.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_discovery_ojqyboim\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_legacy_day_8lqbvrow\result.json`

Correction requirements: carry the canonical discovered directory identity instead
of reconstructing it from a label, validate dates with a calendar parser, and define
deterministic deduplication when legacy and suffixed folders share a date. Test every
supported source, leap days, impossible dates, legacy/current duplicates, moved
folders, and source names containing date-like text.

### CMP-AUD-093 — day consolidation status cannot be repaired by its advertised action

Priority: P2  
Status: RESOLVED 2026-07-18 (`b0add06`) — the day-consolidation badge now describes exactly the refresh action's universe (visible + TSN-ready + exported) and carries an `actionable` flag the UI honors (disabled, no no-op click); `rebuild_day_matrix` short-circuits to `nothing` on zero targets even under `force`. Red->green in `check_day_matrix` (+ `check_p2_freshness` fixture updated for the TSN-scoped badge).
Primary code: `scripts/day_matrix.py:288-308,329-346`,
`scripts/gui_matrix.py:248-260,325-343,1133-1152`,
`scripts/ui/ui-matrix.js:1049-1069`

The day-wide consolidation badge counts every exported supported row, including
hidden rows, and does not require a TSN input. Its refresh action delegates to the
forced comparison-rebuild selector, which requires TSN and selects only visible rows.
These are different target universes behind one promise.

With an export but no TSN source, the badge said consolidation was missing; clicking
the action returned success, started no worker, and silently drained. A hidden missing
consolidation can keep the badge stale indefinitely because that row is never an
action target. Partial false-fresh behavior is separately recorded under CMP-AUD-085.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_targets_fxbljqey\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_cons_badge_lx510il3\result.json`

Correction requirements: give consolidation a dedicated target/action path that does
not depend on TSN comparison availability or row visibility, or make the badge exactly
describe its actionable universe. A zero-target request must report its real reason.
Test no TSN, hidden rows, mixed fresh/missing/partial rows, and concurrent queue work.

### CMP-AUD-094 — removing a running day discards its automatic comparison

Priority: P2  
Status: RESOLVED 2026-07-18 (`b0add06`) — `remove_day_matrix_day` refuses while a by-day export/compare for that date is running or queued (`which=="day"` + `env==date`), so the export-and-compare workflow can't lose its chained comparison. Red->green in `check_day_matrix`.
Primary code: `scripts/ui/ui-matrix.js:319-327,941-949,1104-1124`,
`scripts/gui_matrix.py:1002-1008,1400-1433`

The trash action remains live while a day's export is running, and the bridge accepts
the removal. When that export completed successfully, the automatic chaining logic
looked up the now-removed day, spawned zero day-comparison workers, and returned idle.
The exported artifacts exist, but the requested export-and-compare workflow silently
loses its verification half.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_day_remove_running_0iswt6om\result.json`.

Correction requirements: either lock removal of an active/queued day or bind the job
to a captured target that remains valid even when its column is hidden. Make removal
semantics explicit and test remove/re-add during queued, running, completed, failed,
cancelled, and automatic-comparison phases.

### CMP-AUD-095 — source switching retains impossible day and baseline selections

Priority: P2  
Status: RESOLVED 2026-07-18 (`1400516`) — `set_day_matrix_source` / `set_baseline_matrix_source` reconcile the retained source-scoped day columns (and, for baseline, the baseline id) to the NEW source's exports, dropping any that can't target a real folder. Red->green in `check_day_matrix` + `check_baseline_matrix`.
Primary code: `scripts/gui_matrix.py:980-1000,1184-1194,1222-1249,1310-1326`,
`scripts/settings.py:699-737,759-816`, `scripts/ui/mock.js:1323-1325,1385-1388`,
`scripts/ui/ui-matrix.js:834-848,1180-1220`

The real day source setter saves only the source and retains old source-scoped days.
The real baseline setter also retains both days and baseline ID. This contradicts the
mock, which clears these selections, and the current comparison documentation's claim
that stale IDs cannot target nonexistent folders.

Switching from an populated SSOR source to an exportless ARS source left the old day
and `day:...` baseline active. Picker options were empty, disabled, and unselected,
yet the snapshot still exposed a truthy baseline and marked the absent day as the
baseline. An explicit build then launched against nonexistent source folders; the UI
offered no way to select the impossible option it displayed as active.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_switch_0g5smrq4\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_missing_target_77t2x_4a\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_matrix_state_k9ec2ezb\result.json`

Correction requirements: atomically reconcile days and baseline whenever source
scope changes—clear them or retain only a validated identity intersection. Snapshot
and build endpoints must reject a baseline absent from current options. Test all
source pairs, same-date distinct folders, no-option sources, app restart, and races
between source switching and queued jobs.

### CMP-AUD-096 — invalid scoped filters become full-matrix rebuilds

Priority: P2  
Status: RESOLVED 2026-07-18 (`91eaee1`) — `recompute_matrix` / `rebuild_day_matrix` / `rebuild_baseline_matrix` REJECT a supplied-but-invalid row/env/date instead of normalizing it to None and rebuilding the whole matrix; an absent filter still means everything. Red->green in `check_matrix_bridge` / `check_day_matrix` / `check_baseline_matrix`.
Primary code: `scripts/gui_matrix.py:591-615,1133-1152,1329-1350`

Scoped rebuild endpoints normalize an invalid supplied row/date/environment to
`None`, then interpret `None` as if no filter was supplied. In the baseline harness,
an invalid row and an invalid date each launched all four otherwise valid cells rather
than rejecting the request. The same absent-versus-invalid collapse exists in the
Everything and day rebuild endpoints.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_audit_f6qbdpa0\result.json`
(`invalid_scope_broadening`).

Correction requirements: distinguish a missing optional filter from a supplied but
invalid value and reject the latter before deriving any scope. Test unknown, hidden,
unsupported, blank, wrong-type, and stale row/date/environment values for every scope;
no invalid narrow request may broaden its write set.

### CMP-AUD-097 — unified state drops one side when both inputs are missing

Priority: P2  
Status: RESOLVED 2026-07-18 (`91eaee1`) — `_cmp_state` emits the canonical `both` when >1 side is absent (matching `comparison_state` + the renderer's `both` branch); a single missing side keeps its own actionable name (incl. `tsn`). Red->green in `check_matrix_tsn`.
Primary code: `scripts/matrix_state.py:565-573`,
`scripts/baseline_matrix.py:307-315`, `scripts/ui/ui-matrix.js:272-281`

`_cmp_state` gathers missing input names, then retains only the first. The renderer has
a `both` branch that this unified state cannot reach. A baseline cell with neither the
day nor baseline export present reported only the cell/day side missing, so the UI
said “not exported” and concealed that its reference baseline was also absent. The
older cross-environment `comparison_state` path separately emits both, proving the
state taxonomies have diverged.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_missing_xi5fwdsd\result.json`.

Correction requirements: preserve a structured missing-side list or one canonical
`both` state and render role-aware details. Test every zero/one/two-side combination
for environment, day-TSN, baseline-day, PDF-vs-Excel, and hidden/unsupported cells.

### CMP-AUD-098 — a mid-comparison source mutation can be recorded as fresh

Priority: P1  
Status: Partially remediated 2026-07-14 — the comparison-pipeline half is fixed (pre-comparison capture recorded; raced results auto-invalidate); the evidence-gate half remains Stage-10 work  
Primary code: `scripts/matrix_build.py:127-179,662-680`,
`scripts/baseline_matrix.py:399-425`, `scripts/day_matrix.py:419-433`,
`scripts/matrix_state.py:205-260`, `scripts/matrix_build.py:389-431`

The ordinary and baseline Matrix builders fingerprint effective inputs only after the
comparator has read them and produced its workbook. A controlled comparator read
`OLD`; the source was then externally changed to `NEW` before publication. The build
recorded the `NEW` fingerprint, committed a workbook containing `OLD`, and because the
new source mtime preceded the output mtime, the snapshot rendered a fresh 0/0 match.
Refresh stale selected nothing.

This is distinct from CMP-AUD-080's weak metadata identity: even a strong hash taken
only after the work would bind the output to bytes it never compared. Day comparison
records can likewise hide a race between their persistent consolidation and final
comparison record. TSN consolidation has a pre/post guard, but the comparison cache
does not.

The on-demand evidence gate repeats the timing error. It checks freshness only before
calling the generator. A controlled run changed consolidated, TSN, and comparison
contents during generation while preserving their size and mtime; the action returned
`ok` and published without any post-generation identity check. Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_midrun_mutation_d0s18cwx\result.json`.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_midcompare_race_clean_bhopxl_q\result.json`.

Correction requirements: capture every effective input identity before comparison,
recompute all identities after production and before publication, and publish/cache
only if they are unchanged. Include selected TSN identity, canonical raw/library
generation, consolidated artifact generation, and both environment sides. Quarantine
or invalidate a raced result. Test mutations at read, temp-save, validation, commit,
cache-write, formulas-twin, and automatic-chain boundaries.

Source-capture review on 2026-07-12 confirmed that path/file-ID rechecks alone also leave
evidence PDFs vulnerable to A-to-B-to-A and same-inode/in-place mutation. Evidence opens
the normalized TSN workbook, TSMIS PDFs, and TSN evidence PDFs by live pathname after
discovering them. Highway Log/Sequence TSN PDFs come from canonical `raw/`; Highway
Detail, Intersection Detail, and Ramp Detail use the separate optional `pdf/` sets. The
latter and all TSMIS PDFs are outside the canonical normalized token. Restoring the
original file before the final file-ID/set check can certify images rendered from other
bytes.

**Remediation, comparison-pipeline half (2026-07-14).** All four comparison
record sites — Matrix env cells (`build_cell_comparison`), vs-TSN/self cells
(`build_comparison`), by-day cells (`day_matrix.build_day_cell`), and baseline
cells (`baseline_matrix`) — now capture the TSMIS source-folder fingerprint
BEFORE any consolidation/comparison read (the automatic chain included) and
record THAT capture (`matrix_build._fingerprint_for_record`): the cache binds
the output to the bytes the comparator actually read. A mutation anywhere in
the read→temp-save→validation→commit→cache-write window makes the recorded
(pre) fingerprint mismatch the current folders, so `_inputs_changed` reports
the cell STALE immediately — the raced result is invalidated, never fresh —
and the race is announced (log + events). The live-formulas twin is SKIPPED
loudly when the folders changed after the values build
(`_twin_inputs_unchanged`), so a twin can never be built from different bytes
than its committed values sibling. The TSN side already had this protection
(`captured_tsn_workbook` private snapshot + identity recheck at cache write).
Fixture: `check_p2_freshness.test_midcompare_race` (CT-6d) reproduces the
finding's exact raced-fresh setup (new source mtime before the output mtime),
proves the raced 0/0 "match" now reads stale, and demonstrates the red
mechanism (a post-mutation fingerprint reads fresh) in the same test.
**Still open in this finding:** the on-demand evidence gate's mid-generation
mutation window and the Stage-10 PDF read-set snapshotting — deferred with
Stage 10 (evidence oracles), not silently dropped. Stage 10 must snapshot the exact discovered PDF read set into identity-bound
attempt storage (preserving basenames for adapter lookup), make all locate/render work
use those captures, retain original semantic provenance/current checks, and bind a
path/size/SHA-256 manifest to the evidence generation. Added/removed/renamed/mutated PDF
fixtures must fail or prove the capture stayed on A; no live-path restoration can bless B.

**M9 assessment (2026-07-18) — the remaining half stays Stage-10 (as scoped).** The
comparison-pipeline half is closed (a mid-comparison source mutation reads immediately
stale). The open half is the on-demand EVIDENCE gate's mid-generation mutation window +
the PDF read-set snapshotting, which the remediation note above already assigns to Stage
10 (evidence oracles) — it needs identity-bound attempt storage for the discovered PDF
read set, not a comparison-pipeline change. Deferred with Stage 10, unchanged this
marathon (grouped with the CMP-AUD-106–112/208–210 evidence arc, M10/M11).

### CMP-AUD-099 — baseline switching rebuilds modes that do not use it

Priority: P2  
Status: RESOLVED 2026-07-18 (`91eaee1`) — a baseline switch recomputes with `scope="stale"` (only the now-stale cross-env cells, whose baseline-scoped path is missing), never `"all"` (which rebuilt fresh baseline-independent vs-TSN/self cells); `set_matrix_baseline` sizes the pending count the same. Per-row/column rebuild buttons keep `all`. Red->green in `check_matrix_bridge` + `check_ui_contract` (UI source guard).
Primary code: `scripts/ui/ui-matrix.js:770-793`,
`scripts/gui_matrix.py:110-122`, `scripts/matrix_build.py:183-205`

The confirmation says changing the baseline will recompute cross-environment
comparisons, but the UI calls `recompute_matrix("all")`. All-scope selection includes
selected TSN and PDF-vs-Excel modes, whose inputs and results are baseline-independent.
In the reproduction, fresh TSN and self-check cells produced four all-scope targets
and zero stale targets; changing an unrelated environment baseline would rewrite all
four artifacts.

This remains P2 under this ledger's severity rubric. The direct output is not
semantically wrong, but the endpoint targets operations it says are unaffected and can
spend substantial time rebuilding statewide artifacts; P3 here is reserved for
taxonomy, documentation, drift prevention, or presentation-only defects.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_matrix_state_k9ec2ezb\result.json`
(`baseline_switch_all_targets`).

Correction requirements: on baseline changes, target only environment-mode cells
whose effective side changed. Never rebuild TSN/self-check cells unless their own
identity is stale. Test every row mode, hidden rows, queued work, switching back, and
same-directory aliases across environments.

### CMP-AUD-100 — Matrix cache envelopes and records are accepted under false identities

Priority: P2  
Status: REMEDIATED 2026-07-18 — the dedicated cross-matrix swap + adversarial
nested-record gate now pins the corrected loaders (see Remediation — 2026-07-18)  
Primary code: `scripts/day_matrix.py:116-148`,
`scripts/baseline_matrix.py:140-178`, `scripts/matrix_state.py:83-108,228-260,525-558`,
`scripts/cache_envelope.py:36-64`

Matrix cache loaders unwrap without passing the output identity they expect. A day
cache deliberately labelled `baseline-by-day`, but containing a matching cell key,
was accepted and rendered as a fresh 777-difference result. Calling the envelope
helper with the expected `tsn-by-day` identity correctly rejected that same payload.

Envelope validation stops at the outer schema. A current-version payload whose cell
record was a list crashed the entire day snapshot with `AttributeError` instead of
degrading one corrupt cell to unknown/stale. The shared and baseline loaders repeat
the missing expected-identity and per-record validation pattern.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_day_cache_envelope_tq5v8fop\result.json`.

Correction requirements: require the exact output identity at every load, validate
nested record types and required fields per cell, and isolate bad records. Foreign,
malformed, truncated, or wrong-generation records must become stale/rebuildable—not
trusted and not a whole-snapshot crash. Add cross-matrix cache swaps and adversarial
JSON type/value cases.

#### Remediation progress — 2026-07-11

Everything, day, and baseline loaders now require their exact output identity, isolate
malformed nested records, reject missing fingerprints, and bind accepted records to the
strict published generation. Those states degrade to stale instead of crashing or
rendering foreign counts. The finding remains open until a dedicated persisted fixture
swaps envelopes among all three matrices and exhausts adversarial nested JSON types;
current focused checks cover the corrected branches but not that complete cross-product.

#### Remediation — 2026-07-18

The dedicated gate the finding asked for is now `check_matrix_cache_adversarial.py`,
which exercises the complete cross-product against the real loaders (no product code
changed — the loaders were already corrected; this pins that correctness so a regression
reddens):

* **Cross-matrix identity** — the full 4×4 over the distinct output identities
  (`baseline_key` / `"tsn"` / `"tsn-by-day"` / `"baseline-by-day"`): an envelope is
  accepted ONLY by its own identity and reads empty under every other. Plus the
  END-TO-END persisted swap: a foreign envelope planted at each loader's real results
  path (the finding's exact `baseline-by-day`-at-the-by-day-path case, and three more)
  reads empty via `load_results`, while the matching identity is accepted — so a
  mislabelled cache can never render a fresh foreign 777-difference result.
* **Adversarial nested records** — nine malformed shapes fed through the production
  reader `_cmp_state` (list / string / int record, empty dict, non-numeric / list /
  bool `built_at_mtime`, a partial record, a wrong-generation record): each reads stale
  with NO trusted verdict and never crashes. `_nested_record` likewise returns `None`
  for a list outer, a list inner, and a missing key.
* **Whole-snapshot survival** — a current-version by-day envelope whose cell record is a
  LIST (the exact `AttributeError` that crashed the entire day snapshot) now renders the
  snapshot without crashing, with that cell stale rather than a trusted count.

Red→green confirmed by git-stash: neutralizing the `_staleness` record-type guard
(`rec_is_mapping = isinstance(rec, dict)`) crashes the adversarial records AND the day
snapshot with the finding's exact `AttributeError`. Gate 135 → **136**.

### CMP-AUD-101 — Open Comparisons points away from active non-environment artifacts

Priority: P2  
Status: Verified through real artifact paths and bridge destination resolution  
Primary code: `scripts/matrix_state.py:501-507`,
`scripts/gui_matrix.py:937-942`, `scripts/ui/ui-matrix.js:801-805`

TSN and PDF-vs-Excel Matrix artifacts live under `<dest>/comparisons/tsn`, but the
generic “Open comparisons folder” endpoint always opens
`<dest>/comparisons/<environment-baseline>`. With Ramp Detail in TSN mode, the
executable artifact was not inside the directory the action opened. The user is sent
to a legitimate but unrelated comparison tree and can reasonably conclude the active
result was not saved.

The per-cell Open action is not affected: it resolves the selected row mode and opens
that mode's exact workbook. This finding is limited to the generic folder shortcut.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_open_folder_sqg2s53l\result.json`.

Correction requirements: open the common comparisons root or present mode-aware
destinations, with the active cell's exact artifact directly reachable. Test mixed
modes, all baselines, custom destination roots, missing folders, and formulas siblings.

### CMP-AUD-102 — “Show comparison for all” omits hidden reports

Priority: P2  
Status: Verified through real settings and snapshot filtering  
Primary code: `scripts/gui_matrix.py:45-56,672-687`,
`scripts/ui/index.html:995-1000`

The endpoint iterates `row_modes` from a snapshot that has already removed hidden
rows. Hiding Ramp Detail, selecting “Show comparison for all” as TSN, then unhiding it
left 11 rows in TSN mode while Ramp Detail silently retained environment mode. The
word “all” therefore means only the currently visible subset, but the UI neither says
that nor shows the latent disagreement.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_hidden_mode_3nhmpmc5\result.json`.

Correction requirements: apply the bulk setting over the authoritative supported
catalog, or explicitly rename and scope it to visible rows. Test hide/unhide before
and after every bulk mode, unsupported placements, persisted settings, and new catalog
rows introduced after an upgrade.

### CMP-AUD-103 — explicit cell Build accepts a known missing TSN side

Priority: P2  
Status: Verified through UI predicates, explicit resolution, and bulk control  
Primary code: `scripts/ui/ui-matrix.js:736-741,1010-1018`,
`scripts/gui_matrix.py:232-260,1097-1109`, `scripts/day_matrix.py:329-345`

The day cell Build control checks only that the export side is present. Its explicit
resolver validates the row/date but does not reject `missing_side=tsn`, so the action
is offered and dispatched with an input already known to be absent. The bulk selector
correctly excludes the same cell. Everything's explicit-cell path has the same omitted
missing-side guard.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_missing_action_fhw8qlfk\result.json`.

Correction requirements: use one buildability predicate in cell rendering, explicit
resolution, bulk selection, and queue accounting. Reject known missing inputs before
claiming success and explain the missing role. Test missing TSN/export/baseline/both,
deleted-after-snapshot inputs, hidden rows, and source fallback transitions.

### CMP-AUD-104 — equivalent day export actions disagree about queue availability

Priority: P3  
Status: Verified against the live UI predicates and queue endpoint  
Primary code: `scripts/ui/ui-matrix.js:1123-1124`,
`scripts/gui_matrix.py:1044-1055`

The by-day footer's “Export today” button is disabled whenever any task is active,
although its endpoint is queue-based and equivalent header/row export actions remain
queueable. The same operation therefore appears supported or blocked solely according
to which duplicate control the user clicks, with no explanation for the distinction.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk11_day_export_lock_rzTzyH\result.json`.

Correction requirements: bind every equivalent action to the same queue-capability
predicate, or document and enforce a real semantic difference. Add UI tests for idle,
export, local comparison, auth failure, queued duplicate, and cancellation states.

### CMP-AUD-105 — a selected TSN source can disappear and silently become another source

Priority: P1  
Status: Resolved — Phase-1 explicit-selection gate passed 98/98  
Primary code: `scripts/gui_matrix.py:689-719`, `scripts/settings.py:547-574`,
`scripts/tsn_library.py:605-625`, `scripts/matrix_state.py:641-648`

An explicit TSN override is persisted without a durable availability contract. If it
is deleted or becomes invalid, the resolver ignores that selection and silently falls
through to the canonical consolidated library. The snapshot simultaneously reports
the deleted selected path in `tm.file` and the different canonical path as the active
`source_path`; comparison remains runnable.

This is not merely CMP-AUD-081's failure to mark a changed source stale. The dispatch
contract itself substitutes a different dataset without consent, so a user who chose
a dated or independently reviewed TSN workbook can unknowingly compare against the
canonical fallback and receive a plausible result.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk11_tsn_override_mrpqqelv\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk11_matrix_state_k9ec2ezb\result.json`

Correction requirements: represent “automatic canonical source” and “explicit
override” as distinct modes. A missing explicit override must block dependent cells
and request re-selection; fallback is allowed only after an explicit mode change.
Persist and display the exact effective identity. Test delete, move, permissions,
wrong schema, replacement, canonical availability, restart, and queued-build races.

#### Remediation — 2026-07-11

Explicit picks are now versioned selection records containing the canonical path,
SHA-256 digest, size, mtime, and stable file identity. The five PDF report aliases map
to their owning base TSN dataset. Resolution distinguishes automatic from explicit
mode: a legacy path-only, missing, unreadable, non-workbook, or same-path replacement
returns durable `missing_explicit`, blocks the cell/validation run, and asks the user to
re-pick or clear; it never falls through to a canonical library. Selection identity is
rechecked at dispatch and around comparison use.

Locked by `check_persistence.py`, `check_matrix_tsn.py`, `check_day_matrix.py`,
`check_validation.py`, GUI API checks, and all five PDF-alias fixtures; full runner:
98/98. Residual: selection identity proves the chosen bytes are the same readable XLSX;
report-family semantic shape remains the owning loader's responsibility and is covered
by the later validated-loader phases.

### CMP-AUD-106 — stale evidence survives a clean comparison generation

Priority: P1  
Status: Verified through the real evidence engine's zero-difference path  
Primary code: `scripts/visual_evidence.py:220-231,287-347`,
`scripts/matrix_build.py:374-386,533-552`

Evidence artifacts have no generation manifest or retirement path. When a rebuilt
comparison has no differing columns, `generate` returns before touching its evidence
workbook or image directory. The no-verifiable-example, failure, cancellation, and
toggle-off paths likewise preserve the old set without marking it stale.

The executable reproduction planted a prior red evidence workbook and image, then ran
generation for a newly clean comparison. The engine correctly reported “no differing
columns,” but both old artifacts remained at the canonical current-looking names. A
reviewer opening the siblings beside the clean comparison sees evidence for a result
that no longer exists.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_stale_ym84bvx6\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_stale_va7e0_4t\result.json`

Correction requirements: bind evidence to the exact comparison and source generation
in a durable manifest. Every new comparison attempt must atomically publish a current
evidence state—including an explicit current “no differences/no examples” state—or
quarantine/retire the prior set. Test diff→match, match→diff, partial, disabled toggle,
zero verifiable candidates, exception, cancellation, locked artifacts, and restart.

#### Partial remediation — 2026-07-18

The finding's PRIMARY repro (the clean-comparison path) is closed. When a rebuilt
comparison has no differing columns, `generate` now calls `_retire_stale_evidence`
before its early return: guarded like every other evidence mutation (source-set +
alias + ownership checks), it quarantines (atomic move) then deletes the stale
workbook and image folder; a locked/foreign/source-aliased artifact is left in place
with a logged note rather than force-removed. A clean comparison is a definitive signal
that any prior evidence belongs to a previous generation. `check_visual_evidence`:
`_retire_stale_evidence` removes the canonical set and refuses a source-aliased
artifact, and a real `generate()` call on a clean comparison (planted prior evidence)
leaves nothing surviving at the canonical name — red on the neutralized retire, green
on the fix. **Still open:** the no-verifiable-example / disabled-toggle / restart paths
and the durable per-comparison evidence generation manifest (coupled with CMP-AUD-109).

### CMP-AUD-107 — Highway Detail evidence uses a different equality engine

Priority: P1  
Status: Verified against the production cell predicate and evidence enumerator  
Primary code: `scripts/evidence_highway_detail.py:156-184`,
`scripts/compare_highway_detail_tsn.py:498-517`,
`scripts/compare_core.py:319-355`

Highway Detail evidence enumerates a cell whenever two stripped strings differ.
Production comparison instead uses `compared_cell`, which applies Excel-style internal
whitespace folding and the report's Med V/WDA equivalence. Thus evidence can invent a
red discrepancy that the workbook correctly does not count.

Verified cases:

- loader-valid HG `A  B` versus `A B`: comparison equal, evidence difference;
- Med V/WDA `06V` versus `6V`: comparison equal, evidence difference.

If matching source PDFs carry those display values, the later parse-back check accepts
them and renders authoritative-looking images for a non-difference.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_trim_loader_wujpcq04\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_stale_ym84bvx6\result.json`

Correction requirements: every evidence adapter must consume the exact shared pairing
and `compared_cell` verdict used by its comparison flavor. Add negative equality cases
for whitespace, Med V/WDA, dates, context/non-asserting fields, ditto, casing, numeric
coercion, and every PDF/Excel row-specific schema.

#### Remediation — 2026-07-18

All five evidence adapters now enumerate through the engine's OWN
`compare_core.compared_cell` verdict (`verdict is False`), matching the Highway
Log / Highway Sequence adapters that already did. Highway Detail was the verified
defect — raw `cht._s` compare, no Excel TRIM, no Med V/WDA fold, no context/ditto
suppression; its `enumerate_diffs` now calls `compared_cell(cht._SCHEMA, i, ra, rb, 1)`
and `project()` applies `_xl_trim` so a verified PDF value still round-trips against the
compared_cell display. Intersection Detail (already `_xl_trim`, empty context, no
Med-Wid) is folded on byte-identically. Ramp Detail's parallel `_ALWAYS_CONTEXT`/
`_EXCEL_ROW_SKIPS` lists are replaced by the live per-flavor schema (`_schema_for` —
Excel keeps the print-only On/Off + Ramp Type context, the PDF flavor promotes them),
derived from the base schema so the two can't drift from the comparators.

Real-corpus census (252-route 7.9 ars-prod Highway Detail, 198,752 diff cells): the
`compared_cell` set is a provable strict subset of the raw-compare set
(`_s(a)==_s(b) ⟹ _xl_trim(a)==_xl_trim(b)`, and Med-Wid/context only add equalities),
so the fix can never introduce a diff. NEW == OLD == 198,752 on this data (the loader
pre-projects, so the bug is latent here); the shipped adapter reproduces 198,752 exactly.
`check_visual_evidence`: the finding's HG-whitespace and Med V/WDA cases now do NOT
enumerate (red on the reverted adapter, green on the fix), the projection-TRIM round-trip
is pinned, and `_schema_for` is bound to the live RD comparator context sets. Gate 136/136.

### CMP-AUD-108 — duplicate-only differences vanish from evidence accounting

Priority: P2  
Status: Verified against comparison pairing and all five adapter patterns  
Primary code: `scripts/visual_evidence.py:225-231`,
`scripts/evidence_highway_detail.py:156-184`,
`scripts/evidence_intersection_detail.py:110-139`,
`scripts/evidence_highway_log.py:88-124`,
`scripts/evidence_highway_sequence.py:92-130`,
`scripts/evidence_ramp_detail.py:144-176`, `scripts/compare_core.py:445-554`

All evidence adapters discard keys that are duplicated on either side. The comparison
engine instead pairs those occurrences by similarity and counts their differences.
Ambiguity may make a screenshot unsafe, but the evidence engine never learns that a
field differs: it derives `fields_with_diffs` only from the already-filtered candidates.

An Intersection fixture produced two counted HG differences entirely inside a
duplicate group. Evidence emitted zero candidates and reported that the comparison
had no differing columns, rather than one differing field with no uniquely renderable
example.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_duplicate_8ixl_sjy\result.json`.

Correction requirements: bind evidence to the comparison's persisted pairing trace
and field counts. Duplicate ambiguity should become a named per-field miss, never a
false zero-difference statement. Test duplicate sizes, similarity ties, greedy/limit
boundaries, unequal multiplicities, and fields whose differences exist only in
duplicates.

### CMP-AUD-109 — evidence workbook and images are not one transaction

Priority: P1  
Status: Verified with locked, failed, and cancellation publication harnesses  
Primary code: `scripts/visual_evidence.py:287-347,592-676`,
`scripts/matrix_build.py:389-433`, `scripts/gui_worker_matrix.py:342-365`

Evidence writes/replaces the workbook first and swaps the image directory second.
Those two independent commits have no shared generation identity or rollback. A
simulated locked image folder left the canonical new workbook beside canonical old
loose images, while the new images were diverted to `.new`. A complete publication
failure still returned rendered success and canonical paths even though neither
canonical artifact changed.

Cancellation is checked before workbook writing, not at the final commit boundary.
When cancellation arrived during that write, the engine still promoted the new
workbook and images and returned success; the worker collapsed publication status to
ordinary `ok/error`.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_pairtxn_x74w0r77\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_publish_false_ok_2h75wh7x\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_cancel_publish_clean_u9amd4vy\result.json`

Correction requirements: stage workbook and images as one manifested generation,
validate every staged member, recheck cancellation and source identities immediately
before commit, then publish or preserve the whole set. Return structured
promoted/diverted/preserved/failed paths and surface them durably. Test every failure
and process-crash boundary, locked workbook/folder combinations, disk-full, and retry.

#### Partial remediation — 2026-07-19

`_publish_evidence_set` coordinates the workbook + image commits through the existing
(individually correct, well-tested) `_write_workbook` / `_swap_dir` primitives. The
workbook commits first; if it can't reach its canonical name — the COMMON case, the user
reading the previous evidence in Excel — `_divert_images` sends the new images to a .new
sibling too, so BOTH old artifacts stay at canonical and BOTH new ones divert (never a
new-workbook / old-images mix). `generate()` rechecks cancellation (and the CMP-AUD-112
PDF byte baseline) immediately before this commit boundary, and returns the ACTUAL
committed canonical paths (`None` when diverted) plus a `status` (promoted/diverted)
instead of an unconditional success claim. `check_visual_evidence.CMP-AUD-109`: no lock →
both promoted; workbook locked → the set diverts, status honest, OLD images stay at
canonical, new set in .new — red on the neutralized coordination, green on the fix.

**Closed:** the workbook-locked inconsistency (the common case), the honest-status claim
(harm 2), and cancellation-at-the-commit-boundary (harm 3). **Still open:** if the
workbook DOES commit but the image folder is separately locked, the images still divert
(new workbook beside old images — honestly reported, but on-disk inconsistent). Fully
closing that rarer case needs a quarantine-based TWO-PHASE commit of both artifacts (the
workbook commit is not yet rollback-able), plus the manifested-generation identity + the
process-crash-boundary / disk-full matrix.

### CMP-AUD-110 — queued evidence actions can change their target identity

Priority: P2  
Status: Verified through enqueue and delayed real dispatch  
Primary code: `scripts/gui_matrix.py:126-169,353-380,573-588,1112-1130`

An evidence job stores only row, displayed cell, and day/Everything kind. At dispatch,
it rereads the current baseline, day source, batch destination, TSN selections, and
example setting. A queued camera click is therefore not bound to the comparison the
user clicked.

In the reproduction, an Everything job enqueued under one baseline ran against newly
selected `ssor-test`; a day job enqueued under SSOR ran against newly selected ARS.
Their original queue labels remained, concealing the retarget.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_queue_retarget_atolnynb\result.json`.

Correction requirements: persist the exact comparison path and effective baseline,
day source/folder, TSN source identity, PDF roots, output generation, and example count
in the job. Dispatch must use that immutable identity or reject it as changed. Test
all setting changes, file replacement, destination moves, row-mode changes, and queue
reordering while evidence waits.

#### Remediation — 2026-07-18

`_capture_evidence_identity(which)` freezes the settings that decide WHICH comparison an
on-demand evidence job targets — batch destination, TSN selections, example count,
layout, and the baseline (Everything) or day source (by-day) — into the job at ENQUEUE
(`matrix_evidence_cell` / `day_matrix_evidence_cell`). `_dispatch_evidence_job` targets
that frozen identity, never the live settings (a pre-110 job without it falls back to
live). The comparison-freshness gate in `run_evidence_only` still validates the frozen
target is current. `check_matrix_ownership.evidence_identity_checks`: freeze under
settings A, change everything to B, dispatch, and assert the run targets A — red on the
reverted live-settings dispatch, green on the fix, for both the env and day paths.

### CMP-AUD-111 — evidence summaries execute source values as formulas

Priority: P1  
Status: Resolved — Phase-1 literal-cell gate passed 98/98  
Primary code: `scripts/visual_evidence.py:592-649`, especially `616-621`; correct
control: `scripts/compare_core.py:947-956`

The evidence Summary writes raw compared values directly to openpyxl cells. A value
beginning with `=` is serialized as a live Excel formula, bypassing the literal-cell
formula-injection guard used by comparison workbooks. Reproductions stored
`=HYPERLINK(...)` and `=1+1` with `data_type='f'` instead of literal source text.

This can change the evidence display, execute spreadsheet formulas, or prompt/network
on workbook open depending on the payload and Excel policy. It also invalidates the
claim that Summary records the exact compared bytes.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_formula_injection_ww9qpycb\result.json`.

Correction requirements: use the same literal writer/guard as `compare_core` for
every source-derived evidence cell. Reopen the XLSX and assert literal value and
non-formula type for `=`, `+`, `-`, and `@` leads, formula-like URLs, DDE/WEBSERVICE,
both source roles, blanks, and ordinary numeric/date controls.

#### Remediation — 2026-07-11

`compare_core.set_safe_literal_cell` is the single writer for source-derived evidence
summary values and captions. It forces `=`, `+`, `-`, and `@` leads plus every
openpyxl/Excel error token to a byte-exact STRING cell while leaving engine-authored
formulas intact. `check_evidence_literal_cells.py` reopens the generated XLSX and
verifies values and cell types across both source roles; the expanded comparison
injection and visual-evidence checks also pass. Full runner: 98/98.

### CMP-AUD-112 — evidence verifies and rasterizes different PDF generations

Priority: P1  
Status: Verified with controlled replacement between parse and render  
Primary code: `scripts/visual_evidence.py:390-458`

`_try_example` verifies values against records parsed earlier from each PDF, then
`_strip` reopens those file paths to rasterize the page. No immutable snapshot, file
handle, or content identity connects those operations. Replacing both PDFs between
the checks caused the engine to accept OLD parsed values and captions, rasterize NEW
bytes, and return a verified evidence pair.

This is more direct than a stale cache: the same output entry can assert that an image
was parse-back verified even though the pixels came from a file never parsed for that
entry.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_evidence_parse_render_race__larmwk2\result.json`.

Correction requirements: parse and render immutable content snapshots or shared file
handles and bind every PDF to a pre/post digest in the generation manifest. Abort and
publish nothing on any change. Test replacement, truncation, page reorder, same-
metadata bytes, symlink/junction retarget, and mutation during rasterization.

#### Remediation — 2026-07-18

`generate()` digests the candidate PDFs' bytes (`_pdf_content_digests` — the sampled
TSMIS routes + the TSN district-print set) BEFORE the adapters parse them: the
parse-time baseline. `_ensure_pdf_content_unchanged` re-verifies those exact bytes once
after ALL rendering, before the commit — an unchanged file start→commit means
parse-bytes == render-bytes, so a rendered image can't come from a file never parsed for
it. Any change (or a vanished/unreadable candidate) aborts the publish. This catches a
same-size, same-mtime swap the existing `(dev, inode, size, mtime)` set-identity
tripwire cannot see; only the small sampled subset is digested, so the cost tracks what
is rendered, not the whole statewide corpus. `check_visual_evidence`: a metadata-
preserving swap is proven invisible to the tripwire but changes the sha256 and raises; a
vanished candidate also aborts — red on the neutralized guard, green on the fix.

### CMP-AUD-113 — evidence bundle counts omit validation members

Priority: P3  
Status: Resolved — actual-member bundle gate passed 106/106  
Primary code: `scripts/evidence.py:271-288,297-304`

When validation is present, the collector writes `validation.txt` and
`validation.json` and lists them in the manifest, but its returned `files` count is
always `len(written)+2` for only manifest and self-test. A generated ZIP contained
four members while the result claimed two.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_bundle_count_icjigxe6\result.json`.

Correction requirements: derive both the manifest contents and returned count from
the actual successfully written member list. Lock counts for validation present/
absent, unreadable entries, duplicate archive names, collector failure, and optional
user evidence.

#### Remediation — 2026-07-11

The collector now reopens the completed temporary ZIP and returns the actual
`len(namelist())`; duplicate archive names fail closed rather than creating an
ambiguous bundle. Validation-present and validation-absent fixtures require the
reported count to equal the archive. Locked by `check_validation.py` and the existing
bundle safety checks; full runner 106/106.

### CMP-AUD-114 — unreadable results are certified as fully OK

Priority: P1  
Status: Resolved — strict validation-generation gate passed 106/106  
Primary code: `scripts/validation.py:156-172,215-250,262-280`,
`scripts/gui_worker_maint.py:191-198`, `scripts/gui_settings_api.py:357-371`

Validation's full-success predicate checks only `status=ok` and
`completion=complete`. It ignores `counts_unreadable`, never persists the producer
verdict, and performs no output-workbook integrity check. A missing/unreadable output
therefore produced all three contradictory claims:

- cell: `counts could not be read`;
- manifest total: `1/1 fully OK`;
- UI information modal: `1 fully succeeded`.

The golden validation fixture definitively expects the unreadable-count cell inside
`comparisons_ok`, although the coupling is indirect in syntax. It creates exactly two
cells: one readable `partial` result and one `complete` result whose counts are
unreadable, then requires `comparisons_ok == 1` and `comparisons_partial == 1`. The
complete/unreadable cell is therefore the only possible member of `comparisons_ok`, so
the official suite entrenches the false certification while separately asserting that
the digest prints a warning.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_ui_blast_cicja366\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_acceptance_7d8oeslg\result.json`

Correction requirements: persist verdict and typed counts, validate the workbook, and
require all truth signals to agree before full success. Render missing/unreadable/
contradictory results as indeterminate or failed. Test missing, locked, truncated,
tampered, wrong-generation, partial, and verdict/count contradictions through JSON,
text digest, ZIP, worker, logs, and modal.

#### Remediation — 2026-07-11

Validation's full-OK predicate now requires a successful returned result, trusted and
current strict sidecar, identical committed generation and succeeded attempt, known
typed counts, `completion=complete`, a valid count-consistent verdict, and a generation
ID. Missing, unreadable, tampered, partial, or returned/persisted-mismatched results are
explicitly untrusted/partial/failed and never enter OK. The worker and API preserve all
buckets. Locked by `check_validation.py`, `check_comparison_publication.py`, and
`check_comparison_sidecars.py`; full runner 106/106.

This closure is deliberately bounded: deep workbook semantic-schema validation remains
open under CMP-AUD-115. Resolving its broader header/row/cross-sheet invariants is not
required to prevent an absent or untrusted comparison generation from being certified
fully OK.

### CMP-AUD-115 — comparison artifact validation accepts empty semantics

Priority: P1  
Status: Verified with header-only and malformed Comparison workbooks  
Primary code: `scripts/artifact_store.py:127-152,221-245`,
`scripts/matrix_state.py:133-193`, `scripts/compare_core.py:1554-1592`

Transactional commit checks only that openpyxl can open the XLSX and that a sheet
named `Comparison` exists. A header-only workbook passed publication with
`status=ok/verdict=match`; `read_counts` returned `(0,0)`. A malformed Comparison
sheet with neither `Status` nor `Diffs` headers was also accepted because count
reading falls back to hardcoded positions.

The boundary does not require Summary or Spot Check, any comparison rows, allowed
status domains, labelled counts, self-checks, Report View invariants, or cross-sheet
agreement. Current checks treat `A1='x'` as a valid artifact and explicitly require
the positional fallback, contradicting the Claude contract that counts are located by
header label, never position.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_artifact_acceptance_ddtp2m44\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_acceptance_7d8oeslg\result.json`

Correction requirements: define and enforce a versioned comparison-artifact schema:
required sheets/headers, nonempty or explicitly valid empty universe, allowed row
statuses, typed labelled counts, source/generation identity, and cross-sheet/count/
verdict invariants. Missing labels must fail closed. Add semantic corruption cases to
commit, cache, validation, open, and evidence gates.

**Remediation progress — 2026-07-14 (typed-contract count/verdict invariants).** The
2026-07-14 review flagged, under this finding's "count/verdict invariants" scope, that the
typed contract itself accepted semantically impossible truth. Two invariants added to
`comparison_contract.py` (proved red→green in `check_comparison_contract`; suite 121/121):
(1) `ComparisonCounts` requires `differing_cells <= asserted_cells` — a differing cell is
an asserting cell that is not equal, so differing cells are a strict subset (verified
against 198 genuine persisted `ComparisonCounts`, 0 violations; six unrealistic test
fixtures that set `differing_cells>0` with `asserted_cells=0` were corrected); (2) a
*complete* `diff` verdict must carry at least one difference (the mirror of the existing
match rule). A third proposed sub-claim — bounding pairing-trace side indices by the
declared population — was **evaluated and declined**: `PairingTrace` side indices are
global row ordinals, not positions bounded by the group's sizes or the aggregate counts,
so a population bound would be incorrect; per-side uniqueness across traces is already
enforced. **Still open (the core of this finding):** the workbook-artifact schema
enforcement above — required sheets/headers, valid row-status/universe, source/generation
identity, and cross-sheet agreement — is unchanged.

**M9 assessment (2026-07-18) — DEFERRED (Phase-5-scoped, not forced).** Two of the
finding's three concern-areas are already closed elsewhere: (a) the READ path no longer
"falls back to hardcoded positions" — `matrix_state.read_counts` locates Status/Diffs by
UNIQUE HEADER LABEL and returns `(None, None)` on missing/duplicate labels or an invalid
row status (never a positional guess); and (b) the empty-universe truth is governed by
the route-universe gates (CMP-AUD-019/071/183) plus the typed-contract count/verdict
invariants above — so a header-only workbook cannot certify a green result, because the
Matrix/classic/validation truth is the strict TYPED comparison generation, never the
scraped workbook (CLAUDE.md: "Workbook scraping must never certify a green UI result").
What remains is a defense-in-depth SCHEMA GATE at `artifact_store.commit_workbook` —
requiring the Comparison sheet's labeled columns / valid row statuses / cross-sheet
agreement at commit. That gate sits on the CORRECTNESS-LOCKED transactional commit path
SHARED by every comparator AND every consolidation, so adding it safely needs an
exhaustive per-comparator census proving no legitimate workbook is false-rejected (a
false rejection would BLOCK a valid report — a discrepancy the standing directive
forbids without full proof). Because the truth-critical halves are already closed and
the remainder is a risky defense-in-depth gate, it is deferred to a focused Phase-5
artifact-epoch session (the same disposition as CMP-AUD-080/089), not forced here.

### CMP-AUD-116 — failed validation records default to complete

Priority: P1  
Status: Resolved — structural terminal-status gate passed 106/106  
Primary code: `scripts/validation.py:156-182`; correct reducer:
`scripts/outcome.py:116-128`

`_run_one` serializes `getattr(result, 'completion', None) or complete` before
considering result status. An error or cancelled result whose producer did not set
completion is therefore recorded as `status=error, completion=complete`. This is an
invalid state combination in the very manifest intended to prove completion truth.

A producer that raises instead of returning an error result creates a second unsafe
shape: the exception record omits `completion` entirely. Downstream readers that use
`rec.get("completion", complete)` can then interpret that failure as complete too.

The contradiction appears both in the current executable fixture and in the retained
real work-PC evidence bundle, so it is not a hypothetical stub-only shape.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_acceptance_7d8oeslg\result.json`
- `C:\Users\Yunus\Downloads\TSMIS\evidence-bundles\tsmis_evidence_20260706_154546.zip`

Correction requirements: reduce status/completion through the shared outcome model
and reject impossible combinations at serialization. Exception records must carry an
explicit failed completion. Test returned and raised failures plus every status with
missing, complete, partial, failed, and cancelled completion, legacy manifests, and
UI/bundle rendering.

#### Remediation — 2026-07-11

Structural terminal status now wins before completion reduction. Returned error and
cancelled results serialize explicit failed/cancelled completion, and raised exceptions
serialize explicit failed completion; no terminal failure path defaults absent
completion to complete. Locked by `check_validation.py`; full runner 106/106.

### CMP-AUD-117 — Bearer secrets survive into a credential-safe bundle

Priority: P1  
Status: Resolved — Phase-1 credential/bundle gate passed 98/98  
Primary code: `scripts/validation.py:49-64,173-182`,
`scripts/evidence.py:248-275`

The credential regex consumes only one non-space token after a credential label.
`Authorization: Bearer SECRET-ABC-123` becomes
`Authorization=[redacted] SECRET-ABC-123`; a bare `Bearer SECRET` is untouched.
The planted secret survived `_run_one` and appeared in both `validation.txt` and
`validation.json`, while the manifest called the ZIP credential-safe.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_credential_scrub_r7uwdwg9\result.json`.

Correction requirements: prefer typed safe error codes; otherwise redact the entire
Authorization value plus bare Bearer/Basic credentials, JWTs, multiline headers, URL
tokens, and multiple cookies. Plant secrets in every producer/error position and scan
every generated ZIP member byte-for-byte before declaring it safe.

#### Remediation — 2026-07-11

The new dependency-light `credential_safety` module redacts complete Authorization,
Proxy-Authorization, Cookie, Bearer/Basic, JWT, key/value, query, fragment, and
multiline forms in validation diagnostics. Before publication, `evidence.collect`
scans every final ZIP member and its name/comment/extra metadata, UTF-8/UTF-16 and
binary streams, raw Office container bytes, and decompressed nested OOXML members.
An opaque/unscannable or credential-bearing member aborts publication; the atomic temp
ZIP is discarded and the prior good bundle is preserved. The scanner is included in
the packaged app.

Locked by `check_evidence_bundle.py`, `check_validation.py`, `check_persistence.py`,
and packaged-module checks with planted headers, bare schemes, JWTs, URL tokens,
UTF-16, nested/shared-string, trailing raw Office, member-name, and ZIP-comment cases;
full runner: 98/98.

### CMP-AUD-118 — validation skips raw-only TSN imports

Priority: P2  
Status: Verified with a real redirected Ramp Detail library  
Primary code: `scripts/validation.py:90-111,141-153,194-208`,
`scripts/tsn_library.py:457-476`

`_ensure_tsn_ready` claims to heal `raw`/`pdfs` sources, but calls
`ensure_current`, which deliberately returns `None` when no consolidated workbook
exists. A valid raw Ramp Detail XLSX resolved as `kind=raw`, remained unbuilt, and
validation returned false readiness. Its digest called the library `no data` while
also reporting one raw file.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_raw_only_real_bnnbo7r0\result.json`
- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_raw_only_78wm4t9j\result.json`

Correction requirements: add an explicit first-build path or accurately report that
raw data is imported but awaits a build; count the capability as blocked, not absent.
Test every raw kind, initial build, failed/partial/cancelled build, no-data source, and
subsequent current/stale runs.

Execution disposition (2026-07-16): `_ensure_tsn_ready` now takes the explicit
first-build path — when `ensure_current` returns ``None`` (its deliberate
no-consolidated-yet state) the raw/pdfs kind calls
`tsn_library.build_consolidated(subdir, events=events)` and readiness is that
build's real status; a failing first build reports not-ready rather than a
silent skip, and the digest renders raw-only data as "raw imported, awaiting
first build" (a blocked capability, never absent data). Gated in
`check_validation` (first-build trigger, failing-build refusal, and the
digest state).

### CMP-AUD-119 — TSN heal reporting uses an inverted truth table

Priority: P2  
Status: Verified synthetically and in retained work-PC evidence  
Primary code: `scripts/validation.py:91-109,249-260`

The text renderer checks `current_after` before `healed`, so a successful stale-to-
current rebuild prints merely `current` and hides that validation mutated the library.
Conversely, `healed='ok'` with `current_after=false` prints `HEALED`, certifying a
rebuild that did not achieve current state. The real bundle rebuilt six stale
libraries and described all six only as current.

Evidence:

- `C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_acceptance_7d8oeslg\result.json`
- `C:\Users\Yunus\Downloads\TSMIS\evidence-bundles\tsmis_evidence_20260706_154546.zip`

Correction requirements: define and test a complete truth table for current,
healed-and-current, attempted-but-stale, raw-awaiting-build, absent, partial, failed,
and cancelled. Preserve before/attempt/after state in both JSON and human digest.

Execution disposition (2026-07-16): `validation._tsn_state_text` renders the
complete table with the heal attempt never hidden — ``healed=='ok'`` says
"HEALED → current" when current was reached and "HEAL RAN BUT STILL STALE"
when it was not (the inverted branch is gone); any other attempt status
renders "HEAL FAILED"/"HEAL CANCELLED"/"HEAL PARTIAL"; an untouched current
library still reads "current"; raw-only reads "raw imported, awaiting first
build"; empty reads "no data"; stale-with-no-raw says so; and a heal skipped
by cancellation reads "cancelled before heal". The JSON record preserves
before/attempt/after (`current_before`/`healed`/`current_after`, plus the new
`cancelled_before_heal`). Every branch is pinned in `check_validation`.

### CMP-AUD-120 — pre-cancelled validation still rebuilds TSN libraries

Priority: P2  
Status: Verified with cancellation set before validation starts  
Primary code: `scripts/validation.py:91-111,187-231`,
`scripts/gui_worker_maint.py:170-180`

Cancellation is not checked in the mutating TSN-library stage. Even with
`should_cancel()` already true, validation invoked `ensure_current`; it honors cancel
only later while enumerating comparison cells. A user can cancel before work begins
and still have canonical libraries rewritten.

Evidence:
`C:\Users\Yunus\AppData\Local\Temp\chunk12_validation_acceptance_7d8oeslg\result.json`
(`pre_cancel`).

Correction requirements: poll before every TSN report, propagate cancellation into
each builder, and distinguish not-started, interrupted, and completed-before-cancel
mutations. Test pre-start, mid-first-build, between reports, after build/before
comparison, and application shutdown.

Execution disposition (2026-07-16): `_tsn_stage` polls ``should_cancel()``
before EVERY report's heal and records ``cancelled_before_heal`` — a
pre-cancelled validation reads statuses for the record but never invokes
`ensure_current` (not-started is explicit); builders receive the events sink,
whose worker-wired ``is_cancelled`` cancels a running build (interrupted
renders as "HEAL CANCELLED" via the 119 table), and a heal that finished
before the cancel arrived stays truthfully "HEALED → current" with the later
comparison cells recording "cancelled". The comparisons stage already polled
between cells. Pinned in `check_validation` (pre-cancel attempts no heal and
the digest says "cancelled before heal").

### CMP-AUD-121 — full exact duplicate traces exceed the sidecar ceiling

Priority: P2  
Status: Resolved — schema-v3 41,000-trace scale gate green  
Primary code: `scripts/consolidation_meta.py`, `scripts/artifact_store.py`

Schema-v2 repeats the complete canonical `ComparisonOutcome` in every member's JSON
sidecar and caps each file at 16 MiB. A valid exact result with 41,000 independent
`2 × 2` duplicate groups (82,000 rows per side; every assignment matrix only four
cells) serialized to 16,797,146 bytes before the outer publication completed.
`write_comparison_outcomes` returned false, retained the conservative sentinel, and
strict read exposed partial/untrusted state. This is fail-safe, but retry can never
succeed for that valid result.

Correction requirements: retain the complete typed trace while moving the potentially
large canonical outcome into a shared, bounded, compressed, chunk-capable payload.
Every chunk must be safe-relative, exclusively created or byte-identically reused,
identity/digest/size-bound, resource-bounded, and referenced by identical peer
manifests. Publish all sentinels before chunks, then finals, validate all peers and
workbooks, and remove sentinels last. Dual-read inline schema v2; write schema v3;
reject mixed-schema peers, chunk loss/reordering/tamper, trailing/concatenated zlib
streams, decompression bombs, noncanonical JSON, and ownership races. The actual
41,000-group typed round trip is the exit gate—not a synthetic size estimate.

Schema v3 now writes small peer envelopes referencing one identical canonical,
compressed payload manifest; schema v2 remains strict read-compatible. The final
integrated gate round-tripped all 41,000 exact traces in both opening orders at the
measured 16,795,872 decoded-byte/five-chunk boundary and rejected reordered/duplicate
descriptors. Crash, resource, and concurrency defects found during adversarial review
were split into CMP-AUD-125/126/128 rather than hidden inside this closure.

### CMP-AUD-122 — pairing and typed counting ignored cancellation

Priority: P2  
Status: Resolved — deterministic mid-phase cancellation gates green  
Primary code: `scripts/compare_core.py`, `build/check_compare_cancellation.py`

`run_compare` polled before duplicate pairing and only again after the entire pairing
and count phases. A worst-cap all-zero `316 × 316` Hungarian solve took 8.366 seconds
with no possible cancellation; cost construction scans up to 100,000 row pairs times
all asserting fields, and above-cap positional fallback/counting had similar blind
regions.

The engine now raises the shared `RunCancelled` signal through source validation,
duplicate grouping, exact cost construction, transpose/validation, Hungarian
augmenting scans, capped diagonal fallback, trace materialization/renumbering, and
typed diff counting. `run_compare` catches only that signal and returns cancelled with
unknown counts/quality, empty trace/diagnostics, no workbook, and byte-exact preservation
of any approved existing output. False polling is assignment/count equivalent.

### CMP-AUD-123 — live edits certified stale build-time identity and pairing

Priority: P1  
Status: Resolved — structural and installed-Excel mutation gates green  
Primary code: `scripts/compare_core.py`, `build/check_compare_build_freshness.py`

Formula workbooks recomputed values live but kept row occurrence, helper identity,
duplicate assignment, and familiar views from generation time. Editing a key, helper,
row order, or duplicate value could make live formulas compare under stale pairing and
still leave a green/definitive Summary. A duplicate swap can visibly create phantom
observations even though the correct regenerated assignment is clean.

Every source/helper/Med-Wid cell now has an exact immutable counterpart on very-hidden
`CMP_E2_SNAPSHOT_V1` sheets. Hidden chunk formulas, fixed row counts, and tail sentinels
detect value/key/helper edits, duplicate swaps, insertions, deletions, and appended
rows. Both workbook flavors wrap the headline and self-check in this predicate; stale
state says `REGENERATE REQUIRED` and explicitly labels all observations non-certifying.
Installed Excel passed baseline plus all five mutation families.

### CMP-AUD-124 — uppercase output basenames block metadata publication

Priority: P2  
Status: Resolved — production publication regression green  
Primary code: `scripts/consolidation_meta.py:_strict_member`,
`build/check_comparison_publication.py`

On Windows, artifact generation stores a normalized canonical path but retains the
display-case `relative_path`. `_strict_member` compared the two basenames case-
sensitively. A safe output such as `CORE-ID-78-…xlsx` committed correctly, then failed
comparison-sidecar publication and was returned as untrusted.

Member basename validation now applies the same Windows `normcase` identity rule used
by artifact generation while retaining the original safe relative name for display and
peer lookup. The uppercase production-shaped regression strict-round-trips.

### CMP-AUD-125 — interrupted payload writes poison deterministic chunk names

Priority: P1  
Status: Resolved — crash-safe no-clobber and retry gates green  
Primary code: `scripts/consolidation_meta.py:_publish_payload_chunk`

Schema-v3 initially reserved each deterministic final chunk name with `O_EXCL` and
then streamed compressed bytes directly into that visible file. Process termination
or a short write leaves an ordinary zero-length/partial file at the content-addressed
name. Publication correctly refuses to replace mismatched existing bytes, but the same
typed outcome derives the same name even under a new artifact-generation UUID. Both a
same-result retry and a new-generation retry therefore returned false until the file
was manually removed. This is fail-closed for truth but permanently blocks a valid
comparison and is not an acceptable transaction boundary.

Correction requirements: write, flush, fsync, identity-bind, and digest-check an
unpredictable exclusive sibling temp before atomically installing it with a genuine
no-replace primitive. A crash before install may leave only a non-authoritative temp;
a crash after install must expose the complete reusable chunk. Preserve exact-existing
reuse, never replace or broadly delete a mismatched final, retain ownership guards,
and exercise short-write, process-death residue, destination races, same-result retry,
new-generation retry, and exact-existing reuse.

Chunks are now fully written, fsynced, and identity/digest checked at an unpredictable
exclusive sibling before atomic no-replace installation. A partial temp never reserves
the deterministic final; a completed exact chunk is reused. Conflicting legacy/foreign
primaries are preserved and route through one of eight deterministic content-addressed
fallback slots, so retries remain live without nonce-driven growth. Short-write
residue, same-result retry, exact install race, poisoned slots, and slot exhaustion are
executable green gates.

### CMP-AUD-126 — payload decode limits permit multi-gigabyte memory pressure

Priority: P1  
Status: Resolved — bounded one-decode resource and scale gates green  
Primary code: `scripts/consolidation_meta.py:_read_comparison_payload`,
`scripts/consolidation_meta.py:_validate_comparison_peers`

The schema-v3 reader initially allowed 512 MiB of decoded canonical JSON and 128
independent 4 MiB chunks. Repeated content compresses extremely well: a shaped 512 MiB
payload is roughly 0.5 MiB compressed. One read retains the aggregate bytearray,
decoded JSON object graph, canonical reserialization, and typed reconstruction; the
conservative peak can exceed 2 GiB. Instrumentation also proved that one ordinary
two-member strict read invokes payload decoding three times because self/peer envelope
validation reparses the shared payload.

Correction requirements: establish a measured legitimate decoded ceiling from the
41,000-trace boundary and real canaries, avoid whole-payload canonical reserialization,
validate every peer envelope/manifest/workbook before decoding, and decode the one
shared payload once per strict generation read. Compressed, per-chunk, decoded, object-
shape, and recursion limits must fail closed before unbounded allocation. Add a highly
compressible hostile payload and decode-call-count regression; repeat the actual
41,000-trace round trip after the change.

The final policy caps decoded data at 64 MiB, compressed data at 65 MiB, and canonical
chunks at 16, with a 32:1 aggregate expansion limit validated before zlib is invoked.
The measured 41,000-trace payload is 16,795,872 bytes decoded, 997,633 compressed, and
16.836:1. Strict schema-v3 reads now validate every envelope, peer, sentinel, workbook,
manifest, and binding before decoding the shared payload exactly once; streamed
canonical comparison avoids a second full byte serialization. Highly compressible,
noncanonical, tampered, invalid-peer, and v2-compatibility gates are green.

### CMP-AUD-127 — superseded payload chunks have no bounded lifecycle

Priority: P2  
Status: Verified — safe reference-aware collection design pending  
Primary code: `scripts/consolidation_meta.py`, `scripts/artifact_store.py`

Publishing two distinct schema-v3 outcomes in the same destination leaves both
content-addressed payload sets on disk while only the newest is referenced. The exact
reserved payload namespace is deliberately excluded from source fingerprints and
disposable-placeholder checks, but no collector reclaims superseded chunks. Repeated
comparisons can therefore consume destination storage without bound.

The first conflict-fallback implementation amplified this defect: its name included a
fresh nonce. Five identical successful retries against one poisoned primary created
five byte-identical fallback chunks, and the focused test incorrectly required the
second name to differ. At the configured resource ceiling this could add the full
compressed allowance on every retry. Writes must instead use a bounded deterministic
set of content-addressed fallback slots; generation binding remains in the manifest,
where it is already validated, rather than defeating chunk reuse in the filename.

Correction requirements: collection must be generation/reference aware, operate only
under the exact parent ownership/transaction guard, enumerate live references from
strict current schema-v3 finals, respect any current publication sentinel and a grace
window, and identity-bind every ordinary non-reparse unlink. Near-match `.zlib` files,
mismatched existing chunks, live/in-progress chunks, and unowned destinations must
remain untouched. Cleanup failure should log and retain an orphan without converting a
successfully published generation into false failure. Broad suffix deletion is
forbidden.

Execution disposition (2026-07-16):
`consolidation_meta._collect_superseded_payload_chunks` runs immediately after
a fully validated publication (`exact_records`), under the SAME exclusive
parent lease, and only then. Live references are the union of
`comparison_payload` manifests across every sibling `*.outcome.json` read
STRICTLY — any present publication sentinel, any unreadable/malformed sibling
record, or an unlistable parent aborts collection entirely (retain all).
Candidates are exact `_PAYLOAD_BASENAME_RE` names only (near-match `.zlib`
files are invisible), must be guard-allowed, ordinary/non-reparse, older than
the 15-minute grace window, and their CONTENT must hash to the digest embedded
in their own name (a mismatched chunk is retained as evidence); removal goes
through the CMP-AUD-130 identity-verified handle primitive, never a pathname
unlink, and any failure logs + retains without ever failing the publication
(the whole collector is exception-isolated). Gated in
`check_comparison_sidecars`: supersession across generations reclaims exactly
the dead chunks; sentinel and malformed-sibling suspension; near-match,
mismatched-content, and grace-window retention; the live generation stays
trusted throughout.

### CMP-AUD-128 — overlapping publishers can both claim one output

Priority: P1  
Status: Resolved — local-thread and real subprocess serialization gates green  
Primary code: `scripts/consolidation_meta.py:write_comparison_outcomes`

Two publishers targeting the same comparison sibling set have no attempt lease. Their
fixed sentinels and final envelopes replace one another, and sentinel removal is not
generation-bound. An injected generation-B publication completed while generation A
entered sentinel cleanup. Both calls returned true, the final trusted sidecar contained
only generation B, and A's returned outcome/generation did not equal persisted truth.
The final success loop checked only `record.trusted`; it never required the record to be
the caller's own outcome, generation, and member.

Correction requirements: serialize publication for one output parent/sibling set in
both the local process and other app processes using a crash-released lease; retain the
lease from before the first sentinel through the final postcondition. Sentinel/final
cleanup must not remove a different attempt's protection. Immediately before returning
true, every strict record must equal the caller's exact `ComparisonOutcome`,
`ArtifactGeneration`, and member table. If a different trusted generation wins, the
loser must return false without marking or invalidating the winner. Exercise local
threads, separate processes, both opening orders, interruption/abandonment, same and
different generations, and a forced overlap at sentinel creation, final publication,
and cleanup.

Publication now holds one permanent parent-scoped lease from before the first sentinel
through its final postcondition: a keyed local mutex plus a crash-released OS byte-range
lock on an identity-bound ordinary file. Parent, lock, and ownership are rechecked
throughout. Success requires every strict record to equal the caller's exact outcome,
artifact generation, and member. A different trusted winner makes the loser fail
without poisoning it. Local-thread wait, real subprocess locking, forced trusted-
winner, lock-file fingerprint/non-disposal, and exact final ownership gates are green.

### CMP-AUD-129 — payload and sidecar names exceed Windows path limits

Priority: P2  
Status: Resolved — UTF-16 boundary and packaged-manifest gates green  
Primary code: `scripts/consolidation_meta.py`, `build/app.manifest`

The first bound fallback basename is 251 characters before its parent path. It works on
the development machine because long paths are enabled, but the packaged manifest does
not declare `longPathAware`; conventional packaged Windows paths therefore exceed
`MAX_PATH`. A separate component-length failure needs no long parent: a valid 239-
character workbook basename produces a 256-character fixed sentinel component after
`.outcome.json.tmp` is appended. The workbook can commit, but comparison metadata can
never publish and every retry remains partial.

Correction requirements: shorten payload names (bounded fallback slots satisfy this),
enforce a workbook-basename ceiling derived from every mandatory sidecar suffix before
expensive production, declare and test packaged long-path support, and exercise paths
near both the 255-character component limit and conventional/extended total-path
limits. Failure must be actionable before workbook replacement, not a permanently
untrusted artifact discovered afterward.

Comparison commit now derives every selected, values-twin, producer-temp, sidecar, and
fixed-sentinel component and enforces Windows' 255 UTF-16-code-unit limit before
confirmation, directory creation, temp reservation, or producer entry. Exact selected
budgets are 238 units for formulas/values and 229 for both mode; ASCII and non-BMP
exact/max+1 gates prove preservation of prior twins. New payload primary/slot names are
167/172 units, while legacy 251-unit binding+nonce names remain read-only compatible.
The embedded manifest now contains one correctly namespaced `longPathAware=true` while
preserving `asInvoker`/`uiAccess=false`, and `app.spec` embedding is statically locked.
The OS/registry `LongPathsEnabled` policy remains an external total-path prerequisite;
component safety no longer depends on it.

### CMP-AUD-130 — cleanup can unlink a foreign replacement

Priority: P2  
Status: Verified — handle-bound deletion/retention policy pending  
Primary code: `scripts/consolidation_meta.py:_safe_unlink_sidecar`,
`scripts/consolidation_meta.py:_unlink_bound_payload_temp`

Cleanup currently stats a pathname, compares identity, and later calls pathname
`unlink`. A controlled replacement between those operations caused both helpers to
delete the foreign replacement; sentinel cleanup still returned true. A mandatory
parent publication lock closes this race between cooperating app publishers, and
unpredictable payload-temp names make external interference narrow, but neither makes
the implementation's “only this inode” claim atomic.

Correction requirements: on Windows, delete through an identity-verified handle (or
retain uncertain non-authoritative temps); never claim pathname cleanup is bound more
strongly than it is. Exercise a replacement immediately before delete for fixed
sentinels and random temps. A different trusted generation or foreign replacement must
survive without being marked, quarantined, or removed.

Execution disposition (2026-07-16):
`consolidation_meta._unlink_through_verified_handle` opens the name with
DELETE+FILE_READ_ATTRIBUTES and full sharing WITHOUT following reparse points,
verifies the identity ON THE HANDLE (`GetFileInformationByHandle` volume
serial + 64-bit file index against the caller's `(st_dev, st_ino, S_IFMT)`,
rejecting directories/reparse points), then marks `FileDispositionInfo`
delete-on-close — the check and the removal are bound to one file object, so
a same-path replacement racing in after the caller's stat is observed as a
mismatch and retained, and one racing in after the disposition survives at
the name while only the verified inode dies. `_safe_unlink_sidecar` and
`_unlink_bound_payload_temp` ride it (non-Windows keeps the honestly
documented best-effort pathname fallback). Red→green: the finding's
controlled replacement interposed after the helpers' LAST stat deleted the
foreign file on the legacy path and retains it (reporting False) on the live
path; permanent gates in `check_comparison_sidecars` exercise the race for
both helpers plus verified-absence and identity-mismatch retention. A ctypes
signature defect found during red→green (default `c_int` restype truncating
`INVALID_HANDLE_VALUE`) was fixed with full restype/argtypes declarations.

### CMP-AUD-131 — power-loss durability is not established

Priority: P2  
Status: Verified — durability contract and kill-point gate pending  
Primary code: `scripts/consolidation_meta.py:_atomic_write_bytes`,
`scripts/consolidation_meta.py:_publish_payload_chunk`

Payload temp content is fsynced before atomic installation, which closes process-kill
short writes, but parent directory entries are not durably flushed. Sidecar atomic
writes flush userspace buffers but do not fsync the temp before replacement. POSIX
hard-link installation also lacks a parent-directory sync. The current “crash-safe”
wording therefore proves process-interruption atomicity, not sudden-power-loss
durability.

Correction requirements: either implement and test durable file plus directory-entry
flushes on supported platforms (with explicit failure behavior) or narrow every claim
to process-interruption safety and keep a conservative sentinel through any unproven
durability boundary. Add subprocess termination at each write/install/final/sentinel
boundary; power-loss guarantees must not be inferred from in-process monkeypatches.

Execution disposition (2026-07-16): the sanctioned claims-narrowing option.
Every "crash-safe" claim now states PROCESS-INTERRUPTION safety and explicitly
disclaims sudden-power-loss durability (module docstring, the
`_publish_payload_chunk` docstring, CLAUDE.md's transactional-artifacts
convention, and the engine doc's schema-v3 paragraph), naming why (temp
contents are flushed/fsynced but directory entries never are, and sidecar
temps flush userspace buffers only). The conservative sentinel through the
unproven boundary is the existing fail-closed read side: sentinels dominate
reads until full validation, strict peer/digest/manifest validation marks any
torn or inconsistent state untrusted/partial, and no green can be produced
from a torn publication. The durable-flush + kill-point-gate alternative
remains available as future work if power-loss certification is ever wanted;
no such guarantee is claimed anywhere today.

### CMP-AUD-132 — Highway Log TSN normalization shares a global intermediate directory

Priority: P1  
Status: Resolved — focused interleaving gate and clean 29-member r2 witness green  
Primary code: `scripts/consolidate_tsn_highway_log.py:75,442-520`

The seven-family witness passed an isolated output path to every builder. Highway Log
still wrote all 369 per-district/route workbooks under the process-global
`OUTPUT_ROOT/tsn_highway_log`, first deleting every matching prior workbook there, and
then passed that shared directory to `consolidate_xlsx`. Its successful summary records
the global path even though the requested final workbook is under the isolated audit
root. The other six builders stayed within their requested final output boundary.

This is not merely audit-runner presentation. Two overlapping Highway Log builds with
different raw sets share the delete/write/glob sequence. Either attempt can remove or
replace the other's intermediate members, and either final consolidator can ingest a
mixed member generation. A custom output path therefore does not define the effective
output or input universe. It can also mutate a live app-owned conversion directory from
an otherwise isolated validation/build operation.

Evidence:

- source/result record:
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r1\result.json`
- exact result SHA-256:
  `e8689d37e5b54d9e352875dfc3e71b34516ee9137d29e8678d8b069e7eab05c1`
- event summary: 12 PDFs converted, 369 route files, 60,083 rows, zero
  skipped/failed, with the route-file directory explicitly reported outside the
  isolated audit root.

Correction requirements: allocate one attempt-scoped, ordinary, ownership-leased
scratch directory under an explicit build root; pass its exact generated-member
manifest to consolidation rather than globbing a shared directory; never clear a
global path as part of a custom-output build. Serialize or isolate overlapping app
attempts, identity-bind cleanup, and retain only the requested final artifact plus
explicit diagnostics. The red gate must interleave two disjoint raw sets through the
delete/write/combine boundaries and prove that each output contains only its own exact
members. It must also prove cancellation, failure, retry, and a custom isolated output
cannot mutate anything outside its attempt root.

Remediation evidence: `build/check_tsn_highway_log_isolation.py` interleaves two
disjoint raw universes and proves custom-root containment, exact member manifests,
success/cancellation/failure/retry cleanup, foreign/global sentinel survival, and
identity-guard loss. The source-bound r2 production run then converted all 12 PDFs / 369
route members / 60,083 rows using attempt-local scratch, left zero scratch directories,
and changed zero files under the former global boundary. Result:
`C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\raw-2026-07-12-r2\result.json`,
SHA-256 `1e9e6e689589f5a30eb32899ed163abffc00e73889806a2a8775179df9fd4e25`.
An independent streaming comparison of all seven r1/r2 normalized workbooks found zero
sheet-name, cell-type, or cell-value differences across 5,547,205 cells.

### CMP-AUD-133 — normalized Detail libraries discard source-backed identity, print, and Report View facts

Priority: P1  
Status: Partially remediated 2026-07-14 — RD's PM_SFX identity claim now conserved (v4 sidecar); the remaining column dispositions stay open  
Primary code: `scripts/tsn_load_ramp_detail.py`,
`scripts/compare_ramp_detail_tsn.py`, `scripts/tsn_load_intersection_detail.py`,
`scripts/compare_intersection_detail_tsn.py`, `scripts/tsn_load_highway_detail.py`,
`scripts/compare_highway_detail_tsn.py`

The Stage-6 field-disposition audit proved that exact row-count and current projected-cell
parity are not full source conservation. The canonical normalized workbooks omit facts
that exist in the authoritative TSN extract and, in several cases, in the accepted TSN
print/Report View contract:

- Ramp Detail raw SHA-256
  `3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856`
  has 18 columns; normalized `r7` SHA-256
  `c121a9ca1bed2fad00bfc4b08bfc68fa01cd46da436d6bffa699c5579bb4f5f1`
  has 15 derived/output columns. It omits `PM_SFX`, `ADT_EFF_YEAR`, `EFF_DATE`,
  `RAM_CONNECTION_ID`, and `SEG_ORDER_ID`. `PM_SFX` is a physical-identity claim and
  is populated on 313 rows. `ADT_EFF_YEAR` and `EFF_DATE` are printed in the accepted
  TSN Ramp Detail PDF mapping. The database identifier may remain explicitly
  source-only and `SEG_ORDER_ID` may remain relational, but neither may silently vanish
  from the conservation record.
- Intersection Detail raw SHA-256
  `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2`
  has 36 columns. Its 36-column normalized v3 shape replaces raw facts with derived
  route/location sidecars and omits `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT`.
  The Report View asks for these TSN-only reference values, but the canonical
  normalized path returns blanks for them.
- Highway Detail raw SHA-256
  `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1`
  has 56 columns; normalized `r7` SHA-256
  `46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5`
  has 38 output columns. It omits `THY_ID`, `DIST_CNTY_ROUTE`, `ACC_SIG`,
  `ADT_AMT`, `PROFILE`, `BREAK_DESC`, `LK_BACK_ADT`, `CHNGMILE`, `DVM`,
  `LT_SIG`, `MED_SIG`, `RT_SIG`, `SEG_ORDER_ID`, `REFERENCE_DATE`, and
  `EXTRACT_DATE`. The canonical Report View therefore blanks its DCR and five-value
  TSN ADT-information block even though the raw source and accepted PDF mapping carry
  those facts.

This finding is broader than CMP-AUD-045's physical-pairing defect. It is also distinct
from Stage 10's live-PDF byte-capture requirement: those exact PDF bytes still must be
captured, but byte capture cannot recover facts already removed from the normalized
source representation.

Correction requirements: version each affected normalized schema and retain every
source-backed identity, printed/evidence, category, and Report View fact in typed named
columns or an equally strict hidden source-fact table. Database surrogate fields may be
explicitly source-only and order fields may be relational when an independent contract
proves that disposition; they do not need to become visible compared columns. Update
comparison, evidence, and Report View consumers to use the retained facts without
inventing values or turning TSN-only context into asserted equality. Preserve exact raw
field digests and mutation fixtures through the migration. Product remediation belongs
to the family integration stage after all seven Stage-6 audits are complete.

Current Intersection Detail Stage-8 execution proves the user-visible consequence. The
raw production Report View maps all 16,626 values in each of `MAIN_EFF_DATE`, `MAIN_ADT`,
and `CROSS_ADT`; its exact source-only ledger SHA-256 is
`d0f018d653113b65891215a8b88bbc3cda220d5f6f07d3140e8034282e8c0624`.
The normalized production leg has zero nonblank values in all three columns and the
empty-ledger SHA-256
`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
Both have 16,886 logical Report View records / 33,772 physical rows, so row-count parity
cannot detect the loss. District and County sidecars also remain outside the visible
Comparison projection. This is acceptance-bound as a product defect, not normalized
away as context.

### CMP-AUD-134 — the first Stage-6 Ramp oracle could certify without final source revalidation and understated printed-field loss

Priority: P1  
Status: Remediated in the independently accepted Ramp result and permanent gate  
Primary code: `build/phase6_ramp_detail_conservation.py`

The initial independent Ramp oracle correctly bound the raw and normalized hashes,
enforced exact sheets/headers, and detected the missing `PM_SFX` identity. Its first
review still found three acceptance defects:

1. it captured topology and per-worksheet pre/post identities but did not revalidate
   both pathname/content identities after all projection, digest, collision, anomaly,
   and mutation work immediately before accepting the result;
2. it grouped PDF-printed `ADT_EFF_YEAR` and `EFF_DATE` with generic nonblocking
   source-only review fields, and treated relational `SEG_ORDER_ID` as ordinary
   source-only data; and
3. `stage6_family_complete` combined “the independent audit finished exactly” with
   “the current product retains every required fact,” so a deliberately documented
   Stage-11 product finding could make the audit sequence itself impossible to finish.

The first permanent synthetic review then found a fourth defect before accepting v2:
the independent Ramp date formatter rearranged recognized year/month/day tokens without
constructing a calendar date, so `2026-02-30` was accepted. That copied the
CMP-AUD-038 product failure into the supposed oracle and could have certified the same
malformed fact on both sides.

The independent second review found two further acceptance gaps in the revised Ramp
oracle before promotion. Final source revalidation ran before the result constructor
recomputed all three full dataset digest structures and before `main()` wrote the JSON;
there was no post-result-write source check. Also, raw/normalized physical-row
contiguity was reported but not included in `audit_invariants`, and the permanent Ramp
check did not exercise normalized insert/delete/gapped-row/tail cases. In a later schema
where the current product findings are fixed, `normalized_full_conservation` also was
not explicitly gated by `audit_complete`.

The final provenance re-review then found that the generator captured its own file at
module start, but captured `phase3_xlsx_stream.py` on disk only after both workbook
reads. Python could therefore execute an already-imported reader generation while the
certificate bound a different reader file installed before that later hash. The current
accepted-source facts showed no actual drift, but the reusable attribution was not
race-proof.

Correction requirements: add final raw/normalized identity revalidation to the emitted
certificate; classify identity, printed/evidence, relational, and database-only
dispositions separately; emit distinct `audit_complete` and
`normalized_full_conservation` states; and retain the actual shared-reader mutation
gate as a named dependency rather than presenting a constant inequality as an
end-to-end binding mutation. Construct real calendar dates for every accepted textual
form and reject impossible month/day/leap values. Compute every digest before the final
in-run revalidation, revalidate again after result publication, make both physical row
sequences acceptance invariants, gate full conservation on audit completion, and add
the missing normalized row/layout mutations. Capture the independent reader file at
module initialization before any workbook read and require start/pre/final/publication
identity equality. Re-run the permanent synthetic gate and exact full source after
these changes before accepting the Ramp Stage-6 result.

### CMP-AUD-135 — Ramp normalization deletes all 15 source-backed numeric Description prefixes

Priority: P1  
Status: Resolved 2026-07-14 — TSN Descriptions preserved (edges trimmed per the oracle's reading contract); the TSMIS strip is route-matched; re-blessed  
Primary code: `scripts/compare_ramp_detail_tsn.py:_strip_desc_prefix`,
`scripts/compare_ramp_detail_tsn.py:_tsn_raw_row`,
`scripts/tsn_load_ramp_detail.py:tsn_rows_with_dcr`

The production Ramp normalizer removes every leading `digits/` token from the authoritative
TSN `DESCRIPTION`. The earlier Stage-6 oracle incorrectly copied a rule that treated a
numeric token equal to the route parsed from `LOCATION` as reconstructible. Direct
cross-source verification disproves that premise: the same-pull TSMIS Description has its
own synthetic outer-route prefix, and removing only that one TSMIS-added prefix reproduces
the raw TSN Description exactly on every one of the 15 prefixed rows. The raw token is
therefore data even when it numerically equals the route.

| Raw worksheet row | Outer location/route | Raw TSN and independently conserved Description | Current normalized Description |
|---:|---|---|---|
| 11 | `01-DN-101` | `101/169 NB OFF RAMP` | `169 NB OFF RAMP` |
| 12 | `01-DN-101` | `101/169 SB ON RAMP` | `169 SB ON RAMP` |
| 13 | `01-DN-101` | `101/169 NB ON RAMP` | `169 NB ON RAMP` |
| 14 | `01-DN-101` | `101/169 SB OFF RAMP` | `169 SB OFF RAMP` |
| 299 | `01-MEN-101` | `101/222 SEP NB OFF` | `222 SEP NB OFF` |
| 300 | `01-MEN-101` | `101/222 SEP SB ON` | `222 SEP SB ON` |
| 305 | `01-MEN-101` | `101/222 SEP SB OFF` | `222 SEP SB OFF` |
| 588 | `02-SIS-005` | `5/89 SEP 2-WAY SEG` | `89 SEP 2-WAY SEG` |
| 1998 | `03-YOL-505` | `128/RUSSELL BL, SB ON` | `RUSSELL BL, SB ON` |
| 2001 | `03-YOL-505` | `128/RUSSELL, SB OFF` | `RUSSELL, SB OFF` |
| 3243 | `04-MRN-101` | `131/TIBURON BL, NB OFF` | `TIBURON BL, NB OFF` |
| 5684 | `05-SB-101` | `166/E MAIN ST, SB OFF` | `E MAIN ST, SB OFF` |
| 9519 | `07-LA-210` | `66/FOOTHILL WB,WB ON` | `FOOTHILL WB,WB ON` |
| 9603 | `07-LA-405` | `405/NB ON SEG SANTA FE` | `NB ON SEG SANTA FE` |
| 10815 | `08-RIV-015` | `74/CENTRAL, SB OFF` | `CENTRAL, SB OFF` |

All 15 are source facts, not formatting differences. The loss is present in both `r2`
and `r7`, which explains why the earlier 5,547,205-cell parity check could not discover
it: both production generations contained the same defect. The prior accepted Ramp
Stage-6 result encoded the invalid nine/six split and is superseded. The corrected
source-preserving reissue binds all 15 losses; prior acceptance status did not override
the raw source.

Correction requirements: preserve raw TSN `DESCRIPTION` verbatim apart from authorized
typed/whitespace handling; never remove a numeric prefix merely because it equals the
outer route. Strip only the separately added outer-route prefix from a TSMIS-rendered
Description, then verify the remainder against the source. Bind all 15 rows as an exact
pre-fix red manifest and re-run raw-to-normalized, TSMIS-Excel-vs-TSN,
TSMIS-PDF-vs-TSN, TSN-XLSX-vs-PDF, and both-PDF evidence gates before accepting the
semantic change. Historical normalized bytes/counts do not override the raw facts.

**Remediation (2026-07-14, with the RD family batch).** The TSN side no longer
strips Descriptions — `_tsn_raw_row` and the v4 normalized library conserve the
source text (all 15 authoritative leading numeric prefixes survive; the v4
`normalization_version` bump rebuilds stored libraries). The TSMIS side strips
exactly its export-added outer prefix, and only when the leading number IS the
row's own route (`_strip_desc_prefix(text, route)` — a different numeric prefix
is source data, per the accepted oracle's declared TSMIS reading contract).
Comparison-side Description projection trims text EDGES on both sides (tabs
included) exactly like the oracle's `_text` reading — the raw extract carries
trailing tabs on two censused route-126 rows no TSMIS representation prints;
INTERNAL whitespace still compares per D2. Conservation is untouched (library +
raw claims keep source bytes). Re-blessed: the Excel leg's Description count is
the oracle's exact 185 (was 200 under the old strip), the PDF leg's 181.

### CMP-AUD-136 — the independent XLSX reader can parse synchronized A-to-B-to-A bytes between equal live-file hashes

Priority: P1  
Status: Remediated in the shared private-capture reader and actual A-to-B-to-A fixture  
Primary code: `build/phase3_xlsx_stream.py:read_sheet`,
`build/phase6_ramp_detail_conservation.py:_workbook_topology`,
`build/check_phase3_xlsx_stream.py`

The generic independent reader opens one ordinary-file descriptor, hashes it, parses the
ZIP/XML from that same live handle, and hashes it again. Matching pre/post SHA-256 and
stat identity reject persistent mutation, but they do not make the bytes used by
`ZipFile` immutable. A synchronized writer can change the same file object from A to B
during ZIP parsing and restore A—including size/mtime—before the post-hash. The reader
can then return rows parsed from B while both certified hashes describe A. Ramp's extra
topology reader repeats the same live-handle pattern. The existing XLSX-stream mutation
fixtures cover path/inode/stat drift and persistent changes, not this same-object
A-to-B-to-A content interposition.

This is an audit-oracle defect, not permission to doubt or alter the owner's frozen TSN
facts. It affects the trustworthiness of Phase-3/Stage-6 evidence whenever the reader's
live source could be modified during parsing; the accepted hashes remain the required
bytes.

Correction requirements: capture the exact compressed workbook bytes into a private,
immutable attempt-local payload while the bound source handle remains open; require the
pre-hash, capture hash, and post-parse live-source hash/stat/path identity to agree; and
parse only the private captured payload. Make topology inspection consume the same kind
of immutable capture. Add a permanent synchronized same-object A-to-B-to-A fixture that
preserves size/mtime and proves B cannot be returned under A's certificate. Re-run the
generic stream gate, all affected independent-oracle gates, and the exact Ramp full
corpus before accepting its Stage-6 result.

### CMP-AUD-137 — the independent XLSX reader folds error cells into ordinary strings instead of rejecting them

Priority: P1  
Status: Remediated by rejecting error-typed cells while preserving literal error-looking text  
Primary code: `build/phase3_xlsx_stream.py:_cell_value`,
`build/phase3_xlsx_stream.py:_stream_worksheet`,
`build/check_phase3_xlsx_stream.py:test_types_sparse_dates_and_sheet_resolution`

The OOXML reader currently returns a `t="e"` cell's lexical value such as `#N/A` as a
plain Python string. A true Excel error cell and an ordinary text cell containing
`#N/A` therefore receive the same Stage-6 typed digest. The permanent stream fixture
explicitly accepted the error as text, contradicting the strict raw literal-cell and
Stage-6 source contract that formula/error cells are inadmissible. A matching error on
raw and normalized sides could be certified as a conserved fact instead of a malformed
source.

Correction requirements: reject every OOXML error cell in a declared header/data
position with a schema error that includes the cell reference; retain ordinary text
such as the literal string `#N/A` as text; and add positive/negative fixtures proving
the two cannot share a typed path. Re-run the generic stream, Phase-3 adapters, and all
Stage-6 XLSX family oracles after the correction.

### CMP-AUD-138 — Highway Detail converts exact decimal Length through binary64 and rounds one source row downward

Priority: P1  
Status: **Resolved 2026-07-21 (`d553fbd`)** — `_norm_len` quantizes the exact Decimal with
`ROUND_HALF_UP`, never through binary64.  
Primary code: `scripts/compare_highway_detail_tsn.py:_norm_len`,
`scripts/compare_highway_detail_tsn.py:_tsn_row`,
`scripts/tsn_load_highway_detail.py`

#### Remediation — 2026-07-21

Census on the raw TSN workbook reading the **exact OOXML lexicals** (not floats):
**60,083 LENGTH values** examined — matching the corpus row count exactly — and the
binary64 path is wrong on **exactly one**, worksheet row 32565 (`THY_ID=77645219`,
lexical `1.35E-2`), `000.013` → `000.014`. Half-up and half-even **agree on all
60,083 values**, so the rounding-mode reconciliation the finding required is
satisfied: no corpus row can discriminate the two, and both agree with the D01
print on the only affected row. Half-up was chosen to match the report's own
round-half-away-from-zero rendering and is documented as non-load-bearing.

The other accepted allowlist row (32564, `7.4999999999999997E-3` → `000.007`) does
**not** move, confirming the finding's claim that it is a separate raw-XLSX-to-PDF
question; it is pinned as such.

Normalization is applied at COMPARISON time — `tsn_load_highway_detail` explicitly
delegates length to `compare_highway_detail_tsn` — so the cached TSN library content
is unchanged and **no `normalization_version` bump or user rebuild is required**.

Red→green: with the change reverted the new pins fail and `000.013` returns. Pins in
`check_compare_highway_detail_tsn` cover the tie from both the exact lexical and the
float form, the untouched neighbour row, tie neighbours, the negative tie, both carry
boundaries, and blank/non-numeric/non-finite passthrough. Suite 144/144.

**Method note:** the first census was WRONG — a cell regex that mishandled
self-closing `<c/>` elements mis-attributed columns and reported 1,177 values and
zero changes. It was caught only because 1,177 was implausible against 60,083 and
the finding's named row was absent. Check a census count against the known corpus
size before trusting a "nothing changes" result.

The authoritative Highway Detail XLSX stores raw OOXML `LENGTH` as exact Decimal
`0.0135` on worksheet row 32565 (`THY_ID=77645219`, DCR `01-HUM-096`, postmile
`R044.236`). The current normalizer converts the value to binary64 `float` before
formatting to three decimals and emits `000.013`. The independent Decimal projection
rounds the exact tie to `000.014` under half-even; half-up also yields `000.014`.
The exact D01 print on page 91 renders `000.014` for that same physical record, agreeing
with the independent Decimal projection. The item already exists among the accepted
443 XLSX-to-PDF allowlist entries as one of two `LENGTH` deltas, but the former oracle's
float-rendered `xlsx_stream=000.013` caused it to be classified like a dated source
delta. Across all 60,083 rows this is the only current raw-to-normalized projected-cell
residue, so it is not a broad formatting mismatch.

The other accepted `LENGTH` allowlist item is not the same defect. Its exact raw OOXML
lexical at worksheet row 32564 is `7.4999999999999997E-3`, whose Decimal projection and
current normalized value are both `000.007`; the later PDF prints `000.008`. That item
remains a real raw-XLSX-to-PDF representation/source-date question. Only row 32565 is
currently proven wrong in raw-to-`r7` normalization.

Correction requirements: define the authoritative three-decimal Length rounding rule
over the exact OOXML decimal lexical value and apply it without a binary64 intermediate.
Bind row 32565 plus adjacent below/tie/above, positive/negative, and carry-boundary
mutations. Reconcile the exact TSN PDF rendering and accepted 443-item source-date delta
manifest before choosing the final rounding mode; if the PDF intentionally applies a
different rule, preserve both raw and rendered claims rather than silently overwriting
one. Re-run Highway Detail raw-to-normalized, XLSX-to-PDF, comparison, Report View, and
evidence gates before product remediation is accepted.

### CMP-AUD-139 — the first Intersection Stage-6 oracle has mutable auxiliary scans, split provenance, and permissive numeric admission

Priority: P1  
Status: Remediated in the independently accepted Intersection result  
Primary code: `build/phase6_intersection_detail_conservation.py`

The first exact Intersection result reproduces 16,626 rows with zero projected-cell
residue and correctly reports three omitted TSN-only fields. Its reusable acceptance
mechanism still had four false-green seams:

1. family-local topology and error-cell scans parsed live file descriptors between
   equal pre/post hashes, retaining CMP-AUD-136's synchronized A-to-B-to-A gap even
   though the shared worksheet reader had been corrected;
2. CLI overrides for normalized size/SHA could select alternate workbook bytes while
   the oracle continued to validate the fixed `r7` outcome sidecar/token, allowing
   split normalized provenance;
3. `normalized_full_conservation` was not structurally gated by `audit_complete`; and
4. numeric fields returned malformed nonempty text such as `BAD`, `1e3`, or `.5`
   unchanged, despite the independent specification admitting only its declared signed
   decimal grammar and requiring unknown domains to be anomalies/rejections.

The same review found that the result bound the normalized workbook and its sidecar but
not the accepted `raw-2026-07-12-r7/result.json` lifecycle witness. It also listed the
generic reader mutation check as `declared_not_executed`; the family audit could still
be true because neither execution nor its output was an invariant.

Correction requirements: make every auxiliary ZIP/XML pass consume a private immutable
capture; fix the audit to the exact accepted `r7` normalized workbook and sidecar as one
provenance unit (or require a complete caller-supplied matching binding); gate full
conservation on all audit invariants; reject malformed numeric domains; add permanent
mutations for each seam; and regenerate both result and detached post-write acceptance
records under the final generator/reader bytes before promotion. Bind the exact accepted
`r7` result and execute/persist the hash-bound generic reader mutation gate as part of
the family acceptance rather than citing an unexecuted dependency.

### CMP-AUD-140 — Intersection numeric-postmile collision censuses still group on display text and can split equivalent identities

Priority: P1  
Status: Remediated in the independently accepted canonical numeric-PM census  
Primary code: `build/phase6_intersection_detail_conservation.py:_collision_census`

The corrected Intersection oracle introduced an exact Decimal-canonical
`identity_numeric_postmile` for physical and lossless identities, but its three weaker
collision diagnostics still used the source-display `postmile` string. Consequently
numerically equal forms such as `5.450` and `5.45` remained separate in the
within-county prefix census, route-plus-numeric-PM cross-county census, and
route-plus-complete-prefix-plus-PM cross-county census even though each result is
explicitly described as numeric-postmile truth. The trailing-zero mutation proved only
that the full identities stayed equal; it did not recompute these weaker censuses, so
the permanent gate could falsely remain green while its diagnostic partition changed.

Correction requirements: construct all three maps from the Decimal-canonical numeric
postmile identity, not the display value; extend the trailing-zero mutation to recompute
and require exact equality of the complete collision census; re-freeze the exact six
within-county prefix collisions and both cross-county counts from the fixed semantics;
and regenerate the result plus detached acceptance under final generator bytes before
independent promotion.

### CMP-AUD-141 — the first Highway Detail Stage-6 artifact can report acceptance without one coherent immutable source/result transaction

Priority: P1  
Status: Remediated in the independently accepted Highway Detail artifact  
Primary code: `build/phase6_highway_detail_conservation.py`

The first Highway Detail conservation result independently reconciles the current
60,083-row factual census, but its reusable acceptance mechanism has five false-green
seams. Caller-supplied normalized size/SHA values can describe a workbook other than the
fixed `r7` sidecar/lifecycle witness; the generic immutable XLSX reader gate is cited but
not executed or hash-bound; `r7` result, sidecar, and accepted PDF-oracle JSON are parsed
by later live `read_text()` calls rather than from their already checked private byte
captures; raw and normalized physical-row contiguity are reported but not audit
invariants or mutation-tested; and no detached post-write acceptance record binds the
final result bytes/hash to the final raw, normalized, sidecar, lifecycle, PDF-oracle,
generator, reader, and reader-gate identities. A kill after the final result write or a
synchronized A-to-B-to-A interposition can therefore leave an apparently accepted JSON
whose consumed facts were never the attested bytes.

Correction requirements: fix the run to the exact accepted `r7` normalized
workbook+sidecar+witness as one binding; capture and parse every JSON dependency from the
same private immutable payload whose hash/size is checked; execute and persist the exact
reader gate source/stdout/return code; include both physical-row-contiguity claims and a
row-gap mutation in the audit; and publish an ID-style detached acceptance JSON only
after final result bytes exist and all dependencies/code are revalidated.

### CMP-AUD-142 — Highway Detail drops two PDF-printed snapshot dates and misdescribes them as database-only metadata

Priority: P1  
Status: Verified from authoritative raw XLSX plus accepted all-12 TSN PDF mapping  
Primary code: Highway Detail normalizer/sidecar, Notes, comparison provenance, and
evidence consumers

`REFERENCE_DATE` is uniformly `2025-09-08` in the authoritative XLSX and
`EXTRACT_DATE` is uniformly `2025-09-15`. The accepted source-format oracle maps those
facts to the PDF's printed `REFERENCE DATE` and `REPORT DATE` and uses them to explain
the exact seven-day XLSX-to-PDF snapshot skew. Current normalized bytes/sidecar do not
carry the values, while the app Notes group them with database IDs. That description is
factually wrong and leaves comparisons/evidence unable to prove which dated snapshot a
normalized row set represents.

Correction requirements: retain both exact source dates in immutable normalized
provenance and carry them through comparison/evidence/Report View diagnostics; correct
Notes to describe their printed snapshot roles; reject missing, multiple, malformed, or
incoherent date values; and require the XLSX/PDF source-date relationship to be explicit
rather than treating dated row deltas as unexplained or database-only facts.

### CMP-AUD-143 — the Highway Detail audit's decisive Length projection inherits mutable ambient Decimal rounding context

Priority: P2  
Status: Remediated with explicit context-independent half-even projection and probes  
Primary code: `build/phase6_highway_detail_conservation.py:_fixed_three`

The oracle formats a `Decimal` directly with `07.3f`, which obeys the process-global
Decimal context. Under the default half-even context, exact raw `0.0135` projects to
`000.014` and exposes CMP-AUD-138; under an ambient `ROUND_DOWN` context, the same audit
can project `000.013` and collapse the decisive residue into the current wrong product
value. The result therefore depends on unrelated caller state even though its output is
presented as an independent exact-decimal fact.

Correction requirements: quantize explicitly to `Decimal("0.001")` with the selected
and documented `ROUND_HALF_EVEN` rule before fixed-width rendering; add a probe that
changes ambient context to `ROUND_DOWN` and still obtains `000.014`; bind below/tie/above,
negative, and carry-boundary values; and re-run the exact row-32565 XLSX/PDF classification
under the final generator bytes.

### CMP-AUD-144 — Intersection Summary normalization irreversibly folds six authoritative printed control categories into one count

Priority: P1  
Status: Resolved 2026-07-14 — printed J–P claims preserved + derived-S cross-checked; real-data verified  
Primary code: Intersection Summary normalizer, loader, comparison schema, sidecar, and
Report View/evidence consumers

The authoritative three-page PDF prints 62 category rows. Six separate control rows
J/K/L/M/N/P carry exact counts `207`, `36`, `107`, `65`, `210`, and `2023`, but the
current normalized comparison schema emits only one `S=2648` row for their sum. That fold
may be the selected comparison projection against the current TSMIS taxonomy, yet it is
non-injective: normalized bytes cannot reconstruct the six original labels/counts or
prove which source distribution produced the total. Therefore a zero-residue 57-category
projection plus `Total` is not raw-source full conservation.

Correction requirements: preserve all six printed claims in an immutable source-bound
representation while retaining an explicitly derived `S` comparison category; validate
each component and the exact 2648 subtotal; distinguish source rows, derived comparison
rows, and the grand total in Report View/evidence; and keep audit-complete/projection-
exact separate from full-conservation truth until reconstruction is possible.

### CMP-AUD-145 — Intersection Summary drops the TSN PDF's erroneous raw CONTROL F label while applying the proven RED/MAINLINE canonical mapping

Priority: P1  
Status: Resolved 2026-07-14 — raw F descriptor retained as a declared TSNR-bound correction; drift refuses  
Primary code: Intersection Summary category map, normalized labels, comparison/evidence

The statewide TSN Summary PDF prints CONTROL F as `FOUR WAY FLASHER (RED ON ALL)` and
prints G with the same meaning. That print is defective, not the canonical mapping. The
authoritative `TSNR - Intersection Control and Geometry Type_4.25.24_AT 1.xlsx`
crosswalk defines F as `Four-Way Flasher (Red on Mainline)` and G as `Four-Way flasher
(Red on All)`. Every same-pull TSMIS Excel/PDF route also uses F=`RED/MAINLINE` and
G=`RED ON ALL`. The normalized F label is therefore semantically correct.

The product defect that remains is source-claim loss: normalization silently replaces
the erroneous printed F descriptor, leaving no immutable field that proves what the raw
TSN PDF actually said or that a canonical correction was applied. Comparisons and
evidence can display the right canonical meaning while being unable to reproduce or
flag the source-label defect.

Correction requirements: retain both the exact raw printed F descriptor and the
authoritative canonical F mapping, bind the TSNR decision source, mark the mapping as a
declared correction rather than equality, expose it in Report View/evidence, and
mutation-test raw F, raw G, canonical F/G, and decision-source drift independently.

### CMP-AUD-146 — normalized Summary artifacts omit printed report identity, timing, and submitter provenance

Priority: P1  
Status: Resolved 2026-07-14 — print identity/timing/submitter captured, typed, required exactly-once; exposed in Notes  
Primary code: Summary normalizers/sidecars, comparison Notes/provenance, Matrix/evidence

The accepted `r7` Intersection Summary workbook and sidecar bind the raw PDF bytes but do
not carry its printed reference date `09/15/2025`, report ID `OTM22250`, event `4843738`,
submitter `TRLBUGNI`, report title/location, or printed generation time. These page-2/3
facts identify what was run, by whom, and for which effective snapshot; they are not
reconstructable from the Category/Count rows and are materially different from legal or
presentation-only page furniture. Ramp Summary independently confirms the same class:
report/reference dates `09/15/2025`, report ID `OTM22270`, event `4843742`, submitter
`TRLBUGNI`, `STATEWIDE` scope/title, and the page-3 `05:10 PM` generation time are all
absent from its normalized Category/Count artifact. It must be audited under the same
rule rather than given a family-specific exception.

The accepted Stage-8 TSMIS-vs-TSN oracle reuses those exact TSN bytes and accepted r7
chain, so this finding remains open even though all normalized counts are exact. The
separate current TSMIS Summary provenance loss (07/09/2026 report date, 07/10/2026
reference date, submitter, and generated times) is recorded under CMP-AUD-076 rather
than conflated with this TSN-normalization finding.

Correction requirements: capture each printed report identity/timing field into the
immutable normalized sidecar or an equivalently bound provenance record; type and digest
the exact source values; reject missing/multiple/malformed metadata; expose relevant
facts in comparison Notes/evidence; and explicitly disposition genuine legal/presentation
text without allowing that label to swallow report identity. Category equality alone
may not certify full source conservation.

**Remediation for CMP-AUD-144/145/146 (2026-07-14, one normalizer batch —
summaries' `normalization_version` 2→3).** New `parse_tsn_source_claims` per
summary comparator captures, before any fold: the print identity
(`compare_tsn_common.tsn_print_identity` — report id / report+reference dates /
submitter / title / event id / generation time / location, each REQUIRED with
exactly one distinct value across all pages; the Ramp print's next-line
`EVENT ID :` shape handled; page-1 policy prose dispositioned as legal
furniture), every printed (block, count, raw-label) row (62 on the censused IS
print), the J–P signal components (207+36+107+65+210+2023 = 2,648, cross-checked
against the derived folded S by `validate_claims_against_counts` in both the
normalizer and the raw-compare path), and the declared CONTROL F correction
({printed `F-FOUR WAY FLASHER (RED ON ALL)`, canonical `4-WAY FLASHER
(RED/MAINLINE)`, decision source TSNR 4.25.24} — a drifted printed F or G
descriptor refuses for re-census). Claims ride
`ConsolidateResult.producer_extra["tsn_source_claims"]` into the library
sidecar (`build_normalized` merges producer extra; the version bump D2-rebuilds
stored libraries so every normalized workbook gains its record). Comparisons
expose the claims as familiar-sheet notes + log lines — identity, derived-S
composition, and the declared correction — from a fresh parse on the raw path
or `read_extra` on the normalized path (absent → explicit no-claims
diagnostic). Verified on both real statewide PDFs (censused values reproduced
exactly; both oracles unchanged: 29/0/2·5·24 and 58/8/0·5·53). Fixtures:
`check_compare_intersection_summary_tsn.test_source_claims`, claims stubs in
`check_tsn_normalizer` / `check_tsn_outcome` / `check_tsn_raw_source_contract`.
Honest scope: the workbook rows remain Category|Count (reconstruction lives in
the sidecar claims record, per the finding's "or an equivalently bound
provenance record"); Report View/evidence surfaces beyond the summaries'
familiar sheets don't exist for these families; the TSMIS-side print provenance
loss stays with CMP-AUD-076.

### CMP-AUD-147 — Highway Detail detached acceptance can say accepted when audit invariants are false

Priority: P1  
Status: Remediated in the independently accepted detached acceptance contract  
Primary code: `build/phase6_highway_detail_conservation.py:main`

The corrected detached acceptance initially set `accepted` from post-result identity
stability alone. `run()` can legitimately return
`stage6_family_audit_complete=false`—for example after a collision-contract,
contiguity, mutation, or residue invariant fails—without raising an exception. In that
case the process eventually exits nonzero, but the already published acceptance JSON
still says `accepted:true`. A consumer that trusts the detached record rather than the
ephemeral process exit can therefore promote a rejected audit.

Correction requirements: define detached acceptance as both post-write identity-current
and `stage6_family_audit_complete`; persist audit-complete, projection-exact, and full-
conservation booleans separately from the identity revalidation bit; add a synthetic
false-invariant result proving `accepted=false` under stable identities; and regenerate
the full result/acceptance before independent promotion.

### CMP-AUD-148 — Intersection Summary's J-component mutation probe treats the projector's correct fail-closed rejection as an audit failure

Priority: P2  
Status: Remediated in the independently accepted Intersection Summary gate  
Primary code: Stage-6 Intersection Summary oracle semantic mutation probe

The authoritative extraction and live projection reproduce the derived `S=2648` count
exactly. The planted legacy-J mutation changes printed `J` from `207` to `208`; the
independent fold correctly becomes `S=2649`, and the fixed-contract projector correctly
raises rather than returning a changed accepted projection. The probe incorrectly
expected a returned value, so correct fail-closed behavior made the entire valid source
run fail. This is an audit false-negative, not product residue, and the failed JSON is
not an acceptance artifact.

Correction requirements: catch the expected projection rejection, prove its sole
semantic delta is Control `S 2648→2649` with all other target rows unchanged, and count
that exact rejection as detected. Keep unexpected exception types/messages or any second
delta red; rerun the immutable full PDF/r7 audit and detached acceptance after the probe
correction.

### CMP-AUD-149 — Summary PDF audits do not bind every loaded parser module and can miss same-version code drift

Priority: P1  
Status: Remediated in both accepted Summary parser-provenance manifests  
Primary code: Stage-6 Ramp/Intersection Summary PDF oracle provenance and acceptance

The first Ramp Summary candidate recorded parser versions and initially bound only the
top-level `pdfplumber`/`pypdf` package files. Intersection's candidate scanned package
trees more broadly but omitted `pdfminer`, even though `pdfplumber` executes it, and did
not record the exact loaded module set. A same-version edit to a loaded internal module
can therefore change extraction after the initial audit while version strings and the
incomplete file set remain current. Ramp's first full candidate and Intersection's
pre-publication candidate are rejected evidence, not accepted results. The rejected Ramp
result is 69,618 bytes, SHA-256
`14bd2a8e7f226825f7ecb2e6f9da097b997a3f605266e634d5f673b36a4d3ab4`; its rejected
9,301-byte detached record is SHA-256
`ec62a10204cc994a5d10e1e61e329ba1fad86e1cf94db82b2d01a37c2cba5a93`.

Correction requirements: after parser imports/extraction, enumerate every actually
loaded executable module file under `pdfplumber`, `pdfminer`, `pypdf`, and any other
observed PDF-parser package; persist a deterministic relative-module/path/byte/SHA
manifest plus versions; revalidate that exact set after all digests and after result
publication; reject added/removed/moved/changed loaded modules; and add a same-version
internal-module drift mutation that cannot pass via version equality.

### CMP-AUD-150 — Intersection Summary's successful typed mutation diagnostic cannot be serialized into its result JSON

Priority: P2  
Status: Remediated by canonical typed diagnostics and full-result JSON round-trip gating  
Primary code: Stage-6 Intersection Summary result serialization

The corrected J-component rejection probe records its observed projected delta using
tuple rows that still contain `Decimal(2648)` and `Decimal(2649)`. Python's ordinary
`json.dumps` has no Decimal encoder, so an otherwise complete audit aborts during
publication. This is an audit diagnostic serialization failure, not source/product
residue, and no result or detached acceptance was published.

Correction requirements: convert every typed diagnostic through the oracle's canonical
typed wire or an explicit lossless JSON representation; serialize the entire successful
result before any publication; add a permanent full-result JSON round-trip gate covering
Decimal/date/null/text values; and keep partial/unserializable payloads from replacing a
last accepted result.

### CMP-AUD-151 — Intersection Summary's first green candidate lacks adversarial probes across total, geometry, raw-only, sidecar, and r7-output layers

Priority: P1  
Status: Remediated by the independently accepted five-layer mutation manifest  
Primary code: Stage-6 Intersection Summary mutation manifest and permanent gate

The first green full result has strict source/invariant checks, but its semantic mutation
manifest does not directly prove rejection or detection for five important layers: report
`Total=16626` drift; page word/coordinate topology drift; a printed descriptor/band
change that leaves the derived Category/Count projection unchanged; same-completion
sidecar raw-manifest drift; and accepted-r7 output-hash drift. Those checks may currently
fail through bindings, but without planted mutations the reusable audit can regress or
misclassify the changed layer without turning its own permanent gate red.

The provisional result is 215,236 bytes, SHA-256
`2ee1a436968ee752b4fb5603bfb4aa87c35be87534e71c32401fb09fa2a71952`; its provisional
44,336-byte detached record is SHA-256
`98b45f82e855c5cd48c62ebe1a2734563a726f56497029c4b587be0893f489da`.
It reported 11/11 existing mutations and 137 loaded modules, but is not accepted while
these five coverage gaps remain.

Correction requirements: add exact independent probes for all five layers. The raw-only
descriptor/band mutation must change the raw typed digest while preserving projection,
proving why full conservation differs from comparison projection. Sidecar and r7-output
mutations must retain superficial completion while failing exact provenance; geometry
must move a bound word/coordinate without changing extracted text; and Total drift must
prove both report-total and section conservation fail. Re-run full publication and
detached acceptance under final code/parser manifests before promotion.

### CMP-AUD-152 — Ramp Summary detached acceptance can be published for an audit-false result and has no explicit accepted Boolean

Priority: P1  
Status: Remediated in the independently accepted Ramp Summary artifact  
Primary code: Stage-6 Ramp Summary result/acceptance publication

The candidate writes a detached acceptance record whenever post-result identities are
stable, even if `stage6_family_audit_complete=false`, and the record has no explicit
`accepted` Boolean. A synthetic stable-identity/audit-false run returned process exit 2
but still left an acceptance JSON with `post_result_write_revalidation=true` and no
machine-readable rejection state. A consumer can therefore treat a provenance-current
but semantically failed audit as accepted. The current full result itself reports audit
true, but its reusable publication contract is unsafe.

Correction requirements: publish `accepted = postwrite_current AND
stage6_family_audit_complete`; persist the audit/projection/full booleans separately;
make an audit-false stable-identity fixture emit `accepted=false`; ensure a previous
accepted record cannot survive a failed rerun; and regenerate/re-review the full result
and detached record.

### CMP-AUD-153 — Ramp Summary claims complete PDF source-role disposition without exact observed-role coverage

Priority: P1  
Status: Remediated by exact 13-role coverage in the accepted Ramp Summary audit  
Primary code: Stage-6 Ramp Summary PDF parser role ledger and audit invariants

The parser emits 13 concrete page-role names, but the disposition ledger uses composite
descriptions rather than enforcing an exact one-to-one observed-role universe.
`page_2.cover_title` and `page_3.section_headers` have no explicit disposition, no
coverage invariant, and no negative mutation. The audit can therefore say every source
role is explained while silently introducing, dropping, or misclassifying page content.

Correction requirements: enumerate the exact parser-observed role set; give every role
exactly one compared/derived/provenance/presentation disposition; reject missing,
extraneous, duplicate, or renamed roles; bind the role-universe digest; and add mutations
for both uncovered roles plus an unknown role. Re-run the full PDF/r7 audit only after
the exact coverage invariant is green.

### CMP-AUD-154 — Intersection Summary's per-category conservation omits multiset, target-row, and per-source-disposition typed digests

Priority: P2  
Status: Remediated by accepted 58/58 per-category/source typed digest coverage  
Primary code: Stage-6 Intersection Summary per-category/source-disposition digest ledger

The candidate records complete global raw/projected/normalized ordered and multiset typed
digests, but `per_normalized_category_conservation` retains only each category's ordered
contribution digest. It does not record a per-category multiset digest, an explicit typed
digest of the projected `(Category, Count)` target row, or a typed digest on each
individual source-disposition row. Overall equality can therefore remain green while a
category's contribution attribution or source-row ownership is rearranged incorrectly.
The first corrected digest candidate then covered all 57 projected non-total categories
but omitted normalized row 58, `Total Intersections`, from this per-category ledger;
binding the total elsewhere does not satisfy literal coverage of every normalized
Category row.

The byte-reproducible provisional result is 217,117 bytes, SHA-256
`2bf80001e2b047e4ee4007c429b0dfa06364c87386dcbe7f36095d2443b80531`; its 44,336-byte
detached record is SHA-256
`7b901d1a72bd73bf480b585d72a87c6e5ca78b7c4c927a3d1b5e9563c7d2c939`.
It passed 18 existing invariants and 16 mutations but remains provisional pending the
missing per-category/source digest contract.

The 57/58 interim correction is also retained only as provisional history: result
243,920 bytes / SHA-256
`fb7b52af17ee1c6d5d2fc2e67d8e0eb0efddada840d1699413eecb732b5a0d78`; detached record
44,337 bytes / SHA-256
`ad6b0fd9c38a6b101516d7397357d5ea19dfe8a3c97fce9fdd7ef467fd1d1233`.

Correction requirements: persist ordered and multiset typed contribution digests for
every category, the exact typed target-row digest, and one typed digest per source
disposition; bind the category/source universe including a typed Total contribution/
target digest for exact 58/58 normalized rows; and add a mutation proving that a change
to one category alters only that category's source/target digests while every peer
category stays identical. Regenerate deterministic result/acceptance before promotion.

### CMP-AUD-155 — Highway Sequence normalization drops district, direction, report provenance, and source reliability policy facts

Priority: P1  
Status: Remediated 2026-07-16 (the HSL v4 batch) — was: Verified during Stage-6 authoritative PDF source inspection  
Primary code: Highway Sequence TSN PDF parser/normalizer, sidecar, comparison Notes,
Report View/evidence

The 12 authoritative Highway Sequence PDFs carry internal district ownership, a per-route
printed direction (`S-N`, `W-E`, or `E-W`), report-generation date/time, `Ref Dt`, report
ID/title, PDF metadata, and a cover warning/policy about TSN landmark-description
reliability. Normalized v3 retains neither those facts nor an equivalent immutable
sidecar representation. Current row equality can therefore be exact while route
orientation, source snapshot/identity, and the source's own interpretation limits vanish
from comparisons and evidence.

Correction requirements: give every printed/header/metadata/policy role an exact
disposition; persist district, direction, report identity/timing/reference date, and the
reliability warning in source-bound normalized provenance; reject cross-page/member
inconsistency; expose relevant facts in Notes/evidence; and mutation-test each field
independently from row projection.

**Remediation (2026-07-16).** `consolidate_tsn_highway_sequence.parse_pdf` now parses
every cover (report id, `Reference Date:`, `District:`, the `* * * N O T E * * *`
reliability policy — each required, missing refuses) and every data page's identity
band (report id, title, report date, `Ref Dt`, generation time) under the exactly-one-
distinct-value multiplicity rule; `GROUP_RE` captures the per-route printed direction
(conflicting directions within a document refuse), and `_cross_member_claims` refuses a
member from a different pull (report id/title/date/reference dates must agree across
all 12 districts; generation time and the policy stay per-document). The claims record
rides `producer_extra["tsn_source_claims"]` into the library sidecar and surfaces in
every vs-TSN Notes sheet via `_schema_with_claims` (identity line, direction census,
the reliability policy — with an explicit rebuild hint when the record is absent). The
real-corpus rebuild reproduced the bound census exactly: 12 documents, one distinct
policy text, directions {S-N 190, W-E 172, E-W 5, N-S 2}. Contract fixtures:
`check_tsn_district_source_contract` (missing-NOTE cover, conflicting directions,
cross-member reference-date disagreement, claims presence) and
`check_compare_highway_sequence_tsn`. Evidence exposure beyond Notes remains with the
Stage-10 evidence rework (CMP-AUD-098; 218's Spot Check half was remediated 2026-07-16).

### CMP-AUD-156 — Highway Sequence's numeric-only distance parser erases a real printed landmark pointer

Priority: P1  
Status: Remediated 2026-07-16 (the HSL v4 batch) — was: Verified on the authoritative D01 final page before Stage-6 implementation  
Primary code: Highway Sequence TSN PDF distance/landmark parser and normalized projection

The full 1,540-page census contains 565 nonnumeric printed `DISTANCE TO NXT POINT` claims:
`*P*` appears 283 times and `-------->` appears 282 times, including the visually checked
D01 final-page pointer at HUM / Route 299 / postmile `038.833`. The current parser accepts
only numeric distance values and projects all 565 tokens to blank. They are not page
furniture or generic provenance: they occupy the distance data position and communicate
source-defined point/pointer semantics. Treating them as blank destroys source claims and
can make evidence or comparison output assert that nothing was printed.

Correction requirements: preserve/classify the exact pointer token and every observed
non-numeric distance-domain value; bind its district/page/route/postmile identity;
distinguish pointer semantics from numeric distance and true blank; add missing/moved/
changed/extra-pointer mutations; and re-run raw PDF→normalized→comparison→evidence truth
without silently coercing the marker away.

**Remediation (2026-07-16).** The parser now takes the distance window's first token
verbatim and validates it against the censused domain — numeric, `*P*`, or
`-------->`; any OTHER token refuses loudly ("unrecognized DISTANCE TO NXT POINT
token … re-census"), so a drifted layout can never again silently blank a claim
(`consolidate_tsn_highway_sequence.POINTER_TOKENS`, normalization v4 with the
`TSN Normalization` marker sheet + loader refusal + D2 rebuild). The evidence TSN
scan mirrors the rule. Real-corpus rebuild: exactly 283 `*P*` + 282 `-------->`
(565) conserved through the normalized workbook and the comparison loader
(Distance is a context column: displayed verbatim, never counted). Fixtures:
`check_compare_highway_sequence_tsn` (verbatim one-sided display) and
`check_tsn_district_source_contract`; the foreign-token refusal is pinned in the
green probe/gate fixtures.

### CMP-AUD-157 — Highway Log normalization drops group ownership, three printed ADT fields, totals, and report provenance

Priority: P1  
Status: Verified during Stage-6 authoritative PDF source inspection  
Primary code: Highway Log TSN PDF parser/normalizer, physical identity, sidecar, Notes,
Report View/evidence

The 12 authoritative Highway Log PDFs assign rows through internal district/county/route
group ownership and print three ADT claims (`Look Back`, the P/P flag, and `Look Ahead`).
They also carry report ID/date/title/year/PDF metadata and printed totals blocks.
Normalized v4 drops those claims. County loss already participates in CMP-AUD-045's
unsafe physical-identity boundary; the additional ADT/totals/provenance loss means even
a correctly paired row cannot reconstruct the printed source or evidence context.

The first independent full-crawl stop also proved that the owner grammar is not always
the documented three tokens: D01 physical page 40 prints centered `01 MEN 101 U`, with
the final `U` as a separate glyph token. The production parser consumes only the first
three tokens and the normalized row has no field for the trailing owner qualifier. Its
business meaning is not inferred here; the exact token is a source claim and the full
corpus qualifier census remains part of this finding's Stage-6 closure.

Correction requirements: retain district/county/route ownership and any separately
printed owner qualifier in physical identity without guessing its meaning;
give every ADT, totals, header, and metadata field an exact typed disposition/digest;
persist comparison-relevant source provenance; reconcile totals independently against
row universes; mutation-test source-only changes that leave current normalized rows
unchanged; and require zero unexplained raw-PDF→normalized/evidence residue before family
remediation is accepted.

**Remediation (2026-07-17, normalizer v5 — catalog `normalization_version`
4→5, D2 auto-rebuild; marker-sheet gate on manually-picked files).**
- **The owner qualifier is the route suffix.** The full-corpus census found
  exactly 19 four-token group headers whose (route, letter) combinations are
  exactly TSMIS's ten suffixed routes; the print's own COUNTY/ROUTE totals for
  those sections are all-zero. No meaning was guessed: the correspondence was
  row-verified against the TSMIS per-route exports before the suffix joined the
  route identity (see the CMP-AUD-045 Highway Log record). A 4th token that is
  not a single letter — or any fifth token — refuses (unknown grammar cannot
  own rows).
- **Group ownership conserved.** `tsn_source_claims.documents[].ownership`
  carries one entry per printed header occurrence (2,363 statewide):
  page/district/county/route token/detached suffix/normalized route/row count —
  rows are reconstructible per document in order, and the manifest's row
  counts sum to the exact corpus row count.
- **The three ADT claims conserved by digest.** Per row the ADT zone is
  re-tokenized by word gap and split around the single P/S flag (the fixed
  448pt window boundary bleeds wide Look Back figures, so window-center
  assignment would corrupt the claim); non-numeric Look Ahead claims ("D-C",
  "END") stay verbatim. The sidecar records per-document non-empty counts, the
  flag vocabulary, and the SHA-256 of the canonical per-row stream — typed
  disposition `tsn_only_no_tsmis_column_conserved_by_digest` (no TSMIS
  counterpart exists; never compared, never fabricated).
- **Totals typed, digest-bound, and reconciled against row universes.** Every
  star block (Volume/CITY/COUNTY+CUMULATIVE/ROUTE/DISTRICT/End-of-Report,
  wrapped continuations rejoined) parses into typed values with overflow
  markers ("##########"/"**********") typed as overflow. HARD GATES (a
  violation refuses publication): TOTAL == CONST + UNCONST on every fully
  parsed mileage group (census harness 2,258/2,258 star lines; the
  production parser checks 2,914 groups including the county-cumulative
  sections — 0 mismatches statewide) and all-zero totals on every suffixed
  section (22/22 lines). Corpus block census: 1,234 city / 657 county /
  380 route / 12 district / 7,613 volume / 12 centered "*** End of Report ***"
  markers (typed end_of_report). RECORDED MEASUREMENTS (disclosed
  in the sidecar + comparison Notes, never certified): route/county totals
  vs the additive MI sums (NA='N' non-additive rows excluded, keyed across
  non-contiguous sections) measure 234/369 and 427/641 exact — the print's
  odometer-based accounting is not fully modeled — and Volume Length is
  exact on 6,063/7,613 sections (+7 within 0.001) with DVM within ±1 of
  Length × ADT on 3,196 (289 print zero, 3 overflow).
- **Provenance conserved.** Per document: report id (OTM52010), band date,
  title, cover year, page count — one distinct value per document enforced,
  and the 12 members must agree (`_cross_member_claims` refuses a member from
  a different pull).
- **Zero-residue accounting.** Every below-band line must classify (data /
  description / group header / district line / totals block or fragment /
  cover furniture) or the parse REFUSES listing the residue. The instrument
  immediately found real dropped content: asterisk-leading printed
  Descriptions on exactly FOUR rows statewide (YUB 065 R009.327
  "**** CODE ACCIDENTS TO"; bare "*" on 041/031.050, 041/009.920,
  145/005.010 — the TSMIS export prints the same text on the same four
  rows, so each was a manufactured false Description difference) are now
  conserved; totals star lines print left of the description band and still
  close the open row. It also surfaced two page-break wrap shapes the block
  grammar now models: a totals object continues BELOW the next page's
  reprinted group header (blocks survive group headers and bind their owning
  route/county at OPEN time), and rare stranded keyword/value halves of a
  split line are conserved verbatim as stray fragments (strict totals
  vocabulary only), never guessed onto a block.
- **Mutation test.** A source-only ADT digit change leaves the normalized
  rows byte-identical while the claims digest moves
  (`check_tsn_highway_log_claims`, fixture-PDF-driven through the production
  pipeline). The corpus-level proof: the v4 (pre-batch HEAD module) and v5
  consolidated workbooks built from the SAME 12 raw prints differ by exactly
  the 317 route-moved rows and the four recovered Descriptions — 0
  unexplained v4-only rows, 0 unmatched v5-only rows; every other one of the
  60,083 rows is byte-identical.
- The comparison Notes sheet exposes the conserved claims per run (print
  identity, suffixed sections, ADT/totals dispositions + reconciliation
  summary); absent claims get an explicit rebuild hint.

### CMP-AUD-158 — Highway Sequence drops EQUATES TO annotations that appear before county context exists

Priority: P1  
Status: Remediated 2026-07-16 (the HSL v4 batch) — was: Verified by the full 12-PDF / 1,540-page Stage-6 census  
Primary code: Highway Sequence TSN PDF route/equate ownership parser and normalized rows

The authoritative PDFs print 998 `EQUATES TO` annotations. Current normalization emits
952, but silently drops 46 that occur before the first county-bearing row of a route
group because parser county context is still unset. Inferring the later county is not an
acceptable repair: the source cover explicitly warns that equates and route/county/
district-boundary descriptions may be wrong. The source annotation and its incomplete/
ambiguous ownership must be conserved as printed and surfaced for review.

Correction requirements: preserve all 998 annotations with exact district/page/route/
direction/order provenance; represent pre-county ownership as explicit unknown/ambiguous
rather than discarding or backfilling it; bind the exact 46-item manifest; mutation-test
first/middle/final, moved county headers, and added/removed/changed equates; and require
the comparison/evidence layer to disclose ambiguous ownership without pairing it to an
invented county.

**Remediation (2026-07-16).** The parser now emits every annotation (a route-less one
refuses as unowned); a pre-county annotation keeps its BLANK county exactly as
printed. The comparison loader keys such rows under the reserved
`"(county not printed)"` canonical marker (`compare_highway_sequence_tsn
._physical_pm_key`) — self-describing in the Comparison key column, structurally
unable to pair with any real county, mirroring the Stage-8 oracle's
"explicitly unkeyed TSN-only" disposition — and the Notes disclose the class.
Real-corpus rebuild: 69,758 → **69,804 rows** (998 equates, exactly 46
blank-county, all `EQUATES TO`), and the complete-raw leg shapes now reproduce
the oracle exactly (TSN-only 12,732 / 12,299 — the keyable 12,686/12,253 plus
the 46). Normalization v4 + marker-sheet refusal + D2 rebuild; fixtures in
`check_compare_highway_sequence_tsn` and `check_compare_physical_identity`.

### CMP-AUD-159 — Highway Sequence fabricates punctuation when joining one wrapped printed Description

Priority: P1  
Status: Remediated 2026-07-16 (the HSL v4 batch) — was: Verified by the full Stage-6 source census  
Primary code: Highway Sequence TSN PDF wrapped-description joiner and normalized projection

At D09 / KER / Route 014 / postmile `018.365`, the PDF prints two lines:
`KEMWATER CHEMICAL PLANT - RT/FRONTAGE` and `ROAD - LT.` with no punctuation between
them. Normalized v3 inserts `, ` during the join. This is not a render-only equivalence:
the normalized value contains characters absent from the source and can create a false
TSMIS-vs-TSN Description difference.

Correction requirements: join wrapped source fragments under an explicit whitespace/
continuation contract without invented punctuation; bind this exact row plus punctuation-
present and punctuation-absent neighbors; reject orphan/ambiguous continuations; and
re-run raw PDF→normalized→comparison/evidence cell truth before re-blessing.

**Remediation (2026-07-16).** Wrapped continuations now join on a single space (the
continuation contract stays: description-window words only, no county/postmile
token, attached to the open row); the evidence TSN scan mirrors it. Real-corpus
rebuild: D09 / KER / 014 / `018.365` reads exactly
`KEMWATER CHEMICAL PLANT - RT/FRONTAGE ROAD - LT.` — no invented characters.
Normalization v4; the joined-value pin lives in the gate fixtures
(`check_compare_highway_sequence_tsn` + the batch's green probe).

### CMP-AUD-160 — the first Highway Sequence conservation gate misclassified the library placeholder as comparison truth

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` raw-member admission

The authoritative `highway_sequence/raw/` directory contains the exact 12 bound district
PDFs plus the library-created `_PUT TSN FILES HERE.txt` placeholder. The first oracle
draft compared every ordinary file name with the 12-PDF source universe and therefore
failed before reading any PDF. Treating the placeholder as a thirteenth source would be
worse: it would corrupt source cardinality and manifest claims. Silently ignoring every
non-PDF sibling would also be unsafe because an unrecognized file could then interfere
with a future selector without appearing in the audit.

Correction requirements: admit exactly the 12 bound PDF names as comparison truth;
admit only the explicitly named placeholder as a recorded non-source role; reject every
other sibling; keep the placeholder out of source member/byte/page/record totals; bind its
identity through final acceptance; and mutation-test missing/extra role handling.

### CMP-AUD-161 — the Highway Sequence conservation gate asserted the wrong typed r7 acceptance vocabulary

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` lifecycle witness validator

The accepted `raw-2026-07-12-r7/result.json` stores top-level `acceptance` as the typed
terminal string `complete`. The first validator draft asserted the unrelated Boolean
`true`, so it rejected the exact hash-bound accepted witness before PDF parsing. Replacing
the assertion with loose truthiness would conceal future vocabulary drift and repeat the
comparison project's earlier prose/Boolean terminal-state mistakes.

Correction requirements: require exact typed `acceptance == "complete"`; continue to
bind the witness bytes and all family completion/zero-failure/output/reuse fields; add a
permanent synthetic validator check for wrong Boolean, partial, missing, and unknown
values; and keep this audit-gate defect separate from product comparison findings.

### CMP-AUD-162 — the Highway Sequence conservation gate assumed printed and physical PDF page numbers were one-to-one

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` page-header reconciliation

The first source parser required every data page's printed `Page N` to equal physical PDF
page index minus the cover. D01 violates that assumption at physical page 9. The fail-fast
is correct—page ownership cannot be guessed—but the equality rule was not source-proved.
Printed pagination can legitimately reflect report groups, Oracle report pagination, or
other vendor structure while the physical PDF still remains complete.

Correction requirements: visually/textually inspect pages around every pagination break;
derive and bind the actual per-member printed-page sequence; require every physical data
page to carry exactly one parseable page claim; record resets/repeats/jumps as an explicit
anomaly manifest rather than discarding them; mutation-test missing, malformed, moved,
and out-of-contract claims; and keep physical page identity independently authoritative.

### CMP-AUD-163 — the first Highway Sequence detached acceptance serialized volatile output filesystem identity

Priority: P1  
Status: Resolved in the accepted deterministic detached acceptance  
Primary code: `build/phase6_highway_sequence_conservation.py` detached acceptance writer

The first completed HSL acceptance embedded the newly written result's full filesystem
identity, including `mtime_ns`, device, and inode. Replacing the same deterministic JSON
on a second run can change those attributes even when path, byte length, and SHA-256 are
identical, so the acceptance document itself needlessly becomes non-deterministic. This
would weaken the required byte-for-byte replay proof and make an unchanged audit look
different after a restart.

Correction requirements: use full descriptor/path identity internally while the run is
active, but persist only stable canonical path + byte length + SHA-256 in detached
acceptance; apply that stable projection consistently to result, code, sources, workbook,
sidecar, and lifecycle witness; mutation-test that mtime/device/inode changes do not alter
the persisted projection while size/hash changes do; then require two full result and
acceptance writes to be byte-identical.

### CMP-AUD-164 — the Highway Sequence conservation gate recorded partially asserted page-header and PDF-metadata claims

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` document/page claim parser

The first completed oracle stored every data page's `report_date` as `15-SEP-25` without
first requiring that exact top-left token; it checked only the separate `Ref Dt` value.
It also accepted a page whenever the set of owner headers had one value, which would let
two identical duplicated `DIST/RTE/DIR` headers pass, and it recorded PDF metadata after
checking only title plus the CreationDate prefix. Those are audit-gate defects: persisted
source facts must be extracted and exactly asserted, never filled from expected constants
or accepted under duplicate presence.

Correction requirements: extract exact-one report ID, title, report date, reference date,
time, printed page, and owner header claims on every data page; reject duplicate identical
headers as well as missing/conflicting ones; assert exact Creator/Producer/Author/Title and
member-specific CreationDate/ModDate claims; mutation-test missing/duplicate/wrong values;
then rerun all 1,540 pages twice and require deterministic result/acceptance hashes.

### CMP-AUD-165 — the Highway Sequence hardening draft generalized member-specific creation and generation times

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` PDF metadata and page-header validators

The first CMP-AUD-164 correction draft required a generic `D:20250915` plus six-digit
CreationDate and accepted any syntactically valid printed generation time. That rule
would reject the authentic District 12 metadata value `D:20250915150325Z`, while a
different district's otherwise valid CreationDate or printed time could be substituted
without detection. The already hash-bound PDFs make those values immutable source facts;
the independent gate must nevertheless prove the extracted claim belongs to the correct
member instead of merely fitting a broad pattern.

Correction requirements: bind each of the 12 source roles to its exact CreationDate,
ModDate, and printed generation time; require the same exact printed time on every data
page for that member; mutation-test missing,
duplicate, wrong-format, valid-looking wrong-member, and District-12 trailing-`Z` cases;
then include the exact extracted values in both deterministic full-corpus replays.

### CMP-AUD-166 — the Highway Sequence hardening draft assumed every authentic PDF had identical creation and modification timestamps

Priority: P1  
Status: Resolved in the accepted Stage-6 Highway Sequence oracle  
Primary code: `build/phase6_highway_sequence_conservation.py` per-member PDF metadata validator

The first exact-member correction still assumed `CreationDate=ModDate` for all 12 PDFs.
The authentic, hash-bound District 12 source instead carries CreationDate
`D:20250915150325Z` and ModDate `D:20251121111252-08'00'`; the full parser stopped on
that real source fact after 11 documents passed. A universal equality rule would erase
or falsely reject a genuine provenance claim. This is an audit-gate defect, not evidence
that the District 12 source may be normalized to another member's convention.

Correction requirements: bind and preserve the exact CreationDate and ModDate pair for
each source role independently; retain equality for the 11 members where it is factual
and the exact later, offset-bearing District 12 modification claim where it is factual;
mutation-test swapped, changed, missing, and syntactically plausible wrong pairs; then
restart both required full-corpus deterministic replays from the beginning.

Resolution for CMP-AUD-160 through CMP-AUD-166: the final independent gate passes all
22 invariants and 14 semantic mutations, binds 47 loaded parser modules, and replays all
1,540 pages twice to byte-identical outputs. Final result: 1,276,684 bytes, SHA-256
`bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2`;
detached acceptance: 5,934 bytes, SHA-256
`71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2`.
These resolutions harden the audit mechanism only. CMP-AUD-155/156/158/159 remain
verified product defects with zero unexplained residue outside their exact dispositions.

### CMP-AUD-167 — the first Highway Log visual-sampling command silently omitted every midpoint page

Priority: P1  
Status: Resolved in the accepted exact 36-role visual-source manifest  
Primary code: one-off Stage-6 Highway Log PDF-render sampling command and its output census

The first render command used `[math]::Ceiling()` midpoint values directly with the
integer-only PowerShell `D3` filename formatter. Each midpoint iteration raised a
non-terminating format error, but the overall command still exited zero and produced
only first/final samples: 24 PNGs instead of the intended 36. Accepting the command's
terminal status would falsely claim a complete visual sample while omitting every
document midpoint.

Correction requirements: cast midpoint page numbers to integer before formatting;
derive the exact expected `(district, first, midpoint, final)` filename universe from the
bound page counts; reject missing, extra, or duplicate render roles independently of the
renderer exit code; inspect all 36 images before any visual-pass claim; retain this red
attempt as audit-harness evidence rather than counting it toward acceptance.

### CMP-AUD-168 — the Highway Log visual-sample filename census admitted stale-prefix page overwrites

Priority: P1  
Status: Resolved by the fresh exact source/page/name/image manifest and review  
Primary code: one-off Stage-6 Highway Log PDF-render sampling command and manifest check

The non-terminating midpoint format error left the prior `$prefix` value live. The
renderer therefore wrote a midpoint page under a nominal first-page filename before the
corrected command added the missing midpoint name. The resulting directory had all 36
expected filenames, but at least District 2's nominal page 1 and page 75 images were
visibly identical page-74 content. A name-only universe check cannot prove that a render
artifact came from its claimed source page.

Correction requirements: preserve the red directory; render all 36 roles from scratch
into a new output directory with the integer page and output prefix constructed together;
persist an exact source-PDF/page/output-name/image-byte-digest manifest; reject preexisting
members, missing/extra roles, failed renders, and same-document role aliases; visually
inspect the fresh 36-image universe before resolving either visual-harness finding.

### CMP-AUD-169 — the default independent XLSX event ceiling rejects the authentic Highway Log workbook

Priority: P1  
Status: Resolved by the explicit bounded family limit and retained default-limit red proof  
Primary code: `build/phase3_xlsx_stream.py` Stage-6 invocation contract

The first exact-schema read of the accepted r7 Highway Log workbook stopped with
`XlsxSecurityError: XLSX XML exceeds the event limit`. The file is the bound authentic
6,663,062-byte workbook with 60,083 data rows and 32 columns, but the reader's generic
five-million-event default is below this family's legitimate worksheet event volume.
The fail-closed default is appropriate for generic callers; the defect is an audit gate
that invokes this unusually wide corpus without an explicit, still-bounded family limit.
Without correction, Stage 6 can never examine the workbook and could be mistaken for a
source/parser failure.

Correction requirements: retain the rejected default-limit reproduction; declare a
Highway-Log-specific `XlsxLimits` ceiling sized above the measured authentic workload
without disabling any archive, XML-depth, cell-text, row, or column guard; prove the
exact workbook reads under that ceiling; mutation-test that a lower ceiling still rejects
and that oversized or malformed inputs remain fail-closed; bind the selected limits in
the result and detached acceptance artifacts.

### CMP-AUD-170 — the first Highway Log synthetic negative conflated classified and unexplained residues

Priority: P1  
Status: Resolved in the permanent classified-versus-unexplained mutation gate  
Primary code: `build/check_phase6_highway_log_conservation.py`

The first negative projection fixture changed a Location cell while retaining the
fixture's independently expected whitespace-versus-production-comma Description delta.
The comparison therefore contained two mismatches: one already classified punctuation
residue and one unexplained Location mutation. The gate incorrectly required an
`unexplained_count` of two and failed. Treating total mismatches and unexplained residue
as interchangeable would make the acceptance vocabulary internally inconsistent and
could later encourage an overbroad allowlist.

Correction requirements: assert the three quantities independently—two total typed
mismatches, one exact classified comma residue, and one unexplained mutation; retain the
red assertion output; add a clean one-comma fixture and an unrelated-cell mutation so a
future classifier cannot absorb the latter.

### CMP-AUD-171 — Highway Log invariant failures discard the completed full-corpus diagnostic

Priority: P1  
Status: Resolved by isolated atomic rejected-diagnostic publication  
Primary code: `build/phase6_highway_log_conservation.py`

The first complete run independently parsed all 12 authoritative PDFs and 60,083 data
rows in 828.7 seconds, then correctly stopped on four false invariants. The oracle built
the projection comparison, classified residue, totals reconciliation, document census,
and mutation results in memory, but raised before constructing or atomically writing the
result document. No diagnostic artifact remained. The terminal output preserved only
per-district row/total counts and the four invariant names; it did not preserve the exact
mismatch rows, field census, fragment classes, digests, or arithmetic evidence needed to
separate a product defect from an audit-gate defect. Re-running an authoritative corpus
must not be the only way to recover already computed failure evidence.

Correction requirements: add an explicit diagnostic output path whose atomically written
document is produced on terminal invariant failure, is unambiguously marked rejected,
contains every computed invariant input and failed-name list, and can never satisfy or
overwrite the accepted-result contract. Mutation-test failed-write cleanup, rejection
vocabulary, accepted-result isolation, and serialization of typed mismatch examples.
Retain fail-closed process status and publish no detached acceptance for a diagnostic.

### CMP-AUD-172 — the Highway Log exact-total invariant retained the pre-hardening classifier census

Priority: P1  
Status: Resolved by the exact 13,549-claim statewide/per-document typed census  
Primary code: `build/phase6_highway_log_conservation.py`

The full run's per-district terminal census totals 13,550 typed total claims, with zero
unclassified lines and zero unparsed totals in every district. The invariant still pins
`total_claim_lines` to 13,509, the earlier classifier's total count before exact fragment
classes were added. Both `every_source_line_classified` and
`totals_claim_universe_typed` therefore fail even though every document's independent
physical-line accounting succeeds. The difference is 41, not an assumed 40; the prior
crawl had 40 unclassified lines, so the additional one-claim movement must also be
explained before freezing the corrected census.

Correction requirements: persist and inspect the complete current line/kind/fragment
census; account for every reclassified physical line, including the forty formerly
unclassified fragments and the additional one-claim movement; bind exact per-document
and statewide kind/fragment manifests rather than merely changing the scalar to 13,550;
and add mutations for a claim moving between Description, typed total, unparsed total,
and unclassified roles. No projection mismatch may be waived as part of this correction.

### CMP-AUD-173 — the Highway Log audit's broad `LENGTH` fragment rule steals an authentic Description

Priority: P1  
Status: Resolved by exact fragment grammar and bound D03 Description evidence  
Primary code: `build/phase6_highway_log_conservation.py`

The independent parser classifies every below-band line beginning `LENGTH ` as a
`volume_length_fragment`. That broad prefix consumed the authentic D03 page 126
Description `LENGTH PARTLY IN NEV CO`, printed immediately below Route 080 location
`R058.351`. The accepted normalized workbook correctly retains that text at source row
12,129. This one misclassification explains the unexpected extra total claim: the
hardened diagnostic reported 13,550 totals and 23,096 Description lines instead of
13,549 and the pre-existing 23,097 line count.

Correction requirements: recognize a volume-length fragment only from its structural
numeric/DVM grammar and totals geometry, never from the word `LENGTH` alone; restore the
exact D03 Description with raw member/page/line provenance; freeze a negative fixture for
`LENGTH PARTLY IN NEV CO` and positive fixtures for every authentic split `Length N DVM
M` form; require exact full-corpus projection after all other source roles are
dispositioned.

### CMP-AUD-174 — the Highway Log audit attaches three printed dash separators as segment Descriptions

Priority: P1  
Status: Resolved by the exact three-marker source manifest and blank disposition  
Primary code: `build/phase6_highway_log_conservation.py`

Exactly three printed lines contain 23 hyphens in the Description band: D02 page 112
after Route 273/`015.978`, D07 page 181 after Route 110/`024.574`, and D12 page 66 after
Route 091/`R003.871`. The production TSN parser deliberately recognizes punctuation-only
separator lines and maps them to a blank Description. The independent oracle instead
attached each line to the preceding record, creating three false Description mismatches.
They are nevertheless exact raw source roles and cannot disappear from a raw-to-target
audit merely because their normalized semantic disposition is blank.

Correction requirements: classify the exact dash-only domain as a distinct printed
Description separator/blank-marker role before Description attachment; bind its exact
three-member/page/row manifest and digest; give that role one explicit normalized-blank
disposition; reject near-dash feature text, moved markers, extra markers, and markers
outside the Description band; require all three target Description cells to remain null.

### CMP-AUD-175 — the Highway Log acceptance contract assumes a comma residue absent from the authoritative corpus

Priority: P1  
Status: Resolved by exact zero-residue projection and the retained synthetic wrap negative  
Primary code: `build/phase6_highway_log_conservation.py` and its detached acceptance

The oracle and detached acceptance hardcode `projection_exact: false` because production
joins multiple Description baselines with comma-space while the independent truth joins
with whitespace. The authoritative all-12 corpus has no multi-baseline Highway Log
Description: the exact observed multiplicity is 36,987 zero-line records and 23,096
one-line records in the red diagnostic, with maximum one. After correcting CMP-AUD-173
and CMP-AUD-174 that becomes 36,989 zero-line and 23,094 one-line records, still maximum
one. There is therefore no real comma residue to accept. Synthetic multi-line behavior
remains worth testing, but it cannot be asserted as an observed corpus defect.

Correction requirements: require ordered and multiset projection exactness for the
bound corpus and require zero classified/unexplained residue; set accepted result and
detached-acceptance flags from that proved fact; keep the synthetic multi-line fixture so
a future wrapped source exposes production punctuation rather than being silently
allowed; never convert that hypothetical into a current source allowlist.

### CMP-AUD-176 — Highway Log totals reconciliation uses the wrong continuity and pairing boundaries

Priority: P1  
Status: Resolved by exact owner/reset progression and all-2,905 FIFO pairing manifests  
Primary code: `build/phase6_highway_log_conservation.py::_reconcile_totals`

The first totals reconciliation keyed `County Cumulative DVM` continuity by repeated
`(district, county, route, qualifier)` text across the whole document. The same owner
header can recur as a new physical block whose cumulative counter restarts, and fifteen
printed zero-DVM/zero-cumulative claims explicitly reset a block. The result reported
1,067 failures across 7,024 supposedly assessable intervals, including 79 non-unit
deltas and an impossible 5,205,844 maximum. A physical-owner-occurrence analysis plus
the printed zero/zero reset rule removes every non-unit delta; the remaining provisional
residue is only the printed per-line rounding domain (`-1`, `0`, or `+1`).

The same function pairs a mileage summary only with an immediately following DVMS claim.
Fourteen authentic summaries occur at page bottoms with ordinary volume claims before
their DVMS continuation. The gate called them unpaired. A FIFO pending-summary analysis
pairs all 2,905 summaries to exactly one DVMS/overflow claim, with page gaps zero through
two. Worse, the acceptance invariant checked only total claim count, so neither the
1,067 reconciliation failures nor the 14 missing pairs could stop publication.

Correction requirements: carry an exact physical owner-header occurrence ordinal into
every row and total claim; scope progression to that occurrence; type and bind every
zero/zero reset; classify exact `±1` arithmetic residue as printed rounding and reject
all larger deltas outside reset/fragment boundaries; pair summaries FIFO across
interposed volume rows without crossing documents; require all summaries paired exactly
once; and make every reconciliation terminal count/digest an acceptance invariant with
deletion, reorder, reset, rounding, and cross-owner mutations.

### CMP-AUD-177 — Highway Log raw-role disposition coverage is self-referential

Priority: P1  
Status: Resolved by the independent 50-role source universe and global mutations  
Primary code: `build/phase6_highway_log_conservation.py::_field_coverage`

`_field_coverage()` defines its expected raw-role set as
`set(FIELD_DISPOSITIONS)`. The default table therefore proves itself complete: deleting
a role from the global table also deletes that role from the expected universe. Existing
missing-role tests pass only because they mutate a copy while the unchanged global table
continues to serve as expectation. The newly discovered Description-separator role was
absent from both sides and the gate still reported exact coverage.

Correction requirements: define an independent, explicit raw-role universe derived from
the parser's row, identity, aggregate, structural, provenance, and blank-marker outputs;
compare dispositions against that universe; bind exact one-target coverage for all 32
normalized columns; reject global-table deletion/addition/rename as well as copied-table
mutations; and include the owner-header occurrence plus Description separator roles.

### CMP-AUD-178 — Highway Log sidecar semantics under-assert the bound raw and normalized identity contract

Priority: P2  
Status: Resolved by the exact sidecar/raw/workbook schema, token, and manifest gate  
Primary code: `build/phase6_highway_log_conservation.py::_validate_sidecar`

The full audit binds the accepted 2,521-byte sidecar by exact SHA-256, so its present bytes
cannot mutate unnoticed. Its semantic validator nevertheless checks only completion,
counts, member rows, normalization version, and normalized workbook identity. It ignores
the sidecar/root key universes, raw-manifest version, algorithm, serialization grammar,
root scope, exact manifest SHA-256, normalized artifact identity token, and build-time
field type. No permanent Highway Log fixture mutates these claims. A hash binding proves
identity of this one artifact; it does not prove that the audit understands every field
it cites as a source-to-normalized contract.

Correction requirements: assert the exact sidecar and raw-manifest key universes; bind
version/algorithm/serialization/root scope, the exact independently known raw-manifest
SHA-256, normalized workbook identity, artifact token, and build-time type; mutation-test
each field plus missing/extra roles and cross-field inconsistency; retain the outer
sidecar byte binding as an independent guard.

### CMP-AUD-179 — Highway Log totals pairing mislabels and does not terminally bind 47 continuation/fragment claims

Priority: P1  
Status: Resolved by the exact 35-claim continuation ledger and numeric-fragment exclusion  
Primary code: `build/phase6_highway_log_conservation.py::_reconcile_totals`

The corrected candidate paired every one of 2,905 complete mileage-summary lines, but
reported 47 additional claims as orphan DVMS continuations without making that census an
acceptance invariant. Twelve are `numeric_total_fragment` lines and are not DVMS
continuation candidates at all; they belong only to the exact fragmented-total source
universe. The remaining 35 are 27 explicit `(DVMS)` lines plus eight blank/overflow DVMS
fragments that follow physically incomplete or split total-summary layouts. Their raw
text is conserved, but calling them orphans suggests an unexplained parser failure and
allowing any count/hash to pass leaves deletion or reclassification undetected.

Correction requirements: restrict complete-summary pairing candidates to actual
DVMS/within-District claims and their exact blank/overflow forms; retain all 12 numeric
fragments solely in the typed fragment ledger; rename the remaining 35 as explicitly
unassociated continuation claims rather than inferring missing summary semantics; bind
their exact kind census and manifest SHA; mutation-test add/delete/retype/reorder; and
make the exact count/hash terminal alongside all-2,905 complete-summary pairing.

### CMP-AUD-180 — Highway Log records but does not terminally bind or stability-check its loaded PDF parser modules

Priority: P1  
Status: Resolved by exact pre/post 47-module identity and digest contracts  
Primary code: `build/phase6_highway_log_conservation.py::_loaded_module_manifest` and `run`

The candidate result records an exact 47-member `pdfplumber`/`pdfminer` source-module
manifest (SHA-256 `d9e0ea...fe5d`), but no invariant requires that count or digest. The
tracked-code stability check covers the oracle, gates, generic XLSX reader, and visual
sampler only. It also captures the dependency manifest once, after parsing, so a parser
module file changing during the 13-minute raw crawl is not detected. The result can
therefore say accepted while the dependency provenance it displays is incomplete or
unstable.

Correction requirements: capture the loaded parser-module manifest before and after the
source crawl; require exact equality plus the independently frozen 47-member digest;
persist the stable manifest; reject missing/extra/changed/reordered member projections;
and make the module contract a terminal invariant and permanent synthetic fixture.

### CMP-AUD-181 — Highway Log displays but does not terminally bind its full physical-key collision census

Priority: P1  
Status: Resolved by the frozen four-domain collision census and mutations  
Primary code: `build/phase6_highway_log_conservation.py` collision census and invariants

The candidate result records four complete key/multiplicity censuses, but the only
terminal assertion is that adding an occurrence ordinal makes the final key unique. A
parser can drop or change district, county, owner qualifier, Location, or roadbed context
while still assigning a new ordinal to every row. The authentic weaker domains are
material: route+Location has 798 collision groups/1,725 rows/max 10; adding roadbed still
has 508/1,109/max 10; the full physical owner key has 77 groups/156 rows/max four. None
of those counts, histograms, ordered digests, or multiset digests could stop candidate
acceptance.

Correction requirements: freeze every census field for all four key domains, including
row/distinct/duplicate/affected/max counts, multiplicity histograms, ordered digests, and
multiset digests; require exact equality terminally; mutate each identity component,
occurrence order, duplicate count, and roadbed classifier; retain final uniqueness as one
claim inside the stronger exact census rather than the whole proof.

### CMP-AUD-182 — Highway Log computes decisive source manifests without comparing them to frozen oracle values

Priority: P1  
Status: Resolved by frozen dataset/document manifests and two byte-identical full replays  
Primary code: `build/phase6_highway_log_conservation.py` dataset/document manifests and invariants

The candidate serializes typed ordered/multiset/per-field digests for the 39-column raw
row source, 12-column provenance, 14-column totals, 15-column Description separators,
nine-column document metadata, both projected row variants, and the normalized workbook.
It also serializes each document's page-header, owner-header, separator, and total-claim
manifests. Acceptance compares projection and several scalar censuses but never compares
these decisive source manifests to frozen oracle values. A deterministic parser shift in
source-only ADT, owner occurrence, raw totals text/value, or provenance can therefore
produce a different displayed digest and still pass. Mutation probes prove only that a
digest changes when input changes; they do not establish which digest is true.

Correction requirements: freeze and terminally compare every dataset's row/column count,
ordered typed digest, and multiset typed digest; freeze every per-document role manifest;
bind the exact global three-separator manifest; require projected/production/normalized
digests to be identical; mutation-test swapped fields/roles and expected-digest changes;
and restart deterministic replays after the final constants and code identities are
fixed.

Accepted closure evidence: the final 34-invariant/53-mutation result is 10,879,397
bytes, SHA-256 `f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4`;
its detached acceptance is 6,502 bytes, SHA-256
`012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61`.
Fresh 822-second and 823-second all-2,121-page replays produced byte-identical copies of
both files. All D01-D12 runs retained 60,083 rows, 13,549 typed totals, zero
unclassified/unparsed lines, exact projection, eight frozen dataset contracts, the
four-domain collision census, 12 document manifests, and the exact pre/post 47-module
parser manifest. CMP-AUD-167 through CMP-AUD-182 are audit-gate closures only;
CMP-AUD-045 and CMP-AUD-157 remain product-red and are not allowlisted away.

### CMP-AUD-183 — Intersection Summary aggregation accepts dropped and duplicate routes without validating its route universe

Priority: P1  
Status: Resolved 2026-07-14 — route universe validated + producer census reconciled; real-data verified  
Primary code: `scripts/compare_intersection_summary_tsn.py::_load_tsmis/_load_pair` and
`scripts/consolidate_intersection_summary.py::consolidate`

The exact positive control is 217 ordered, unique route identities across both TSMIS
Excel and PDF, with suffix routes `008U`, `010S`, `014U`, `058U`, `178S`, and `210U`;
route 170 is absent in both source formats. Production reproduces that universe on the
current clean run but does not require it for comparison completion. An isolated copy
with route 905 deleted was accepted and changed the statewide total from `16459` to
`16458`. A copy with route 001 duplicated was also accepted and changed the total to
`17752`. Neither path returned a missing/duplicate-route diagnostic.

This is not CMP-AUD-071: that finding and its 126-route contract are explicitly scoped
to Ramp Summary. Intersection needs its own source-bound universe because its input,
suffix set, expected count, and positive canary are different.

Correction requirements: persist and validate the discovered ordered route identities;
reject blank, malformed, duplicate-identical, duplicate-conflicting, dropped, extra,
reordered, and suffix-collapsed routes; reconcile the exact producer/source manifest
before statewide aggregation; surface the route census in structured comparison
diagnostics; and permanently bind the 217-route Excel/PDF positive control plus each
mutation above.

**Remediation (2026-07-14).** Producer side: `consolidate()` refuses blank/
malformed route identities per file (FAILED, loud), excludes EVERY claimant of a
duplicated route identity (both files FAILED, PARTIAL — identical duplicates
would double-count and conflicting ones cannot be arbitrated), and persists the
ordered `route_census` via the new generic `ConsolidateResult.producer_extra` →
`write_outcome(extra=…)` path (cli, gui_worker_export ×2, matrix_build now pass
it through). Comparison side: `_load_tsmis` always validates internal soundness
(usable route identity per data row, no route on more than one row, non-empty
universe) and, whenever a census is recorded beside the workbook, requires the
aggregated routes to match it EXACTLY (dropped/extra/renamed/reordered/
suffix-collapsed all refuse with the first divergence named); the census status
is surfaced as a familiar-sheet note + log line. Real-corpus positive control:
the ars-prod 7.9 tree consolidates to the exact 217-route census (suffixed
008U/010S/014U/058U/178S/210U; 170 absent), the comparison census-verifies with
the oracle unchanged (58/8/0 · 5/53), and the finding's two isolated mutations
(route 905 deleted; route 001 duplicated) now REFUSE on a sidecar-coupled copy.
Fixtures: `check_compare_intersection_summary_tsn.test_route_universe` (13
mutations incl. census-less diagnostics) + the consolidator duplicate/census
checks in `check_consolidate_intersection`. Honest scope limits: a workbook
whose sidecar is absent (older consolidation, or a copy without it) keeps
internal checks only and gets an EXPLICIT no-census diagnostic — hardening to
require the census needs a matrix auto-rebuild migration (roadmap follow-up);
surfacing the census through the TYPED comparison contract (LoadedSide claims)
stays with the Phase-5/7 overlay work; Ramp Summary's separate 126-route
contract remains CMP-AUD-071.

### CMP-AUD-184 — Intersection Summary's familiar view note contradicts its structural-absence cells and cites Ramp categories

Priority: P2  
Status: Resolved 2026-07-14 — the shared note now states the blank/one-sided truth; Ramp example removed  
Primary code: `scripts/summary_layout.py::make_extra_sheet_writer` and the Intersection
Summary familiar-view note configuration

The familiar Intersection Summary sheet correctly leaves the TSN and delta cells blank
for all eight structurally TSMIS-only categories. Its explanatory line nevertheless says
categories one system does not classify “show 0 on that side” and illustrates the claim
with “TSN-only ramp types P / V,” which are Ramp Summary concepts. A reviewer can
therefore read the right blank cells under a false zero-fill rule and an irrelevant
family example. This does not change the generic Comparison sheet's correct one-sided
statuses, but it makes the report-view contract self-contradictory.

Correction requirements: make the familiar note family-specific; say that structural
absence remains blank and one-sided, distinguish an explicit source zero from absence,
remove the Ramp P/V example, and mutation-test every one-sided Intersection category in
both formulas and values views so note, cells, delta, and generic status agree.

**Remediation (2026-07-14).** The shared `_render` note line now states what the
cells actually do: "A category one system doesn't classify stays BLANK on that
side (no Δ) and is listed under 'Only in …' in the Comparison sheet; an explicit
0 is a real source zero" — no zero-fill claim, no cross-family example (the
family-specific detail rides each spec's own `notes`, which for Ramp already
names P/V and for Intersection the signal fold/roundabout). New
`test_one_sided_familiar_agreement` sweeps ALL 8 TSMIS-only Intersection
categories with non-zero counts through mode="both": familiar row shows
value/BLANK/BLANK in the formulas AND values workbooks (section-scoped lookup —
several blocks share the '+ - NO DATA GIVEN' label) and the generic Comparison
marks each 'TSMIS only'. The Ramp check asserts the same note truth plus the
P row rendering BLANK/5/BLANK. Real-corpus re-verify: both oracles unchanged
(29/0/2·5·24; 58/8/0·5·53) and the regenerated real workbook carries the
corrected note.

### CMP-AUD-185 — Ramp Detail omits District and hides a real District disagreement as identical

Priority: P1  
Status: Resolved 2026-07-14 — District is a compared field on every RD leg; the 005/SD/72.366 disagreement now surfaces; re-blessed  
Primary code: `scripts/compare_ramp_detail_tsn.py::SHARED_HEADER/_raw_tsn_row/
_tsmis_row/_normalized_row`, inherited by
`scripts/compare_ramp_detail_pdf.py::_RampDetailFileCompare`

The authoritative raw TSN XLSX, its 500-data-page PDF, and both current TSMIS
representations expose District. Under the approved physical identity
`(Route, County, norm_pm(PM))`, exactly one paired row disagrees on that asserted field:
`005/SD/72.366` is District `12` in TSMIS Excel row 338 and TSMIS PDF page 11 row 13,
but District `11` in raw TSN row 13,250. Every other asserted value on that paired row
is equal. This is source data, not a parser inference: both TSMIS forms agree with each
other, both TSN forms map the same record, and the accepted raw-to-normalized chain
retains the TSN District in its sidecar.

Production's `SHARED_HEADER` contains neither District nor County. All Ramp Detail
PDF/Excel/raw/normalized comparisons inherit that projection, so the row appears with
`Diffs = 0` and all visible states equal/non-asserting. Consequently production reports
861 cells instead of the independent Excel-vs-TSN 847 and 1,012 instead of the
independent PDF-vs-TSN 998: each includes 15 false Description-prefix differences from
CMP-AUD-135 while omitting this one real District difference, for a net inflation of
14. Raw and normalized product runs are identically wrong. PDF-vs-Excel correctly has
no District difference because both TSMIS forms say 12, but it still fails to show and
assert that agreement.

This is distinct from CMP-AUD-045. That finding makes County part of row identity and
prevents cross-county mispairing; District is a separately visible, source-backed
asserted field whose disagreement must count after correct pairing. It also extends
CMP-AUD-133's requirement that normalized sidecar facts remain usable by the comparison
and evidence layers rather than being evidence-only metadata.

Correction requirements: project District from TSMIS Excel, TSMIS PDF, raw TSN, and
normalized TSN into one typed, visible, compared field on every Ramp Detail triangle
leg; retain County as the separate CMP-AUD-045 key component and visible provenance;
reject missing/malformed/conflicting District/County claims instead of blank-filling;
make the normalized sidecar participate in the comparison projection without allowing
it to override raw claims; preserve District through Comparison, Report View, snapshots,
counts, diagnostics, and evidence; bind the exact `005/SD/72.366` positive disagreement
and same-source PDF↔Excel agreement; mutate District independently on each source/format;
and require corrected production counts to equal the accepted source oracle rather than
the pre-fix 861/1,012 canaries.

**Remediation (2026-07-14, with the RD family batch).** `District` joined
`SHARED_HEADER` as a compared field on every Ramp Detail path (from each
source's Location; from the library's District sidecar on the normalized path)
and in the evidence adapter's FIELDS/maps (the print Location column / LOC
window). Re-blessed: every leg reports exactly the oracle's District 1 — the
`005/SD/72.366` TSMIS-12-vs-TSN-11 disagreement is now visible instead of an
"identical" row.

### CMP-AUD-186 — Highway Detail truncates multi-baseline line-two records as complete

Priority: P1  
Status: Verified on the frozen current 7.9 TSMIS PDF/Excel pair  
Primary code: `scripts/consolidate_tsmis_highway_detail_pdf.py::_row_groups/parse_pdf`

The current `highway_detail_route_395.pdf`, physical page 4 / printed page 1, contains
one visibly four-baseline line-two record at `08 SIE 395 / R000.000E`. Its Description
is the complete printed sequence beginning `KERN/INYO CO LINE / BEGIN RT INDEP ALIGN`
and ending `END INDEP ALIGN=CO LINE`. The later baselines on that same logical row also
carry all left-roadbed, median, and right-roadbed values. The same-pull Excel row 3
contains that full Description plus LB Eff `86-08-07`, LB `H/02/Z/10/10/24/05/05`,
Med `76-11-24/K/7/Z/99P`, and RB
`76-11-24/H/02/Z/05/05/24/10/10`.

Production treats the first physical baseline after line one as the entire line two,
immediately clears `pending_1`, and has no continuation ledger. Direct parsing emits
only `KERN/INYO CO LINE / BEGIN RT INDEP ALIGN / BEGIN LT INDEP ALIGN / BEGIN RT INDEP`
as Description and blanks every one of the 23 printed attribute cells. The remaining
Description/attribute baselines are ignored. Nevertheless `parse_pdf` reports 1,192
emitted rows, 86 pages, `orphans=0`, `single_line=0`, and no fallback pages; consolidation
therefore certifies the corrupted row as complete.

The independent Stage-8 oracle was corrected only after this finding was recorded. Its
route-395 replay reconstructs 1,192 Excel and 1,192 PDF rows, pairs every row, and matches
all 34 cells exactly with zero unclassified groups. The PDF census contains exactly one
multi-group logical line two made from three physical groups; that positive source proof
does not remediate the production parser and this finding remains product-red.

This is the Highway Detail analogue of CMP-AUD-056's Intersection wrap defect, but it
is independently owned because the parser, record layout, and current real-source
canary differ. It is also distinct from CMP-AUD-053: this row does have a line-one
partner; the failure is premature completion followed by invisible continuation loss.

Correction requirements: retain a logical line-two record until the next proved line
one, DCR boundary, or document end; merge every continuation baseline into its cell by
printed geometry and reading order; distinguish description overflow from attribute
wraps; reconcile every data-area word/character exactly once; preserve continuations
across physical-page boundaries; and return partial/failed for any unexplained fragment.
Bind the exact route-395 current row as a positive canary, plus synthetic wraps in every
line-two cell, simultaneous multi-cell wraps, header-like continuation text, and a
continuation whose first token resembles a post mile. The corrected product row must
equal both the visible PDF and the same-pull Excel row cell-for-cell.

### CMP-AUD-187 — independent oracle builds statewide key order quadratically

Priority: P2  
Status: Verified in the audit harness before correction  
Primary code: `build/phase3_independent_oracle.py::compare_rows`

`compare_rows` stores first-seen canonical keys in a list and tests every new row with
`key not in order`. Highway Detail raw-versus-normalized has nearly 60,000 distinct
physical keys, so this otherwise linear grouping step becomes quadratic. A measured
60,083-by-60,083 reproduction spent 46 seconds reading/digesting raw TSN, another 46
seconds reading/digesting normalized TSN, and 746 seconds in comparison. It still
returned the correct 60,083 pairs and sole Length difference, but repeating that path
for five Stage-8 legs would make adversarial replay needlessly fragile and expensive.

Correction requirements: use a set solely for first-seen membership while retaining the
existing list for deterministic encounter order; do not alter canonical keys, row order,
duplicate minimum-cost assignment, caps, counts, or diagnostics; prove the optimized
path byte-for-byte/count-for-count equivalent to the existing oracle over unique keys,
duplicates, one-sided groups, reordered groups, typed keys, and capped assignments; and
keep prior accepted artifacts bound to their original code identities rather than
silently pretending the dependency did not change. Stage 8 may use a local equivalent
indexed implementation until shared-oracle promotion is deliberately revalidated.

### CMP-AUD-188 — Highway Detail product witness was not resumable at committed-leg boundaries

Priority: P2  
Status: Remediated in the accepted Highway Detail Stage-8 artifact  
Primary code: `build/phase8_highway_detail_product_witness.py`

The first isolated Highway Detail witness ran both 252-member consolidations and all
five formulas-plus-values comparison legs inside one process, created its work root
with `exist_ok=False`, and wrote its only structured witness result after the fifth leg.
The execution wrapper reached its 3,601-second limit during the second comparison. The
process was gone afterward. Both consolidations and the first raw-TSN twin had already
been atomically committed, but no top-level result or caught-exception record existed;
the in-progress normalized files were only temporary. The original helper could neither
prove and reuse the committed leg nor resume in the existing root, so a wrapper timeout
discarded returned evidence disproportionate to the actual completed work.

The harness now checkpoints after every comparison leg and supports explicit
`--resume --leg`. Recovery is fail-closed: both canonical twins must be nonempty; both
outcome sidecars must declare the same complete/committed `both` generation; every
member path, byte length, and SHA-256 must match; every compressed payload chunk must
match its manifest; the decoded byte length and SHA-256 must match; and its structured
outcome must be complete with zero skipped/failed inputs. Temporary artifacts never
qualify. The already committed raw twin passed that entire recovery chain; the
interrupted normalized leg was rejected and restarted from its source inputs. The two
consolidations are reused only because the first successful comparison could not have
started unless each returned `ok`, and the final independent oracle still re-reads and
reconciles every consolidated cell against raw source truth.

Correction/acceptance requirements: complete and independently inspect all five legs;
bind every recovered or newly created artifact and the exact loaded product code; prove
one-sided, paired-cell, formula/value, snapshot, Report View, and source-consolidation
ledgers; reject all stale temporary members; then replay the final oracle twice against
the same frozen witness with byte-identical result bytes. Do not treat resumability as
permission to accept a partial family result.

Accepted resolution: all five legs, both consolidations, ten canonical workbooks, ten
sidecars, five payload chunks, and the exact artifact universe passed independent
post-write authentication with no temporary/failure residue. Two complete replays
produced byte-identical 3,384,044-byte results at SHA-256
`9d793fb166197701e20d8ac6bc8aa34bd64221a15507dff5bbe7416bc7095554`.

### CMP-AUD-189 — Highway Detail publication gate compares different duplicate-trace wire schemas byte-for-byte

Priority: P2  
Status: Remediated in the accepted Highway Detail Stage-8 artifact  
Primary code: `build/phase8_highway_detail_comparison.py:_product_expected`,
`_inspect_publication_pair`

The first full five-leg Highway Detail draft correctly failed closed, but its reason was
an audit representation mismatch rather than a proven product assignment error. The
production schema-v3 payload and the independent Phase-3 oracle both retained 851 exact
duplicate groups for Excel-vs-raw. Production serializes `key_components`, complete
side-index inventories, an assignment vector, per-pair costs, positional cost, and pair
objects; the independent trace serializes typed normalized `key` components and
`source_pairs`. The gate compared those different dictionaries directly. It therefore
rejected at group zero even though both described key `001 / 020.370`, a 1-by-2 matrix,
source pair `62 -> 66`, and total cost 3. Production's raw trace SHA-256 is
`9b7d642d5da0f7ed9bbc8cc8f92c58f1eafd2d3aaa2c2b614b2eb898bef89854`;
the independent wire-shape SHA-256 is
`db472529a04ca19e4bff84416d7cbd3976bf61e6ad582ee7df20662c124b88ac`.
Different hashes do not establish different assignments when the schemas differ.

Correction/acceptance requirements: project both traces into one audit-owned semantic
record containing normalized key text, matrix and side sizes, smaller side, exactness,
algorithm, total cost, and ordered source-index pairs; compare every semantic record and
freeze its digest. Separately validate every production-only field internally: exact
side-index censuses, matrix product, assignment-vector range/uniqueness and its mapping
to the emitted pairs, per-pair cost sum, and positional/total cost. Preserve both raw
wire digests as provenance. Mutation-test semantic pair/key/cost changes plus malformed
assignment vectors, side inventories, and costs. Never resolve this finding by dropping
the persisted trace check or trusting aggregate counts alone.

The semantic diagnostic then exposed six of 851 groups whose only remaining difference
was pair-list wire order. All six carried the identical pair set and identical optimum
cost: production orders pair records by smaller-side position so its assignment vector
is directly reconstructable, whereas the independent oracle returns comparison pairs in
side-A order. The live examples are routes/PMs `035/007.680`, `080/R058.712R`, and four
route-166 groups. The audit now canonicalizes the already validated source-index pair
mapping lexicographically by side A then side B before comparing it; it does not sort or
otherwise weaken the production vector/pair reconstruction check. The resulting
wire-order-neutral contract is locked by a 3-by-2 transposed-order fixture plus vector,
cost, inventory, semantic mismatch, chunk, generation, and member mutations. The
Highway Detail permanent gate later expanded to 79/79. Both accepted full replays prove
all five live semantic ledgers exactly, so this audit-harness finding is closed without
weakening the production trace or pairing contract.

### CMP-AUD-190 — Highway Detail formula/value gate requires source-sheet counts both different and equal

Priority: P2  
Status: Remediated in the accepted Highway Detail Stage-8 artifact  
Primary code: `build/phase8_highway_detail_comparison.py:_inspect_product_workbook`

The corrected full replay passed the first publication trace and then failed the
Excel-vs-raw workbook flavor contract even though every observed fixed census equaled
the independently derived expectation. The formulas workbook contains 358,912 formulas
on `TSMIS` and 420,582 on `TSN`; the values workbook intentionally retains 102,547 and
120,167 formulas on those sheets. Those are exactly `7 * source_rows + 1` versus
`2 * source_rows + 1`, as the same audit function declares. A leftover conjunction then
also required `formula_census[side] == value_formula_census[side]` for both sources.
The gate therefore demanded the counts be both unequal by exact formula and equal by a
second assertion. The exception handler correctly rejected the draft; this is an audit
predicate defect, not evidence that the workbook census drifted.

Correction/acceptance requirements: centralize the flavor predicate in a pure helper;
require exact sheet order and the complete independently calculated per-sheet census for
both flavors, plus the expected formula-rich relationship for Comparison and total
counts. Remove only the contradictory source-sheet equality clauses. Mutation-test a
valid deliberately different source-sheet pair and reject a one-count change in either
flavor, missing/extra/reordered sheets, collapsed formula/value totals, and a Comparison
sheet that is not formula-richer. Then replay all five live twins; do not replace exact
counts with a merely relative check.

The flavor predicate is now a pure audit helper. `Comparison` is also fully exact-bound:
every union row carries 39 formulas in the formulas flavor, while the values flavor
retains two formulas for each paired row and one for each one-sided row. Every other
sheet retains its independently derived exact formula count. The contradictory source
equality checks are removed; source sheets must instead be formula-richer and their exact
different counts must match. Seven new fixtures accept the deliberately different valid
pair and reject formula or values count drift, reordered or missing sheets, collapsed
source richness, and collapsed Comparison richness. The permanent gate later expanded
to 79/79; all five formula/value workbook pairs passed in both accepted full replays.

### CMP-AUD-191 — Highway Detail can classify but still leave 298 County-less Excel rows physically unattributed

Priority: P1  
Status: Remediated in the accepted Highway Detail Stage-8 oracle  
Primary code: `build/phase8_highway_detail_comparison.py:_analyze_excel_owner_constraints`,
Stage-8 terminal invariants

The first complete five-leg draft passed all 31 declared invariants, but that did not
establish full physical identity for every current TSMIS Excel row. The workbook package
contains no County claim. Exact companion-PDF signatures uniquely attest 50,751 of
51,273 rows, and a unanimous current companion-PDF owner at the observable
Route/PP/numeric-PM/roadbed key constrains another 224. The remaining 298 rows are still
unattributed: five have multiple companion-PDF owners, 287 have only a single TSN owner
that was correctly not promoted, one has multiple TSN owners, and five have no owner
candidate. Route 005 contains 296 of these rows and 005S contains two.

The draft invariant named `excel_owner_constraint_residue_fully_classified` requires
only that all rows receive a classification, the promoted-row count reconciles, pairing
finishes, and no TSN-only owner is promoted. Those are necessary controls, but they do
not require `unresolved_owner_rows == 0`. If the terminal completion flag were frozen on
that basis, the audit could describe the source oracle as complete while
`excel_vs_tsn_full_physical_truth_known` remained false. The draft was still rejected by
its intentionally unset Stage-8 completion flag, so no incomplete artifact was accepted.

Correction/acceptance requirements: do not use TSN to manufacture the missing TSMIS
owner. Test whether audit-owned Excel/PDF sequence alignment and exact companion anchors
can attribute an unmatched Excel interval to one printed DCR owner without crossing an
owner boundary; bind every promoted row, anchor, interval, owner, and rejection reason in
a deterministic ledger. Ambiguous boundary intervals remain unresolved. The terminal
gate must either prove zero unattributed Excel rows or explicitly keep full Excel
physical truth and Highway Detail Stage-8 acceptance false. Mutation-test a changed
anchor owner, removed anchor, boundary crossing, reversed interval, and a tempting
TSN-only candidate. Classification alone is never a substitute for attribution.

Accepted resolution: the first interval idea was not used as a substitute for source
evidence. Content-snapshot discovery instead found the exact same-build route-005
Excel/PDF pair, resolving all 3,125 route-005 rows at 34/34 rendered cells. Current
companion evidence resolves 48,143 exact rows and three unanimous-key rows; two final
005S descriptions receive owner-only attestation from their unique printed composite.
The final classification ledger accounts for 51,273/51,273 rows, reports zero unknown
County, promotes zero TSN-only candidates, and is frozen at SHA-256
`87f92d930dd33187502e60f1b6d7dbf8f52b2d532fc0b806efeeb87c54bfc49b`.

### CMP-AUD-192 — Highway Detail route-005 Excel is a stale 7.7 payload beside a later PDF whose DCR owner changed on eight identical rows

Priority: P1  
Status: Verified source-export delta; version-separated in the accepted Stage-8 oracle  
Primary evidence: current and historical `highway_detail_route_005.xlsx` plus both
versioned `highway_detail_route_005.pdf` files

The route-005 Excel file stored under the current 7.9 development tree is byte-for-byte
identical to the route-005 Excel file in the separately versioned 7.7 bundle: 3,812,860
bytes, SHA-256
`00a359555c964f46a68f36b32ae1a44501168eaee553911aa85838b9afef24c5`.
The audit-owned parser aligns that Excel payload to the 7.7 PDF at 3,125/3,125 rows,
all 34 rendered cells exact, no one-sided rows, and every row under one uniquely printed
DCR owner. The later 7.9 PDF is a distinct snapshot and has 3,070 parsed route-005 rows,
with 492 Excel-only and 437 PDF-only rows in the strict cross-format alignment.

An attempted historical owner bridge correctly failed closed because eight Excel rows
that are exact in both editions sit under different printed DCR owners in the two PDFs.
The row payloads did not change, but their owner claim did. Historical owner evidence
therefore cannot be treated as a timeless Route/Post-Mile lookup, and the later PDF
cannot silently relabel a byte-identical older Excel payload as if both came from one
snapshot. Conversely, rejecting the exact 7.7 companion while calling the copied Excel
file a 7.9 export would erase the only fully coherent source pairing.

Correction/acceptance requirements: bind Highway Detail members by actual content
snapshot, not folder label or filesystem timestamp. For route 005, use the byte-identical
7.7 Excel/PDF pair as the Excel member's same-build owner source and retain the later
7.9 PDF as a separate comparison snapshot. Preserve all eight cross-edition owner
changes in an exact ledger. Do not apply this exception to 005S: its current Excel bytes
differ from 7.7, so its current PDF plus explicit printed composite mapping must own that
edition. Mutation-test an Excel byte change, historical PDF row change, owner conflict
addition/removal, and an attempt to promote historical owners for a non-identical Excel
member. The final comparison/evidence surfaces must disclose rather than blend the
source editions.

Accepted disposition: the Stage-8 oracle applies exactly that versioned policy. Route
005 uses its byte-identical 7.7 Excel/PDF companion for Excel ownership, while the later
PDF remains an independent current-PDF comparison source. The eight owner changes are
frozen in ledger SHA-256
`45a306a0f2872883cc0c1410b759f5c185cd23d890c1af9cfc659a7ef397a747`.
The exception is not applied to 005S; its two otherwise unmatched rows use only the
current PDF composite owner attestation. CMP-AUD-192 remains a real source-export delta,
not a product or audit defect erased by acceptance.

### CMP-AUD-193 — Highway Sequence current parity can inherit a stale cross-bundle residual and omit July-9 Excel updates

Priority: P1  
Status: Current source correction proved; product publication, permanent gate, and final replay pending  
Primary evidence: route 037 PM `003.809` in the HSL 7.8 Excel, first 7.9 PDF bundle,
and current `All Reports 7.9` same-run Excel/PDF pair

The prior Highway Sequence PDF verification deliberately paired the July 8 Excel bundle
with the first July 9 PDF drop. In that cross-bundle pair, Excel row 31 at
`SON / 003.809 / HG D / FT R` has a blank Description while the PDF visibly prints
`037/WB ON FR SB RTE 121`. That historical Excel is 55,120 bytes at SHA-256
`1e9e18ab9b58e9c08c0182a0b438031615a4da055b399b869a064f71cd21f1c0`.

The freshest same-run July 9 Excel is a different 55,167-byte file at SHA-256
`b271f74be2cea85d095767564a98f1858e53666c99dbb7d8bc5c2b042db64987`.
Its same physical row contains the exact printed Description. The first-bundle and
`All Reports 7.9` route-037 PDFs are byte-identical at 138,448 bytes / SHA-256
`44d2535ff6aa820eb39876e238b927c71c5fcfc0c57c43b381f6b14bfc2d3eab`.
Therefore the missing Description was corrected between the 7.8 and 7.9 Excel exports;
it is not a current PDF-vs-Excel discrepancy.

The complete old/current Excel hash census then found exactly four changed route files
and no changed PDF: routes 002, 010, 037, and 101. The July 9 Excel adds six nonblank
Descriptions and one row relative to July 8:

- route 002 PM `014.348`: `002/EB ON FR GLENDALE BLVD`;
- route 010 PM `014.814`: a new row with `010/EB ON FR VERMONT`;
- route 010 PM `014.820`: `010/SEG EB CONN OFF TO GRAND/18TH`;
- route 037 PM `003.809`: `037/WB ON FR SB RTE 121`;
- route 037 PM `003.981`: `037/WB OFF TO NB RTE 121`;
- route 101 PM `002.999`: `101/SB TO 156 TWO WAY CONN`.

Direct 150-DPI inspection of the authoritative PDF pages proves that only route 037
PM `003.809` is printed. Four other paired Description cells are visibly blank, and
route 010 PM `014.814` is absent entirely. Thus the freshest same-run pair removes the
old route-037 discrepancy but retains four real paired Excel-description/PDF omissions
plus one Excel-only described row: five unrepresented Description claims total. Those
are source-format deltas to preserve, not values to normalize away.
The current/old Excel tree manifests are respectively
`31a13ebc388951fdcadbba69d9188218af4548dd56d68c91e09f96bcb41765c8`
and `4bb040280bab17fd14283aa20178d189b4e499291eea1345adba0e0bb7f72c4f`;
both PDF trees are byte-identical at manifest
`072e538e5ebcbf015ec719565f003fb72027973a11d63c42f123802d8856dfa7`.

Unqualified narrative in `CLAUDE.md`, `docs/comparison-engine.md`, and
`docs/tsn-parsers.md` calls this an Excel export defect, and the provisional
`HSL-PDF-79` canary still names a cross-bundle 7.8-Excel/7.9-PDF pairing. Reusing that
residual as a current expected difference would blend snapshots, falsely reject the
same-run pair, and permit evidence/Report View logic to reproduce a stale source delta.

Correction/acceptance requirements: Stage 8 must bind the complete `All Reports 7.9`
same-run 252-Excel/252-PDF trees and independently establish their actual row/cell
parity. The 7.8 Excel plus first 7.9 PDF remains a separately named historical
cross-edition fixture for Stage 9. The current oracle must freeze the six old-to-current
Excel changes and classify the four paired PDF omissions plus one Excel-only described
row independently of equate representation differences. Update the unqualified
documentation only after
the statewide source oracle proves the complete current residual; never delete the old
source fact or silently re-bless the historical canary as current.

### CMP-AUD-194 — Highway Sequence source oracle treats visually composed legend labels as contiguous PDF text

Priority: P2  
Status: Remediated in the independent Stage-8 source-oracle draft; acceptance pending  
Primary code: `build/phase8_highway_sequence_source_oracle.py`, PDF legend-role gate

The first independent current-source pass stopped before emitting any dataset because
it required the phrases `Highway Group` and `File Type` to occur contiguously in
`extract_text()` output. They are visually valid labels in the two-column legend, but
PDF reading order interleaves their words with the adjacent code descriptions. The
assertion therefore tested one text-extraction serialization rather than the actual
legend role. This is an audit-harness defect, not a source or product discrepancy.

Accepted draft disposition: the rerun binds stable, visibly distinct legend roles whose
text order is unambiguous (`Legend`, route/postmile code headings, equation definition,
and font-color heading), retains exact cover/date/route claims, and parses all 252
immutable members. No row from the failed run was emitted or accepted. Final status is
still gated on the complete Stage-8 oracle replay.

### CMP-AUD-195 — Highway Sequence source oracle confuses harmless header-label width movement with a changed data grid

Priority: P2  
Status: Remediated in the independent Stage-8 source-oracle draft; acceptance pending  
Primary code: `build/phase8_highway_sequence_source_oracle.py`, PDF header-anchor gate

The parser deliberately uses fixed statewide data-column windows so it has a different
failure surface from production's per-page header-derived windows. Its initial safety
gate nevertheless required every header label's left edge to remain within three PDF
points of one sample page. A real frozen page places `NEXT` at x=247.992 rather than
251.300. That 3.308-point typography movement does not cross or alter any fixed data
boundary, but the audit rejected the page as if the layout grid had changed.

Accepted draft disposition: the parser validates header order and a conservative envelope
that cannot cross the fixed data-column boundaries, retain the exact statewide x-range
for every header token in the result, and require all table lines to classify with zero
residue. A wider label envelope must never widen the data windows or bless an unknown
line. The full draft parse now records all eight header ranges and classifies every one
of 60,493 PDF rows; final status remains gated on complete Stage-8 replay.

### CMP-AUD-196 — Highway Sequence display projection recognizes only one case of the OOXML carriage-return escape

Priority: P2  
Status: Remediated and verified against installed Excel in the source-oracle draft; final acceptance pending  
Primary code: `build/phase8_highway_sequence_source_oracle.py`, `_display_text`

The raw Excel corpus contains both `_x000D_` and lowercase `_x000d_` encodings for a
carriage return. The first render-equivalence projection removed only the uppercase
form. Four route-010 Cactus City Rest Area Descriptions therefore remained falsely
different from their visually identical PDF cells, even though the following literal
newline was removed correctly. Raw-value accounting was unaffected and continues to
preserve both encodings.

Accepted draft disposition: the explicitly named display projection decodes the OOXML
escape case-insensitively while raw accounting preserves the source string. A fresh
full-corpus run removes exactly the four false display differences, leaving exactly
four real paired Description omissions and the one Excel-only row. Installed Excel
independently returns CRLF codepoints `13,10` for `Value2`, `Formula`, and displayed
text in cells I1299:I1302. Final status remains gated on complete Stage-8 replay.

### CMP-AUD-197 — Highway Sequence comparison reports decoded carriage returns as literal `_x000d_` Description differences

Priority: P1  
Status: Verified with raw OOXML, openpyxl, installed Excel, and the current PDF  
Primary code: `scripts/compare_highway_sequence_tsn.py`, `_load_tsmis` / `_v` /
`_norm_desc`; `scripts/compare_highway_sequence_pdf.py`, PDF-vs-Excel Notes

Route-010 cells I1299:I1302 contain lowercase `_x000d_` followed by LF in the raw
worksheet XML. Openpyxl exposes that serialization literally. Installed Excel instead
decodes each value to the Description followed by CRLF; `Value2`, `Formula`, and
displayed text all terminate in codepoints `13,10`. The current PDF prints the same
Description without a visible token or substantive trailing content.

The product TSMIS loader uses openpyxl and collapses ordinary tab/newline characters,
but it does not apply OOXML string unescaping. It therefore retains `_x000d_` in the
normalized Description and reports four false differences against the PDF (and any
otherwise matching TSN row). The PDF-vs-Excel Notes currently reinforce the defect by
calling the token a literal Excel value that should surface honestly. It is an encoded
carriage return according to installed Excel, not substantive report text.

The exact-byte four-leg residual classifier refines the current vs-TSN effect: all four
current TSN partners already carry a different `(cid:13)` source string, so the product's
OOXML mutation changes the Excel claim without changing those four rows' already-
different Description state. They are difference-preserving source-claim mutations in
the vs-TSN legs, not four additional state false positives. PDF-vs-Excel still reports
the four false differences described above.

Correction/acceptance requirements: decode OOXML control escapes according to installed
Excel semantics at the comparison load boundary, mutation-test both hex-letter cases
and escaped literal underscores, retain real interior line-break semantics, and update
the Notes. The fix must remove exactly these four false current differences without
normalizing away the 2,154 genuine raw-whitespace serialization differences, the four
paired PDF Description omissions, or the Excel-only route-010 row.

**Remediation (2026-07-16) — the SAME-SOURCE half.** The owner reported the sibling
class live (Intersection Detail PDF-vs-Excel: eight "HILLCREST RD ≠ HILLCREST RD"
cells — the Excel export's censused trailing-tab padding, which Excel TRIM's
space-only collapse let through) and ruled the whole class false positives
(*"approved as long as it results in all correct comparisons"*).
`compare_tsn_common.same_source_render_text` now applies render-artifact
equivalence at the load boundary of every PDF-vs-Excel flavor (and ONLY those —
each vs-TSN leg keeps its accepted oracle's byte-exact semantics): OOXML
`_xHHHH_` escapes decode per installed Excel (both hex cases;
`_x005F_xHHHH_` preserves the literal token; interior breaks stay separation),
and edge whitespace-class padding never counts. PhysicalKey cells pass through
by identity. Corpus-verified on the 7.9 pairs: **ID 16,459/0/0 with exactly the
one real 108/TUO HG defect remaining (was 9 cells — the 8 tab rows are gone);
RD 15,216/0/0 fully identical (the 4 `_x000d_` gone); HSL 1,410 rows / 3,721
cells {Desc 1,133, FT 1,129, HG 910, PM Suffix 549} — the Stage-8 oracle table
EXACTLY.** Notes updated in all three flavors; contract fixtures in
`check_compare_tsn_common` (escape cases, `_x005F_`, tab padding, PhysicalKey
passthrough, real-diff control, and the flavor opt-in census). The HSL vs-TSN
load-boundary decode LANDED with the CMP-AUD-220 batch (2026-07-16, same day,
later): `compare_highway_sequence_tsn._v` now applies the shared
`compare_tsn_common.decode_ooxml_escapes` (proven byte-equivalent to
openpyxl's unescape — the Stage-8 oracle's xlsx reading — in
`check_compare_tsn_common`), so the four `_x000d_` Excel cells compare as
their real CRLF content on the vs-TSN legs too; zero literals survive the
loader on the 7.9 corpus, and the legs land on the oracle table exactly (see
the 220 execution disposition).

**Remediation (2026-07-16, later) — the RD vs-TSN half. The finding is now
CLOSED for every current family.** The family census settled the deferred
decision with source facts: the four Cactus City cells (route 010 @ 71.863 /
72.028 / 72.200 / 72.355) end `…REST AREA_x000d_\n` in the ssor-prod 7.9
Excel consolidated, while their partners in the bound raw TSN extract
(`TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx`, which contains ZERO literal
`_x000d_` anywhere) end `…REST AREA\n` — unlike HSL (whose TSN partners carry
their own `(cid:13)` strings, making the decode difference-preserving there),
RD's TSN side is clean, so the product's four Description diffs were pure
Excel-export encoding. `compare_ramp_detail_tsn._v` and `_strip_desc_prefix`
now decode OOXML escapes at the load boundary (decode-before-trim; both hex
cases; `_x005F_` literals preserved; interior decoded characters survive as
real compared content), pinned red→green in `check_compare_ramp_detail_tsn`.
Corpus re-measure through the product engine: Excel-vs-TSN moves from the
accepted RD-79 numbers 741 differing rows / 847 cells {Description 185} to
**737 / 843 {Description 181}** with every other per-field count and the
15,212 / 4 / 198 shape identical — an explained amendment to RD-79's
Excel-vs-TSN leg justified source-first (the raw extract proves the bytes
are not data); PDF-vs-TSN stays exactly the accepted 774 / 998 and
PDF-vs-Excel stays 15,216 fully identical (no double-decode drift through
the shared `_v`).

### CMP-AUD-198 — permanent installed-Excel escape probe over-specifies optional COM open arguments

Priority: P2  
Status: Remediated in the source-bound installed-Excel proof artifact  
Primary code: `build/probe_phase8_highway_sequence_excel_escape.ps1`

The interactive read-only Excel COM probe succeeded with the minimal
`Workbooks.Open(path, 0, true)` signature. The permanent source-bound script attempted
to serialize every optional argument with `[Type]::Missing`; PowerShell's COM dispatcher
rejected that call before opening the workbook, so it could not emit the durable JSON
proof even though the underlying four-cell observation was already known.

Accepted disposition: the probe uses the proven three-argument read-only signature,
retain disabled alerts/links/macros and `SaveChanges=false`, bind the route-010 member
hash, assert exact CRLF codepoints and Value/Formula/display agreement, and save the
result without modifying the workbook. The 31,722-byte artifact is SHA-256
`ec8c61c8cb8e629abee82d83abaacc1b9c9ebc3ce4c2356a6da527e4ead42b07`;
all three invariants pass for all four cells.

### CMP-AUD-199 — Highway Sequence PDF-vs-Excel uses the changing equation suffix as identity

Priority: P1  
Status: Remediated 2026-07-16 (the HSL family batch) — was: Verified on all 60,494 current Excel and 60,493 current PDF rows  
Primary code: `scripts/compare_highway_sequence_pdf.py` reuses
`compare_highway_sequence_tsn.py`'s glued prefix+PM+suffix key

The same-run source census proves all 1,129 PDF `EQUATES TO` annotations have a
semantic Excel partner at the same route, normalized County, prefix, base PM, and
occurrence. Every PDF annotation is immediately followed by an `E`-suffixed row.
Their exact Excel/PDF event classes are:

- 852 events use the PDF/TSN convention in both formats: annotation unsuffixed,
  following row suffixed;
- 272 events move `E` between formats: Excel puts it on the annotation while PDF puts
  it on the following row; and
- five events have `E` on the PDF following row but nowhere in the Excel event.

Thus 544 suffix-cell differences are a precisely mapped representation move and five
are real missing-Excel-suffix source deltas. Pairing by route + County + prefix + base
PM + occurrence preserves 60,493 semantic pairs and the one genuine Excel-only
route-010 row, while exposing all 549 suffix cells. The product instead glues suffix
into the row key. On the historical pair this creates the blessed 547/547 one-sided
class; on the current pair it produces 548 Excel-only and 547 PDF-only rows because
the new route-010 row adds one more Excel side.

Worse, one duplicate group proves that the loss is not merely less-readable output.
Route 152 / SCR / `T003.273` has three occurrences. Excel seats `E` on occurrence two
(`END I.A; R-BR @ LINCOLN`), while PDF seats it on occurrence three
(`END LT INDEP ALIGN`). Full-key grouping therefore forces those two different
physical descriptions to pair and lets the two blank-suffix occurrences cross-pair;
the full-key multiset loses only 547 pairs even though occurrence-aligned truth has
549 suffix differences. It hides two logical row identities by swapping them.

This supersedes the D6 assumption in
`docs/planning/comparison-perfection/fable5-comparison-remediation-decisions.md` that equation seating should
remain one-sided. That record was based on the earlier cross-bundle canary, not this
complete same-run event proof. Source facts and the user's perfection rule take
precedence over the historical decision.

Correction/acceptance requirements: give PDF-vs-Excel a same-source identity profile
of route + normalized County + prefix + base PM with exact duplicate assignment; expose
suffix as an asserted compared field; preserve all 1,129 annotation field differences,
classify exactly 272 two-row moves and five missing-Excel suffixes, and keep the one
Excel-only row plus four paired Description omissions. Mutation gates must move, add,
remove, and swap suffixes inside duplicate groups, including the exact route-152
three-occurrence topology. The vs-TSN identity policy remains a separate question and
must not be changed by analogy without raw-TSN proof.

The clean current product witness now reproduces the predicted defect exactly:
59,946 pairs, 547 PDF-only rows, and 548 Excel-only rows. It reports only 1,725 asserted
cells (FT 858, Description 867) while suppressing every HG/City/Distance difference and
turning suffix into key membership. The independent source contract is 60,493 pairs,
zero PDF-only, one Excel-only, with 3,721 same-source cells including all 549 suffix and
910 HG differences. The six-workbook parity artifact at SHA-256
`bb7c8550724b71e657781f86579e25b2f70c96bf8bf3380d049f70118f98961f`
authenticates both the observed product output and the deliberate contract failure.

**Remediation (2026-07-16).** `compare_highway_sequence_pdf` now gives PDF-vs-Excel its
own same-source profile (`SS_HEADER`/`_tsmis_row_same_source`/`_SS_SCHEMA`): rows key
on the typed PhysicalKey (Route, County, prefixed postmile WITHOUT the suffix), "PM
Suffix" is a compared column, EVERY column is asserted (no context suppression), and
Descriptions are compared verbatim on both sides. On the current ssor-prod 7.9 pair the
product loaders reproduce the source contract: **60,493 paired / 0 PDF-only / 1
Excel-only**, with FT 1,129 / HG 910 / **PM Suffix 549** exactly (the 272 two-row moves
= 544 cells + the five missing-Excel suffixes) — the route-152 / SCR / `T003.273`
swap class is structurally gone (suffix is no longer identity). Description counts
1,137 vs the oracle's 1,133: the +4 was exactly the four `_x000d_` Cactus City cells
(CMP-AUD-197 — closed for this leg by the same-source render rule later the same
day) — re-pairing the same loaded rows under the oracle's assignment
objective with those four unescaped reproduces the full 1,410-row / 3,721-cell
per-field table EXACTLY, so no other residual exists. The engine-side
assignment-objective difference was CMP-AUD-220 (since remediated — the product
now reproduces this leg's oracle table exactly). Contract fixtures:
`check_compare_physical_identity` (same-source identity, suffix compared) and the
updated Notes describe the two-cell suffix-move representation.

### CMP-AUD-200 — Highway Sequence product witness is externally terminated after 180 seconds

Priority: P2  
Status: Remediated in the clean r2 current product-source witness  
Primary code: `build/run_phase8_highway_sequence_product_sources.py` execution wrapper

The source-bound product witness needs longer than the shell wrapper's initial
180-second limit to parse 252 PDFs. The wrapper terminated the Python process before the
consolidator returned. The unaccepted root contains a complete 2,424,212-byte Excel
consolidation and only 67 converted PDF members (routes 001 through 068); it contains no
PDF consolidated workbook and no `result.json`. Because the external termination
prevents a producer-owned `ConsolidateResult`, this state says nothing about product
completion and cannot be resumed or cited as a partial product result.

Accepted disposition: the failed root remains separately preserved. A clean r2 root ran
for 392 seconds and returned its own complete producer outcomes: 252/252 Excel inputs,
252/252 converted PDF members, 60,494/60,493 rows, zero skipped/failed inputs, both
consolidated outputs, unchanged source manifests, and terminal `result.json`. The
242,779-byte result is SHA-256
`39eb2e53091bfcfdd6a3b4a2997b8700c1d617e94f136f4d3a0603730df82493`.

### CMP-AUD-201 — Highway Sequence parity probe requires worksheet dimensions that streaming product workbooks omit

Priority: P2  
Status: Remediated in the exact product-source parity artifact  
Primary code: `build/check_phase8_highway_sequence_product_sources.py`

The product's consolidated workbooks are written through a streaming/write-only OOXML
path and legitimately omit the optional worksheet dimension metadata. Openpyxl therefore
reports `max_column=None` and `max_row=None`. The first parity probe treated that absence
as a schema failure and stopped before reading the header or any data row. No product
cell conclusion was emitted. The first streamed correction then exposed the same flawed
assumption at row level: row 122 has a blank Description, so sparse OOXML omits trailing
cell J and openpyxl returns nine physical cells even though the ten-column logical schema
is unambiguous from the exact header.

Accepted disposition: the probe streams physical rows, requires the exact ten-cell
positional header, pad only omitted trailing blank cells to that logical width, reject
any extra cell or blank physical row, count rows from the stream, and compare every
value. Missing optional dimension metadata and sparse trailing blanks must neither
reject a valid stream nor weaken extra-column/extent checks. The corrected full run
finds zero cell mismatches and zero missing/extra rows for both current product
consolidations. Its 1,739-byte result is SHA-256
`011b5dc5d017b95f16125dc9d991aa030d96da923d852b65e9ffa1c933093f9d`.

### CMP-AUD-202 — Highway Sequence comparison witness gives three large legs one shared 600-second wrapper

Priority: P2  
Status: Remediated in three clean per-leg witnesses and the independent twin audit  
Primary code: `build/run_phase8_highway_sequence_product_comparisons.py` execution strategy

The first source-bound product-comparison witness placed Excel-vs-normalized-TSN,
PDF-vs-normalized-TSN, and PDF-vs-Excel sequentially inside one Python process governed
by one 600-second shell timeout. Excel-vs-normalized-TSN legitimately consumed most of
that budget while generating and atomically committing its roughly 53 MB formula and
34 MB value workbooks plus both outcome sidecars. The wrapper then terminated the
process while PDF-vs-normalized-TSN had only producer-temporary workbooks. There is no
terminal `result.json`, no PDF-vs-TSN product outcome, and no PDF-vs-Excel attempt.

This is an audit-runner lifecycle defect, not evidence that any product comparison is
partial or failed. The failed r1 root is retained separately: its first leg may be used
only after independent sidecar/workbook verification, while its temporary second leg
and absent third leg are never completion evidence.

Correction/acceptance requirements: execute each comparison leg in its own clean,
source-bound process with its own sufficient timeout; require a producer-owned complete
result, both committed workbook flavors, both outcome sidecars, unchanged inputs, and a
terminal per-leg manifest before proceeding. Compose the three verified leg records
only after all pass. Final acceptance must allow and inventory only the product's exact
code-backed, zero-byte permanent publication lease while rejecting every other lock,
temporary/staging file, missing leg, or monolithic wrapper partial directory. It must
reproduce the composed result byte-for-byte in a second clean root.

Accepted correction evidence: the three isolated r2 legs each completed in 365–409
seconds with their own unchanged inputs, exact loaded-code manifest, committed
formula/value twins, trusted outcome sidecars, decoded comparison payload, pairing
trace, exact artifact universe, and terminal result. Their result identities are:

- Excel-vs-normalized-TSN: 16,069 bytes, SHA-256
  `b1cf6f791c18917dfb51b3f9f2d8331075091992ce3d3c3415032108ee9bec83`;
- PDF-vs-normalized-TSN: 16,228 bytes, SHA-256
  `65d79577e9dbc7dfbce22d3d12fa4b8a670edb78b439b56b2802afeaa077a59a`;
- PDF-vs-Excel: 15,896 bytes, SHA-256
  `972ea8466903a27d2cc609769d6fead11aceb5e2dd8d1a4e653cc0b92309f581`.

The independent six-workbook reader then authenticated every cell, formula/value shell,
sidecar, chunk, exact duplicate assignment, source snapshot, and tree manifest. Its
42,381-byte artifact is SHA-256
`bb7c8550724b71e657781f86579e25b2f70c96bf8bf3380d049f70118f98961f`
with deliberate status `pass_with_expected_product_defect`: publication is authentic,
while the PDF-vs-Excel source contract remains red under CMP-AUD-199. A second clean
three-leg replay is still required for final Stage-8 family acceptance, not for closure
of this single-wrapper lifecycle defect.

### CMP-AUD-203 — Highway Sequence witness would reject the intentional permanent publication lease

Priority: P2  
Status: Remediated in three clean per-leg witnesses and independent artifact-universe audit  
Primary code: `build/run_phase8_highway_sequence_product_comparison_leg.py` artifact-universe gate;
source contract: `scripts/consolidation_meta.py` and `scripts/artifact_store.py`

The first correction design for CMP-AUD-202 required a completed leg directory to
contain no lock file. Production intentionally creates
`.tsmis-comparison-publication.lock` as a permanent transaction lease anchor and never
unlinks it: process/thread exclusion lives in the held byte-range and keyed Python lock,
not in removing the ordinary file. `artifact_store.py` likewise excludes that exact
name from data fingerprinting while explicitly refusing to treat its parent as safely
disposable. Therefore a blanket lock-file ban would make every legitimate product
publication fail the audit after it completed successfully.

Accepted design disposition: the per-leg witness requires that one exact fixed lease
name, requires it to be an ordinary zero-byte file, records its identity and the bound
product-code definitions, and rejects Excel locks, producer temp/staging names,
publication sentinels, any other lock, or any unknown artifact. This is a narrow
infrastructure exception; it cannot hide an uncommitted workbook or broaden the allowed
artifact universe. Final status remains pending the clean per-leg executions and replay.

Execution disposition: all three clean roots contain exactly one ordinary zero-byte
lease with the code-backed fixed name, no other lock/temp/staging/sentinel/unknown file,
and the exact workbook/sidecar/chunk/audit-manifest universe. The independent parity
artifact cited under CMP-AUD-202 re-authenticates those universes. A future unexpected
ordinary file remains a hard failure; the lease exception did not broaden.

### CMP-AUD-204 — Highway Sequence comparison deletes authoritative TSN numeric Description prefixes

Priority: P1  
Status: Remediated 2026-07-16 (the HSL family batch) — was: Verified on raw and normalized authoritative TSN plus both current TSMIS formats  
Primary code: `scripts/compare_highway_sequence_tsn.py`, `_norm_desc` and `_load_tsn`;
inherited by `scripts/compare_highway_sequence_pdf.py` and Highway Sequence evidence

The comparator applies the same leading `digits[/]` Description rewrite to both sides.
That rule was intended to remove a separately added TSMIS outer route label, but it is
also applied indiscriminately to authoritative TSN text. Raw TSN and the accepted
normalized TSN workbook contain the exact same 154 numeric-prefix Descriptions: 108
begin with the owning route token and 46 intentionally begin with a different route.
Product loading changes all 154; only two remain numeric-prefix-leading because their
source value contains two nested prefixes and the product removes only the first.

Exact full-PM pairing against both current TSMIS formats proves that 81 real Description
differences become equal solely because product deletes the TSN prefix. The count is 81
on all four current legs: Excel/PDF against raw/normalized TSN. Examples include route
001 / LA / `008.266`, where TSMIS says `103 SEP 53-145` and TSN says
`1/103 SEP 53-145`, and route 680 / SOL / `013.088`, where TSN's leading `680/` is a
source claim. The canonical 81-row ledger is SHA-256
`5dacffd43c62ea8001796e5b4d87d1290b07cd7084861f26cf8cf047d452eab7`.
The same rewrite also collapses two real duplicate-location Description distinctions:
route 028 / PLA / `009.880` and route 145 / FRE / `033.129` each contain distinct
prefixed and unprefixed TSN descriptions at one physical identity.

The later exact-byte four-leg residual classifier closes the other direction too. On
the source-owned fixed pairs, the same TSN rewrite creates 15 false-positive Description
states per leg in addition to the 81 false-cleans. The symmetric product rule also
changes 90 cross-route numeric-prefix Descriptions in each TSMIS form; current Excel has
four additional CMP-AUD-197 CRLF mutations, for 94 changed source rows. Raw and
normalized TSN each still have 154 changed rows. These source-claim mutations can
preserve, remove, or create aggregate state depending on the paired occurrence, so a
net cell total cannot represent their full impact.

This is not covered by treating Description normalization as a harmless display rule.
Evidence imports the same loader and therefore cannot discover the loss independently.
CMP-AUD-067 already proves same-source projection loss; this finding binds the separate,
live authoritative-TSN false-clean and exact affected population.

Correction/acceptance requirements: keep TSN Description text verbatim as a compared
source claim; on TSMIS only, remove a separately proven outer label when the token
exactly names that row's owning route, remove only its delimiter padding, and retain the
raw value. Never remove a cross-route or nested token by pattern alone. Permanent gates
must preserve all 154 TSN prefixes, the 46 cross-route cases, the two duplicate-key
distinctions, all 90 TSMIS cross-route prefixes per form, and expose exactly the 81
currently hidden plus 15 currently fabricated Description states in every raw and
normalized comparison leg, with independent evidence.

Durable development proof now binds the frozen source-row/TSN-row caches, accepted
normalized workbook, capture manifest, and exact product module without importing the
product comparator. It reproduces both the 7,517-byte order-bound ledger SHA above and
the independently content-sorted SHA-256
`59f3afe3336d07daaf5fd6e228b060ab5e822c1040f2e21e3dd2fca88b9d11e7`, all four
81-row populations, the two collapsed duplicate identities, and the 154/46/2 prefix
census. Three separate runs produced byte-identical 174,929-byte artifacts at SHA-256
`202fcb82b6ba62d15fcd273b19f4f35de672d06da39fd710982ba65350e8bdd1`.
The artifact is explicitly non-acceptance because it consumes development row caches;
the final family oracle must reparse immutable raw inputs.

The expanded residual artifact is 2,475,505 bytes at SHA-256
`ebe0f9efb6025525024d7183211e52f5cf4a10fba1dc9bfcbe02513ce38cb45b`.
Two hardened exact-byte runs are identical. It reconstructs every persisted pair/cell,
binds the 81/15 effects and 90/94/154/154 source-projection populations, and leaves zero
unexplained residue. It remains explicitly non-acceptance and cache-backed.

**Remediation (2026-07-16).** The symmetric strip is gone. `_desc_plain` (the TSN side
and both PDF-vs-Excel sides) compares Descriptions VERBATIM apart from whitespace
collapse — all 154 numeric-prefix TSN Descriptions (108 owning-route + 46 cross-route)
survive load, corpus-verified — and `_desc_tsmis` (the TSMIS side of the vs-TSN legs
only) removes the leading label ONLY when its token names that row's own route
(canonical, padding-insensitive comparison; `s[m.end():].lstrip()` also removes only
the delimiter padding, the CMP-AUD-205 rule), so the 90 cross-route TSMIS prefixes per
form are kept and nested tokens strip once at most. The evidence projection is
side-aware through the same functions. On the current pair, re-pairing the product-
loaded rows under the oracle's assignment objective reproduces the oracle's complete
per-field tables EXACTLY on all three legs (Excel-vs-TSN 23,691 rows / 30,005 cells /
asserted 5,589 with Description 4,894; PDF-vs-TSN 29,189 / asserted 5,001 with
4,916; the four `_x000d_` Excel cells unescaped per CMP-AUD-197's proven CRLF
equivalence) — the 81 false-cleans and 15 fabricated states are gone; the last
engine-side delta was the CMP-AUD-220 assignment objective, since remediated
(the PRODUCT now lands on these oracle tables directly). Fixtures:
`check_compare_highway_sequence_tsn` (own-route strip / cross-route kept / TSN
verbatim, and the false-clean class now surfaces end to end) and
`check_visual_evidence` (side-aware projection).

### CMP-AUD-205 — Highway Sequence audit projection leaves separator padding after an approved TSMIS route label

Priority: P2  
Status: Remediated in the corrected draft and direct-source r2 checkpoint; final acceptance replay pending  
Primary code: `build/phase8_highway_sequence_comparison_draft.py`, `_semantic_desc`

The independent draft first collapses whitespace, then removes an exact matching
TSMIS outer route token with `text[match.end():]`, but does not trim the separator space
that can follow the slash. Exactly three source rows use that form in current Excel,
current PDF, and historical Excel: `005/ SEG...` at ORA / `020.746`, `070/ EB...` at
YUB / `000.204`, and `073/ NB...` at ORA / `016.689`. The projection leaves each as
`' SEG...'`, `' EB...'`, or `' NB...'` while TSN correctly projects without that one
delimiter space. All three keys are singleton-to-singleton, so duplicate assignment is
unaffected.

The draft therefore reports 84 Description differences made equal by product
normalization, but only 81 are CMP-AUD-204 source losses. The other three are this
audit-only artifact. Correct current source truth reduces independent Description and
asserted-row/cell totals by three per leg: Excel-vs-raw/normalized TSN Description
differences become 4,894; PDF-vs-raw/normalized become 4,916.

Correction/acceptance requirements: trim only the delimiter padding after removing an
already-approved exact matching TSMIS outer route label; do not broaden which prefixes
are removable. Re-run the four independent current legs, bind the three-row census, and
mutation-test matching, cross-route, nested, and no-padding forms. The draft is marked
non-acceptance and none of its pre-correction totals may be promoted into the final
Highway Sequence oracle.

The corrected draft rerun is 113,580,300 bytes at SHA-256
`4198f7e4a65a4afbe164e738defaf36ec0270efc328f0e46d400937c7b9efb1c`.
It preserves all pairing/one-sided counts and reports the corrected current asserted
totals: Excel-vs-raw 4,894 rows / 5,589 cells, Excel-vs-normalized 4,895 / 5,594,
PDF-vs-raw 4,916 / 5,001, and PDF-vs-normalized 4,917 / 5,006. This remains development
evidence; final acceptance must reparse immutable raw sources rather than trust the
cache-backed draft.

The replay-stable Description-normalization probe cited under CMP-AUD-204 independently
binds the exact three-row slash-padding census in current Excel, current PDF, and
historical Excel and requires the corrected 4,894/4,916 Description totals. It therefore
closes the draft correction without weakening the final raw-source replay gate.

The exact-byte direct-source r2 checkpoint reparses all three affected TSMIS editions,
retains the same three identities, applies the corrected delimiter-only trim, and runs a
real padding-contract mutation through the gate. The mutation is rejected. This closes
the source-core correction; product/evidence acceptance remains pending.

### CMP-AUD-206 — Highway Sequence raw-twin verifier requires optional dimensions from its own write-only XLSX

Priority: P2  
Status: Remediated in the clean streaming-verified raw-TSN development twin  
Primary code: `build/build_phase8_highway_sequence_raw_tsn_twin.py`, post-write reopen gate

The development raw-TSN twin is intentionally written through openpyxl's write-only
path. That valid package may omit the optional worksheet `<dimension>` claim, so a
read-only reopen reports `max_row=None` and `max_column=None` even though the header and
all streamed records are intact. The first verifier treated those optional hints as the
physical/logical extent and stopped after writing the workbook. It emitted no terminal
result, provenance sidecar, or accepted twin. This repeats the same OOXML assumption
class first caught in CMP-AUD-201, now at the raw-twin construction boundary.

Correction/acceptance requirements: preserve the failed workbook root as non-result
evidence; rebuild into a different clean root; stream every physical row; require one
exact eight-cell header plus exactly 69,804 records; pad only omitted trailing blank
cells to the eight-column logical schema; reject any extra cell, blank physical row,
wrong scalar, changed value, or additional worksheet. Optional dimensions must be
recorded when present but can neither prove nor disprove completeness. Only a terminal
result that also binds the full provenance sidecar, package members, inputs, and exact
raw/normalized conservation counts may remediate this finding.

Accepted development disposition: the workbook-only failed root is preserved with no
terminal result; its 2,541,735-byte XLSX SHA is
`c5ec614109d8e5b2a35f4d6705c8da218c84ec8b286b861095af260c5591ae9e`.
A different clean r2 root streams exactly 69,805 physical rows (one exact eight-column
header plus 69,804 records), pads 13,468 omitted trailing blanks to the logical schema,
and finds zero extra cells or blank rows while `max_row/max_column` remain `None`.
It preserves 68,806 data + 998 equate rows, 46 blank-County pre-county equates, 283
`*P*` plus 282 `-------->` pointer tokens, and the one Description punctuation delta.
The raw workbook is 2,541,734 bytes / SHA
`d594e2441b81c4d4d81c11aa5bbf01418bcd2dcc0bedf3ee9a6221a66cb03fa1`;
its 23,610,997-byte provenance sidecar SHA is
`f27c7724f9acc8988bfd65c896e8278853b70690ed36d0317fabf6c5af8920f2`,
and its terminal result SHA is
`51a0cfb70611442fc5b7ca4bb1acbb2779446b7d5400d10590d31c798629d1bc`.
The twin remains explicitly non-acceptance because it consumes the development row
cache; final acceptance must rebuild it by reparsing the immutable 12 raw PDFs.

### CMP-AUD-207 — Highway Sequence duplicate-cost projection treats historical Excel as TSN

Priority: P2  
Status: Remediated in the corrected draft and direct-source r2 checkpoint; final acceptance replay pending  
Primary code: `build/phase8_highway_sequence_comparison_draft.py`, `_comparison`

The full-PM duplicate projector decides whether to apply TSMIS-side Description
semantics with `row.source.startswith("current_tsmis")`. That happens to identify both
current TSMIS forms but excludes the separately named
`historical_tsmis_excel_7_8` dataset. Historical Excel rows therefore receive the
TSN-side cost projection during exact duplicate assignment even though their reported
left values later use the TSMIS projection. This violates the declared side role and
makes the historical duplicate trace/cost depend on a naming convention.

The current frozen corpus masks the semantic severity: correcting the role changes no
historical pair, one-sided count, differing field, or asserted total. Historical
Excel-vs-raw keyable semantics remain 57,071 / 3,422 / 12,687 with 4,898 asserted rows /
5,593 cells; the complete raw publication has 12,733 TSN-only rows after adding the 46
explicit blank-County annotations. The normalized leg is 57,071 / 3,422 / 12,687 with
4,899 / 5,598 after its classified normalization deltas. Assignment costs and trace
identity do change, so the pre-correction trace is not acceptance evidence. Current
Excel/PDF legs are unaffected only because their names match the brittle predicate.

Correction/acceptance requirements: project duplicate costs from an explicit typed
side/source-flavor role, never a source-name prefix; rerun every current and historical
leg; require current pair maps and counts unchanged; require historical counts unchanged
but bind the corrected cost/trace; and mutation-test arbitrary dataset labels so renaming
cannot alter semantic assignment. Final raw-source oracle code must not inherit this
development shortcut.

Correction disposition: the draft now selects the TSMIS projection from the row's typed
`kind == "tsmis"` role. Historical Excel-vs-raw assignment cost changes from
`(44,930, 216,793, 1,856)` to `(30,009, 157,065, 1,856)` and duplicate-trace SHA from
`d4ceaf9fdbba6ea9cca4e6eb360debb93942784243888665195afe1ec005651a` to
`896f2be36d8f2f5474331c0f79afa87ca4fc3c02df55f7e6f332ca7ca534538e`.
Historical Excel-vs-normalized cost changes from `(45,202, 219,369, 1,850)` to
`(30,281, 159,641, 1,850)` and trace SHA from
`2f70716cb436b14732632d3c9eabecfc6ab0adef3c6f76279d46254d96b99b8e`
to `db5d93c9d52e718118c07da770545ec23b22f10a65fc2867a182ff384ae3e829`.
Pair maps and all current/historical counts remain unchanged. The latest combined draft
is 113,580,300 bytes at SHA-256
`4198f7e4a65a4afbe164e738defaf36ec0270efc328f0e46d400937c7b9efb1c`;
it supersedes the earlier cache-backed draft identity cited under CMP-AUD-205 without
promoting either draft to acceptance.

The exact-byte direct-source r2 checkpoint independently reproduces both corrected
costs/traces from immutable current/historical members, preserves the complete 69,804-
row raw shape, proves dataset renaming leaves both typed projections unchanged, and
rejects typed-role mutations. This closes the source-core correction; detached final
acceptance is still pending.

### CMP-AUD-208 — visual evidence never reads the Comparison cells it claims to verify

Priority: P1  
Status: Verified in the Highway Sequence evidence and Matrix publication path  
Primary code: `scripts/visual_evidence.py`, `scripts/evidence_highway_sequence.py`,
and `scripts/matrix_build.py`

`visual_evidence.generate` captures `comparison_path` and later uses its basename, but
never opens either the formula or value Comparison workbook. Candidate rows and values
are recomputed by `adapter.load_sides` and `adapter.enumerate_diffs`; the Highway
Sequence adapter imports the same product loaders, schema, key builder, and compared-cell
predicate whose losses are documented in CMP-AUD-065/197/199/204. Matrix publication
authenticates generation metadata before and after, but it never supplies persisted
Comparison rows, state masks, one-sided inventories, or pairing traces to evidence. The
formula twin is produced separately and is outside evidence `source_paths` entirely.

Evidence captions nevertheless say an image was verified against the compared values.
What they actually verify is a second execution of the same projection, not the cells,
formulas, pairing, or source indices that were published. A consistently wrong loader
can therefore make both Comparison and evidence agree while raw truth is absent.

This does not duplicate CMP-AUD-106 (durable generation retirement), CMP-AUD-112
(PDF parse-to-raster byte race), CMP-AUD-108 (duplicate candidate erasure), or the
formula/value publication findings. It is the missing semantic link from an exact
published comparison cell to its claimed visual proof.

Correction/acceptance requirements: evidence must consume and authenticate the exact
committed formula/value generation plus canonical comparison payload and pairing trace;
each evidence item must name the workbook flavor, sheet, row/cell, state, both persisted
source indices/roles, and raw-source provenance. An independent reader must recompute
that cell from immutable sources, require the caption/highlight/image to agree, and fail
if either twin or its payload changes. Re-running the product loader is diagnostic only,
not independent verification.

#### Disposition — 2026-07-19 (the CMP-AUD-108 / 208 / 209 Stage-10 cluster)

CMP-AUD-108 (duplicate-only differences vanish), 208 (evidence never reads the published
Comparison cells), and 209 (whole discrepancy classes excluded before sampling) are ONE
coupled effort, and they are the CLAUDE.md-flagged "Highway Sequence imagery is not yet an
end-to-end comparison verifier" gap. All three require the same spine: drive evidence from
the PUBLISHED comparison (its per-cell E/D/N/U state masks, the persisted pairing trace,
and the per-column counts) rather than re-executing `adapter.load_sides` /
`enumerate_diffs`. Investigation (2026-07-19) confirmed the discrepancy truth is persisted
as Excel FORMULAS / computed-value caches + a `pairing_trace` (compare_core), so consuming
it needs a state-mask/pairing-trace decoder, AND the acceptance bar explicitly requires an
INDEPENDENT raw-source oracle ("recompute that cell from immutable sources") — the Stage-9/
10 work the project is building toward, not a single-marathon slice. Deliberately NOT
sliced: a partial published-cell reader in this most-uncertain area would risk a false
"evidence reads the cells now" impression. **108 note:** its false-zero (a comparison whose
only differences live in duplicate groups reports "no differing columns") now also lets the
CMP-AUD-106 clean-comparison retirement fire — the retirement of the stale prior set is
still correct, but the "no differing columns" note is wrong; both are subsumed by this
cluster's published-count reconciliation. **210** (no source-faithful Excel / PDF-vs-Excel
evidence path) rides the same spine plus new source-role/mode routes — a deferred multi-part
feature with its own mini-plan.

### CMP-AUD-209 — Highway Sequence evidence excludes whole discrepancy classes before sampling

Priority: P1  
Status: Verified and quantified on both current vs-normalized-TSN product legs  
Primary code: `scripts/evidence_highway_sequence.py`, candidate schema/enumerator;
`scripts/visual_evidence.py`, sampling and no-difference behavior

The Highway Sequence evidence schema removes PM, intersects only common routes/keys,
requires exactly one row on both sides, skips the key field, and applies the product's
counted-cell predicate before sampling. Consequently every one-sided row, every
duplicate-paired cell, every key/prefix/base-PM/suffix claim, and every context-only
difference is unrenderable. The generic generator then samples only this reduced set
and can announce no differing columns after the exclusions.

The current authenticated Excel-vs-normalized-TSN workbook contains 5,517 counted cells
(4,819 Description + 698 FT); evidence can enumerate only 4,358 (3,774 + 584), omitting
1,159 counted cells, or 21.01%, before sampling. PDF-vs-normalized contains 4,930
(4,842 + 88); evidence exposes only 3,938 (3,879 + 59), omitting 992, or 20.12%.
It also excludes every one of 3,422 + 12,686 = 16,108 Excel-leg one-sided rows and
2,988 + 12,253 = 15,241 PDF-leg one-sided rows. Default Highway Sequence imagery can
show at most four examples and the maximum setting twenty; neither is a completeness
ledger.

CMP-AUD-108 owns the duplicate-only subcase; CMP-AUD-065/199 own comparison context and
suffix semantics. This finding owns evidence's broader pre-sampling erasure of counted,
one-sided, identity, and context classes.

Correction/acceptance requirements: build an exhaustive source-to-Comparison evidence
locator for every paired asserted/context/key cell, duplicate assignment, and one-sided
row before selecting any display sample. Sampling may choose presentation examples only
after the exhaustive ledger is complete and hash-bound. Mutation gates must target each
excluded class and require an evidence locator even when no screenshot is appropriate.
The final raw-source oracle—not current aggregate counts—sets the expected universe.

### CMP-AUD-210 — Highway Sequence Excel and PDF-vs-Excel comparisons have no source-faithful evidence path

Priority: P1  
Status: Verified in source routing, Matrix wiring, UI gating, and current same-source truth  
Primary code: `scripts/visual_evidence.py`, `scripts/matrix_build.py`,
`ui/ui-matrix.js`, and Highway Sequence evidence adapter

Both Highway Sequence row keys route visual evidence to the companion TSMIS PDF.
When the compared source is Excel, `_try_example` still rasterizes that PDF and rejects
the candidate whenever the PDF value differs from Excel. Matrix injects evidence only
for `kind=tsn`; the PDF-vs-Excel self-check branch has no evidence hook, and the UI
camera is hard-gated to TSN mode. Therefore the system has no way to prove an Excel-only
claim or the relationship between both TSMIS renderings.

Current same-source truth makes the gap concrete: 60,493 semantic pairs plus one
Excel-only row; 1,133 Description, 1,129 FT, 910 HG, and 549 suffix differences; four
paired PDF Description omissions; four installed-Excel CRLF cells; and the route-152
suffix cross-pair. A PDF screenshot cannot evidence the omitted Excel Description or
the Excel-only route-010 row, and current PDF-vs-Excel output cannot request evidence at
all. CMP-AUD-065/067/197/199 own the comparison transformations; this finding owns the
absent source-role/mode evidence route.

Correction/acceptance requirements: support evidence for both TSMIS roles and the
PDF-vs-Excel flavor. Excel claims require workbook/cell/source-value evidence (including
installed-Excel display semantics where relevant), PDF claims require the exact parsed
and rasterized source page, and the triangle ledger must show how each maps to the
published Comparison cell and TSN/raw provenance. A value absent from PDF must remain
evidenceable as Excel truth rather than being rejected for disagreeing with PDF.

Highway Sequence currently has no Report View sheet. That absence is not independently
classified as a defect for this flat report: Stage 10 must either certify the generic
Comparison/source sheets as its complete flat view after raw prefix/base/suffix/
occurrence claims are visible, or add a typed equate-event view. It may not claim that a
Highway Sequence Report View already exists.

### CMP-AUD-211 — raw-product witness can hash and decompress different payload bytes

Priority: P2  
Status: Remediated and independently verified in the raw-product development witness  
Primary code: `build/run_phase8_highway_sequence_product_raw_tsn_leg.py`, independent
sidecar/chunk decoder

The first raw-product witness draft called the shared stable-identity helper for a
sidecar or compressed comparison chunk, then made a separate `read_bytes()` call for
JSON parsing or decompression. A mutation between those calls could make the decoded
payload differ from the bytes whose length/SHA were inventoried, while both operations
still succeeded independently. That would break the evidence chain from persisted
sidecar identity to the typed counts being audited.

Accepted design disposition: `_identity_bound_read` now captures stable file identity
before and after the one byte read, hashes those exact bytes, and requires their length/
SHA to equal the bound identity. It is used for both peer sidecars and every compressed
chunk. The aggregate decoded payload must also match its declared decoded size/SHA,
strict canonical JSON, and the returned typed outcome. Both raw-TSN comparison legs
completed, and an independent checker re-read every sidecar/chunk and reconstructed both
formula/value workbooks. Its 36,706-byte non-acceptance artifact has SHA-256
`8b59cb5062be9e3345b68b7d7024436275dd5de8ee9cb0d20bb90a7d4b0e0abd` and passes
all 15 recorded invariants. Final status still requires the direct-from-PDF raw twin and
complete acceptance replay; this cache-derived development witness cannot substitute for
them.

### CMP-AUD-212 — raw-product witness can admit orphan comparison payload chunks

Priority: P2  
Status: Remediated and independently verified in the raw-product development witness  
Primary code: `build/run_phase8_highway_sequence_product_raw_tsn_leg.py`, exact artifact
universe and decoded-payload set gate

The inherited residue gate accepts any filename matching the strict comparison-payload
grammar and requires at least one. That is sufficient to reject arbitrary names, but it
does not prove that every discovered well-named chunk is referenced by the trusted
sidecar. An old or planted `.cmpv3-*.comparison-payload.zlib` could therefore be
inventoried yet remain semantically orphaned.

Accepted design disposition: the raw witness requires exact set equality between chunk
names decoded from the sidecar manifest and chunk names inventoried by the residue gate,
then requires exact final-name equality after publishing its audit result. The only
allowed files are the two workbooks, two outcome sidecars, exactly the referenced
payload chunk set, the one code-backed zero-byte lease, product-code manifest, artifact
manifest, and result. Missing, extra, orphan, nonordinary, temp, staging, or foreign lock
entries fail. Both clean raw legs and the independent 15-invariant reconstruction now
pass that exact artifact-universe contract. The final direct-from-PDF acceptance replay
must repeat it before promotion.

### CMP-AUD-213 — audit checks Summary and Spot Check formula quantity but not semantics

Priority: P2  
Status: Verified in the current Highway Sequence product checker; permanent semantic gate pending  
Primary code: `build/check_phase8_highway_sequence_product_comparisons.py`, workbook
formula census; source contract: `scripts/compare_core.py`, Summary/Spot Check writers

The independent six-workbook checker strongly reconstructs Comparison, source snapshots,
one-sided inventories, Routes, formula/value shells, payloads, and pairing traces. For
Summary and Spot Check, however, it proves only that the formula flavor contains more
formulas and expected sheet-level formula counts. It does not assert exact labels,
references, evaluated values, default selected row, source-row identity, state-mask
reconstruction, or the absence of unexplained cells. A workbook could therefore retain
the expected formula census while Summary or Spot Check points at the wrong rows/cells.

Manual independent mapping found no new count defect in the three current values twins:
their Summary values agree with persisted typed counts, and Spot Check selects the first
paired differing row (row 2 for both vs-TSN legs; row 278 for PDF-vs-Excel), with source
links matching the hidden snapshots. That inspection is evidence of current content,
not a permanent fail-closed gate.

Correction/acceptance requirements: reconstruct Summary totals from Comparison status,
diff, link, and state cells; require exact per-flavor cell maps/formulas/labels/evaluated
values; independently reproduce Spot Check's default selection, lookup, source/snapshot
rows, all six field states/displays/verdicts, and formula/value parity; reject extra
cells. Mutation-test formulas, labels, state masks, selection, source links, snapshots,
and evaluated caches. Known product-red semantics must remain explicit even when the
workbook mechanically agrees with itself.

Execution disposition: `build/check_phase8_highway_sequence_summary_spot.py` now captures
and hashes the exact ten workbook payloads before inspecting the same bytes, authenticates
all five witness results and declared inputs, reconstructs every Comparison formula/value
cell from embedded sources, and requires exhaustive exact cell maps for Summary and Spot
Check. All source/snapshot/backlinks, selected keys, six field states/displays, formulas,
labels, section boundaries, and formula/value exceptions are explicit. Four map mutations
(missing, extra, value, and type) reject. The 35,937-byte non-acceptance result SHA-256 is
`331d4aba8321cb8e61080678f5b71357f3da249cdf02f5ad23b18ae01b9f7395`;
all 13 invariants pass. Final promotion still requires the direct-PDF raw legs and the
corrected product workbooks, so this closes the development audit gap without blessing
CMP-AUD-214/218.

### CMP-AUD-214 — Spot Check overwrites its field-by-field banner with headers

Priority: P2  
Status: Verified in the shared writer and all three current Highway Sequence twins  
Primary code: `scripts/compare_core.py`, `_write_spot_check`

The writer calls `banner(15, "FIELD BY FIELD — RECOMPUTED FROM THE DATA SHEETS …")`,
then writes the field header row at `F_FIRST - 1`. `F_FIRST` is 16, so both writes target
row 15 and the headers immediately replace the banner. The intended reviewer statement
never appears in either workbook flavor. The field table and calculations remain intact,
but the sheet loses the explicit boundary and independence explanation promised by the
writer.

Correction/acceptance requirements: give the banner and header distinct rows, update all
formula/reference/layout offsets atomically, and render/reopen both workbook flavors.
The permanent Summary/Spot Check gate under CMP-AUD-213 must require exactly one banner,
one header, the expected cell map, and no overwritten or orphaned content.

Five-leg execution evidence: the exact semantic oracle finds no intended banner cell and
`B15="Field"` in the formula and values workbook for every normalized-TSN, raw-TSN, and
PDF-vs-Excel leg (10/10 workbooks). The field calculations remain intact. This is a
verified product defect, not an audit-oracle omission.

Execution disposition (2026-07-16): `_write_spot_check` now separates the two
rows — the FIELD BY FIELD banner keeps row 15, the header row writes at
`F_FIRST - 1 = 16`, and the field rows start at `F_FIRST = 17`; every
formula, helper header, CF range, and note derives from `F_FIRST`, so the
sheet shifted atomically (the rows-2–14 block, including the CMP-AUD-218
derivation/Row-integrity cells, is unchanged). Red→green fixture proven on
both twins (pre-fix: no banner text anywhere and `B15="Field"`; post-fix:
exactly one banner at `B15`, exactly one header row at 16, first field at
`B17`, `Agree?` formulas at row 17). Pins shifted atomically:
`check_compare_audit` (Agree? at `G17`, `EXACT($K17,$M17)`/`EXACT($L17,$F17)`,
plus a new exactly-one-banner/one-header/no-overwrite gate on both twins) and
`check_compare_equality_policy` (helper-header rows 15→16, field-row scans
16/17→17/18, all K/L/M/F/G/H/I cell reads +1 in the hermetic and COM
sections). The frozen `check_phase8_highway_sequence_summary_spot.py` remains
the pre-fix witness. Counts/status/display semantics are byte-identical; only
Spot-sheet addresses from row 15 down shifted. Gate 121/121; the equality
policy's installed-Excel COM section re-ran green including the CMP-AUD-218
mutation gate.

### CMP-AUD-215 — source-core mutation probes do not exercise the gates they claim to harden

Priority: P2  
Status: Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending  
Primary code: `build/phase8_highway_sequence_comparison.py`, `_negative_mutations`

The first direct-source-core checkpoint labels several booleans as negative mutation
probes without passing the mutated data through the contract under test. For example,
removing one blank-County equate is declared detected because `len(raw_unknown[:-1]) !=
46`; blanking one pointer is declared detected because the replaced dataclass is unequal
to the original; and the equate-order probe rechecks the original next-record shape
without actually reordering records. The numeric-prefix probe similarly confirms that
one edited string no longer matches the prefix regex while reading the unmutated
population count. These assertions prove that Python observed the edit, not that the
raw census, provenance ledger, topology, projection, or publication gate would fail.

The checkpoint is explicitly non-acceptance, so no source fact is invalidated. It may
not be promoted or described as a permanent mutation gate. Correction requires each
mutation to run the same production acceptance predicate over a copied mutated dataset
and capture the expected rejection or changed bound digest. At minimum, deletion of any
of the 46 unknown-County equates, pointer loss, equate adjacency/order changes, numeric
Description-prefix removal, and delimiter-padding regression must fail their actual
census/ledger/topology/projection contracts. A clean replacement run must supersede the
first checkpoint rather than overwrite it.

Execution disposition: r2 reruns nine mutated copies through the actual event, typed-
role, pointer, 46-row unknown-County, numeric-prefix, padding, historical-edition, and
equate-topology contracts. All nine return a distinct expected/observed digest or typed
rejection reason; zero escape. The empty r1 root is recorded as incomplete/non-evidence.

### CMP-AUD-216 — raw semantic legs can be mistaken for complete raw-source coverage

Priority: P1  
Status: Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending  
Primary code: `build/phase8_highway_sequence_comparison.py`, `_raw_tsn_rows` and
the `excel_vs_raw_tsn` / `pdf_vs_raw_tsn` leg specifications

The first source-core checkpoint correctly parses all 69,804 TSN records, then splits
them into 69,758 rows with known County and 46 pre-County equate annotations. Its two
raw comparison legs receive only the known-County list but are labeled as comparisons
against authoritative raw TSN. Their shapes therefore end at 12,686 and 12,253 TSN-only
rows—the same row shapes as normalized TSN—while the complete raw product publications
correctly contain 12,732 and 12,299 TSN-only rows. A reviewer could read the smaller
numbers as complete raw coverage and accidentally re-certify the exact 46-record loss
already exposed by CMP-AUD-158.

The keyable 69,758-row semantic comparison is useful and should remain, but it must be
named as a subset. Final source truth must expose a separate complete 69,804-row raw
publication contract, list all 46 unkeyed records with exact member/page/line/raw-text
provenance, prove that they appear as explicit TSN-only publication rows, and fail if any
is missing. Neither layer may silently stand in for the other.

Execution disposition: r2 exposes both layers. The keyable contracts remain
57,072 / 3,422 / 12,686 for Excel and 57,505 / 2,988 / 12,253 for PDF; the complete
69,804-row raw contracts are 57,072 / 3,422 / 12,732 and 57,505 / 2,988 / 12,299.
Both bind the same exact 46-record ledger at SHA-256
`bbd85ad3b3de2bf5312e6a2945270b4d1a521acc690de62dabe833a810f8aeab`, and deletion
of one record fails the real manifest/census gate.

### CMP-AUD-217 — source-core binding and parsing use separate reads of each capture member

Priority: P1  
Status: Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending  
Primary code: `build/phase8_highway_sequence_source_oracle.py`, `_bind_capture`,
`_parse_excel_tree`, and `_parse_pdf_tree`; caller
`build/phase8_highway_sequence_comparison.py`

The source core first manifests every private Excel/PDF capture member by path, then
later asks the source oracle to reopen the same paths for `openpyxl` or `pdfplumber`
parsing. It repeats the manifest after the run, which detects a persistent change, but
it does not prove that the parser consumed the exact bytes whose SHA-256 was recorded.
A member changed after the first manifest and restored before the second can supply
unbound parse bytes while both endpoint manifests still match. Separate `stat()` and
hash reads also do not form one identity-bound capture.

Final acceptance must capture each member once through a stable read, hash those exact
bytes, and parse that same in-memory payload (`BytesIO` for XLSX/PDF, including bytes
passed to PDF worker processes). Pre/post filesystem identity remains a mutation guard,
not the source of parsed-byte identity. The result must bind each parsed payload digest
and fail a mutation inserted between manifesting and parsing. Existing source counts
remain evidence only until that path/byte split is closed.

Execution disposition: r2 captures each of the four 252-member TSMIS trees once and
parses those exact byte payloads through `BytesIO`, including bytes passed to PDF worker
processes. The recorded capture totals are 24,634,973 / 39,236,260 current and
24,634,499 / 39,236,260 historical; every parser diagnostic carries its captured member
SHA. Pre/post manifests remain explicitly labeled mutation guards only.

### CMP-AUD-218 — Spot Check cannot independently detect a wrong row pairing or one-sided status

Priority: P1  
Status: Verified in the shared Spot Check writer; five-leg workbook mutation proof pending  
Primary code: `scripts/compare_core.py`, `_write_spot_check`

Spot Check tells the reviewer that its field verdict is recomputed directly from the two
data sheets without reading the Comparison answer. The field equality itself is
recomputed, but the sheet first obtains status from `Comparison` into `$C$11` and the
two source-row numbers from `Comparison` into `$C$12` / `$F$12`. Every raw data-sheet
lookup then uses those supplied row numbers. Its supposedly independent one-sided status
is derived only from whether those same two Comparison-owned row numbers are blank.

Consequently, a comparator that selects the wrong duplicate pair, links the wrong source
rows, or labels a row one-sided can still receive `OK` when its displayed values and
hidden state are internally consistent with those wrong links. Spot Check verifies field
rendering for the pairing chosen by Comparison; it does not independently verify the
identity, occurrence, membership, or pairing decision. This is especially material for
Highway Sequence because its duplicate assignment and PDF/Excel equate representation
are already source-proven failure surfaces.

Correction/acceptance requirements: derive the selected identity/occurrence and both
source rows independently from immutable source/helper keys, not Comparison row links;
independently derive Both/one-sided membership; then compare that identity, membership,
state, and display against Comparison. The permanent gate must plant a consistently
wrong pair and a consistently wrong one-sided status/link set and prove Spot Check says
`CHECK`. Until then, its label must not imply independent row-matching verification.

Five-leg mutation evidence: in both workbook twins for all five legs, the oracle proves
`C11`, `C12`, and `F12` originate in Comparison and that the field formulas use those
cells while ignoring the displayed key inputs. A real selected row was then relinked to
a different source identity (for example `001/ORA R000.129` to `001/MEN 000.000`) and
Comparison's state/display was recomputed consistently; all six Spot verdicts still say
`OK`. A second mutation suppresses the existing right link and falsely marks the row
one-sided; all six again say `OK`. CMP-AUD-218 is therefore mutation-verified across the
complete current five-leg surface. The future corrected gate must make both cases say
`CHECK`.

Execution disposition (2026-07-16): the Comparison sheet now carries a hidden
trailing `__CMP_E2_KEY_V1_TOKEN` column — each row's opaque helper key written
as a LITERAL in both workbook twins (injective, guarded, outside the visible
filter/CF geometry; `_Layout.c_token`, and the Excel-limit guard counts it).
Spot Check derives the selected row's token (`M12 =
INDEX(Comparison!<token col>, C6)`) and MATCHes it into each side's literal
"Key (helper)" column (`K12`/`L12`); `$C$12`/`$F$12` — the cells every field
lookup and the K/L independent recomputation ride — display those independent
rows, and the one-sided callout now rides the independent membership instead of
Comparison's status. A new Row-integrity line on row 14 EXACT-compares
Comparison's claimed trow/nrow/status against the independent derivation with
loud conditional formatting (`F_FIRST` stays 16; every pinned Spot geometry is
unchanged). Red→green: on the pre-fix writer both planted forgeries (a
consistently relinked pair; a falsely one-sided status/link set) showed all-OK
under installed-Excel `CalculateFullRebuild`; post-fix both say `CHECK`
per-field AND on Row integrity, while the untouched workbook stays all-OK.
Permanent gates: `check_compare_audit.test_p5_spot_row_matching_independent`
pins on both twins that K12/L12/C12/F12 and the callout never read
`INDEX(Comparison!` (the Row-integrity line is the sole claimed-link consumer)
and that the token column is hidden/literal/injective;
`check_compare_equality_policy --excel` plants both forgeries and requires
CHECK via `CalculateFullRebuild` (hermetic CI skips COM, as designed).
Real-corpus verify (ssor-prod 7.9 HSL PDF-vs-Excel, 60,493×60,494): counts
canary-exact (1,410 / 3,721), token column complete + injective over the full
union in both twins, clean rebuild Spot all-OK with Row integrity OK, the
planted relink CHECK at scale, Summary SELF-CHECK all OK.
`check_phase8_highway_sequence_summary_spot.py` remains the FROZEN witness of
the pre-fix behavior; any post-fix Spot audit needs a new instrument version.
Out of scope here: CMP-AUD-214 (the banner-overwrite display defect) stays
open, and a forged token column itself remains detectable only through the
identity displays/back-links (the token is a pointer into the snapshot-bound
data-sheet key columns; Comparison itself is still not snapshot-bound).

### CMP-AUD-219 — historical TSMIS PDF rows carry the current-PDF source label

Priority: P2  
Status: Remediated and verified in the direct-source r2 checkpoint; permanent acceptance pending  
Primary code: `build/phase8_highway_sequence_source_oracle.py`, `_pdf_member` and
`_parse_pdf_tree`

The PDF member parser constructs every `SourceRow` with
`source="current_tsmis_pdf"`. The same function parses both the current July-9 PDF tree
and the separately retained historical July-9 PDF tree, so every historical row is
serialized and digested with a false current-source role. Later comparison code supplies
an explicit dataset name and therefore happens to preserve current counts, but that does
not repair the row-level provenance claim or make the source digest edition-faithful.

The identity-bound byte parser replacing this path must accept a typed source role and
carry it through every worker result, row, diagnostic, digest, and ledger. It must assert
that all members/rows from the historical root have the historical role and that a
role-swap mutation fails. Dataset-name strings may not silently determine comparison
semantics, but they must still truthfully record provenance.

Execution disposition: the r2 byte parser passes the typed dataset into each PDF worker,
requires all 60,493 historical PDF rows to retain `historical_tsmis_pdf_7_9`, and rejects
a planted historical-to-current role relabeling through the dataset-role ledger gate.

### CMP-AUD-220 — Highway Sequence duplicate matching optimizes the asserted surface, not source identity

Priority: P1  
Status: Verified and exactly reconciled on all four current Highway Sequence vs-TSN legs  
Primary code: `scripts/compare_core.py`, `_row_diff_count` and
`pair_occurrences_by_similarity`; Highway Sequence context-field schema

The shared duplicate matcher minimizes only cells that `compared_cell` marks asserting.
For Highway Sequence vs TSN, that means FT and Description after product normalization;
City, HG, and Distance To Next Point are excluded even though they distinguish repeated
source occurrences. Ties then resolve by the product's lexicographic assignment vector.
The source-owned oracle instead pairs under the same complete-PM key using all five
available source fields, character edit distance, and source position, while still
counting only the approved asserting fields in the final verdict.

The hardened four-leg residual classifier reconstructs both objectives and every
persisted Comparison pair map from exact captured bytes. Relative to source assignment,
product assignment changes 445 duplicate groups / 462 pairs for Excel-to-raw TSN and
448 / 465 for Excel-to-normalized TSN; the PDF legs change 357 / 373 and 360 / 376.
It changes which TSMIS row is one-sided in 439 Excel and 352 PDF cases, plus three raw-
TSN or six normalized-TSN memberships per form. Five raw groups and eight normalized
groups change FT counts. The resulting asserted-count contributions reconcile exactly:
Excel/raw is -7 cells (-10 Description, +3 FT), Excel/normalized -11 (-9, -2),
PDF/raw -6 (-9, +3), and PDF/normalized -10 (-8, -2), with no unexplained residual.

This is not permission to count every context difference as a defect. Pairing identity
and asserting verdict are separate decisions: context/source fields may determine which
physical occurrences correspond while remaining non-asserting in the final count.
Correction must use the source-proven duplicate objective, persist its complete trace,
then compute FT/Description truth on those fixed pairs. Mutation tests must change each
context field inside a duplicate group and prove the corresponding occurrence follows
the source row rather than an arbitrary low-asserted-difference assignment.

Execution disposition (2026-07-16, the owner-approved D3 assignment/verdict
split): `compare_core.pair_occurrences_by_similarity` now builds every
within-cap duplicate group's assignment from the source-identity objective —
the lexicographic (all-compared-field diff count, summed character edit
distance, |within-group position gap|) tuple, computed in one compared-cell
pass per candidate (`_pair_cost_components` + the oracle-mirroring
`_char_distance`), encoded order-preservingly into the exact integer solver so
the D3.2 smallest-smaller-side-vector tie rule and the 100,000-cell
capped/partial semantics are unchanged. Verdicts and counts stay asserted-only:
`PairingPair.cost`/`total_cost`/`positional_cost` remain the asserting-cell
sums, and the new `SOURCE_PAIRING_ALGORITHM` traces carry additive
`objective`/`objective_total`/`objective_positional` triples with monotonicity
bound to the objective (the v1 asserted-monotonicity provably cannot hold —
identity may legitimately cost more asserting cells than file order; persisted
v1 payloads keep their own invariants and stay readable). The 197 HSL half
landed in the same batch (`_v` gains the openpyxl-equivalent OOXML decode).
Corpus proof on the ssor-prod 7.9 pair + the bound 12-PDF TSN build: the
PRODUCT engine is now ORACLE-EXACT on all three Highway Sequence legs — shape,
all-field, asserted, and per-field tables (Excel 4,894 rows / 5,589 cells
{Desc 4,894, FT 695}; PDF 4,916 / 5,001 {4,916, 85}; same-source 1,410 /
3,721) — with zero residue. Family re-bless: RD (3 legs, the one 101/LA/1.284
group) and ID (3 legs, 16/16/18 groups) pair byte-identically under both
objectives — no count moved; HL Route-1 is exact on the locked
299/18/69/221/969 canary, and the June statewide diagnostic pair re-pairs
57/1,002 groups toward full-content identity (asserted cells in changed groups
457→500, one-sided membership moves 96 TSMIS/16 TSN rows — the
verdict-follows-identity direction this finding mandates; measured, not
canary-bound). Highway Detail statewide was NOT re-measured (no consolidated
input on the dev PC; its golden fixtures pass) — re-measure before any HD
statewide re-bless claim. Fixtures: `check_compare_pairing_policy`
(component semantics, the source-identity fixture, the finding's per-field
mutation tests, the asserted-exceeds-positional class),
`check_comparison_contract` (v2 round-trip, legacy-payload compat, the
rejection matrix), `check_comparison_sidecars` (v2 persistence),
`check_compare_cancellation` (the new cost seam). Profile under the cap:
316×316 all-distinct strings 17.4s (a shape no real corpus produces; largest
real group ≈ 12), realistic near-cap 1.1s, the 1×100,000 boundary 0.9s.

### CMP-AUD-221 — residual assignment classification is structurally tautological

Priority: P1  
Status: Remediated and verified in two byte-identical hardened classifier replays  
Primary code: `build/probe_phase8_highway_sequence_product_residuals.py:1228-1328,1762-1805,1856-1857`

The cache-backed residual classifier correctly reconstructs all four persisted product
pair maps and the aggregate projection-plus-assignment arithmetic. It does not,
however, prove its stronger `all_residuals_classified` claim for duplicate assignment
changes. Every changed group is unconditionally seeded with
`PRODUCT_ASSERTED_ONLY_VS_SOURCE_ALL_FIELDS_ASSIGNMENT_POLICY`, and the function
unconditionally returns
`all_pair_map_differences_have_recomputed_policy_cause=true`. Assignment records have
no unexplained branch and are never added to the top-level unexplained ledger; only
fixed-projection and source-population records can reach that ledger.

An independent two-by-two duplicate fixture replaced the recomputed product pairing
with an arbitrary pair swap. `_assignment_residuals` still returned one changed group,
the asserted-policy cause, the true all-caused flag, and no `unexplained` key. Therefore
the replay-stable 2,475,505-byte artifact remains useful measured evidence for exact
maps/counts, but its zero-unexplained assignment wording is not promotable.

Correction requirements: recompute the claimed product and source objectives inside
the classifier, require each persisted pair/membership change to equal the deterministic
result of the named objective, and place every mismatch into an explicit assignment
unexplained ledger that participates in terminal status. Mutations must inject an
arbitrary swap, tie-break drift, membership move, and wrong cause and prove all four are
rejected before the authentic four-leg result is promoted.

Execution disposition: the hardened classifier recomputes both source-all-field and
product-asserted-only optima for every changed duplicate group, proves the persisted
source/product selections equal those deterministic optima, and gives assignment
residue its own terminal unexplained ledger. All authentic changes prove exactly:
445 Excel/raw, 448 Excel/normalized, 357 PDF/raw, and 360 PDF/normalized. An arbitrary
3-by-3 swap now fails with
`PRODUCT_PAIRING_IS_NOT_RECOMPUTED_PRODUCT_OPTIMUM` and one unexplained record (ledger
SHA-256 `d264fc96a39817ec1ed4ab2f0f30cd4e430dc502c712f2b3daeeaf70c7af4261`).
Independent hardened replays r3/r4 are byte-identical at 3,509,121 bytes / SHA-256
`f6fa06569b28cdba66d059e6e9c9f40b4464149754a2561075b02c6c0307c8cc`;
zero unexplained residue remains under the executable attribution contract.

### CMP-AUD-222 — resolving a path before `is_symlink` defeats the indirect-input guard

Priority: P2  
Status: Remediated and verified with real Windows file/directory link mutations  
Primary code: `build/probe_phase8_highway_sequence_product_residuals.py:279-281,327-329,727-728`

Three input helpers call `Path.resolve()` and only then check `not path.is_symlink()`.
Resolution dereferences the link, so the predicate observes the ordinary target rather
than the supplied indirect path. The result therefore advertises an indirect-input
rejection that the code cannot provide. This did not alter the current frozen-input
arithmetic, but it prevents the harness from being promoted as a strict ordinary-file
source gate.

Correction requirements: reject symlinks/reparse points on the supplied path before
resolution, bind the resolved canonical target separately, and repeat the guard for
every parent/output relationship that matters. Add a real platform-supported file-link
fixture plus an ordinary-file control; if Windows link creation is unavailable, the
gate must report that mutation unexecuted rather than claim it passed.

Execution disposition: supplied paths are now inspected as supplied for ordinary-file
and reparse/link status before canonical resolution; each parent component is also
checked. The hardened run creates disposable Windows file-symlink and directory-symlink
fixtures and requires both to reject. The platform supported both probes and both
passed in each independent r3/r4 replay; no skipped probe was promoted as executed.

### CMP-AUD-223 — aliased output can overwrite a frozen classifier input after validation

Priority: P1  
Status: Remediated and verified with hardlink, lexical, and bound-input output rejections  
Primary code: `build/probe_phase8_highway_sequence_product_residuals.py:1551-1562,1807-1808,1861,1878-1880`

The CLI accepts any `--output`. The last frozen-input recheck occurs before publication,
then `_write_atomic` replaces the requested path with the result. There is no
canonical-path, `samefile`, file-ID, or input-universe exclusion for the output. Passing
one of the bound cache/result/workbook paths as `--output` therefore overwrites that
input after the audit has declared the before/after guard stable. The destructive
reproduction was intentionally not executed because the control-flow proof is exact.

Correction requirements: validate the requested output and temporary publication
directory against every bound input and source tree before reading begins and again
immediately before replacement; reject canonical aliases, hard links, symlinks/reparse
points, parent/child collisions, and case variants. Exercise the rejection safely with
disposable copied inputs, including direct alias, hard-link alias where supported,
symlink alias, and ordinary distinct-output controls.

Execution disposition: the hardened output guard compares the requested path against
all 19 consumed/protected artifacts before probes, binding, or writing and repeats the
check before publication. Disposable hardlink and lexical-alias mutations reject. A
real invocation naming the authoritative `source_rows` input as `--output` exits 1
before any read/write work; its SHA remains
`564cf21972aeaf461811095997524c2d02f3ca4f238bb8da8b715415df2762f8`.
The independent r3/r4 full replays also repeat these guard probes and produce identical
hardened result bytes. This remediation is confined to the non-acceptance audit
classifier; CMP-AUD-225 separately remains open for product-witness root containment.

### CMP-AUD-224 — raw equate topology is asserted only in the forward direction

Priority: P2  
Status: Remediated and verified in direct-source raw-twin r6/r7; family acceptance pending  
Primary code: `build/phase8_highway_sequence_comparison.py:1587-1625,2294-2307`,
`build/build_phase8_highway_sequence_raw_tsn_direct_twin.py:519-637,1158-1170,1268-1293`

The direct-source checkpoint walks every raw `EQUATES TO` annotation and requires the
immediately following same-owner data row to carry an `E` postmile suffix. That proves
998 annotation-to-data links, but it never performs the reverse census from every
data-`E` row back to a preceding annotation. A mutation can change an unrelated data
postmile to an `E` suffix while leaving the forward count and predicate green.

Independent review of the bound 69,804 raw records establishes that the current source
is clean: 998 annotations, 998 data-`E` rows, and zero data-`E` rows without an immediate
owned annotation. This finding therefore does not change any source count or pair map;
it prevents the one-directional predicate from being promoted as a bijection proof.

Correction requirements: the final direct-PDF gate must persist both directional
ledgers, require exact one-to-one membership and owner/order agreement, and reject at
least one mutation that creates an additional unpreceded `E` row without changing the
annotation count. The existing annotation/following swap mutation remains necessary
but is not sufficient by itself.

Execution disposition: the corrected direct-source raw-twin builder persists both
directional ledgers and requires their exact membership/order agreement. Final r6/r7
each bind 998 annotations, 998 data-`E` rows, 998 pairs in each direction, and zero
unpaired rows. Its reverse-only mutation leaves the 998 forward links valid while
creating 999 data-`E` rows, 998 reverse pairs, and one orphan; the gate rejects it.
The two complete roots reproduce identical builder outputs. This resolves the defect
for the direct-source audit-input twin only: its result explicitly sets
`acceptance_eligible=false` and `stage8_family_accepted=false`, so product comparison,
evidence, permanent-gate, detached-decision, and final family replay work remains.

### CMP-AUD-225 — a clean witness output can still contaminate a bound input tree

Priority: P2  
Status: Remediated and verified in final direct legs and two family-gate replays  
Primary code: `build/run_phase8_highway_sequence_product_comparison_leg.py:201-224`,
`build/run_phase8_highway_sequence_product_raw_tsn_leg.py:472-482`,
`build/build_phase8_highway_sequence_raw_tsn_direct_twin.py:231-392`

The shared one-leg root helper requires only that the requested directory be absent and
resolve beneath the private audit root. It never compares the candidate root with the
bound consolidated-source, normalized-TSN, or raw-twin roots. A caller can therefore
place a new comparison directory inside one of those input-artifact directories. All
bound input files remain byte-identical, so the before/after input guard and the output
root's own flat artifact census both pass while the input tree has gained unrelated
publication files.

This is distinct from CMP-AUD-223: no input file need be replaced. The defect is source-
tree contamination and an incomplete disjointness claim in the audit harness. It does
not change the already observed product counts because the recorded runs used separate
roots.

Correction requirements: the direct-source witness must prove its output root is
disjoint from every bound input file and input-artifact/source directory in both
directions, reject canonical aliases and reparse points, freeze the relevant input tree
universes before and after execution, and mutation-test child-of-input, parent-of-input,
same-root, link-alias, and valid-sibling placements using disposable fixtures.

The first direct-twin builder draft partially narrows this problem by rejecting an
output nested under the authoritative raw source root and exact static-file aliases,
but it still allows an output child inside the Stage-6/normalized artifact directories
and does not enforce the private visual-root boundary. Its corrected output-root gate is
therefore part of this same finding and must pass the same two-way disjointness/tree-
stability mutations before the direct twin is promotable.

Execution disposition (builder half only): the corrected direct-twin builder first
walks every existing lexical component without resolving it, then requires the output
to remain below the private visual root and be disjoint in both directions from the raw
source root, every bound static artifact, and each bound artifact's parent tree. Its
controls reject raw-tree children, static-tree children, `..` aliases, and a real
multi-level directory-symlink component while accepting a valid private sibling. Final
r6/r7 reproduce identical artifacts with these controls green. The two one-leg runner
helpers named above have not yet been corrected and replayed against the same contract;
that runner half remains pending and this finding does not confer family acceptance.

### CMP-AUD-226 — direct-twin XLSX canonicalization leaves volatile core metadata

Priority: P2  
Status: Remediated and verified by delayed/full twin builds and final family replays  
Primary code: `build/build_phase8_highway_sequence_raw_tsn_direct_twin.py:792-919,921-987,1294-1300`

The direct raw-TSN twin draft sets fixed workbook created/modified properties before
save and then canonicalizes ZIP member order, ZIP timestamps, attributes, extras, and
comments. openpyxl nevertheless rewrites the `dcterms:modified` core property to the
current time while saving. The canonicalizer copies `docProps/core.xml` unchanged, so
the package still varies even though every ZIP-level timestamp is fixed.

An independent in-memory reproduction called the draft `_build_workbook` twice over the
same one-row payload 1.2 seconds apart. The packages differed: SHA-256
`ac78f7ec4c1da15e6f7419a780cbc20a958f89ef5bc156964ae139ee7b797db4`
versus `103d4212dfac12323daf08c528f1c3062d7b6511bc1693c6a82a3974814cbbe3`.
Their only observed core-property change was `2026-07-14T08:07:12Z` versus
`2026-07-14T08:07:13Z`; the intended fixed created time remained stable.

Correction requirements: canonicalize the core-property XML itself to the declared
fixed modified time after openpyxl serialization, fail if the expected single modified
node is absent/duplicated/malformed, and bind its member digest in the package ledger.
Two delayed in-memory builds and two full 69,804-row direct-source roots must be byte-
identical; a planted modified-time mutation must fail the canonical package gate.

Execution disposition: the corrected canonicalizer requires exactly one `created` and
one `modified` core node, rewrites both to `2000-01-01T00:00:00Z`, and then fixes ZIP
member order, timestamps, attributes, extras, and comments. Delayed 1.2-second in-memory
builds are byte-identical. A planted modified-time package is rejected by the exact core
contract and recanonicalizes to the original bytes. Full r6/r7 workbooks are identical
at 2,422,010 bytes / SHA-256
`68b28921c4ca8290810c92653b4a96077d6a28bdb7954447c287cf3e78d3f67d`;
all four artifacts in each root are byte-identical. This resolves direct-twin package
determinism, not Highway Sequence family acceptance.

### CMP-AUD-227 — direct-twin plain-file checks ignore reparse parent components

Priority: P2  
Status: Remediated and verified with real reparse mutations and final family replays  
Primary code: `build/build_phase8_highway_sequence_raw_tsn_direct_twin.py:190-216,231-392`

The first direct-twin draft calls an input plain when `Path.is_file()` is true and
`Path.is_symlink()` is false. It does not inspect the supplied entry with `lstat`, test
Windows `FILE_ATTRIBUTE_REPARSE_POINT`, or walk parent components. A directory symlink/
junction above an ordinary child file therefore passes. The check that `RAW_ROOT.resolve()`
equals `stage6.RAW_DIR.resolve()` adds no independent protection because both constants
name the same supplied path and resolve through the same redirection.

The captured bytes remain SHA-bound, so this does not contradict any current row fact.
It does make the claimed ordinary-source origin and anti-indirection boundary incomplete,
which blocks final promotion of the direct fixture.

Correction requirements: inspect the supplied file and each existing parent component
without following links, reject symlink/reparse entries before canonical resolution,
and persist both lexical and canonical paths only after that proof. Real disposable
file-symlink, directory-symlink/junction-parent, ordinary-file, and unsupported-platform
cases must execute or be truthfully reported as unexecuted; a skipped mutation cannot
be counted as passed.

Execution disposition: the corrected builder uses `lstat` plus Windows
`FILE_ATTRIBUTE_REPARSE_POINT` on every existing lexical component before its first
canonical resolution, for the output path, raw source tree, and bound static inputs.
Its executed disposable control plants a directory symlink multiple levels above the
candidate output, proves the alias is a reparse point, rejects it during the lexical
walk, and removes the fixture. Final r6/r7 pass the same guard and reproduce all four
artifacts byte-for-byte. This resolves the builder defect; it does not substitute for
the still-pending CMP-AUD-225 runner correction or the family acceptance chain.

### CMP-AUD-228 — direct runner follows aliases before its claimed lexical capture

Priority: P2  
Status: Remediated and verified in final direct legs and two family-gate replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:245-279,430-479,2007-2025`

The first direct raw-product runner draft describes its component inspection as
non-following, but `_existing_components` calls `Path.exists()`/`Path.is_symlink()`
before `os.lstat`. `Path.exists()` follows the candidate, so the claimed first
non-following operation is already false even when the later `lstat` and disposable
link probes happen to reject the tested aliases. This is runner-specific and distinct
from the corrected direct-twin builder under CMP-AUD-227.

The same class recurs at the final publication boundary. `_revalidate_final_chunks`
calls `path.resolve(strict=True)` and passes the resolved target into `_capture_file`.
A planted chunk symlink/reparse is therefore erased before the lexical plain-component
check, and the target can sit outside the output root while satisfying the recorded
chunk length/hash. The earlier generic alias controls do not exercise this final-chunk
call path.

Correction requirements: obtain each existing lexical component by direct `lstat`
(treating `FileNotFoundError` as the first absent component) without any follow-semantic
predicate or resolution first. Final artifacts must be selected by an exact flat name,
captured through the supplied lexical path, proved ordinary/non-reparse at every
component, and proved contained below the output root before and after capture. Execute
an actual disposable final-artifact chunk symlink/reparse mutation and require rejection
before target bytes are read, alongside ordinary-file, directory-link, file-link, and
broken-link controls. Product launch remains held pending the corrected full rerun.

Frozen-candidate disposition: the 183,748-byte candidate at SHA-256
`507237e47dcd2d043fdb3320ed6db18a3926e136ffd2c014b39e1df667703643`
corrected the general component walk and final flat-artifact capture, but independent
review still found `_capture_audit_code` constructing `REPO_ROOT` with
`Path(__file__).resolve()` and resolving each expected/reported audit path before its
lexical `_capture_file`/`lstat` proof. The full r7 preflight was green because the real
paths are ordinary; it does not mutation-prove this remaining call path. That candidate
was rejected before either product leg or output root was launched.

### CMP-AUD-229 — terminal PASS is published before post-result validation finishes

Priority: P1  
Status: Remediated and verified in final direct legs and two family-gate replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:2133-2255`

The runner serializes `result.json` with `terminal=true` and status
`PASS_DIRECT_SOURCE_AUDIT_INPUT_NOT_FAMILY_ACCEPTANCE` before its final residue census,
artifact-name check, payload-chunk revalidation, post-result frozen-input check, and
output/input disjointness check. Any later check can fail the process while leaving a
durable terminal PASS artifact in the output root. The result even states that
post-result revalidation is required for process success, but it cannot record whether
that still-fallible work actually passed.

Correction requirements: no durable artifact may claim terminal PASS until every
fallible publication, input-stability, containment, and final-universe predicate has
completed. Use a clearly nonterminal provisional record or a detached terminal decision
published exclusively as the last success action, and ensure every failure path leaves
no PASS-looking artifact. Mutation-test failures in each formerly post-result predicate
and prove both nonzero process outcome and absence of terminal success. Stage 8 and the
direct product launch remain held until the corrected lifecycle replays cleanly.

### CMP-AUD-230 — final success does not rehash the complete declared artifact universe

Priority: P1  
Status: Remediated and verified across all 20 direct artifacts and two replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:1981-2025,2115-2244`

The pre-result artifact manifest hashes the files that exist before `result.json`, and
the terminal residue pass later checks names and revalidates the decoded payload chunks.
`_revalidate_final_chunks` is the only final exact-byte recapture. The formula/value
workbooks, both outcome sidecars, permanent lease, loaded-product-code manifest,
artifact manifest, and terminal result are not all reopened and length/SHA-checked at
the final success boundary. An ordinary same-name artifact can therefore change after
its earlier check without being covered by the runner's final-success claim.

Correction requirements: define the exact terminal flat-file universe and lexically
recapture every member without following aliases. Reconcile every final length/SHA
against one authoritative terminal manifest, including workbooks, sidecars, chunks,
lease, audit manifests, result, and any detached decision; handle self-reference with an
explicit exclusion/binding relationship rather than silently omitting files. Plant
post-manifest mutations in every artifact class and require terminal rejection. Those
mutations must name the actual product outputs `comparison.xlsx`,
`comparison (values).xlsx`, and both corresponding `.outcome.json` sidecars rather than
synthetic aliases that never enter the production universe. Final success cannot be
emitted until the complete universe is stable and exact.

### CMP-AUD-231 — direct-v1 validation permits extra top-level contract fields

Priority: P2  
Status: Remediated and verified by exact-v1 mutations and final replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:669-695,1617-1750`

The runner's strict JSON decoder rejects duplicate keys and several nested objects use
exact `_require_keys` sets, but the top-level direct-twin result, manifest, and provenance
objects are validated only through selected `.get()` predicates. Their complete v1 key
universes are never asserted. Extra top-level fields can therefore enter the accepted
contract even when they introduce a second status, acceptance, count, source-role, or
output-root claim that the runner ignores.

Correction requirements: declare and enforce exact versioned top-level key sets for all
three direct-v1 documents before interpreting any field. Missing and extra keys must
fail with a precise ledger, while the existing duplicate-key rejection remains. Add
mutations for plausible conflicting acceptance/status fields, alternate count/source
ledgers, and an embedded output-root/path claim. Re-run the complete direct-twin
preflight after correction; current validation remains non-promotable.

### CMP-AUD-232 — direct raw witness omits its audit runner and helper-code identities

Priority: P1  
Status: Remediated and verified with exact four-role code bindings and final replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:32-43,1886-1900,2561-2564,2608-2840`,
`build/run_phase8_highway_sequence_product_comparison_leg.py:485-532`,
`build/run_phase8_highway_sequence_product_raw_tsn_leg.py`

The direct raw-product witness pins and captures the final direct-twin builder and writes
a manifest for loaded product modules under `scripts/`. It does not capture or bind its
own `__file__` bytes. The two imported audit helpers under `build/` supply stable-identity,
publication, validation, and raw-payload decoding logic, but the scripts-only loaded
product manifest excludes them as well. The preterminal record and detached completion
can therefore authenticate product code and source-builder code without proving which
audit-runner/helper bytes interpreted those inputs and published the witness.

This is also a stability gap. The missing audit-code set is not re-statted or rehashed
before preterminal publication and detached completion. A runner or helper could change
after its logic was imported while the completion still carries no before/after identity
or drift signal. The final family verifier would have nothing exact to pin for the gate
that produced each direct leg.

Correction requirements: define the exact named audit-code universe as the direct runner,
`run_phase8_highway_sequence_product_comparison_leg.py`,
`run_phase8_highway_sequence_product_raw_tsn_leg.py`, and the final direct-twin builder.
Capture each ordinary lexical file by stable stat + exact bytes/SHA before product import,
repeat the capture immediately before preterminal publication and detached completion,
and require exact equality. Each role must also prove that its physical path is exactly
the declared repo-relative runner, comparison helper, raw-TSN helper, or direct builder;
same-byte substitutes at another path are not valid role provenance. Embed the
repo-relative role plus bytes/SHA ledger in both records without volatile absolute paths,
and make the final-family gate pin the exact ledger. Execute copied-file mutations for
each of all four roles, plus mid-run replacement/drift, while preserving unchanged
positive controls; every mutation must fail without leaving a terminal completion.
Correction and a fresh full runner replay remain pending.

Frozen-candidate disposition: SHA-256
`507237e47dcd2d043fdb3320ed6db18a3926e136ffd2c014b39e1df667703643`
does capture and revalidate four roles and rejects byte mutations of copied fixtures, but
its completion validator checks the claimed audit ledger only for internal
shape/order/digest and equality with the preterminal copy. It never compares the
candidate payload ledger with the freshly captured physical four-file manifest. The
final callback compares live code with a closed-over baseline, not with the payload's
claim. Its one completion mutation corrupts a SHA without recomputing the aggregate or
preterminal claim, so it cannot reject a consistently fabricated ledger. The corrected
publisher must receive/bind the exact expected physical ledger, and each coherent
four-role mutation must recompute internal metadata so rejection proves external
binding rather than a stale checksum.

### CMP-AUD-233 — final output members are not proved physically distinct from bound inputs

Priority: P1  
Status: Remediated and verified with physical-distinctness controls and final replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:361-389,2213-2260,3122-3195`

The direct runner proves that its output root is path-disjoint from every protected input
root/file and rejects a hardlinked *output-root candidate* during its disposable
containment controls. That does not prove the files later placed inside a valid sibling
root are physically independent. `_capture_file` records device/inode, type, size,
times, and Windows attributes internally, but it neither rejects `st_nlink > 1` nor
compares a captured final member with every bound input through `os.path.samefile`.

The complete flat-output capture therefore accepts an ordinary same-name workbook,
payload chunk, sidecar, manifest, or zero-byte publication lease whose bytes/hash match
the declaration even if that member is a hard link to a protected input. Root-level
containment remains green because the member's pathname is below the output root, while
mutating either link would still mutate the shared source object. The current final
manifest publishes only relative name, length, and SHA and cannot reveal this alias.

Correction requirements: at output creation, precompletion capture, terminal staging,
and immediately before terminal commit, require every output member to be physically
distinct from every bound input and audit-code file. Reject `samefile` equality and
unexpected multi-link state (`st_nlink > 1`, with an explicit platform contract) before
trusting bytes; persist a path-neutral physical-distinctness ledger in the preterminal
record and completion. Execute a real disposable mutation that replaces a final
workbook/chunk/lease with a hard link to a protected file and require rejection before
any terminal completion is committed. The product launch remains held pending corrected
full replay evidence.

### CMP-AUD-234 — detached publisher does not authenticate the completion contract it commits

Priority: P1  
Status: Remediated and verified by 30 semantic mutations, final legs, and two replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:2340-2481,2500-2875,3287-3345`

The detached completion publisher now verifies its staging bytes, exclusive final rename,
declared final filenames, the precompletion artifact identities, frozen inputs, audit-code
stability, and physical disjointness. Those are necessary publication controls, but the
publisher does not validate the semantic completion document it is about to make
authoritative. It canonicalizes any mapping whose
`expected_final_artifact_names` includes the destination and whose
`complete_output_artifact_manifest` has the minimal expected shape. Its successful
publication control demonstrates this with a disposable payload whose status is unrelated
to the production direct-leg contract. The separate `preconditions` argument cannot
authenticate the payload's claimed status, terminal/acceptance boundary, leg, audit-code
ledger, preterminal result, manifest totals, or final-universe relationship.

Consequently a hostile payload can retain mechanically valid filenames and member hashes
while claiming a different terminal status, `acceptance_eligible=true`, family acceptance,
the wrong leg, a fabricated or incomplete audit-code ledger, an unbound preterminal result,
or inconsistent complete-manifest counts. The exclusive rename would still commit it as
the last action. Main currently constructs the intended document before calling the
publisher, but the trusted commit boundary itself does not prove that the bytes reaching
it are that exact contract; a future/corrupted call or mutation can therefore turn sound
publication mechanics into an authoritative false claim.

The first corrective draft was also rejected before launch because it pre-populated the
claimed semantic-mutation labels and `left_no_terminal_file=true` in its disposable
control payload without actually executing those mutations. That draft could therefore
make the new validator agree with invented audit evidence. The corrected candidate must
derive the published label census only from real per-label publisher failures, verify no
completion or pending file after every failure, and compute the aggregate control result
from the observed outcomes. No direct product output existed when this was found.

The next frozen candidate did execute 12 real mutations, but independent review still
rejected that matrix as incomplete. The publisher accepts either enumerated leg and only
checks agreement with the preterminal copy; it receives no externally expected leg.
There is no real wrong-leg mutation, nor executed semantic mutations for output-root,
artifact-status, invariant, payload-chunk universe, terminal-residue, post-result tree,
containment-evidence, or audit-mutation-evidence claims. Its audit-code mutation is also
internally incoherent rather than an all-four-role externally bound test. A structurally
green aggregate therefore remained insufficient. SHA-256
`507237e47dcd2d043fdb3320ed6db18a3926e136ffd2c014b39e1df667703643`
was held before any product output; the next correction must execute and derive the
complete branch matrix and bind the caller's exact expected leg and audit-code manifest.

Correction requirements: add one exact versioned `completion-v1` semantic validator and
invoke it on the actual payload immediately before serialization/publication. Enforce the
complete top-level and nested key universes; exact non-family-acceptance status;
`terminal=true`; `acceptance_eligible=false`; `stage8_family_accepted=false`; exact leg;
the exact four-role audit-code ledger and repo-relative role identities; the exact bound
nonterminal result; exact manifest member names, lengths, hashes, aggregate byte/member
totals, and canonical digest; exact final universe; exact true invariant and precondition
sets; and agreement among every repeated claim. Run permanent semantic mutations for each
field class, including all four audit-code roles with unchanged positive controls, and
prove rejection before a staging file or terminal completion exists. CMP-AUD-230's
artifact-class mutations must use the actual product names `comparison.xlsx`,
`comparison (values).xlsx`, and both `.outcome.json` sidecars. No direct leg may launch
and no completion may be promoted until the corrected publisher and full runner replay
are independently green.

### CMP-AUD-235 — Windows directory-size hydration falsely rejects frozen trees

Priority: P2  
Status: Remediated and verified by retained-field/member mutations and final replays  
Primary code: `build/run_phase8_highway_sequence_product_direct_raw_tsn_leg.py:452-463,585-648`

The corrected direct runner's exact tree snapshot uses the same `_stat_token` for
ordinary files and directories. File size is a required identity field, but Windows can
report an unenumerated NTFS directory with `st_size=0` and then report `st_size=4096`
after the first read-only enumeration. The directory's device, file ID, type, modified
time, change/creation time, link count, and file attributes remain unchanged, as do the
complete child-name universe and every child file byte/hash. Treating the directory
size transition as source mutation makes a clean preflight fail depending only on
whether that directory was previously touched.

This was reproduced adversarially rather than inferred. Three consecutive full r7
preflights failed closed on three different first-touched `consolidated`/converted
directories before any product import or output creation. An instrumented read-only
traversal then found exactly three more transitions, each solely `st_size: 0 -> 4096`,
across 15 files / 20,967,716 bytes; all other directory-stat fields were identical.
Immediate before/after probes on already hydrated directories were stable. No source
member, source digest, or artifact universe changed.

Correction requirements: retain the existing full file token, stable-stat byte capture,
recursive exact name/type universe, per-file length/SHA, and reparse rejection. Introduce
a directory-specific token that excludes only `st_size` while retaining device/file ID,
type, modified/change times, link count, and attributes. Mutation-test that a size-only
directory-stat change is accepted, while changes to every retained directory identity
field and any added/removed/changed member are rejected. Re-run the full r7 preflight
from the exact authoritative inputs before either direct product leg launches.

### CMP-AUD-236 — an external audit ceiling interrupted Highway Log Excel publication

Priority: P2  
Status: Remediated; rejected attempt preserved and clean r2 completed  
Primary code: audit-process wrapper around
`build/run_phase8_highway_log_product_comparison_leg.py`; no product-code defect

The first isolated Highway Log Excel-vs-TSN attempt was terminated by its external
1,200-second shell ceiling after 1,200.7 seconds while the product publisher was still
working. The stopped root contains only `comparison (values).xlsx` at 97,123,576 bytes,
SHA-256 `bcb61cd3e33075dddcbd7671a818e205faa7a343c900f053b108426198b2151a`,
and `comparison.tmp-2ac56ad46964.xlsx` at 254,174,524 bytes, SHA-256
`76fc2208bb5614e8caa199a34dca0c6bf0027419e06790d0794e4ea01a4913dd`.
It has no outcome sidecars or `result.json`. It was therefore never accepted as a
product result and provides no terminal comparison claim.

The audit orchestration was corrected by using an absent r2 output root and a ceiling
longer than the measured statewide build. The clean r2 completed with an exact
seven-file publication universe and terminal result SHA-256
`028c9caeedd1a080150f0dc96739b4641190af6b564ca2d5d2ab7f7195adabab`.
The final family gate accepted only that clean r2 result. No application or comparison
source was changed for this audit-process correction.

### CMP-AUD-237 — the audit consumer imposed an unsupported JSON newline convention

Priority: P2  
Status: Remediated and verified by no-LF producer artifacts and final gate replays  
Primary code: `build/run_phase8_highway_log_product_comparison_leg.py:116-146`

The first isolated PDF-vs-TSN product generation completed both workbook twins, both
outcome sidecars, the payload chunk, and the publication lock. The audit wrapper then
rejected the completed publication solely because its JSON reader required compact,
canonical JSON followed by LF. The product outcome sidecars were valid compact canonical
JSON without a trailing LF. Separately, the accepted Stage-6 result is valid
pretty-formatted JSON whose exact byte identity is already frozen and whose semantic
contract is independently validated. Formatting style was not a producer promise for
either artifact class.

The audit consumer now accepts the exact compact canonical bytes either with or without
one trailing LF for product sidecars, while retaining strict schema, identity, generation,
payload, and semantic validation. Exact SHA-256 bindings remain authoritative for the
accepted Stage-6 record, and the final gate enforces canonical serialization only on
artifacts whose own audit contract requires it. The corrected PDF r2 terminal result is
SHA-256 `5df98a2233986a7665f6cdfe181c2e22e479d5d5985ae4c5aca763755cdb3227`.
This was an audit-consumer overconstraint, not a product comparison correction.

## Phase-4 oracle-gate second-review disposition

These were defects in the audit gates, not permission to change source facts. Ramp v3
and Intersection v2 now close the first five with fresh source-bound full-corpus results:

- Resolved: Intersection date equivalence is directional; reverse Excel-flag mutations
  fail and only PDF-added `Y`/`*` on the same unflagged date are render-equivalent.
- Resolved: Intersection Description truncation requires the measured exact 32-character
  boundary, including the exact character-32-space case; shorter/wrong limits fail.
- Resolved: Ramp binds exactly four `(cid:13)` identities/page-rows/raw strings and fails
  missing, extra, moved, or changed artifacts.
- Resolved: Ramp reports the last PDF content character's endpoint and makes no claim
  about measuring an absent Excel character.
- Resolved: Ramp gives all 18 XLSX columns exactly one printed/relational/source-only
  disposition; the source-only value conservation itself remains Stage 6.
- Resolved: Highway Detail's first all-12 oracle paired duplicate physical identities by
  ordinal occurrence. D03 has four raw versus two printed occurrences under one identity,
  and a D11 duplicate pair prints in reverse workbook order. The final oracle uses
  maximum-cardinality/minimum-content-difference assignment across all 77 collision
  groups, binds the exact two XLSX-only occurrences and 441 field deltas in a 443-item
  allowlist, and passes ten internal negative mutations with zero unresolved residue.

Ramp result SHA-256
`47383b5d00ed4b72fa72ed711d165c0ec633d2d7c8f86edd695f4f0a2e886ed1`
and Intersection result SHA-256
`63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e`.
Highway Detail result SHA-256
`540b1ce575be880f506ebc435acaabe253e238f4eba312a72a310129f4ecdc36`
and exact allowlist digest
`d101bc1263188dcb436a9218bad6774ab047368e819c205d1e53b9b812b56d8a`
complete the three accepted source-format permanent gates with zero unresolved residue.

## Candidates awaiting independent reproduction

| Candidate | Current evidence | Required next probe |
|---|---|---|
| CMP-CAND-001 | Highway Sequence PDF and Ramp Detail PDF comparator checks do not exercise an end-to-end adversarial comparison | Plant independently computed per-field mutations and wrong-role/layout inputs through both adapters before deciding whether a product defect exists |

## Verification log

### 2026-07-14 — Highway Log Stage-8 base-family audit closed without product remediation

- Bound all 252 current TSMIS Excel files (59,441,628 bytes; manifest
  `f9cafb2958842550b2eeefd2117b061db45d8a02ace51428d5c97b68f8e9155e`) and all
  252 current TSMIS PDF files (36,545,107 bytes; manifest
  `26fec6f7fec944681c96d7970ae6ed5c2791f173379c1e74ce050f44484c9d15`), with exact
  route-token parity.
- Bound normalized Excel/PDF/TSN workbooks at SHA-256
  `329ccf68caf0c476d9360cb69dd28c0ab78a588d0e9bd9c816d5b484444fd660`,
  `17c04bb7400eded5c7b372d4ca87728735f8481fd37394c592e7dd0180f0333d`, and
  `fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa`.
  Source witness, accepted Stage-6 result/decision, and independent-oracle result are
  respectively SHA-256 `4fc4009c5b3be05b0be3d90cab5823e8397d34d623543a6215a03a238c27b8a1`,
  `f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4`,
  `012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61`, and
  `3b778c089e2070f4da9bea82aa0584b8bc4c35840dd0273fef1b2cd9f8c6a121`.
- Excel-vs-TSN completed at 48,094 paired, 3,790 Excel-only, 11,989 TSN-only,
  39,466 differing rows, 140,333 differing cells, 1,430,451 asserted cells, and
  12,369 context cells. PDF-vs-TSN completed at 48,096 paired, 3,790 PDF-only,
  11,987 TSN-only, 39,463 differing rows, 139,786 differing cells, 1,430,511
  asserted cells, and 12,369 context cells.
- Every per-field count matched the independent oracle. Each leg's 989 exact duplicate
  assignments matched the oracle manifests
  `435d1ab1f8909225396ba0461790c5053893dddd4152acb13b36f1566a2650a1` and
  `e287bad0bea608b7adc919a602f2f3ddfb8a1562311e80b72c364e1063a4f3d0`.
- Clean Excel/PDF r2 result hashes are
  `028c9caeedd1a080150f0dc96739b4641190af6b564ca2d5d2ab7f7195adabab` and
  `5df98a2233986a7665f6cdfe181c2e22e479d5d5985ae4c5aca763755cdb3227`;
  both exact seven-file publication universes, payloads, sidecars, workbook twins, and
  loaded 12-file product-code manifest were revalidated by the final gate.
- Two clean final-gate replays produced byte-identical 9,036-byte results at SHA-256
  `7acf9986055750bbc49be0d4fa422329d06893f379da0cd6ded945936549860b` and
  byte-identical 839-byte acceptances at SHA-256
  `170d622d751e96e97c7f8420c0a60172e57a31838a3d1b3de090c76972dd62b6`.
- The accepted scope is only `accepted_stage8_base_family_audit_only`.
  `stage8_family_accepted`, `product_comparison_perfect`,
  `product_end_to_end_perfect`, `comparison_end_to_end_perfect`,
  `full_physical_identity_perfect`, `workbook_cell_evidence_end_to_end_exact`, and
  `evidence_end_to_end_exact` all remain false. No product code was changed.

### 2026-07-12 — Stage-6 raw-to-normalized conservation in progress

- Re-read `CLAUDE.md` and the owner-facing project/source/canary ledgers after the task
  interruption. A fresh read-only `tsn_library` inventory found 54 files only in the
  declared raw/PDF roles plus README placeholders, with zero generated consolidated or
  normalized workbook members.
- Hardened the shared stdlib XLSX reader to parse only private captured bytes and reject
  error-typed cells. Its actual same-object A-to-B-to-A fixture, Ramp synthetic Stage-6
  gate, and compilation of the accepted XLSX family oracles are green.
- The original Ramp Detail result
  `d3dc1fdb6cddc2ba7c2daf634a38f3e5c50f4f078e1f5c8a9945ae98c26d91be` and acceptance
  `8e1dd321dee09cb930099d1b8bb2dde5802889978bd1f1fdd9eac09a194e67ee` are superseded for
  Description semantics. Corrected result
  `3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd` and acceptance
  `2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb` bind all 15 losses,
  pass 14/14 invariants and 6/6 mutations, and replay byte-identically. The audit is
  complete while CMP-AUD-133/CMP-AUD-135 remain product-red.
- Accepted Intersection Detail result
  `4d507661835cdd9e9267f05f7700777ba97b8a3948797ac3e436be8db8d21b88` plus detached
  acceptance `7077358da9ca016c12a4d1bc2cf8e09c95b20ac588272febf9b307f5856c7b43` after a final
  independent PASS over all 24 invariants, 25 mutations, and canonical numeric-PM
  collision counts. Three omitted source fields remain product-red.
- Rejected the first Highway Detail artifact despite an independently confirmed factual
  census, then accepted the corrected 60,083-row result
  `283315b30605461e748246444ea523542f61b0a205cd70131c73e1f6b77fb20b` and detached
  acceptance `d26dee5d11517478312cde6361c4567c30a4f8d534d822539bb36388c170cf03`
  after 23 invariants, 22 probes, and a final second-review PASS. CMP-AUD-141/
  CMP-AUD-143/CMP-AUD-147 are audit-harness remediations; CMP-AUD-138/CMP-AUD-142 and
  the other source-claim omissions retain the product defects.
- Began independent Ramp/Intersection Summary PDF conservation. Before implementation,
  the Intersection lane documented CMP-AUD-144/CMP-AUD-145 for irreversible control-
  category folding and an unproven source-to-canonical CONTROL F label change. Both
  Summary lanes independently confirmed CMP-AUD-146: printed report identity/timing/
  submitter provenance is absent from normalized artifacts even when category rows are
  exactly projectable.
- Accepted Ramp Summary result
  `38b500489c8a310529c4c7b76bea3fe7461374d6c786b992caaa458e0ef65421` and detached
  acceptance `55c43d501960d3ca3702e5eac1202f96ac6c9b3e1df2eb915b19c593669bf74c`
  after rejecting earlier parser-provenance, acceptance, and source-role candidates.
  Final proof covers 31 rows, four exact 15,410 totals, 18 invariants, 13 mutations,
  13/13 roles, 95 modules, and zero residue; only CMP-AUD-146 remains product-red.
- Accepted Intersection Summary result
  `f3a0aa0dfb15cf2ca911ec98721c8dcc0d5d9b25c0ce3cc89184d2959aaf64de` and detached
  acceptance `cdf63defdb62d2066a2cafb7229d0c1539a0c6d90f80ea1b96c07c77f609b703`
  after multiple documented false-negative/coverage reopenings. Final visual/lifecycle
  review covers all three pages, 62 source dispositions, 58/58 typed category ledgers,
  19 invariants, 17 mutations, 137 modules, and zero residue. CMP-AUD-144/145/146 remain
  product-red; CMP-AUD-148/149/150/151/154 are audit-gate remediations.

### 2026-07-12 — Phase-3 E1/E2 closure

- All 31 comparison checks passed on the frozen tree; the complete offline runner
  passed 119/119 in 95 seconds.
- The integrated 41,000 exact-duplicate-trace gate passed at the measured 16,795,872
  decoded-byte/five-chunk boundary under the final resource, crash, lease, and path
  policies.
- The clean `CORE-ID-78-XLSX-TSN` `r3` production canary completed in 762.424 seconds,
  preserved the exact 218-member manifest before/before-compare/after, and reproduced
  16,199 paired, 260/427 one-sided, 16,053 differing rows, 21,675 differing cells,
  518,368 asserted cells, and 106 exact/zero-capped duplicate groups.
- Installed Excel formula/value evidence agreed across 16,886 Comparison rows, 11
  Summary self-checks, 56 shared numeric labels, 32 Spot fields, 33,087 helpers, and
  both 43,350-row Report View totals.
- A separate verifier rehashed all 15 artifacts and 11 frozen production sources,
  found no sentinels/owner locks, and strict-read both peers trusted/current. Accepted
  result SHA-256:
  `a54448f621beb27cea4e4b7a82af1b0a65580e84c5eac6df313242959a1111b2`.

### 2026-07-10 — Chunks 0–2

- Generated isolated synthetic workbooks in formulas, values, and both modes.
- Recalculated with installed Microsoft Excel using `CalculateFullRebuild` and saved
  cached results.
- Inspected Summary, Comparison, Spot Check, Routes, Only-in, and input sheets.
- Ran the complete offline suite: 95/95 checks passed. `check_source_zip_smoke` was
  rerun outside the sandbox because Git rejected the sandbox account's repository
  ownership; its assertions passed.
- Repository worktree was clean after the audit.
- Temporary real-Excel evidence directory:
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_chunk2_audit_la3n50ba`

Primary evidence hashes:

```text
adversarial formulas  A05D5F428AA5117C039E2BBFB4FC3581BF17F576E5D894705856B320774453F5
adversarial values    ED2A97EC93A296D691C482031D871C0FA0745730A7894B85760869B7B6743734
error formulas        BA081467B7CB262D42E6A326874E03D41BC38D1FFA17A368BCF6AAE79F491CF5
error values          00F75200F1F48D77C81DCB0138AA216E7B92A32AE2125EE592CE887BF1F25E3C
```

### 2026-07-10 — Chunks 3–4

- Exercised generic folder discovery with missing keys, header-only routes, duplicate
  route files, route padding, owner-lock files, stray headers, and arbitrary folders.
- Ran all five real PDF consolidators with clean, skipped-line, and failed-PDF producer
  outcomes, then carried them through 20 cross-environment comparisons in both modes.
- Recalculated all 20 formula workbooks in real Excel; formula and values agreed on the
  same incorrect completeness verdicts.
- Built real malformed Intersection Summary XLSX fixtures and stubbed Ramp Summary PDF
  records to test cross-environment parser integrity.
- Built complete/invalid normalized aggregate universes for total reconciliation,
  numeric coercion, duplicate categories, side taxonomy, and Rural/Urban parent state.
- Relevant existing comparison, consolidation, matrix, and aggregate checks remained
  green, confirming these are coverage gaps.
- Temporary evidence directories:
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_pdf_producer_outcomes_alc76yxc`,
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_pdf_env_completeness_4yc0vgi9`, and
  `C:\Users\Yunus\AppData\Local\Temp\aggregate_audit_9eepw_eh`.

### 2026-07-10 — Chunk 5

- Exercised all four flat normalized-library loaders with semantic column reorders,
  all four consolidated TSMIS loaders with superficial/junk headers, and all three
  statewide raw-XLSX loaders with identity columns only.
- Exercised all four flat cross-environment adapters with identical malformed
  schemas, legacy schemas, blank-tail data, filename aliases, route padding, and
  county/prefix/suffix duplicate identities. Compared their results with the stronger
  domain keys used by the reconciled vs-TSN comparators.
- Ran tagged end-to-end header swaps, stale route/PM/description representations,
  PM numeric variants, malformed dates, a truncated Ramp PDF shape, same-source
  aliases, and an output/input alias through the production adapters.
- Compared Highway Detail's raw and canonical normalized TSN paths. The raw `E`
  equation marker produced one difference; the normalized path erased it and produced
  a clean match.
- Built Report View contradictions in both Detail families. Then edited clean formula
  workbooks in installed Microsoft Excel, ran `CalculateFullRebuild`, and proved the
  live Summary/Comparison/Spot Check update while Report View remains stale.
- Existing focused checks remained green:
  `check_compare_ramp_detail_tsn`, `check_compare_ramp_detail`,
  `check_compare_highway_sequence_tsn`, `check_compare_highway_sequence`,
  `check_compare_intersection_detail_tsn`, `check_compare_highway_detail_tsn`,
  `check_intersection_detail_pdf`, `check_highway_detail_pdf`, and
  `check_visual_evidence`. These are coverage gaps, not failures already caught by
  the suite.
- Primary temporary evidence directories:
  `C:\Users\Yunus\AppData\Local\Temp\chunk5_normalized_header_xsw6r3ze`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk5_tsmis_header_wbqc2ajh`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk5_raw_minimal_erbuk2w3`,
  `C:\Users\Yunus\AppData\Local\Temp\flat_tsn_audit_dlidebtt`,
  `C:\Users\Yunus\AppData\Local\Temp\tag_e2e_n96sdds8`,
  `C:\Users\Yunus\AppData\Local\Temp\pm_e2e_oceh0wsn`,
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_comparison_audit_dylo1kv0`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk5_same_input_we_4__28`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk5_output_alias_tl7rni93`.

### 2026-07-10 — Chunk 6

- Loaded the bundled real statewide Highway Log pair through production loaders:
  TSMIS PDF 50,723 rows/252 routes and TSN 60,083 rows/263 routes. Audited route
  padding, date representations, raw/canonical roadbed keys, duplicate occurrences,
  ditto distribution, and ambiguous-block fallbacks.
- The core roadbed/ditto controls held: all roadbed-block dittos were full blocks,
  explicit R/L and inferred roadbeds stayed distinct, and the 340 TSN rows with both
  blocks dittoed coincided with the documented 340-row shared AC/median ditto class.
  No partial roadbed blocks were present in either real source.
- Exercised direct per-route source identity, blank-tail truncation, canonical/vendor
  header pairs, arbitrary same-width headers, tab-padded descriptions, PDF producer
  partial outcomes, filename-versus-cover route conflicts, and duplicate-route PDFs.
- Existing focused checks remained green:
  `check_compare_highway_log`, `check_highway_log_ditto`,
  `check_highway_log_roadbed`, `check_highway_log_columns`,
  `check_compare_env_highway_log_pdf`, `check_tsmis_pdf_parse`, and
  `check_tsmis_pdf_reconcile`.
- Primary retained evidence:
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_hl_env_audit_vjj2wlkk`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk6_route_mismatch_f9sqyw3m`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk6_blank_tail_9zxmxkw5`.

### 2026-07-10 — Chunk 7

- Exercised every TSMIS PDF parser with real or parser-faithful adversarial PDFs,
  including clean controls, wrapped rows, PM-shaped spill, header-word collisions,
  leading/trailing orphan halves, truncation, numeric furniture, damaged repeated
  headers, mixed report editions, vestigial-column drift, invalid PM codes, per-page
  geometry changes, fallback grids, and cancellation at multiple phases.
- Ran the shared route-conversion path across all five table-PDF families with
  normalized duplicate routes and content/filename route conflicts. Also exercised
  Ramp Summary's separate converter with duplicate and blank route identities.
- Verified that malformed/unclassified controls which the parsers already recognize
  do become partial, corrupt-plus-valid sets retain partial state, corrupt-only sets
  error, and mid-parse cancellation normally prevents output. Normal Highway Detail
  wraps, Highway Sequence PM-less/equate/trailer rows, shifted per-page headers, Ramp
  null/on-off/type placement, and Intersection dangling-rowA handling remained sound.
- Existing focused parser, schema, comparison, evidence, and catalog checks remained
  green, including `check_highway_detail_pdf`, `check_intersection_detail_pdf`,
  `check_ramp_summary_schema`, `check_ramp_summary_partial`, `check_pdf_row_oracle`,
  `check_visual_evidence`, `check_report_catalog`, and the four Sequence/Ramp
  comparison goldens. The new failures sit outside their fixture envelopes.
- Primary temporary evidence directories:
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_hd_pdf_audit_54d061d5`,
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_idpdf_audit_97017e5b`,
  `C:\Users\Yunus\AppData\Local\Temp\tsmis_pdf_parser_audit_k1brx7we`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk7_ramp_duplicate__3eo617j`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk7_ramp_missing_route_5xg9qr0p`.

### 2026-07-10 — Chunk 8

- Built clean and one-field-mutated PDF/Excel/TSN triangles for Highway Log,
  Highway Sequence, Highway Detail, Intersection Detail, and Ramp Detail, plus
  aggregate Ramp Summary inputs. Checked route/row universes, field labels, counted
  versus context fields, Notes/Report View sheets, source roles, sidecar completion,
  and all supported raw/normalized TSN legs.
- Ran two-county same-route+PM value swaps on every Ramp and Intersection triangle
  edge. All returned false-clean matches, including normalized libraries that retained
  county sidecars which their loaders then discarded. County-aware controls required
  two Description differences.
- Mutated same-source fields hidden by reused TSN projection: Highway Log and Detail
  roadbed suffixes, Highway Detail NA, Highway Sequence Description prefix plus three
  context fields, and Intersection control type. Exercised explicit Intersection Route
  and S-field conflicts, two-native-Excel source-role substitutions, and current
  producer-partial sidecars.
- Exercised Ramp Summary with zero route rows and duplicate normalized routes, plus
  Ramp PDF/Excel render equivalences, null tokens, print-only fields, missing-input
  diagnostics, and source-role gates.
- Loaded the retained real Highway Log PDF/TSN pair: 50,723 versus 60,083 rows,
  252 versus 263 routes, 242 common routes, zero blank routes/keys, and the documented
  10 suffixed TSMIS-only versus 21 TSN-only route class. No current real TSMIS Excel
  artifact was present, so PDF-vs-Excel canaries used isolated synthetic workbooks.
- Existing Highway, Intersection, Ramp, visual-evidence, report-catalog, and comparison
  golden checks remained green; clean semantic triangles and intended render-only
  normalizations also passed.
- Primary temporary evidence directories:
  `C:\Users\Yunus\AppData\Local\Temp\chunk8_highway_triangle_0om4h1lv` and
  `C:\Users\Yunus\AppData\Local\Temp\chunk8_triangles_ufyik7l3`.

### 2026-07-10 — Chunk 9

- Routed all 29 classic recipes through the actual UI/bridge boundary: 17 file and
  12 folder recipes reached the correct endpoint, every wrong endpoint was rejected,
  stable keys/registry/mock metadata remained one-to-one, and formulas/values/both
  selections mapped to the documented modes and legal output names.
- Exercised file and custom-folder selection across recipe changes, deleted/nonexistent
  inputs, asynchronous folder discovery in both response orders, raw-PDF picker
  filters, per-route versus consolidated contracts, missing inputs, and task-gate/
  Save-dialog failure paths.
- Exercised both-mode transactional publication with a pre-existing values twin, a
  twin appearing during production, source aliases, partial outcomes, per-artifact
  sidecars, cancellation, producer exceptions, and temp-file cleanup.
- Inspected saved workbook/sidecar provenance with same-basename sources, result
  discrepancy fields, modal titles, and Cancel visibility while navigating classic,
  day-matrix, and baseline-matrix sub-tabs.
- Existing focused controls remained green: `check_report_catalog`,
  `check_compare_routing`, `check_gui_api_surface`, `check_gui_bridge`,
  `check_compare_audit`, `check_report_recipe`, `check_stable_ids`,
  `check_compare_tsn_common`, and `check_artifact_store`.
- Primary temporary evidence directories:
  `C:\Users\Yunus\AppData\Local\Temp\chunk9_classic_bridge_dxbuceq8`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk9_twin_overwrite_k45n6pfo`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk9b_classic_api_frjakdx5`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk9_hint_rejection_teyscnlk`.

### 2026-07-10 — Chunk 10

- Enumerated all 12 Everything-matrix rows and all 30 supported row-mode placements.
  Every placement resolved by exact object identity to one direct comparison adapter;
  no shadow Matrix comparator was found. Evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_mode_dispatch_xao9ekxy\result.json`.
- Exercised source/output replacement, cache-envelope loss, selected TSN switches,
  stale canonical TSN libraries, semantic comparator replacement, arbitrary/lock-only
  report folders, values/formulas sibling lifecycle, partial consolidation overwrite,
  partial caching/target selection/rendering, failed/cancelled rebuilds, and mixed-
  prerequisite shared-queue failures.
- Reproduced the partial lifecycle with the real Highway Sequence consolidator: a
  two-route complete persistent workbook was replaced by a fresh-marked one-route
  partial workbook after the second input became invalid.
- Read root `CLAUDE.md`, the owning comparison/reliability/testing/report/GUI docs, and
  the v0.18 Claude investigation/plan/close-out as intended-behavior evidence. Current
  documentation conflicts were isolated as CMP-AUD-086 rather than used as canaries;
  the historical “hash content only after a same-metadata counterexample” trigger is
  now satisfied by CMP-AUD-080.
- Existing controls remained green: `check_matrix`, `check_matrix_tsn`,
  `check_matrix_bridge`, `check_artifact_store`, `check_consolidate_outcome`,
  `check_tsn_outcome`, `check_read_counts_layout`, `check_mx_partial_render`, and
  `check_report_catalog`. Several green controls intentionally lock behavior now
  identified as defective (partial-cache reuse and all-queue clearing), so their
  assertions must change with the correction.
- Primary additional evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_same_meta_hydtqmjy`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_cache_contract_huac_oin`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_tsn_switch_cg3ypj31`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_stale_tsn_library_t12oang3`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_formula_toggle_qi2yx17_`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_stale_formulas_n_kc72t1`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_lock_freshness_4r8n6quh`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_partial_overwrite_iuu8p2x7`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_missing_cache_refresh_xwwbx7tp`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_auth_queue_clear_eja9rhch`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk10_failed_rebuild_wad37jg4`.

### 2026-07-10 — Chunk 11

- Enumerated all 12 day-vs-TSN rows and all 12 baseline-matrix rows. Every row reached
  the exact direct adapter object; the baseline sweep exercised 432/432 unique
  row/day/baseline targets without finding a shadow comparator. Evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_census_lh9fk2xd\result.json`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_dispatch_8up32s9b\result.json`,
  and `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_audit_f6qbdpa0\result.json`.
- Exercised legacy and suffixed day discovery, impossible dates, source changes,
  missing/both-missing inputs, hidden rows, explicit and bulk targets, invalid scoped
  filters, baseline switching, day removal during export, midnight rollover, queue
  chaining, output-folder routing, TSN override disappearance, source/output aliases,
  foreign ownership stamping, and Reset deletion selection.
- Replaced source content with restored metadata, switched to older TSN files, changed
  comparator implementations, deleted/cross-labelled/malformed caches, mutated source
  bytes during comparison, and propagated partial/skipped outcomes through persistent
  consolidations, comparison workbooks, caches, badges, stale selectors, and rendered
  cells. This independently extended CMP-AUD-017, 041, 080, 081, 083–085, and 087
  across the day/baseline implementations.
- Rechecked the current Claude-authored comparison, GUI, reliability, report, TSN,
  verification, lessons, roadmap, and v0.18 planning documents against these runtime
  behaviors. They were used as design oracles only where consistent with the
  executable census; contradictions remain isolated under CMP-AUD-086.
- Verified a deliberate non-issue: the work queue, progress state, Clear Queue, and
  Stop controls are intentionally global across all three Matrix panels and target the
  shared endpoints. No correctness finding was logged merely because a job remains
  visible after switching panels.
- Existing controls remained green: `check_day_matrix`, `check_baseline_matrix`,
  `check_matrix_bridge`, and `check_report_catalog`. They do not cover the adversarial
  lifecycle and identity cases above.
- Primary additional evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_wrong_ownership__mcn7a80`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_rollover_5k4g907c`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_discovery_ojqyboim`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_targets_fxbljqey`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_remove_running_0iswt6om`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_switch_0g5smrq4`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_baseline_missing_xi5fwdsd`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_midcompare_race_clean_bhopxl_q`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_day_cache_envelope_tq5v8fop`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_matrix_tsn_alias_gukunz5m`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_tsn_override_mrpqqelv`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_open_folder_sqg2s53l`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_hidden_mode_3nhmpmc5`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk11_missing_action_fhw8qlfk`.

### 2026-07-10 — Chunk 12

- Audited the five-family/twelve-row visual-evidence registry, every adapter's diff
  enumeration and PDF source routing, automatic and on-demand gates, queue dispatch,
  parse-back verification, rasterization, cancellation, workbook/image publication,
  stale/partial lifecycle, locked outputs, source/output aliases, formula payloads,
  and same-metadata/mid-run replacement.
- Audited one-click validation from TSN readiness through real Matrix dispatch, result
  classification, workbook/count acceptance, text/JSON rendering, worker/API/modal,
  cancellation, credential scrubbing, and the ZIP collector. The 12-row census showed
  only seven validation-ready row subdirs and independently extended CMP-AUD-007.
- Re-read root `CLAUDE.md` and the owning comparison, verification, work-PC,
  reliability, reports, TSN-parser, roadmap, lessons, GUI, packaging, and historical
  Claude documents. Their labelled-count, parse-back, producer-completion,
  transactional-publication, formula/value, credential-safe, and statewide-canary
  claims were used as oracles only after checking them against executable behavior.
- The full blocking offline gate passed 95/95. `check_source_zip_smoke` alone first
  hit the sandbox account's Git ownership guard and passed unchanged when rerun under
  the repository owner. The exact packaged/frozen self-test also passed, including
  its WebView bridge. Evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk12-frozen-selftest.txt`.
- Real Route-1 Highway Log formulas/values held exactly: 299 paired, 18/69 one-sided,
  221 differing rows, and 969 differing cells. Installed Excel
  `CalculateFullRebuild` left all six Summary checks and 30 applicable Spot Checks
  `OK`. Evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk12_route1_current.xlsx`,
  `C:\Users\Yunus\AppData\Local\Temp\chunk12_route1_current (values).xlsx`, and
  `C:\Users\Yunus\AppData\Local\Temp\chunk12_route1_current_com.xlsx`.
- Raw statewide canaries held exactly on isolated rebuilds:
  - Ramp Summary: 126/126 PDFs complete; totals 15,215/15,410; 31 both,
    1/0 one-sided, 27 differing, 4 identical
    (`C:\Users\Yunus\AppData\Local\Temp\chunk12_ramp_summary`).
    **Source-bound supersession (2026-07-12):** this unmanifested historical output is
    retained only as investigation history. The exact current All Reports 7.9 source is
    TSMIS 15,216 / TSN 15,410; independent truth is 29 shared, 0/2
    TSMIS-only/TSN-only, 24 differing shared, and 5 identical shared. Current production
    instead emits 31 shared + one TSMIS-only and 26 differing because of CMP-AUD-024/025.
    The accepted Stage-8 result is the oracle; the 15,215/27/4 observation must not be
    reused as expected truth.
  - Ramp Detail: 15,215/15,410 rows; 15,211 both, 4/199 one-sided,
    767 differing rows, 902 cells
    (`C:\Users\Yunus\AppData\Local\Temp\chunk12_ramp_detail`).
  - Highway Sequence: 252 XLSX + 12 district PDFs; 60,493/69,758 rows,
    57,071 both, 3,422/12,687 one-sided, 5,521 cells, 52,244 identical
    (`C:\Users\Yunus\AppData\Local\Temp\chunk12_hsl`).
- A real statewide Highway Log PDF-vs-TSN values build completed in 443.3 seconds:
  50,723/60,083 rows, 46,919 paired, 3,804/13,164 one-sided, 40,402 differing
  rows, 175,269 cells, 6,517 identical; routes 242 both, 10/21 one-sided. The
  164-pair shift from the older canary is arithmetically consistent with TSMIS data
  drift, but CMP-AUD-076/080/081/084 prevent durable attribution. Evidence:
  `C:\Users\Yunus\AppData\Local\Temp\chunk12_hl_pdf_vs_tsn.xlsx`.
- The environment's external-read quota was exhausted before these retained bundles
  could be re-run; their gates remain explicitly unavailable rather than assumed:
  - `C:\Users\Yunus\Downloads\TSMIS\ground-truth\Intersection Detail Bundle 7.8`
    plus the 6.19 Intersection Detail TSN workbook;
  - `C:\Users\Yunus\Downloads\TSMIS\ground-truth\Hwy Detail Dev Bundle 7.7`;
  - `C:\Users\Yunus\Downloads\TSMIS\ground-truth\HSL PDF + IS Bundle 7.9\TSMIS\highway_sequence_pdf`;
  - `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ssor-prod\{ramp_detail,ramp_detail_pdf}`;
  - `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 6.19\{TSMIS,TSN}\Intersection Summary`.
  These are the remaining ID, HD, HSL-PDF, RD-PDF, and Intersection Summary current-
  bundle acceptance gates; their absence is not counted as a product failure.
- Focused evidence/validation/artifact/count/worker controls all remained green,
  including `check_visual_evidence`, `check_evidence_bundle`, `check_validation`,
  `check_artifact_store`, `check_read_counts_layout`, `check_matrix_tsn`,
  `check_day_matrix`, `check_compare_audit`, `check_compare_skipwarn`,
  `check_compare_blankkey`, and `check_worker_lifecycle`. Several green assertions
  explicitly lock defects CMP-AUD-114 and 115.

### 2026-07-11 — independent second-opinion reconciliation

- Read Claude's complete second-opinion report, the current root `CLAUDE.md`, current
  comparison/reliability documentation, the complete v0.18 final plan, and the relevant
  production/check paths. Historical design was treated as evidence, not authority
  over contradictory current docs.
- Independently reproduced the realizable duplicate-pairing non-monotonicity, the
  `read_counts` marker ambiguity, all openpyxl error-code guard misses, and ownership
  stamp-on-sight through the real Reset selector. Evidence is incorporated into the
  existing stable findings rather than duplicated.
- Rechecked CMP-AUD-016, 085, 099, 101, 114, and 116 at their exact boundaries. The
  ledger was narrowed/reframed where warranted; the 099 priority and 114 golden-check
  statement were retained with explicit rationale.
- Recut the broad remediation outline into typed-contract, parser-family, persisted-
  schema, Matrix-surface, evidence, validation, UI, and acceptance batches. No product
  code was changed.

### 2026-07-11 — Phase-1 safety remediation completion

- Resolved CMP-AUD-041, 090, 105, 111, and 117 after retaining their red
  reproductions, adding lower-level bypass/race fixtures, and independently rerunning
  their focused owning checks.
- Expanded the safety boundary beyond the original symptoms: direct comparator temps,
  classic both-mode consent, staging and promotion journals, descendant reparses,
  consolidation/PDF/evidence sidecars, Matrix dual leases, Reset quarantine, all five
  PDF TSN aliases, Excel error tokens, and nested Office/ZIP credential carriers.
- Verification: focused comparison 26/26; focused cross-surface 9/9;
  `check_silent_swallows.py` 0 new; `build/run_checks.py -j 4 -k` 98 passed,
  0 failed in 41 seconds. The worktree was not committed or pushed.

### 2026-07-11 — Phase-2 typed truth implementation checkpoint

- Added the validated comparison types, exact producer completion/count reduction,
  strict SHA-bound member sidecars, central artifact publication, and the shared
  returned/persisted generation reducer.
- Switched Matrix, day, baseline, classic UI, validation, and evidence preflight away
  from summary prose/workbook count scraping. Partial/untrusted states are never green;
  validation has explicit terminal buckets and actual ZIP-member accounting.
- Closed the final returned-state gap at the shared public boundary: missing inputs/
  folders, malformed loaders, producer no-data/failure, overwrite cancellation, and
  artifact commit failure now return typed failed/cancelled outcomes and attempts with
  no invented artifact generation.
- Resolved CMP-AUD-011, 017, 026, 077, 078, 087, 113, 114, and 116. CMP-AUD-075,
  080, 081, 085, and 100 record partial remediation without losing their remaining
  closure gates.
- Focused publication/consumer checks and the full offline runner passed 106/106.
  Same-size/same-mtime peer tamper remained detected after rejecting an unsafe stat-only
  digest cache.
- Read the local corpus `_INDEX.md` and created
  `docs/planning/comparison-perfection/comparison-canary-bindings.md` without crawling the corpus. The exact
  Route-1 inputs are now bound as SHA-256
  `34787055E8710CB656D0C016FD2290F222897089305097F072F146E78F2F15E2`
  (TSMIS) and
  `93DA8DF0FF0C147E3456B889A8525C52B04871368AFFD2AAA893C09C02AD3303`
  (TSN). The same ledger now records the dirty-source manifest, strict both-mode output
  digests, Excel `CalculateFullRebuild`, six Summary checks, and 30 Spot Checks. The
  statewide member manifests remain pending.

### 2026-07-12 — Stage-8 Ramp Summary base comparison acceptance

- Revalidated the interrupted work from disk after the usage-limit reset. Direct
  authoritative-source versus local-audit-copy comparison found zero member differences
  across 504 TSMIS files: 126 Summary PDFs, 126 Summary XLSX files, 126 Detail XLSX files,
  and 126 Detail PDFs. Canonical manifests use
  `name<TAB>bytes<TAB>lowercase-sha256<LF>`; earlier inventory digests with undocumented
  serialization are retained as provenance but are not used as comparable canonical
  hashes.
- Added the independent truth oracle
  `build/phase8_ramp_summary_comparison.py`, isolated production witness
  `build/phase8_ramp_summary_product_witness.py`, and permanent adversarial gate
  `build/check_phase8_ramp_summary_comparison.py`. The gate rejects Boolean/fractional/
  text counts, route suffix/drop/duplicate/order mutations, PDF/XLSX/detail mismatches,
  unexplained P/V residuals, TSN duplicate/order/type drift, non-core ZIP mutations,
  formula/literal semantic drift, and detached acceptance errors.
- Independently parsed every current Summary form. All 126 two-page PDFs and 126
  one-sheet 47-row workbooks agree across 3,780 typed values; ordered digest
  `57514b890de9d1e49ed605c0fa095fade6a264f821e8177ac19aa852d87c2f1b`.
  Every route total reconciles to both 15,216-row Detail forms. The nine-route printed
  Ramp-Type residual totals 22 and is exactly the same-pull Detail P/V census (P=2,
  V=20), with no unexplained remainder.
- Independent comparison truth is 29 shared categories, two TSN-only Summary categories
  (P/V), zero TSMIS-only comparison categories, five identical shared rows, and 24
  differing shared rows. Its ordered digest, explicitly using `TSMIS - TSN`, is
  `a3cbf7528aa66989f08a0d28efd8ba0e4588b8e3675ef108b0b791fdd35a2d63`.
  TSMIS Total is 15,216; TSN Total is 15,410; TSN minus TSMIS is 194.
- Two isolated production runs per oracle execution and two complete source-bound oracle
  executions agree. The final result is 491,099 bytes / SHA-256
  `f05bad6e7442fd3f345f86c8b61f334f44bd6cbaced1341d4e24b277c2ef3ba2`;
  detached acceptance is 11,568 bytes / SHA-256
  `46ff47b2c73675b321ac88fc872767ef8446d7d09c3a3d1a36923a23fee782ca`.
  Both files reproduced byte-for-byte on the second full run.
- Terminal facts are deliberately separated:
  `source_truth_exact=true`, `production_value_projection_exact=true`, and
  `stage8_base_oracle_complete=true`; `production_comparison_semantics_exact=false` and
  `comparison_end_to_end_perfect=false`. Production's exact semantic gap set is P
  fabricated as TSMIS zero, V fabricated as TSMIS zero, and the 59-point no-linework
  display metric injected into Comparison/verdict. These refine existing
  CMP-AUD-019/020/024/025/071/076/146; no duplicate finding ID and no production
  correction was introduced.

### 2026-07-12 — Stage-8 Intersection Summary base comparison acceptance

- Bound the direct authoritative current TSMIS sources under `All Reports 7.9\2026-07-09
  ars-prod`: 217 Excel members / 5,953,364 bytes / manifest
  `e3e235e0f48645750b65b9df966a963c5a9bb856798d23661c95ab44056956e5`
  and 217 PDF members / 21,518,480 bytes / manifest
  `63f06f7b7f483a1fcd85be60278e7eebfbab51a79a1de955e9d3eac5bb8c8c2a`.
  Both have the same ordered route universe and suffixes, omit route 170, and agree on
  all 14,322 fixed-layout category/Total values; typed cross-format digest
  `9c012be4529d358181010dca4c89d0e0e4a759d9c066248feddf0f7149b2f33a`.
- Bound the exact raw TSN PDF, accepted r7 normalized workbook, Stage-6 result and
  acceptance, Intersection Detail XLSX↔PDF Summary cross-format oracle, and TSNR
  reference. TSNR plus the same-pull TSMIS pair resolve the source decision: canonical
  Control F is red on the mainline and G is red on all; the raw TSN Summary PDF itself
  erroneously prints red on all for both. CMP-AUD-145 now records lost raw contradiction
  and correction provenance, not unresolved business meaning.
- Independent truth is 66 union rows, 58 shared, eight TSMIS-only, zero TSN-only, 53
  differing shared, and five identical shared. TSMIS/TSN totals are 16,459/16,626;
  ordered comparison digest
  `60459ed21842e53460e10ddc60c66e1cdbab1bf716b76826a5f4128c8b8fc120`.
  Production's source-backed values and current generic comparison semantics are exact.
- Added `build/phase8_intersection_summary_comparison.py`, isolated production witness
  `build/phase8_intersection_summary_product_witness.py`, and permanent gate
  `build/check_phase8_intersection_summary_comparison.py`. The gate covers strict typed
  counts; Total and every partition; rural/urban parents and orphans; distinct J–P fold
  versus repeated rows; exact route suffix/drop/duplicate/order/170 behavior; PDF
  geometry/provenance; Excel/PDF mismatch; TSN and TSNR drift; package volatility;
  formula/literal semantics; structural absence; and detached acceptance/rejection.
- Two new product findings were recorded before any correction: CMP-AUD-183 proves the
  Intersection-specific route universe is not enforced; CMP-AUD-184 proves the familiar
  note contradicts its correct one-sided blank cells and cites Ramp P/V. The exact open
  product set is CMP-AUD-020/021/022/023/076/144/145/146/183/184. All 10 headings were
  independently found in this ledger before detached acceptance.
- Audit-harness incidents were retained rather than hidden: the first product witness
  hit a Windows CP1252 encoding error on a diagnostic cross and was changed to emit UTF-8
  bytes; the first exploratory workbook helper attempted a read-only sheet-property
  assignment and used the same unsafe console character, so that inspection was
  discarded and rewritten; an early candidate launch used a one-second timeout and a
  later final-replay launch was cut off after five seconds, neither of which published or
  counted as acceptance; the first full candidate correctly exposed persisted blank
  cells as `None` rather than `""`, so the inspector was corrected without accepting
  zero; repetitive recoverable pdfminer `FontBBox` warnings were suppressed only after
  the all-member pixel census and cross-render review independently passed.
- The final direct-authoritative result is 1,124,870 bytes / SHA-256
  `7e4acebabd2efc8ac2d765c78493048117eb0bd2431cd01d032c0272cd9ea7bd`;
  detached acceptance is 11,322 bytes / SHA-256
  `d1758926e6fa7672bbce75e02b51686326ea192275393918667386632fedab31`.
  Two complete replays reproduced both files byte-for-byte. Independent post-run checks
  found 12/12 source invariants and 24/24 audit invariants true, exact acceptance/result
  binding, no rejection file, all three scripts compilable, and the permanent gate green.
  Terminal facts are `source_truth_exact=true`, `production_value_projection_exact=true`,
  `production_comparison_semantics_exact=true`, `stage8_base_oracle_complete=true`,
  `normalized_source_full_conservation=false`, and
  `comparison_end_to_end_perfect=false`. No product correction was made.

### 2026-07-12 — Stage-8 Ramp Detail base comparison acceptance

- Bound the current `2026-07-09 ssor-prod` Ramp Detail trees directly: 126 Excel
  members / 7,858,480 bytes / manifest
  `7c10fbf6b996a8a9fbb0e8c8c30d8d2dac0a80c0befb7c12bdeb0151f7ff7489`
  and 126 PDF members / 12,792,211 bytes / manifest
  `6e8a2b669148738344a0173cca52a16884b972cba4679ba6446547ce8286c4c9`.
  Also bound the exact raw TSN XLSX/PDF, accepted r7 normalized workbook/sidecar,
  corrected Stage-6 result/acceptance, and accepted TSN cross-format oracle.
- Independent D4-key truth is 15,212 paired, four TSMIS-only, and 198 TSN-only in both
  TSMIS formats. Excel has 741 differing rows / 847 cells and 14,471 identical rows;
  PDF has 774 differing rows / 998 cells and 14,438 identical rows. PDF↔Excel pairs all
  15,216 rows and differs in four Description cells only. The exact source ledgers are
  `7bd713435c4d20d7ea0ffccfc23c26d1f6ad23418b5cde60e24489594ff33e73`,
  `c7edcc516cc10ef7e687c106d1d8b0de28a4811629e2cf34a921f0583b6b2310`,
  and `050fb352d69565f54bf3df07aa80c251ea2ba584b4d4034085e3d587fd01938d`.
- Raw TSN↔normalized pairs all 15,410 rows and differs only at the exact 15
  source-backed numeric Description prefixes already recorded by CMP-AUD-135; paired
  ledger `4a9de9a5369e4f104f40ead979becec6ef1d39f0b9d92a738d40b998e4ada131`.
  All 18 raw XLSX columns, every PDF field, 500 data pages, 626 TSMIS PDF pages, 306
  whitespace collapses, 59 dash/blank cells, 59 no-linear-event/blank cells, four
  `_x000d_` rows, and all source-dated cross-format residues are dispositioned.
- Added `build/phase8_ramp_detail_comparison.py`, isolated
  `build/phase8_ramp_detail_product_witness.py`, and permanent
  `build/check_phase8_ramp_detail_comparison.py`. The witness rebuilds both TSMIS
  sources and runs five `mode="both"` legs: Excel/PDF against raw/normalized TSN plus
  PDF↔Excel. The gate passes 36 assertions covering D4 identity, District/PR/PM_SFX,
  Description, duplicate pairing, PM/date, PDF headers/prefixes/render classes,
  malformed/formula XLSX, physically omitted trailing blanks, package volatility, and
  detached acceptance/rejection.
- Four product-red findings are exact and were checked before acceptance:
  CMP-AUD-045 (81 weak Route+PM keys span 163 county identities), CMP-AUD-133 (raw
  claims omitted from normalized/comparison), CMP-AUD-135 (15 false Description
  differences), and new CMP-AUD-185 (the real District 12-vs-11 difference at
  `005/SD/72.366` is false-clean). Product Excel-vs-TSN is 750 differing rows / 861
  cells; product PDF-vs-TSN is 783 / 1,012. Raw and normalized product outputs are
  semantically identical, proving normalization does not rescue the comparison path.
- Audit-harness failures were retained and corrected without weakening the oracle: an
  initial outer-route assumption rejected authentic no-prefix `RTE 156` Descriptions;
  a single-word `CITY` header detector consumed a data row and was replaced by the full
  seven-token header constellation; suffixed routes were proven to use base outer-route
  prefixes; the normalized XLSX's absent cached dimension required physical header/row
  validation; compound `_x000d_` plus newline facts required multi-class disposition;
  a Windows temporary-directory lock caused a fail-closed rejection and gained bounded,
  verified cleanup; product consolidated XLSX rows physically omit a declared trailing
  blank and gained exact trailing-only padding plus full payload equality; and a
  diagnostic replay exposed provenance-sensitive digest changes when private TSN
  captures were renamed, so authoritative basenames are now preserved. No failed or
  diagnostic candidate was promoted.
- The final result is 1,703,996 bytes / SHA-256
  `6cdf3ad5f5c1453df77515ca4cc30535f263bbe36eeaf2ab1e392771adbaf556`;
  detached acceptance is 13,473 bytes / SHA-256
  `77b3af5f5273666296c6304f28eb69137b69f67779d95cd3ca34e4ab6d3bbd64`.
  Two complete direct-authoritative executions reproduced both files byte-for-byte;
  the second took 818 seconds. Independent filesystem verification found zero private
  work entries, current code/source hashes, and the protected Fable file unchanged.
  Terminal facts are `source_truth_exact=true`,
  `production_tsmis_projection_exact=true`,
  `production_value_projection_exact=false`,
  `production_comparison_semantics_exact=false`,
  `stage8_base_oracle_complete=true`, and
  `comparison_end_to_end_perfect=false`. No product correction was made.

### 2026-07-13 — Stage-8 Intersection Detail base comparison acceptance

- Bound the direct current `All Reports 7.9\2026-07-09 ars-prod` trees: 217 Excel
  members / 23,464,055 bytes / manifest
  `885149005ab9a261ca83b686f68cfc3fc4fe550d8fd42d99252dcd36fb365bc9`
  and 217 PDF members / 31,673,183 bytes / manifest
  `01e62eb195ab0bd5494cdb1b7a6a5ccbc35bd451bb5320a9bab0a045c58773c9`.
  Also bound the exact raw TSN XLSX/PDF, accepted r7 normalized workbook/sidecar,
  Stage-6 result/acceptance, and accepted TSN cross-format oracle. Live origins and
  private captures were rehashed before and after acceptance.
- Independently parsed every source without importing product parser, consolidator,
  schema, comparator, or writer code. The 217 TSMIS PDFs contain 1,844 pages and all
  16,459 expected records with zero parser residue. Raw TSN↔normalized pairs all 16,626
  rows with zero asserted differences. Physical identity is
  `(base Route, County, complete PP, numeric Post Mile)`; six within-county numeric-PM
  collisions prove complete PP is not optional.
- Exact source truth is 16,199 paired / 260 TSMIS-only / 427 TSN-only for each TSMIS
  form. Excel has 16,053 differing rows / 21,676 cells; PDF has 16,053 / 21,683.
  PDF↔Excel pairs all 16,459 rows with zero one-sided and exactly nine differences:
  eight Excel trailing-tab Description values that PDF cannot render and one HG cell at
  `108/TUO/<blank>/5.87`, where Excel says `U` and PDF plus both TSN forms say `D`.
- Added `build/phase8_intersection_detail_comparison.py`, isolated
  `build/phase8_intersection_detail_product_witness.py`, and permanent
  `build/check_phase8_intersection_detail_comparison.py`. Each full witness consolidates
  both TSMIS forms and builds formulas+values workbooks for five legs: Excel/PDF against
  raw/normalized TSN plus PDF↔Excel. The independent inspector verifies all source
  sheets, snapshots, paired cells, one-sided rows, formula censuses, and Report Views.
- Production preserves every nonblank typed consolidation cell, every member Route, and
  every physical `S`. Excel's only representation change is exactly 125,152 explicit
  empty strings serialized as physical blanks. Product overlapping comparison cells are
  exact on the current corpus, but physical identity and source visibility remain false:
  CMP-AUD-045/068/070/133 are the complete product-red set. No new finding ID was
  created merely to restate those owned defects.
- Raw Report View maps 16,626 values apiece for `MAIN_EFF_DATE`, `MAIN_ADT`, and
  `CROSS_ADT`; normalized Report View blanks all three, and both PDF-vs-TSN legs omit
  Report View. The permanent gate passes 31 assertions covering Location/PM, strong
  identity versus weak masking, District, complete PP, tabs, deterministic counters,
  raw/normalized views, consolidation Route/S/blank semantics, workbook universes,
  formula tags, snapshots, PDF grids, and the vestigial PDF cell.
- Audit-harness incidents were retained rather than hidden. The first private capture
  attempted a literal wildcard and produced empty TSMIS directories; it was discarded
  and recaptured with exact member enumeration. A static PDF grid failed after 386.9
  seconds because page geometry varies by document; per-document exact rectangles
  replaced it and the full 1,844-page census passed. Several product-witness starts were
  non-evidence: one PowerShell launch duplicated `Path`, two used stale TSN/normalized
  names, one launcher tested an output before it existed, and detached children were
  killed with their sandbox command. None published a result. The uninterrupted
  foreground witness then completed all ten workbooks.
- Three inspection assumptions also failed closed before acceptance. The first full
  candidate exposed exact Excel empty strings persisted as physical blanks; acceptance
  was withheld until a complete 125,152-cell/22-column census proved this was the sole
  serialization class. A global “values workbooks contain no formulas” assumption was
  rejected because deterministic helper/self-check formulas intentionally remain; exact
  per-sheet formula censuses replaced it. A merged Report View header-coordinate guess
  was rejected and replaced by the exact four-row header map. No failed or diagnostic
  candidate was promoted.
- Replay 1 result is 1,059,072 bytes / SHA-256
  `7c7734aae212fbf9ad55de554cd2a0111549479b764ff3b91695fb524f21d86c`;
  its 2,063-byte acceptance SHA-256 is
  `67a267b491ecd380a8156af6b5d216cb27d875ac20175e5fe964acc61a0bbb30`.
  After the network interruption, no process or execution cell was assumed live. Disk
  inspection proved replay 2 had already atomically completed with byte-identical result
  SHA-256; its 2,063-byte acceptance differs only by result path and hashes
  `737ceb082ecf0f18d9a21d44b29d1893e4e455e854798d5e9a46779493d659b8`.
  All 24/24 audit invariants and 31/31 permanent assertions pass. Terminal facts are
  `source_truth_exact=true`, `production_tsmis_projection_exact=true`,
  `production_overlapping_comparison_cells_exact=true`,
  `production_value_projection_exact=false`,
  `production_comparison_semantics_exact=false`,
  `stage8_base_oracle_complete=true`, and
  `comparison_end_to_end_perfect=false`. No product correction was made.

### CMP-AUD-238 — the public comparison decoder is permissive and its frozen objects are shallowly mutable

Found by the 2026-07-14 Codex adversarial review of the recovered engine and
independently reproduced against the code. Two related public-contract defects in
`scripts/comparison_contract.py`:

- **Permissive decode.** `from_json` decodes with a bare `json.loads`, which accepts
  `NaN`/`Infinity` (Python's default `parse_constant`) and duplicate object keys
  (last-wins). `to_json` uses `allow_nan=False`, so a payload can decode but fail to
  re-encode — an asymmetric, non-round-trippable public contract. `from_dict` also
  ignores unknown tagged-envelope fields rather than rejecting them. A payload
  containing `NaN` was reproduced: it decoded successfully and then could not be
  re-encoded.
- **Shallow immutability.** `ComparisonCounts` is `frozen=True`, but `per_field_counts`
  is stored as a live `dict`. Its validated invariant (values sum to `differing_cells`,
  from `__post_init__`) can be violated by mutating the mapping in place after
  construction — reproduced by assigning `counts.per_field_counts[...] = N`.

Schema-v3 **sidecar** reading independently rejects duplicate/nonfinite/noncanonical
payloads, so this is not currently a schema-v3 bypass; it is a real public-API defect.
It does not fit CMP-AUD-231, so it carries its own ID.

Correction (Wave 1): `from_json`/`from_dict` must reject `NaN`/`Infinity`, duplicate
keys, and unknown envelope fields (strict, symmetric with `to_json`); frozen contract
objects must wrap their mappings (e.g. `MappingProxyType`) so a validated invariant
cannot be mutated away. Capture the defect red before the change.

**Remediation — 2026-07-14 (decoder half).** `from_json` now parses with
`parse_constant` (rejects `NaN`/`Infinity`/`-Infinity`) and an `object_pairs_hook`
(rejects duplicate keys); `from_dict` requires the exact `{schema_version, type, value}`
envelope (rejects unknown fields). Proved red→green in `build/check_comparison_contract.py`
(the added block fails on the pre-fix engine — "duplicate top-level key accepted" — and
passes after); full gate 121/121, ruff clean. **Still open:** shallow immutability of the
frozen contract mappings (`ComparisonCounts.per_field_counts`,
`LoadedSide.raw_identity_claims`/`display_metrics`,
`ArtifactGeneration.content_digests`/`producer_versions`). `MappingProxyType` is not
serializable by `dataclasses.asdict` ("cannot pickle mappingproxy"), so closing it
requires reworking each type's `to_dict`; deferred to a focused batch to avoid rushing a
foundational serialization change.

**Remediation — 2026-07-14 (immutability half; finding now Resolved).** Added `FrozenMap`,
a `dict` subclass that refuses every post-construction mutator (`__setitem__`,
`__delitem__`, `update`, `clear`, `pop`, `popitem`, `setdefault`). It stays a real `dict`,
so `dataclasses.asdict`, `json.dumps`, `_jsonable`, and equality with a plain `dict` all
keep working, and a custom `__deepcopy__` keeps `copy.deepcopy` from hitting the blocked
`__setitem__`. The five frozen-contract mapping fields are wrapped in `__post_init__` via
`object.__setattr__` (`ComparisonCounts.per_field_counts`,
`LoadedSide.raw_identity_claims`/`display_metrics`,
`ArtifactGeneration.content_digests`/`producer_versions`). Round-trips are byte-identical;
`check_comparison_contract` gained mutation-rejection assertions (red on the pre-wrap
engine, green after); full suite 121/121, ruff clean.

### CMP-AUD-239 — Intersection Detail PDF-vs-TSN had no Report View

Reported by the owner while reviewing the two Intersection Detail vs-TSN comparisons
(2026-07-17): the **TSMIS (Excel) vs TSN** workbook carries the two-line "Report View"
replica, but **TSMIS (PDF) vs TSN** did not. Cause: the Report View is attached by a
per-call schema in `compare_intersection_detail_tsn.compare()` (it needs both input
paths to read the TSN one-sided columns + TSMIS Location), and the PDF flavors in
`compare_intersection_detail_pdf` built their schema with a plain
`replace(_id._SCHEMA, …)` that never set `extra_sheet_writer` /
`report_view_diff_check`.

**Remediation — 2026-07-17 (Resolved).** Extracted the schema augmentation into a shared
`add_report_view(schema, tsmis_path, tsn_path)` helper in
`compare_intersection_detail_tsn`; `compare()` now uses it, and `TSMIS_PDF_VS_TSN`
(`_IntDetailFileCompare(report_view=True)`) builds its per-call schema through the same
helper via `_schema_for(path_a, path_b)`. Both vs-TSN legs project the TSMIS side onto
`SHARED_HEADER` and read the identical TSN one-sided columns + TSMIS Location (the
PDF-consolidated workbook shares the Excel export's 36-column layout, Location at
position 4), so the replica is byte-for-byte the same regardless of which render fed it.
The same-source **PDF-vs-Excel** self-check deliberately does NOT get a Report View: its
"soft/structural" date classification (Int St / ML / CS Eff-Date) and TSN-only reference
columns are TSN-specific — on two TSMIS renders a date disagreement is a real defect, so
"soft" would understate it. Statewide proof: the PDF-vs-TSN Report View renders
identically to the Excel one (16,886 records, two physical rows each, diff markers +
Major/Diffs counts live). `check_intersection_detail_pdf` locks that PDF-vs-TSN builds a
Report View (`extra_sheet_writer` set + `report_view_diff_check == ("Report View","B",2)`)
while PDF-vs-Excel does not; `check_compare_intersection_detail_tsn` stays green (the
Excel-vs-TSN path is behavior-neutral after the refactor).

### CMP-AUD-240 — cross-env Intersection Detail refused across the July-2026 edition

Found while running the owner's 2026-07-17 "compare against the previous version, for
both PDF and Excel" test: `compare_env.INTERSECTION_DETAIL.compare_folders(new, old)`
returned "The two folders' Intersection Detail files have different column layouts —
compare exports made by the same app version." The new (2026-07-17) and old (7.8) per-route
Excel exports carry the July LABEL-ONLY header change (`P`->`PP`, `S`->`PS`, the INT
Type / INT Eff-Date labels realigned over their own values, `Ctrl T`->`Ctrl T Eff-Date`,
`Xing P/S`->`Int PS`), and the flat cross-env path compares headers by exact equality, so
it refused — even though every VALUE stayed in an identical column position (proven
cell-for-cell; the vs-TSN comparators already read both editions by position). The PDF
cross-env row is unaffected: its parser emits a fixed canonical header for both sides.

**Remediation — 2026-07-17 (Resolved).** Added `_id_canonical_header` to
`compare_env.INTERSECTION_DETAIL` (`header_canonicalizer=`), mirroring Highway Log's
`_hl_canonical_header` (CMP-AUD-048): it maps either supported edition (current or
legacy labels, optional leading Route) to ONE canonical header so a new-vs-old / pre-post
comparison aligns by position, while any OTHER header is returned UNCHANGED — Intersection
Detail carries no `force_header`, so the existing strict same-layout equality (and its
refusal of a genuine column move where the two sides differ) is preserved for every
non-edition case; the change only ADDS the cross-edition bridge. Real-corpus:
new-vs-old now aligns 16,459 intersections across 217 routes (was: hard refusal). The
delta it surfaces is the expected data refresh (Int St Eff-Date bulk stamp + HG + the
Location suffix). Red→green in `check_compare_env_intersection`
(`test_detail_edition_boundary`: both editions canonicalize to one header, an
unrecognized header is identity, and a cross-edition position-aligned Description diff is
flagged); the pre-existing detail/summary env tests stay green (their custom headers hit
the identity branch).

### CMP-AUD-241 — Intersection Detail PDF-vs-TSN Description: 8 trailing-tab false positives

**Status: RESOLVED 2026-07-17 (owner ruling) — shipped in `a4ccd23`.** This heading read
"(OPEN)" and the recommendation below still said "needs owner greenlight" long after the
summary table recorded it Resolved; the stale text caused the owner to be asked to re-decide a
settled question on 2026-07-21. Real-corpus result: PDF-vs-TSN Description 12→4 and total
5,100→5,092, now EQUAL to Excel-vs-TSN (unchanged 5,092/4). See the summary-table row.

Confirming an owner observation ("the PDF vs TSN for Intersection Detail had some false
positives for Description"): the statewide **TSMIS (PDF) vs TSN** comparison shows 12
Description diffs where **TSMIS (Excel) vs TSN** shows 4. The 8 extras are ALL
trailing-tab-only, e.g. TSN `HILLCREST RD\t\t` / `HARRIS ROAD \t\t` / `BELMONT AVE\t`
vs the PDF's clean `HILLCREST RD` / `HARRIS ROAD` / `BELMONT AVE` (the 8: HILLCREST RD,
BELMONT AVE, HARRIS ROAD, KEYSTONE ROAD, SCHARTZ ROAD, WILDCAT ROAD, ROCKER BOX RD,
GLENNISON GAP RD/JENNINGS RT). The TSN extract carries the edge tabs; the TSMIS Excel
export preserves them (so Excel-vs-TSN matches — Excel `HILLCREST RD\t\t` == TSN
`HILLCREST RD\t\t`); the TSMIS PDF print physically cannot render trailing tabs, so
PDF-vs-TSN flags them. The 4 genuine Description diffs (real street differences + the
documented KER 046 `''F''` vs `"F"` quote edit) are present identically in BOTH legs.

The same-source `compare_tsn_common.same_source_render_text` already rules this exact
edge-tab class a render artifact for every PDF-vs-Excel flavor (the same-source ID
PDF-vs-Excel is 0/0 statewide). But the owner deliberately scoped that normalization
"never the vs-TSN legs" — the vs-TSN comparison is byte-exact so real data edits (the
quote character) surface.

**Recommendation — ACCEPTED and SHIPPED 2026-07-17:** apply an edge-tab-only trim (map leading/
trailing `\t\r\n\f\v` away, NOT the OOXML-decode half of `same_source_render_text`, and
NOT interior text) to the Description on BOTH sides of the vs-TSN comparison. It is
provably non-semantic — trailing field padding is never part of a street name, the PDF
medium cannot carry it, and a value differing only in trailing tabs represents the same
street — so it cannot hide a real difference: it leaves the Excel-vs-TSN 4 unchanged and
drops PDF-vs-TSN from 12 to 4, making the two legs agree. Deferred to the owner because it
moves the deliberately-drawn vs-TSN byte-exact line (CLAUDE.md / the visual-evidence memo
state edge-tab normalization is "never the vs-TSN legs"). Evidence: scratchpad
`id_task/cmp_A_excel_vs_tsn.xlsx` (Description 4) vs `cmp_B_pdf_vs_tsn.xlsx`
(Description 12), both statewide on the 2026-07-17 export.

### CMP-AUD-242 — payload chunk basename overruns Windows MAX_PATH on the deployment target (RESOLVED — rides the completion release)

Priority: P1  
Status: **RESOLVED 2026-07-22** — chunk basenames shortened 167→71 chars (16-hex name
abbreviations; the manifest still records and verifies the FULL digests); legacy
full-hex names stay readable everywhere; two new UNCONDITIONAL gates in
`check_comparison_path_limits` were red on the old code for exactly the field's
failure. Per the owner's 2026-07-22 release policy the fix ships with the
comparison-perfection completion release (CHANGELOG "Unreleased" section).

**Remediation (2026-07-22).** `consolidation_meta._payload_primary_basename` /
`_payload_slot_basename` now emit `.cmpv3-{16hex}-{index:06d}-{16hex}[-f-NN]
.comparison-payload.zlib` (71/76 UTF-16 units; worst case at the field's measured
97-char parent = 174 < 260, pinned by a module-level assert). Acceptance of BOTH
shapes: `_strict_payload_manifest` (exact short/legacy primary, then shape-matched
fallback prefix — legacy binding+nonce keys only on the legacy shape; a short-name
nonce hybrid REFUSES), `_PAYLOAD_BASENAME_RE` + `artifact_store._COMPARISON_PAYLOAD_RE`
(fingerprint exclusion), and the reclamation `_PAYLOAD_CHUNK_SHA_RE` (full-digest
equality for legacy names, 16-hex prefix for short ones, atop the live-reference/
lease/grace gates). Census: every `cmpv3` site repo-wide — the two product files,
three live checks updated to derive names via the product helpers
(`check_comparison_sidecars`, `check_artifact_store` incl. new short-shape
fingerprint fixtures, `check_comparison_path_limits`), `check_comparison_payload_
resources` retained as a de-facto legacy-shape consumer, and the frozen
`check_phase*` audit instruments untouched (excluded from the gate by
`run_checks.AUDIT_PREFIX`; they authenticate legacy-named frozen artifacts).

**Red→green.** The two new gates, both RED on the old code: (1) unconditional
field-depth arithmetic — 97 + 1 + 172 = 270 > 260; (2) a REAL
`artifact_store.commit_workbook` publication at a parent padded to exactly 97 chars
with `os.open/os.replace/os.rename` shimmed to refuse ≥260 (`LongPathsEnabled=0`
semantics) — failed with the field's exact signature (chunk refused → publication
False → untrusted). Green after the change; neither can be skipped by a
long-path-aware dev box. Full gate 144/144.

**Real-corpus proof (2026-07-22).**
- *Legacy read:* a real HSL vs-TSN publication written under the OLD code (167-char
  chunk name) reads back **trusted** under the new code with typed counts intact
  (5,589 diff cells / 16,154 one-sided — the bound canary).
- *Short-name publication:* the SHIPPED path (ConsolidateWorker TSN build →
  MatrixCompareWorker) over the real 126-route `All Reports 7.9` Ramp Detail corpus
  publishes 71-char chunk names, reads back trusted, and the recorded counts equal
  the bound RD-79 canary EXACTLY (843 differing cells / 202 one-sided) — the naming
  change moved nothing semantically. Deepest chunk path at the field parent: 169.

**Field-confirmed on the work PC, v0.27.0, 8/8 comparison runs.** Every by-day
vs-TSN comparison built its workbook correctly and then vanished from the matrix.

Root cause: the schema-v3 payload chunk basename is **~148 characters** —
`.cmpv3-{64 hex}-{index:06d}-{64 hex}.comparison-payload.zlib`
(`consolidation_meta._payload_primary_basename` / `_payload_slot_basename`). At the
field install depth
`C:\Users\<user>\Downloads\Apps\TSMIS Exporter\output\comparisons\tsn-by-day\<day>\`
(parent = 97 chars) the published path is **265 characters**, over the classic
260 limit. A process is exempt only when the OS policy `LongPathsEnabled=1`; the
dev machine has 1, **a managed Caltrans PC has the default 0 and cannot change it
without an administrator**. `os.open` refuses → `_publish_payload_chunk_with_fallback`
returns `None` → `write_comparison_outcomes` returns `False` →
`artifact_store._publish_artifact_generation` flips ok→error and marks the members
untrusted → the matrix correctly refuses to display an uncertifiable comparison.
The workbook itself is committed and valid.

This is a **deployment-target defect, not a logic defect**: CLAUDE.md requires the
app to run as a plain unsigned exe from a user-writable folder on a locked-down PC.
`check_comparison_path_limits.py` exercises a real >260 publication only "when the
development runtime/Windows policy permits it", so it passes on a long-path-aware
dev box and is **structurally incapable of catching this** — that conditional is
part of the finding.

**Reproduced** (2026-07-21) by running a real Highway Log vs TSN comparison into a
tree padded to the field's exact 97-char parent with `os.open`/`os.replace` refusing
`>=260`: the field message appears verbatim, `published=False`, `workbook=True`.

**Shipped so far (v0.27.1, `f55d946`) — diagnosis only, NOT the fix.** Every
fail-closed publication gate now names itself; the chunk gate prints the full path
and its length and, when over the limit, names the remedy; the user-facing message
says the same in UI-neutral terms. Behavior unchanged.

**The fix that MUST ship before comparison-perfection is called done:** shorten the
chunk basename. Truncating each hex to 16 (`.cmpv3-{16}-{6}-{16}…` ≈ 52 chars) cuts
~96 characters and is safe on integrity grounds — reads resolve the chunk via
`descriptor["relative_path"]` from the manifest and verify the **full** sha256 and
size, so the NAME is an addressing convenience, not the integrity claim. It is a
**persisted-format change**, so it needs its own census + red→green + real-corpus
re-verify, and must keep reading existing v3 payloads (manifest-driven reads already
do). Call sites that pin the current shape:

- `scripts/consolidation_meta.py:86` — `^\.cmpv3-[0-9a-f]{64}-[0-9]{6}-[0-9a-f]{64}`
- `scripts/consolidation_meta.py:1847` — same shape, **captures** the digest (chunk reclamation)
- `scripts/artifact_store.py:58` — same shape
- `scripts/consolidation_meta.py:167` / `:173` — the two basename builders
- `scripts/consolidation_meta.py:1296` / `:1299` / `:1306` — primary + fallback-prefix build and parse
- `_NEW_PAYLOAD_PRIMARY_MAX_NAME` / `_NEW_PAYLOAD_SLOT_MAX_NAME` (`:182`/`:184`) — derived budgets
- `build/check_comparison_path_limits.py` — must gain an UNCONDITIONAL total-path
  budget assertion against a realistic deep install parent, independent of the
  runtime's long-path policy

**Owner workaround until it ships:** move the app to a short folder path
(e.g. `C:\TSMIS\TSMIS Exporter\`); this works on an existing install with no rebuild.

### Note — ACL "lease-leak" hypothesis disproved (2026-07-14)

The reconciliation flagged that three audit directories were ACL-locked against the
owner and hypothesized a leaked product `OwnershipLease`/reserved-temp. The Codex review
disproved it against the code: the two Highway Sequence replay roots are created by audit
code with `os.mkdir(..., 0o700)` and the intersection `source-transaction-*` directory by
`tempfile.TemporaryDirectory`; none contains `.tsmis-owned.json` or the publication lock;
`OwnershipLease` holds no OS handle; and the real publication lock is closed in `finally`.
The directories were merely inaccessible to the sandbox account (protected DACLs omitting
the inherited sandbox ACE), not to the owner. **No product lease-release defect; no new
finding.** Relevant existing audit-residue context: CMP-AUD-203, CMP-AUD-236.

## Remediation order after the audit

The audit initially made no product corrections. Phase 1 is resolved and the Phase-2
typed producer/publication/consumer slice is closed. Its named Phase-5/7 integrations
remain open under their own findings. The authoritative implementation sequence is
`docs/planning/comparison-perfection/comparison-remediation-plan.md`.
In summary:

1. complete — freeze red reproductions and record the decision gates;
2. complete — land isolated safety containment for aliasing, ownership/Reset, evidence
   literals, bundle credentials, and missing explicit sources;
3. complete offline — typed source/outcome/count/generation contracts, truthful
   producer plumbing (including no-artifact terminal paths), strict publication, and
   consumer migration;
4. in progress — D2/D3 are approved in
   `docs/planning/comparison-perfection/comparison-phase3-decision-gates.md`; retain the full run manifest and
   independently establish the input-bound statewide canary's typed oracle/red fixtures,
   then correct core equality/identity and migrate one loader family at a time;
5. switch all remaining persisted comparison/cache metadata in one coordinated identity
   epoch, including Matrix formula twins and durable attempts;
6. migrate remaining Everything/day/baseline orchestration findings one surface at a time;
7. bind secondary views/evidence and validation to the exact generation; then correct
   classic UI/docs and run the full synthetic, Excel, real-data, frozen, and work-PC
   acceptance gates.
