# CLAUDE.md — TSMIS Reports Exporter

A portable Windows desktop tool that bulk-exports TSMIS (Caltrans Transportation
System Management Information System) reports for every California state route. The
user picks one, several, or all report types; one shared SSO login serves them all.
It ships as a **single-folder portable app** (bundled Python + an Edge WebView2 GUI;
no installer, no Python needed on the target), with a `.bat` console flow retained
for development and fallback that runs the same core engine.

One TSMIS page serves every combination of **data source** (SSOR / ARS) and
**environment** (prod / test / dev); defaults are SSOR + Prod.

> **This file is the router.** It holds the project snapshot, the report table, and
> the **non-negotiable conventions**. All the deep knowledge — architecture, auth,
> the GUI, the comparison engine, Highway Log internals, build/release, IT/security,
> verification, lessons, history — lives in the **[`docs/`](docs/INDEX.md) library**.
> Start at **[docs/INDEX.md](docs/INDEX.md)** and open the topic doc for whatever
> you're touching. Keep this file a thin index; don't re-expand `docs/` detail here.

---

## Supported reports

| # | Report | Output | Folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/<run>/ramp_summary/` |
| 1b | TSAR: Ramp Summary (Excel) | XLSX | `output/<run>/ramp_summary_excel/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/<run>/ramp_detail/` |
| 2b | TSAR: Ramp Detail (PDF) | PDF (Letter, landscape) | `output/<run>/ramp_detail_pdf/` |
| 3 | Highway Sequence Listing | XLSX | `output/<run>/highway_sequence/` |
| 3b | Highway Sequence Listing (PDF) | PDF (Letter, portrait) | `output/<run>/highway_sequence_pdf/` |
| 4 | Highway Log | XLSX | `output/<run>/highway_log/` |
| 4b | Highway Log (PDF) | PDF (Letter, landscape) | `output/<run>/highway_log_pdf/` |
| 5 | Intersection Summary | XLSX | `output/<run>/intersection_summary/` |
| 5b | Intersection Summary (PDF) | PDF (Letter, portrait) | `output/<run>/intersection_summary_pdf/` |
| 6 | Intersection Detail | XLSX | `output/<run>/intersection_detail/` |
| 6b | Intersection Detail (PDF) | PDF (Letter, landscape) | `output/<run>/intersection_detail_pdf/` |
| 7 | Highway Detail | XLSX | `output/<run>/highway_detail/` |
| 7b | Highway Detail (PDF) | PDF (Letter, landscape) | `output/<run>/highway_detail_pdf/` |
| 8 | Highway Summary | XLSX | `output/<run>/highway_summary/` |

