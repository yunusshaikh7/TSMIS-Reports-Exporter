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

`<run>` is a run folder `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`);
**since v0.32.0 each per-route file inside it carries that run identity
front-anchored in its NAME** (`2026-07-23 ssor-prod highway_log_route_3.xlsx` —
`paths.resolve_route_file`; legacy dateless names are honored on resume so an old
partial run never leaves one route with two files, and the end-anchored
`_route_<token>.<ext>` contract is untouched).

**Current export state.** Every enabled report exports from the **production** site
(the 2026-07-09 prod rollout; the dev site — Settings ▸ "Use development site" — is
only needed for Route History testing), and every enabled on-site report exports in
**BOTH formats** the site offers. **1b/5b are export-only by design** (their siblings
already consolidate + compare); **8 (Highway Summary) is export-only** until the site
un-greys it and a schema can be verified. **Selecting both editions of one report
coalesces** — the route is generated ONCE and both files saved off that render — on
the standard path (v0.19.2), in fast mode, and for matrix-queued edition steps (both
v0.32.0). Where the live site greys a report, `select_report` fails fast rather than
stalling. The dev site's **Route History Table** is a greyed reserved placeholder
(stable id 15), and the **Clean Road Files** group (`clean_highway` /
`clean_intersection` / `clean_ramp`, stable ids 16/17/18) is `cs-disabled` on the
site with refusing placeholder specs (`export_clean_road.py`).

**The 12 fully-integrated export types consolidate AND compare vs TSN** — each has a
vs-TSN comparator and lives in the Everything, by-day, and (for the 5 dual-edition
families) PDF-vs-Excel matrices. Per-report schemas + locked canaries:
[docs/reports.md](docs/reports.md) / [docs/tsn-parsers.md](docs/tsn-parsers.md);
exact counts and hashes:
[comparison-canary-bindings.md](docs/planning/comparison-perfection/comparison-canary-bindings.md).
Format-change precedents are absorbed and gate-guarded: Intersection Detail follows
the site's July-2026 35-column overhaul (pre-update files are refused with re-export
hints), and Intersection Summary's `MASTARM`→`MASTERARM` rename rides a parse-only
alias + a section-partition tripwire so the next silent reshape fails loudly.

**⛔ Highway Detail (7/7b) is PRE-RELEASE (owner, 2026-07-21): the vendor ACCIDENTALLY
enabled its exports, they are GREYED OUT again, and the report is in ACTIVE
DEVELOPMENT.** Every HD artifact on disk came from that accidental window — treat none
of it as ground truth, do not re-bless HD canaries as stable, and do NOT fix the HD
parser/normalizer against it (CMP-AUD-133/142/186 are deferred). 045's HD-Excel county
cannot be answered yet — never infer it. The owner will supply NEW HD exports on
official integration; that delivery is the trigger to re-verify the schema and resume.

**The ArcGIS tab (v0.29.0) builds the HIGHWAY clean-road file WITHOUT the site**: our
own 74-column CA HIGHWAYS table from the owner's per-layer ArcGIS exports in
`arcgis_layers/` (the 40-layer library; county+PM overlay as-of the TSN extract's own
date; per-column Provenance colour-coded by tier), compared vs the TSN extract in both
flavors with every column indexed to its source layer and the 24 context columns
tinted grey in the values sheet (v0.32.0). Blessed statewide canary `CRH-SW-E2`;
measured build rules + provenance tiers in
[docs/planning/cleanroad-highways.md](docs/planning/cleanroad-highways.md), the family
in [docs/comparison-engine.md](docs/comparison-engine.md) §9j. `tsn_load_clean_road`
normalizes CA HIGHWAYS verbatim (marker v1); the Intersection/Ramp slots stay
deliberately normalizer-less until their builds land on the same pattern.

**Consolidate-only sources**: TSN Highway Log district PDFs (dropped into
`tsn_library/highway_log/raw/` — the one drop location since v0.30.0 retired
`input/`) and the app's own five PDF editions. The **Compare** tab diffs every report
TSMIS-vs-TSN (each PDF edition also offers a PDF-vs-Excel self-check), runs
cross-environment comparisons, and hosts three matrices beyond the Everything one:
the **by-day** vs-TSN matrix, the **vs Baseline Matrix** (any exported day vs an
EARLIER pull of the same report; `baseline_matrix.py`, §12c), and the **PDF vs Excel
Matrix** (v0.31.0 — the 5 dual-edition families × exported days, each cell that day's
PDF export self-checked against its Excel export from the SAME run folder;
`pdf_excel_matrix.py`).