`<run>` is a run folder `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`).
**Every enabled report exports from the production site since the 2026-07-09 prod
rollout** (it un-greyed Intersection Summary/Detail + Highway Detail — verified on
both data sources; the dev site, Settings ▸ "Use development site", is only needed
for Route History testing now). **Since v0.25.1 every enabled on-site report exports
in BOTH formats the site offers**: the five Excel reports each have a print-layout
**PDF** edition (2b / 4b / 5b / 6b / 7b — **3b graduated in v0.25.0**, **2b in
v0.26.0**, each off its first real work-PC print set —
parser/consolidator/comparisons/matrix row; **5b joined in
v0.25.1** via `ints_printAll`), and the natively-PDF Ramp Summary gained its **Excel**
sibling (**1b**, v0.25.1 — the site's `rs_exportToExcel`, previously unwired). 1b/5b
stay **export-only** by design (their siblings already consolidate + compare). The dev
site's new **Route History Table** (an embedded SSRS
report, no export flow) is wired as a **greyed reserved placeholder** (stable id 15,
the v0.18.1 Highway-pair pattern). v0.17.0 brought
reports 1–6b to parity, **v0.20.0 added Highway Detail (7/7b)**, **v0.25.0 added
Highway Sequence (PDF) (3b)**, and **v0.26.0 added Ramp Detail (PDF) (2b)**: the
**12 fully-integrated export types consolidate AND
compare vs TSN** — each has a vs-TSN comparator and lives in both the Everything and
by-day matrices (see
[docs/roadmap.md](docs/roadmap.md) / [docs/tsn-parsers.md](docs/tsn-parsers.md)
for the per-report schema + locked canaries; Highway Detail's schema was verified against
the full statewide bundle — 252 routes vs the 60k-row TSN extract — and its comparison
carries an Intersection-Detail-style **Report View** replica). Report **8 (Highway
Summary)** is **export-only** (export-enabled app-side but still site-greyed); its
integration waits for a verifiable schema. **Intersection Detail follows the site's
July-2026 report overhaul since v0.22.0** (35-column export, re-verified statewide on the
7.8 bundle; pre-update workbooks/PDFs are refused with re-export hints; canary
163,310 → 21,675). **Intersection Summary absorbed the July rename in v0.25.0**
(`MAINLINE MASTARM` → `MASTERARM`: a parsing-only alias + a section-partition tripwire —
every block but the site-under-counted Highway Group must sum to the route total, so the
next silent reshape fails loudly). **The Highway Sequence historical 7.8-Excel/
first-7.9-PDF fixture remains retained** (60,493/60,493 rows), but it is not current
same-run truth. The current July-9 pair is 60,494 Excel / 60,493 PDF rows: route 037
`003.809` is fixed in Excel, four paired PDF Descriptions are blank, and one described
Excel row is absent from PDF. Installed Excel also proves the four lowercase `_x000d_`
values are CRLF, not substantive differences. The Stage-8 audit further proves
PDF↔Excel must pair on route/county/prefix/base PM with suffix asserted — and **since
the 2026-07-16 Wave-4 batch the product does exactly that** (CMP-AUD-199: "PM Suffix"
is a compared column; 60,493 / 0 PDF-only / 1 Excel-only corpus-exact). The same batch
removed the symmetric Description rule (CMP-AUD-204 — TSN text verbatim incl. its 154
numeric prefixes; TSMIS strips only its own-route label), rebuilt the TSN normalizer
source-exact at v4 (CMP-AUD-155/156/158/159 — 69,804 rows incl. the 46 blank-county
equates, the 565 pointer tokens, no invented comma, sidecar identity/direction/policy
claims), and put typed physical identity on every HSL path (the CMP-AUD-045 gate is
**11 green / 0 known-red since 2026-07-17** — RD, ID, HSL, and HL integrated; only
HD-Excel stays vendor-blocked). **The 2026-07-17 HL batch closed CMP-AUD-157 +
045-HL with TSN Highway Log normalizer v5**: detached suffixed-route group headers
("07 LA 005 S") key their rows as the suffixed TSMIS route (005S… — 317 rows
statewide un-misattributed, exactly TSMIS's ten suffixed routes), asterisk-leading
printed Descriptions are conserved (four rows statewide — 065's "**** CODE
ACCIDENTS TO" + three bare "*" — each a manufactured false diff, TSMIS prints the
same text on the same rows), and district/county/route
ownership + the three ADT claims + typed totals + report provenance ride the
sidecar with reconciliation gates (TOTAL=CONST+UNCONST exact; suffixed sections
all-zero; zero-residue line accounting refuses unclassified content); the vs-TSN
loaders refuse pre-v5 files with a rebuild hint (marker sheet + D2 catalog bump
4→5) and the comparison Notes expose the claims; HL Route-1 re-blessed EXACT
(299/18/69/221/969). The
2026-07-16 CMP-AUD-220 batch then landed the owner-approved assignment/verdict split
(duplicate ASSIGNMENT minimizes the source-identity tuple — all-compared-field diffs,
char edit distance, position gap — while verdicts/counts stay asserted-only) plus the
HSL `_x000d_` decode (197's HSL half), so **the live HSL vs-TSN aggregate counts now
equal the Stage-8 oracle's exactly** (Excel 4,894/5,589; PDF 4,916/5,001; same-source
1,410/3,721); RD/ID re-blessed byte-identical, HL Route-1 969 intact, HD statewide
re-measured EXACT (48,644/2,599/11,439/208,596, RU Eff 48,211 — the objective change
moved nothing). The same day, **CMP-AUD-218 made Spot Check's row matching
independent** (a hidden Comparison key-token column MATCHed into the data sheets +
a Row-integrity line; forged row links/status now say CHECK — COM-mutation-gated),
and **CMP-AUD-197 closed for every current family**: RD's vs-TSN loader decodes the
Excel export's OOXML escapes too (the four Cactus City `_x000d_` cells were export
encoding — the raw TSN extract carries none), amending RD's Excel-vs-TSN canary to
737 rows / 843 cells {Desc 181} with the PDF legs unchanged. The cache-backed residual classifier
reproduces those persisted maps and aggregate arithmetic. Its original zero-unexplained claim was
withdrawn after CMP-AUD-221 through 223 exposed unconditional attribution, post-resolve
link checks, and an output/input alias hazard. The hardened classifier now proves every
assignment objective, rejects an arbitrary swap and real Windows link/alias probes, and
replays byte-identically; it is still cache-backed non-acceptance evidence. Direct-source
acceptance must reproduce the same contracts before any product count is blessed.
Stage-8 base-family audits are complete: **7/7**. Highway Log closed on exact 252-member
Excel/PDF source witnesses, its accepted-red Stage-6 chain, an independent projection
oracle, two clean seven-file product-leg universes, and two byte-identical final-gate
result/acceptance pairs. The gate accepts only the base audit: product, full-physical,
workbook-evidence, and end-to-end perfection remain false. Every owned
provenance/projection finding is now closed (047/048 shipped 2026-07-16;
157 + 045-HL + 050 + all three CMP-AUD-049 halves + 066 + 067 shipped
2026-07-17 — 050: the shared PDF-conversion driver and Ramp Summary REFUSE
duplicate or blank route claims with both source PDFs named; 049: the
DOCUMENT's own route claim — page banners (HSL/RD/HD), the ID cover's
"ROUTE : NNN" parameter, the HL cover line — is the authoritative per-route
identity in all five PDF converters AND the evidence adapters
(`reconcile_route_identity` / `RouteIdentityError`), proven refusal-free on
all 1,099 statewide 7.9 per-route documents; 066: every PDF-sourced workbook
carries a very-hidden `TSMIS PDF Conversion` marker — the TSMIS (PDF)
comparison role requires it, the TSMIS (Excel) role rejects it, pre-marker
PDF workbooks re-consolidate once; 067: the PDF-vs-Excel self-check flavors
project SAME-SOURCE values verbatim on the shared physical pairing keys —
ID's J→S fold and display rewrite are gone, HD surfaces "PM (raw)" + verbatim
NA, HL surfaces "Location (raw)" with the §7b roadbed key + ditto conventions
untouched, all guarded by the `check_compare_same_source` mutation matrix,
with statewide re-verifies: ID 16,459/0/0 + only the real 108/TUO HG cell,
HD topology exactly the v0.26.0 reference, HL measured
51,884/51,261/623/624; 045's HD-Excel leg stays blocked on the vendor county
answer — never infer it), and no product code changed during the bounded
closeout itself. The 067 sweep surfaced one follow-up, now SHIPPED: the
TSMIS-PDF Highway Log parser dropped asterisk-leading printed Descriptions
(the mirror of the TSN v5 star-recovery) — the star-guard is positional now
(left-margin totals stars close the row; description-band stars attach), all
four real rows recovered, statewide Description class 5→1. The 2026-07-17
unowned-findings triage then bucketed the 112 remaining findings A–I and
closed bucket A: CMP-AUD-065 (already fixed by 199), the 040 file half (066),
CMP-AUD-006 (the RD physical-identity postmile is Decimal-canonical now —
`decimal_pm` shared with Intersection Detail; `9.6`/`9.600`/`009.600` are one
ramp; the statewide coincidence census proved ZERO pairing changes, only
1,755 canonical-key display texts), and CMP-AUD-037 (the last direct-path
freshness gap — the three XLSX-sourced vs-TSN families now stamp an in-workbook
"TSN Normalization" marker and their `_load_tsn` refuses a pre-current library:
RD v5 / ID v5 / HD v3, HD's loader had none before; the shared
`compare_tsn_common` marker helpers, the catalog-mirror invariant gated by
`check_tsn_normalization_marker`; marker-only bumps proven row-identical on the
real statewide corpus). Exact
counts and hashes live in
[docs/planning/comparison-perfection/comparison-canary-bindings.md](docs/planning/comparison-perfection/comparison-canary-bindings.md).
The owner-authorized remediation is live on branch `comparison-perfection`; the single
resume surface is the "RESUME HERE" block in
[docs/planning/comparison-perfection/COMPLETION-PLAN.md](docs/planning/comparison-perfection/COMPLETION-PLAN.md)
(the archived implementation handoff is historical).
New reviewers start at
[docs/planning/comparison-perfection/README.md](docs/planning/comparison-perfection/README.md)
and use the linked reconciliation prompt before deciding whether to finish Stages 9–10
or propose implementation.
**Ramp Detail (PDF) was
blessed the same way in v0.26.0 on the `All Reports 7.9` pair** (15,216/15,216 rows parse
back vs the same-day Excel; PDF↔Excel now identical 15,216/15,216 — the 4 `_x000d_`
residuals were the Excel export's encoded CRs, ruled render artifacts by the owner on
2026-07-16 and decoded by the same-source rule (`compare_tsn_common
.same_source_render_text`, which also ignores edge tab padding — the Intersection
Detail PDF↔Excel false-positive class — in every PDF-vs-Excel flavor, never the
vs-TSN legs); the print carries the On/Off + Ramp Type
columns the Excel export DROPS, so the PDF-vs-TSN flavor compares two MORE columns than
Excel-vs-TSN can — +151 diff cells of new coverage statewide). Where the live site
still greys a report, `select_report` fails fast rather than stalling.
**Selecting both editions of one report (Excel + PDF, same `data_value`) coalesces** — the route
is generated **once** and both files saved off it (`run_export_combined`, v0.19.2; standard path
only, not fast mode). Consolidate-only sources exist too — **TSN**
Highway Log district PDFs (dropped into `input/tsn_highway_log/`) and the app's own
**Highway Log (PDF)**, **Intersection Detail (PDF)**, **Highway Detail (PDF)**,
**Highway Sequence (PDF)** and **Ramp Detail (PDF)** exports. The **Compare** tab diffs every report
**TSMIS-vs-TSN** (the PDF-sourced
editions among them, each also offering a **PDF-vs-Excel** self-check), runs
cross-environment comparisons, and (v0.26.0) hosts the **vs Baseline Matrix** — any
exported day of a report diffed against an EARLIER pull of the same report (a prior
day's run folder or the Everything store; same format on both sides by construction;
`baseline_matrix.py` over `compare_env`, see
[docs/comparison-engine.md](docs/comparison-engine.md) §12c). **Visual evidence (v0.21.0; + Intersection Detail in
v0.22.0; + Highway Log in v0.24.0; + Highway Sequence in v0.25.0; + Ramp Detail in
v0.26.0):** Highway Detail,
Intersection Detail, Highway Log, Highway Sequence and Ramp Detail vs-TSN comparisons
can also render sampled diffs as highlighted snippets from BOTH
PDFs (parse-back-verified; ditto-aware for HL; context-field-aware for HSL;
dual-row-aware for RD — its PDF row compares two print-only columns the Excel row
can't; `… (evidence).xlsx` with stacked +
side-by-side image tabs, plus the loose image folder, beside the comparison) — one
shared toggle+count on both matrix pages, enabled per report once its TSN prints are in
place (HD: district PDFs in `tsn_library/highway_detail/pdf/`; ID + RD: each one
statewide print in `…/intersection_detail/pdf/` / `…/ramp_detail/pdf/`; **HL + HSL: the
SAME district prints their TSN
libraries build from, read from `…/highway_log/raw/` and `…/highway_sequence/raw/` — no
duplicate drop**), and since v0.23.0 a
per-cell **camera action** regenerates a BUILT comparison's evidence on demand (no
re-compare; freshness-gated). **Since v0.24.0 the toggle spells itself out per report**
(✓ will generate / ○ needs prints → folder / a named no-support list) and supported
matrix rows carry a camera badge. See
[docs/comparison-engine.md](docs/comparison-engine.md) §13.

**Comparison-perfection audit warning (2026-07-14): Highway Sequence imagery is not
yet an end-to-end comparison verifier.** The current evidence adapter recomputes through
the product loaders instead of reading the published Comparison cells, excludes whole
difference and one-sided classes before sampling, routes Excel comparisons through a
companion TSMIS PDF, and has no source-faithful PDF-vs-Excel mode. (Spot Check's
row-matching half of this warning is REMEDIATED as of 2026-07-16 — CMP-AUD-218: it now
key-token-MATCHes both source rows independently and its Row-integrity line flags any
disagreement with Comparison's stored links/status — but a clean sample image set still
cannot bless HSL on its own.) The live source-first status and exact findings are in
[docs/planning/comparison-perfection/archive/comparison-perfection-project.md](docs/planning/comparison-perfection/archive/comparison-perfection-project.md)
and [docs/planning/comparison-perfection/comparison-audit-findings.md](docs/planning/comparison-perfection/comparison-audit-findings.md).

→ Per-report behavior + the "add a report/consolidator/comparison" recipes:
[docs/reports.md](docs/reports.md). Highway Log columns / PDF parsing / comparisons:
[docs/highway_log/](docs/highway_log/columns.md) and
[docs/comparison-engine.md](docs/comparison-engine.md).

---