**Visual evidence** (HD, ID, HL, HSL, RD vs-TSN + the self checks): sampled diffs
render as highlighted snippets from both sources — parse-back-verified, ditto-aware
for HL, context-field-aware for HSL, dual-row-aware for RD — as an
`… (evidence).xlsx` + image folder beside the comparison. One shared toggle+count on
the matrix pages (per-report readiness spelled out; camera badges; a per-cell camera
regenerates a BUILT comparison's evidence, freshness-gated). TSN prints live in
`tsn_library/<report>/pdf/` (HD/ID/RD) or ARE the library's own `raw/` district
prints (HL/HSL — no duplicate drop). See
[docs/comparison-engine.md](docs/comparison-engine.md) §13.

**The evidence truth layer** (shipped with the comparison-perfection completion):
`published_comparison.py` decodes and authenticates the committed values workbook's
own cells (the hidden `E`/`D`/`N`/`U` state masks, the anchored Status/Diffs
contract, opaque row tokens) — the published cell, not the adapters, decides whether
an image may be taken. An EXHAUSTIVE hash-bound **Ledger** sheet is written before
any sample is drawn; each side is evidenced **from the source that side was read
from** (an Excel-compared row renders from the workbook itself, and since v0.32.0
its column is resolved the COMPARATOR'S OWN way via each adapter's
`excel_column_for` — the M2-D fix); the whole set is ONE published generation
(`evidence_manifest.py`: content digest + ledger digest + a private read-set
snapshot + two-phase quarantine-and-promote). **Not claimed:** the loaders'
per-field projections against the raw PDFs — the separately-tracked direct-source
acceptance. Details + acceptance oracles: §13 and the
[finding ledger](docs/planning/comparison-perfection/comparison-audit-findings.md).

**The comparison-perfection project is COMPLETE (2026-07-22, v0.28.0).** 237 of 242
findings closed; `main` is the completion state. The 5 still open are ALL the ⛔
Highway Detail pre-release block (133 · 142 · 186 · 192 + 045-HD) and reopen only when
the vendor delivers official HD exports. The
[COMPLETION-PLAN](docs/planning/comparison-perfection/COMPLETION-PLAN.md) + finding
ledger are the PROJECT RECORD of why each comparison behaves as it does (start at
[README.md](docs/planning/comparison-perfection/README.md)).
**Owed, and only the owner can do it: the work-PC acceptance run — now targeting
v0.32.0** (the dev box cannot reach the TSMIS intranet): comparison + evidence output
intentionally differ from v0.26.2/v0.27.x (re-run both sides, never reconcile old
against new), TSN libraries rebuild once, PDF-sourced workbooks re-consolidate once,
plus the v0.30–v0.32 items in
[the backlog plan §4](docs/planning/v0.30-owner-backlog-plan.md) (Edge Retry, the
PDF-vs-Excel matrix, fast-mode dual-format, the mixed-name resume, an Excel-row
evidence run).

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
- **Comparison work stays source-first and end to end.** The project that established
  this closed in v0.28.0, but the DISCIPLINE is permanent, not a phase. Before changing
  any comparison family, read
  [docs/planning/comparison-perfection/COMPLETION-PLAN.md](docs/planning/comparison-perfection/COMPLETION-PLAN.md)
  and the finding ledger — now the PROJECT RECORD of why each behavior is what it is
  (start new reviewers at [README.md](docs/planning/comparison-perfection/README.md); the
  [archived project doc](docs/planning/comparison-perfection/archive/comparison-perfection-project.md)
  holds the point-in-time Stage-8 audit history). If you reopen a finding or open a new
  one, update its entry Status line AND the ledger index table AND the plan together —
  index tables drifting behind entries caused repeated stale-directive incidents. Keep
  detailed bugs/hashes in the linked finding/source/canary ledgers, not in new planning
  files. Raw TSN is the starting truth; rebuild normalized inputs in isolation, prove
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
  generation may be committed and cached so it can be shown amber and retried, but it
  may never be called fresh, green, or a match. **The last-complete/unpromoted-partial
  policy is DECIDED and SHIPPED** (2026-07-22, CMP-AUD-085 — see the last-complete
  convention below). See
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
  the matrix/by-day caches — including the per-cell **attempt overlay**
  (`comparisons/_attempts.json`, CMP-AUD-089): every compare worker persists each
  touched cell's terminal state there, `ok` clears it, and the snapshot merges it as
  `cmp.last_attempt` so a failed/stopped/incomplete refresh marks the cell WITHOUT
  erasing the last-good result it did not replace. Matrix formula-twin unification and
  exact-generation evidence remain their assigned Phase-5/7 work.
- **The canonical persistent consolidation is the LAST COMPLETE generation** (owner
  decision 2026-07-21; CMP-AUD-085). When a trusted COMPLETE canonical exists, a refresh
  builds into an unpromoted attempt sibling and only a `status=ok` + COMPLETE result is
  promoted over it; anything else KEEPS LAST-GOOD — the verified bytes and sidecar are
  untouched, the attempt is published beside them carrying its own PARTIAL sidecar, and
  the caller is REFUSED so no comparison ever diffs the stale complete generation
  against current inputs. A first build with no complete predecessor still persists the
  flagged partial (amber, retryable). Never restore replace-and-flag.
- **Source and cached-output identity is CONTENT, not metadata** (CMP-AUD-080).
  `artifact_store.fingerprint` is the v2 content fingerprint; per-file digests may be
  memoized ONLY against a change token that a same-size, timestamp-restored rewrite
  cannot forge (on Windows `FILE_BASIC_INFO.ChangeTime` beside size/mtime/file id) —
  stat-only memoization is prohibited, and a file with no obtainable token is re-hashed.
  A typed comparison's VALUES artifact must also satisfy the versioned
  `COMPARISON_ARTIFACT_SCHEMA` at the commit boundary (CMP-AUD-115): uniquely labelled
  `Status`/`Diffs`, a valid status on every row, and rows present when the typed outcome
  claims rows. That gate shares its reader with `read_counts`, so what it refuses was
  already unreadable — keep it that way; a gate that could refuse a workbook the Matrix
  can read would block a valid report.
- **Workbook count scraping is diagnostic/migration-only.** `read_counts` locates
  Status/Diffs by HEADER LABEL (never hard-coded position), but Matrix, classic UI,
  and validation truth comes from the strict typed comparison generation. Workbook
  scraping must never certify a green UI result.
- **`report_catalog.py` is the report-metadata SoT**; `reports.py` is **derived** from
  it (EXPORT/CONSOLIDATE/COMPARE lists, matrix rows, stable-ID lookups, the picker
  `group`/`short_label` + `_PICKER_ORDER`). Stable IDs are immutable string keys;
  `batch_manifest._V017_EXPORT_ORDER` (== `EXPORT_KEYS`) is **append-only** — positions
  0–7 frozen; v0.18.1 appended Highway Detail/Summary at 8/9 as reserved-DISABLED
  groundwork, **v0.19.1 enabled their EXPORT** (cleared the Highway pair from
  `DISABLED_EXPORT_SUBDIRS`; real Excel-sibling specs — the gate now holds only the
  reserved Route History placeholder, id 15). Highway Detail now consolidates and participates in the
  Matrix, cross-environment, vs-TSN, and PDF-vs-Excel comparisons; Highway Summary
  remains export-only until a real enabled-site schema can be verified. Add a report by editing the catalog;
  `check_report_catalog` proves the derivation, and **`check_report_wiring` (v0.31.0)
  derives from `report_catalog.MATRIX` what every registered report MUST have —
  dispatchable vs-TSN/self comparators, dual-edition completeness, a by-day row, Reset
  coverage — and FAILS naming the missing touchpoint** (the v0.17.3 "forgot one mirror"
  field-crash class). See [docs/reports.md](docs/reports.md).
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
  report_catalog.py          the report-metadata source of truth (P4); reports.py derives from it.
                             Its MATRIX table (v0.31.0, M2-A) is the ONE per-row comparison
                             wiring (vs-TSN + PDF-vs-Excel comparators + the format tag) that
                             matrix_state/day_matrix/pdf_excel_matrix all derive from
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
  arcgis_layers.py           the manually-stocked ArcGIS layer drop-zone (staging only, no parser)
  highway_log_columns.py intersection_detail_columns.py highway_detail_columns.py   the per-report column labels
  gui_main.py gui_api.py     GUI entry / the bridge core (state, pump, gate)
  gui_export_api.py gui_auth_api.py gui_compare_api.py gui_settings_api.py gui_update.py   the endpoint mixins (S1)
  gui_worker.py              re-export SHIM over gui_worker_export/_env/_maint/_matrix.py (S2)
  task_coordinator.py contract.py        GUI task-state owner / Python⇄JS bridge enum SSOT
  gui_endpoint.py gui_matrix.py gui_win32.py   the endpoint envelope (+_task_endpoint/pick_path) / matrix mixin / Win32
  validation.py credential_safety.py     one-click validation + diagnostic credential guard
  site_capture.py            the Settings website-source capture (v0.26.0, local-only)
  baseline_matrix.py         the Compare-tab "vs Baseline" day-vs-baseline matrix (v0.26.0)
  pdf_excel_matrix.py        the Compare-tab "PDF vs Excel" by-day self-check matrix (v0.31.0, M2-B)
  ui/                        index.html app.css app.js + ui-export/-batch/-compare/-matrix/-settings/-dom.js + mock.js + contract.js
  published_comparison.py evidence_ledger.py evidence_manifest.py   the evidence TRUTH layer: decode+authenticate the published comparison / the exhaustive ledger / the durable generation record
  self_test.py evidence.py pdf_row_oracle.py owned_dir.py safe_delete.py   self-test / the work-PC diagnostic bundle (--collect-evidence) / safety
  updater.py login.py logging_setup.py batch_manifest.py report_library.py
build/                       build.ps1, app.spec, prune_bundle.ps1, full_smoke.py, check_*.py
  gen_release_notes.py release_notes_header.md backfill_release_notes.ps1   per-version release notes
CHANGELOG.md                 user-facing changelog (one section per version; source of release bodies)
tools/                       dev utilities (not shipped) — screenshots.py regenerates the site/README shots
docs/                        the knowledge library (start at docs/INDEX.md)
output/                      generated data (git-ignored except .gitkeep stubs)
tsn_library/ arcgis_layers/   manually-stocked source libraries (git-ignored, local-only;
                             TSN district PDFs live in tsn_library/<report>/raw/ — input/ retired v0.30.0)
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