## The knowledge library — read the owning doc before you touch its area

| Area | Doc |
|---|---|
| Big picture: core + front-ends, registry, run folders, data location, feature buckets | [docs/architecture.md](docs/architecture.md) |
| Export loop runtime: resume, retry, skip/cancel, fast-fails, timeouts, fast mode | [docs/engine-and-reliability.md](docs/engine-and-reliability.md) |
| Sign-in: token-in-hash, `CONFIG` trap, device SSO, Edge recapture, LNA, login chips | [docs/auth-and-signin.md](docs/auth-and-signin.md) |
| Desktop GUI: pywebview/WebView2, threading/queue, the **5 pywebview traps**, the `#mock` | [docs/gui.md](docs/gui.md) |
| Report catalog, `ReportSpec`, `cs-disabled`, the extension recipes | [docs/reports.md](docs/reports.md) |
| `compare_core`: regression lock, flavors, key/roadbed/ditto, write-path safety, families | [docs/comparison-engine.md](docs/comparison-engine.md) |
| Corrected 31-column Highway Log labels | [docs/highway_log/columns.md](docs/highway_log/columns.md) |
| Highway Log PDF (cell-rect) + TSN (char-window) parsers | [docs/highway_log/pdf-and-tsn-parsing.md](docs/highway_log/pdf-and-tsn-parsing.md) |
| The `+`/`++` ditto domain convention + evidence | [docs/highway_log/comparison-study.md](docs/highway_log/comparison-study.md) |
| Build, `app.spec`, DLP prune, browser channels, the **updater**, CI | [docs/build-and-release.md](docs/build-and-release.md) |
| IT/DLP/security, the **work-PC capability model**, audit findings, code-signing | [docs/it-and-security.md](docs/it-and-security.md) |
| The **`gh-pages` landing page** — layout, live download button, theme toggle, screenshot/OG regen, SEO | [docs/website.md](docs/website.md) |
| How to verify (no test framework): golden `check_*.py`, COM-recalc, `#mock`, test-data locations | [docs/verification-and-testing.md](docs/verification-and-testing.md) |
| The durable lessons (field failures, one-core, regression discipline, audit method) | [docs/lessons.md](docs/lessons.md) |
| The narrative history | [docs/history.md](docs/history.md) |
| Roadmap / deferred / dormant backlog | [docs/roadmap.md](docs/roadmap.md) |
| The reusable read-only code-review prompt | [docs/code-review-prompt.md](docs/code-review-prompt.md) |

Code-level deep-dives (algorithms, data/control flow, extension points) live under
**`docs/internals/`** — `compare-core`, `highway-log-data-processing`, `gui-bridge`,
`auth-state-machine`, `export-engine`, `updater-swap`. Full map with "read this when…"
for each topic + internals doc: **[docs/INDEX.md](docs/INDEX.md)**.

---

## Conventions (non-negotiable — apply every session)

- **Core is console-free.** `common.py`, `exporter.py`, the consolidator/comparison
  cores report via the `Events` sink (`scripts/events.py`) and raise exceptions —
  **never** `print`/`input`/`sys.exit`. Only `cli.py` and `gui_*.py` touch
  I/O/the window. User-facing strings from the core stay **UI-neutral** (no ".bat"
  names, no "this window" / "menu option N" — that guidance lives in the driver).
- **No AI attribution anywhere** — commits, PR titles/descriptions, code, comments.
  Write as if the user authored it. (Project-specific reinforcement of the global rule.)
- **Never commit** `scripts/tsmis_auth.json` (treat as a credential), generated
  `output/`, or build artifacts (`build/.venv`, `dist/`, `.claude/` state).
- **`compare_core` semantics are correctness-locked, not history-locked.** Equality,
  formula, normalization, identity, pairing, and count changes must follow the approved
  domain contract and be proved cell-for-cell against the independent oracle plus both
  workbook flavors. Preserve historical output only when it is correct; a confirmed defect
  must be fixed globally when the contract is global, even if canary counts or bytes change.
  Every deliberate delta needs exact input/output evidence and an explained re-bless. Opt-in
  `CompareSchema` fields remain appropriate for truly report-specific behavior, but are not a
  shield for a broken shared engine. The typed `ComparedCell` and hidden versioned
  `E`/`D`/`N`/`U` state masks own discrepancy truth; the visible ` ≠ ` separator is content/
  presentation only and must never be scanned for state. See
  [docs/comparison-engine.md](docs/comparison-engine.md). Before Phase-3 equality/pairing
  work, read and honor the approved policy/oracle gates in
  [docs/planning/comparison-perfection/comparison-phase3-decision-gates.md](docs/planning/comparison-perfection/comparison-phase3-decision-gates.md).
- **Comparison perfection is source-first and end to end.** Before changing any
  comparison family, read the CURRENT surface:
  [docs/planning/comparison-perfection/COMPLETION-PLAN.md](docs/planning/comparison-perfection/COMPLETION-PLAN.md).
  Its "YOU ARE HERE / RESUME HERE" block is the owner-facing progress surface; update it
  whenever a finding closes, a blocker is added/removed, or the next proof changes (start
  new reviewers at [README.md](docs/planning/comparison-perfection/README.md)). The
  [archived project doc](docs/planning/comparison-perfection/archive/comparison-perfection-project.md)
  holds the point-in-time Stage-8 audit history only. Keep detailed bugs/hashes in the
  linked finding/source/canary ledgers rather than duplicating them into new planning files.
  Raw TSN is the starting truth; rebuild normalized inputs in isolation, prove
  raw-to-normalized record/field conservation, re-prove comparison cells independently,
  and require all supported evidence to agree with both PDFs and the Comparison sheet.
  Historical outputs/counts never override source facts, and a missing source fact is a
  hard stop rather than permission to infer it.
- **Duplicate identity is exact, typed, and auditable.** Within the 100,000-cell
  product cap, use the rectangular Hungarian assignment under the owner-approved
  source-identity objective — the lexicographic (all-compared-field diff count, char
  edit distance, |position gap|) tuple, where context/ditto cells decide WHICH
  occurrences correspond while verdicts and counts stay asserted-only (the CMP-AUD-220
  assignment/verdict split; D3 amendment 2026-07-16) — with the approved
  lexicographically-smallest smaller-side vector as the final tie; never reintroduce
  greedy, file-order, or asserted-only-assignment certification. Above the cap,
  positional output is partial/capped diagnosis only and
  can never be green or a match. Persist the complete typed duplicate trace and capped
  diagnostics (v2 traces carry the objective triples; v1 payloads stay readable and
  byte-stable). Workbook lookups use versioned opaque ordinal tokens—never delimiter-
  flattened route/key text. Cancellation during source validation, pairing, or count
  construction returns unknown counts/quality with no trace or workbook mutation.
- **A generated workbook certifies only its build-time identity.** The visible source
  sheets, opaque helpers, Med-Wid stages, and row universe are bound to very-hidden
  `CMP_E2_SNAPSHOT_V1` sheets and tail sentinels. Any post-build source/helper edit must
  make Summary say `REGENERATE REQUIRED`; live observations under stale duplicate
  assignment are diagnostic and cannot certify either match or differences.
- **Completion is producer-owned; prose is never state.** `outcome.py` owns the
  consolidator vocabulary (completion ∈ complete/partial/no_data/cancelled/failed ×
  artifact ∈ promoted/new_unpromoted/previous_preserved/none), while
  `comparison_contract.py` owns typed comparison truth. Canonical report/store
  promotion still requires a complete result. A comparison's observed partial
  generation may currently be committed and cached so it can be shown amber and
  retried, but it may never be called fresh, green, or a match. The Phase-5
  last-complete/unpromoted-partial policy remains open. See
  [docs/engine-and-reliability.md](docs/engine-and-reliability.md).
- **Every returned public comparison terminal is typed, even without an artifact.**
  `comparison_result_boundary` covers file and folder adapters, normalizing missing
  input/dependency/preflight/shape errors, overwrite cancellation, `no_data`, and commit
  failure into a fail-closed `ComparisonOutcome` plus terminal `AttemptState`. It never
  parses `summary_lines`. If no workbook committed, `artifact_generation` MUST remain
  `None` and `attempt_state.generation_id` MUST remain empty; only real committed bytes
  receive a generation and member sidecars.
- **Generated artifacts are transactional and ownership-bound.** Reject every selected/
  derived output that aliases an effective input; under user destinations, write only
  through a current purpose-bound `OwnershipLease`. Use exclusively reserved,
  identity-bound temps then `os.replace`;
  a partial/failed/cancelled refresh **keeps last-good** (never clobbers it). Ordinary
  persistent workbooks carry producer-set `consolidation_meta` completion sidecars.
  Comparison consumers use the stricter contract instead: returned
  `ComparisonOutcome`, committed `ArtifactGeneration`, succeeded `AttemptState`, and
  the trusted/current persisted member generation must agree exactly through
  `consolidation_meta.require_published_comparison`. A sentinel, peer/digest mismatch,
  malformed metadata, or returned/persisted disagreement is untrusted; missing/stale
  metadata is stale. Comparison schema v3 uses one bounded canonical compressed payload
  shared by small peer envelopes; inline schema v2 remains read-compatible. Publication
  is parent-serialized across local threads/processes, installs chunks
  process-interruption-safely without replacement (power-loss durability is NOT
  claimed — readers fail closed on torn state; cleanup unlinks are bound to the
  verified inode via a Windows handle), and succeeds only when the persisted
  outcome/generation/member exactly equals its own attempt. Peers are validated before the payload is decoded
  once; over-limit or high-expansion payloads fail closed. No-artifact terminal results
  are not sent through this committed-generation reducer. `cache_envelope.py` versions
  the matrix/by-day caches. Matrix
  formula-twin unification, durable attempt overlays/provenance, and exact-generation
  evidence remain their assigned Phase-5/7 work.
- **Workbook count scraping is diagnostic/migration-only.** `read_counts` locates
  Status/Diffs by HEADER LABEL (never hard-coded position), but Matrix, classic UI,
  and validation truth comes from the strict typed comparison generation. Workbook
  scraping must never certify a green UI result.
- **`report_catalog.py` is the report-metadata SoT**; `reports.py` is **derived** from
  it (EXPORT/CONSOLIDATE/COMPARE lists, matrix rows, stable-ID lookups, the picker
  `group`/`short_label` + `_PICKER_ORDER`). Stable IDs are immutable string keys;
  `batch_manifest._V017_EXPORT_ORDER` (== `EXPORT_KEYS`) is **append-only** — positions
  0–7 frozen; v0.18.1 appended Highway Detail/Summary at 8/9 as reserved-DISABLED
  groundwork, **v0.19.1 enabled their EXPORT** (`DISABLED_EXPORT_SUBDIRS` now empty;
  real Excel-sibling specs). Highway Detail now consolidates and participates in the
  Matrix, cross-environment, vs-TSN, and PDF-vs-Excel comparisons; Highway Summary
  remains export-only until a real enabled-site schema can be verified. Add a report by editing the catalog;
  `check_report_catalog` proves the derivation. See [docs/reports.md](docs/reports.md).
- **Select reports by stable `data_value`, not visible text** (v0.18.1). `select_report`
  and the env-scan probe match the `#customReport` option by its `data-value` (the site's
  stable id) and reveal the `cs-submenu` flyout for a leaf, falling back to exact text/
  `data-label`. This keeps exports working as the site migrates its report dropdown from a
  flat list to grouped fly-outs (live on **dev**) WITHOUT breaking the current flat **prod**
  menu. Each `ReportSpec` carries its `data_value`; the picker is grouped to mirror the site.
- **Sync Playwright API** (not async); Playwright is **thread-affine** — only the
  owning thread may touch a page.
- **Call the timeout ACCESSORS** (`report_timeout_ms()` etc.) in engine code, not the
  raw constants — they read Settings overrides at run time.
- **Log every decision.** Each decision point (site/browser pick, channel fallback,
  saved-session-vs-device-mode, per-route outcome) and every swallowed exception logs
  at least `type(e).__name__` + the first line — the "one log upload answers it"
  contract. Error messages name the failing step and stay UI-neutral; the WHY goes to
  the log.
- **The updater TLS trusts the Windows cert store** (`ssl.create_default_context()`).
  Never switch it to `requests`/`certifi` — a bundled CA list breaks corporate
  TLS inspection on exactly the managed PCs that need it.
- **Real test data + the live TSMIS website source are LOCAL ONLY** under
  `C:\Users\Yunus\Downloads\TSMIS\…` — never commit, copy into the repo, or push;
  the website source is Caltrans-internal. Read that corpus's `_INDEX.md` before
  choosing fixtures: `ground-truth/` is the acceptance oracle, `report-samples/`
  is for parser spot checks, `comparison-outputs/` is historical reference only,
  and `_scratch/` is disposable and must never become an oracle. Bind and record
  the exact canonical bundle/input identities used by each real-data canary in
  [docs/planning/comparison-perfection/comparison-canary-bindings.md](docs/planning/comparison-perfection/comparison-canary-bindings.md).
- **Work-PC reality:** any feature that must run on the locked-down Caltrans work PC
  must work as a plain unsigned exe from a user-writable folder — no PowerShell, cmd,
  admin, temp scripts, or scheduled tasks. See [docs/it-and-security.md](docs/it-and-security.md).
- **Git:** commit/push only when asked; if on `main`, branch first. Commit messages
  are short, imperative (`add route 395`). Release branches share the tag name, so
  push tags explicitly: `git push origin refs/tags/<tag>`.

---

## Repo layout (orientation)

```
1.–5. *.bat                  setup / login / export / consolidate / fast export (console flow)
run app (GUI preview).bat    dev launcher for the GUI
version.py                   app name/version + pinned Playwright (single source of truth)
scripts/                     the engine (console-free) + console & GUI drivers + UI
  common.py                  a re-export SHIM over the acyclic engine leaves below
  auth_nav.py report_nav.py session.py site_target.py routes.py errors.py timeouts.py
  browser_channels.py edge_device.py   the extracted engine leaves common.py re-exports
  exporter.py exporter_parallel.py export_multi.py run_report.py cli.py events.py settings.py paths.py
  outcome.py comparison_contract.py cache_envelope.py consolidation_meta.py artifact_store.py owned_dir.py
                              outcome/typed comparison/transaction/ownership
  report_catalog.py          the report-metadata source of truth (P4); reports.py derives from it
  reports.py                 the report/consolidate/compare registry view + stable-ID lookups
  export_*.py                one thin ReportSpec per report type (incl. *_pdf editions)
  consolidate_*.py           per-route exports → one workbook (+ TSN / TSMIS-PDF parsers)
  compare_core.py            the correctness-locked comparison-workbook engine
  compare_tsn_common.py      the shared FILE-comparator substrate (P5b; every comparator rides it since v0.19.0)
  compare_env.py compare_highway_log*.py compare_*_tsn.py compare_*_pdf.py   the comparison families over compare_core
  visual_evidence.py evidence_*.py       the evidence-images engine + adapters (HD, ID, HL, HSL, RD)
  pdf_table_lib.py           the shared PDF-table machinery (clusterer/columns/writer/convert loop, R2)
  matrix.py                  the matrix FACADE (patch matrix.<name>) over matrix_state.py + matrix_build.py
  matrix_state.py matrix_build.py day_matrix.py summary_layout.py   matrix reads / builds + by-day + summary
  tsn_library.py tsn_load_*.py   the canonical TSN library (versioned normalization, D2) + its loaders
  highway_log_columns.py intersection_detail_columns.py highway_detail_columns.py   the per-report column labels
  gui_main.py gui_api.py     GUI entry / the bridge core (state, pump, gate)
  gui_export_api.py gui_auth_api.py gui_compare_api.py gui_settings_api.py gui_update.py   the endpoint mixins (S1)
  gui_worker.py              re-export SHIM over gui_worker_export/_env/_maint/_matrix.py (S2)
  task_coordinator.py contract.py        GUI task-state owner / Python⇄JS bridge enum SSOT
  gui_endpoint.py gui_matrix.py gui_win32.py   the endpoint envelope (+_task_endpoint/pick_path) / matrix mixin / Win32
  validation.py credential_safety.py     one-click validation + diagnostic credential guard
  site_capture.py            the Settings website-source capture (v0.26.0, local-only)
  baseline_matrix.py         the Compare-tab "vs Baseline" day-vs-baseline matrix (v0.26.0)
  ui/                        index.html app.css app.js + ui-export/-batch/-compare/-matrix/-settings/-dom.js + mock.js + contract.js
  self_test.py evidence.py pdf_row_oracle.py owned_dir.py safe_delete.py   self-test / evidence / safety
  updater.py login.py logging_setup.py batch_manifest.py report_library.py
build/                       build.ps1, app.spec, prune_bundle.ps1, full_smoke.py, check_*.py
  gen_release_notes.py release_notes_header.md backfill_release_notes.ps1   per-version release notes
CHANGELOG.md                 user-facing changelog (one section per version; source of release bodies)
tools/                       dev utilities (not shipped) — screenshots.py regenerates the site/README shots
docs/                        the knowledge library (start at docs/INDEX.md)
output/ input/               generated/user data (git-ignored except .gitkeep stubs)
```

The **landing page** is on a separate **`gh-pages`** branch (GitHub Pages), not in
`main` — see [docs/website.md](docs/website.md). Detail on anything above is in the
matching `docs/` file (see the table above).

---

## Pinned versions

`version.py` / `requirements*.txt`: `playwright==1.60.0` (Node driver only — no
Chromium ships in the default build), `pdfplumber==0.11.9`
(→ `pdfminer.six==20251230`; its `pillow==12.2.0` + `pypdfium2==5.9.0`
transitives are LOAD-BEARING since v0.21.0 — the evidence-image render stack —
and pinned explicitly), `openpyxl==3.1.5`, `pywebview==6.2.1`
(→ `pythonnet`/`clr_loader`), `pyinstaller==6.20.0`,
`pyinstaller-hooks-contrib==2026.5`. Built/tested on **Python 3.11**. Rationale +
the three release variants: [docs/build-and-release.md](docs/build-and-release.md).
