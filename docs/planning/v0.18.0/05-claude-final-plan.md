# Claude Final v0.18.0 Plan — Ready for User Approval

**Release:** v0.18.0 — structural optimization + engineering overhaul.
**Baseline:** HEAD `d2ee353`, tag `v0.17.1`, clean tree; compile green; 44/44 CI golden checks pass.
**History:** `01-claude-investigation.md` + `02-codex-investigation.md` → `03-claude-draft-plan.md` →
`04-codex-plan-review.md` (Round 1, verdict **NOT READY**) → **this final plan.**

Codex Round 1 raised 12 blocking + ~30 required/recommended findings. **All blocking and required
findings are resolved below** with repository-backed reasoning; the few items needing a genuine user
decision are isolated as gates (O1/O2/O7) and excluded from the definition of done. The central thesis
is unchanged and was endorsed: **make the implicit completion/freshness/promotion contracts explicit
and tested first; decompose second.**

---

## A0. Readiness reviews — blocker dispositions

### Round 1 (resolved)

Disposition ∈ Resolved · Resolved-with-mod · Rejected (repo-backed) · Requires-user-decision.

| ID | Readiness item | Disposition | Resolution |
|---|---|---|---|
| RR1-B1 (blocking) | Item-by-item disposition of every still-open Phase-3 audit finding must be **in the plan now**, not deferred to P11 (§I doesn't disposition most). | **Resolved** | New **§J2** dispositions every still-open finding (incl. all 10 Codex named) to a phase or explicit deferral + destination; none silently dropped. §A.5/R1-M05 and P11 now point to §J2; P11 only **writes** the decisions into canonical docs. |
| RR1-B2 (blocking) | Updater `size-and-checksum-guards-both-skippable` is mis-marked "Implement" while size-only install still proceeds with a warning; publication checks don't close the **runtime** fallback. | **Resolved-with-mod** | §J/§J2 changed to **Implement (fail-closed)**: the runtime updater **requires a verified `.sha256`/API digest before extraction** and **aborts + shows the release page** when absent — never installs size-only (also subsumes `asset_size==0`, since the SHA covers integrity regardless of size). |
| RR1-C1 (caution) | "13 work units" vs 16 headings; P11's broad `P1..P10` edge. | **Resolved** | §H now reads **16 phase headings = 13 release-blocking + 3 conditional**; P11 depends only on the **release-blocking** phases. |
| RR1-C2 (caution) | Clarify the `cryptography` pin locks the existing `pdfminer.six` transitive, not a new crypto dependency. | **Resolved** | P10 clarified: pin the **existing** `cryptography` transitive (pulled by `pdfminer.six`) for lock integrity — **not** a new dependency; distinct from the deferred runtime-signature dep (A03). |
| RR1-C3 (caution) | P2 journal must sit outside any renamed dir; specify the `mode="both"` wrapper while keeping `compare_core` untouched. | **Resolved** | §C.2 now places the journal at `<dest>/.promote/<token>.json` (parent, never inside the renamed `live`) and specifies the values-first/formulas-best-effort `mode="both"` wrapper that hands the comparator temp paths and rewrites returned paths — `compare_core` unchanged. |

No readiness item requires a **new** user decision; the standing gates remain **O1/O2/O7** (unchanged). The
DPAPI half of the auth-at-rest finding stays under O2.

### Round 2 (current)

Disposition ∈ Resolved · Resolved-with-mod · Rejected (repo-backed) · Requires-user-decision.

| ID | Readiness item | Disposition | Resolution |
|---|---|---|---|
| RR2-B1 (blocking) | §J2 wrongly lists the **PDF Highway Log trio** (`pdf-consolidator-no-row-count-verification`, `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-stale-geometry-carryforward-silent-corruption`) as closed; v0.17.0 added **reporting only** — rows are still emitted from stale geometry and there is no independent completeness check. | **Resolved** | §J2 removes the trio from "closed" and **dispositions each explicitly** (Resolved / Mitigated / Deferred) with phase + acceptance evidence. Verified at HEAD: `consolidate_tsmis_highway_log_pdf.py:294` ("reporting only … row-emit logic unchanged"), `:386` (stale page counted, still emitted); `check_tsmis_pdf_reconcile.py:78–81` asserts banners only (parse_pdf stubbed). The reporting change is **not** described as closing parser correctness. |
| RR2-C1 (caution) | `wait_js` validation sits in behavior-neutral P8b. | **Resolved** | Kept in **P8b as the single explicitly-permitted narrow behavior change**, with `check_export_engine` characterization (offline; not O7-gated). §J2 row updated. |
| RR2-C2 (caution) | P8c audit items marked unconditionally "Resolved" despite O7. | **Resolved** | §J2 records the **default for every P8c item as Deferred (point release) when O7 is unavailable**; Resolved only once work-PC acceptance lands. |
| RR2-C3 (caution) | Extracted `mock.js` can't keep `app.js`'s immediate `boot(makeMockApi())`. | **Resolved** | §C.6 Q10 + P9 specify **`mock.js` owns the mock boot** (defines `makeMockApi`, then calls `boot(...)`); `app.js` auto-boots only in production. |

No new user decision; the standing gates remain **O1/O2/O7** (unchanged).

### Round 3 (current)

**Verdict: `READY FOR USER APPROVAL`** — no blocking corrections. Architecture, contracts, sequencing, and
the full Phase-3 audit reconciliation are accepted. Three **non-blocking cautions** are folded in below;
none requires a redesign or a new user decision.

| ID | Readiness item (caution) | Disposition | Resolution |
|---|---|---|---|
| RR3-C1 | If O7 is unavailable, **omit** the P8c behavior-change commits from v0.18.0 rather than shipping dormant code whose live acceptance is deferred. | **Resolved** | §J2 summary + P8c "Completion" + §M now state the P8c commits are **omitted from the v0.18.0 release branch entirely** when O7 is unavailable (not shipped dormant/flagged-off); the work moves to a point release. |
| RR3-C2 | Keep P0's two small behavior changes — env-compare **side-label preservation** and the **Ramp Summary schema guard** — in isolated, characterized commits despite P0's mostly-diagnostic scope. | **Resolved** | P0 now lists both §J2 findings explicitly; each ships as its **own isolated commit with an offline characterization check**, and P0's "Protected" line carves them out instead of claiming zero behavior change. |
| RR3-C3 | Ensure the **release** cache-envelope `schema_version` already includes the P2 fingerprints so users rebuild once. | **Resolved** | §C.2 + P2 "Migration" now state the **released** `schema_version` is the single final value carrying **both** the P1 fields and the P2 `input_fingerprint`; P1 and P2 ship together with **no intermediate release cut**, so upgrading users rebuild exactly once. |

This plan is **ready for user approval**. Implementation has **not** begun and is **not** authorized by the
review — it awaits the user's go-ahead, phase by phase from P0.

---

## A0c. CR-001 — mid-implementation amendment (ACCEPTED WITH REQUIRED MODIFICATIONS, 2026-06-23)

After P9 committed (`decced4`), the user directed a scope change (CR-001): **opt into every *offline-doable*
deferral** for v0.18.0 and **add a final phase** that designs the work-PC validation handoff + the **v0.18.1**
close-out. Codex reviewed and returned **ACCEPTED WITH REQUIRED MODIFICATIONS**. The amendment is incorporated
throughout §H/§I/§J/§J2/§K/§K2/§L/§M/§N. Full proposal + review:
`change-requests/CR-001-claude-proposal.md` + `change-requests/CR-001-codex-review.md`.

**Two-tier release model (RM02):**
- **v0.18.0 = offline-validated *validation candidate*** — fully offline-provable before every commit/release;
  MAY carry live-path code (P8c) intended for work-PC validation. "Enterprise-ready" here means
  **offline-validated and packaged for work-PC/enterprise validation**, NOT operational sign-off.
- **v0.18.1 = the field-validated close-out** — after the user runs v0.18.0 on the work PC and returns
  evidence (per the P13 kit), v0.18.1 applies real-log fixes and closes the refactor.

**Required-modification dispositions (RM01–RM08), each applied:**

| RM | Requirement | Applied as |
|---|---|---|
| RM01 | Don't reopen committed P5; add a new post-P9 phase for the comparator remainder | committed P5 (family-1, `c0cfa39`) stays historical/complete; new **P5b** added (§H/§I). Only *pending* phases (P7b/P8c) reclassified. |
| RM02 | v0.18.0 = offline-validated candidate, not field-validated GA | two-tier model above; §K (0.18.0 offline DoD) + new **§K2** (0.18.1 acceptance DoD) |
| RM03 | P8c = revertible RC behavior, **no default runtime flag**, fixture-first | P8c §I: blocking for v0.18.0 *code*; acceptance not claimed until v0.18.1; each change its own revertible commit; fake-site fixture **extended BEFORE** any behavior change; no live TSMIS/credential/profile access |
| RM04 | Narrow P12 PDF/parser claims to offline-provable | §J2 + P12 §I: oracle *harness* + capture path in v0.18.0; real-PDF acceptance → v0.18.1 unless a committed fixture truly reproduces the exact failure |
| RM05 | P13 evidence collection privacy/credential-safe | P13 §I + §M: never collect auth/profiles/cookies/DPAPI/credentials; no private outputs/PDFs by default; explicit user-placed evidence folder + a manifest listing every file; manual fallback; exercised by offline tests without launching the GUI |
| RM06 | Keep hard-deferrals deferred unless user separately opts in | §N: DPAPI/O2, runtime-signature/cert, `compare_core` min-cost, and the D16-dropped set all stay excluded pending explicit separate approval |
| RM07 | Correct stale counts | the suite is **65 `build/check_*.py`** (+3 `.js`) verified 2026-06-23; P5b cites the **five** `check_compare_*_tsn.py` canaries; Route-1/COM acceptance is external unless a local harness is committed |
| RM08 | Keep P7b/P9b decomposition bounded | §I + §N: no framework/ES-modules (unless separately justified+proven in pywebview/file/frozen), no one-class-per-action sprawl, no behavior-with-movement; API names/event order/`#mock`/script-ordering/Lesson-10 protected; P9b extends `check_ui_boot.js`/`check_ui_contract.py` + `#mock` smoke; P7b adds an API-surface identity check for moved methods |

**Amended phase set (post-committed-P9, in order): P5b → P7b → P7c → P8c → P9b → P10(expanded) → P12 → P13 →
P11(last).** P7b + P8c reclassified conditional → blocking; P5b/P9b/P12/P13 new; committed P0–P9 untouched
(RM01). **No further user approval is required for this amended plan provided the hard-deferral items stay
deferred** (Codex §"Whether Claude may resume"); DPAPI / runtime-signature / `min-cost-pairs` each need an
**explicit separate** user decision beyond CR-001.

---

## A0d. CR-002 — mid-implementation amendment (ACCEPTED WITH REQUIRED MODIFICATIONS, 2026-06-25)

After **P12 committed (`d15216d`)**, with no phase `in_progress`, the user directed a forward-port: while the
refactor sat on its **v0.17.1** branch point (`d2ee353`), `main` shipped v0.17.2–v0.17.8, so **`origin/main` is
now v0.17.8 (`068b697`)**, ~10 commits ahead. CR-002 brings that already-shipped behavior **into the refactored
v0.18.0 architecture** so v0.18.0 supersedes v0.17.8 cleanly. Codex reviewed and returned **ACCEPTED WITH
REQUIRED MODIFICATIONS (CR002-RM1–RM7)**. Full proposal + review: `change-requests/CR-002-claude-proposal.md` +
`change-requests/CR-002-codex-review.md`.

**Accepted source of truth + method (CR002-RM7):**
- **Source:** `origin/main` `068b697` (v0.17.8), guided by `origin/main:docs/refactor-handoff-v0.17.1-to-v0.17.5.md`
  (the user's file-by-file forward-port map + the locked canaries). **Local `main` (v0.17.7) is stale — not used.**
- **Method: a deliberate FORWARD-PORT into the refactored sources of truth — NOT a `git merge`/rebase of
  `origin/main`** (a merge would reintroduce pre-refactor structure + endanger committed v0.18.0 work).
- **The divergence is ONE feature:** the **Intersection Detail (PDF)** report family (an exact `highway_log_pdf`
  parallel) + its **vs-TSN comparison evolution** (localized to `compare_intersection_detail_tsn` + a
  `summary_layout` fold). `version.py` stays the refactor's target **0.18.0** (supersedes 0.17.8 — CR002-RM6).

**Required-modification dispositions (CR002-RM1–RM7), each applied:**

| RM | Requirement | Applied as |
|---|---|---|
| CR002-RM1 | Port into the refactored SoT, not the pre-refactor registry | P14 adds report metadata to **`report_catalog.py`** first (`reports.py` stays the **derived** API); matrix PDF-consolidator branch + catalog parity (`check_report_catalog.py`) are the targets — **not** old `reports.py` rows / `_CONSOLIDATOR_BY_SUBDIR` as primary. |
| CR002-RM2 | Frontend mock → `mock.js`, not `app.js` | P14 UI fixtures target **`scripts/ui/mock.js`** (owns `makeMockApi`/boot) + `contract.js`/bridge payload checks; **never** reintroduce `makeMockApi` into `app.js`; `check_ui_boot.js` stays green. |
| CR002-RM3 | Do NOT port dormant `compare_core.context_fill` | **`context_fill` excluded from CR-002.** v0.17.8 final compares the formerly-greyed date columns and uses the EXISTING `extra_sheet_writer` for Report View. `compare_core` stays **protected/unmodified** (no opt-in added). Porting it would need a **separate explicit decision**. |
| CR002-RM4 | Stable IDs + manifests = explicit P14 compat gate | `intersection_detail_pdf` is **append-only**; the existing **7 export keys keep positions 0–6**; `batch_manifest.py` + `check_stable_ids.py` prove v1 integer-index manifests (pre-Int-PDF shape) AND the new key both resolve; `_V017_EXPORT_ORDER` preserves 0–6 + appends the new key only. |
| CR002-RM5 | Keep P14/P15 boundaries distinct; P13 after both | P14 = report-family plumbing; P15 = vs-TSN comparison evolution; **P13 moves after P14+P15** (work-PC verify must cover the final **8-report** shape, not the 7-report pre-port shape). |
| CR002-RM6 | Packaging/build verify for the refactored branch | P14 updates `app.spec` hidden imports + **proves** source-zip/console derivation from `EXPORT_REPORTS` (not literal old menu edits); **does NOT port `version.py`**; no extra runtime artifacts beyond the existing `.gitkeep` policy. |
| CR002-RM7 | `origin/main` + handoff as inputs; no merge/rebase | recorded above; file-by-file port into the refactored architecture. |

**Amended phase set (post-committed-P12, in order): P14 → P15 → P13 → P11(last).** P14/P15 are new blocking
forward-port phases; **committed P0–P12 are untouched/additive (RM01-style)** — the port registers a NEW report
family on the existing contracts (P3 stable IDs, P4 catalog, P1 outcome, P2 store, P7c matrix), it does not
reopen them. **`compare_core` remains protected** (CR002-RM3 — no `context_fill`). **No further user approval is
required** provided dormant `context_fill` is omitted (Codex §"Whether Claude may resume").

---

## A. Disposition of every Codex review ID

Disposition ∈ Accepted · Accepted-w/-mod · Rejected (repo-backed) · Deferred (reason→destination) ·
Unresolved-blocker.

### A.1 Blocking defects
| ID | Disposition | Resolution (repo-backed) | Phase |
|---|---|---|---|
| R1-B01 | Accepted | Replace the single 6-value enum with **two orthogonal fields** — `completion ∈ {complete,partial,no_data,cancelled,failed}` and `artifact ∈ {promoted,new_unpromoted,previous_preserved,none}` — plus a normative producer mapping for every `RunResult`/`ConsolidateResult` (§C.1). Producers set machine-readable fields; **never parse `summary_lines`**. | P1 |
| R1-B02 | Accepted | Define an **artifact-set transaction protocol** with a journal + startup recovery sweep, deterministic backup name, validate-before-commit, and a values-canonical / formulas-best-effort multi-file policy. Atomicity lives in an `artifact_store` **wrapper** so `compare_core` stays untouched and temp names are rewritten out of results (§C.2). P2 depends on P1. | P2 |
| R1-B03 | Accepted | Cyclic chain confirmed (`edge_device`→`navigate_with_auth`+`launch_browser`). Replaced with the **verified acyclic DAG** (§E): leaves → `browser_channels` ∥ `auth_nav` → `report_nav`/`edge_device` → `session`. Extraction order follows it. | P8a/P8b |
| R1-B04 | Accepted | Add a `--self-test` flag to the **real** `gui_main` entry (runs a non-GUI self-test path before webview) so the **exact** windowed exe is exercised; gate both windowed variants after copy/prune; give the source ZIP its own console smoke (§C.3). | PA |
| R1-B05 | Accepted | Narrow `report_catalog` to **report/capability metadata + import refs only**. Keep packaging completeness as a **separate runtime-module reachability** check; keep fake-site fixtures **independent** (§D.4, §C.4). | P4/PA |
| R1-B06 | Accepted | Define a **4-tier ID taxonomy** (report-family / export-op / consolidation-op / comparison-op keys) with uniqueness rules + HL examples; `batch_job.json` persists the **export-op key** (§C.5). | P3 |
| R1-B07 | Accepted | P1 now includes the exact `run_ended` payload additions, `app.js`/mock handler changes, default-handling of absent fields, and bridge + mock tests (§C.1, P1). | P1 |

### A.2 Required changes
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-R01 | Accepted | Route-status→completion table (saved+empty=complete; empty-only=no_data; user_skipped/failed=partial; `exists` in fresh stage=reject) (§C.1). CT-1 covers each row. | P1 |
| R1-R02 | Accepted | Add producer-owned partial status to `consolidate_xlsx_base` + PDF/TSN consolidators; update console/GUI/auto-consolidate/matrix/TSN-library consumers together (§C.1). | P1 |
| R1-R03 | Accepted | Define the fingerprint (sorted relative names, type filter, sizes, hi-res mtimes; exclude temp/lock; unreadable⇒stale); sidecar written **after** a successful commit; missing/corrupt⇒stale (§C.2). | P2 |
| R1-R04 | Accepted | Explicit v1/v2 manifest loaders; v1 indices map through a **frozen `_V017_EXPORT_ORDER`**; **reject (not drop)** unknown/dup/disabled/removed keys; no env marked done on empty resolution (§C.5). | P3 |
| R1-R05 | Accepted | **Removed** the `paths.py` `init_browser_path()` rewrite (contradicts D7; import-time mutation is intentional). | — (dropped) |
| R1-R06 | Accepted | Define the **single owner** of task state; split P7 into **P7a** (state-machine/owner + dispatch table + enum SSOT + exactly-once lifecycle) and **P7b** (mechanical endpoint grouping). Mixins only for endpoint grouping after the boundary exists. | P7a/P7b |
| R1-R07 | Accepted | **O3 recorded non-reproducible** (verified: env/active-check workers use `set_thread_site`; `get_site` prefers the pin). No global lock. "Snapshot site once per run" dropped unless a focused behavior-neutral need appears. | P8 (narrowed) |
| R1-R08 | Accepted | P8 split into **P8a** (pure leaves), **P8b** (mechanical channel/auth/edge movement behind shim, behavior-neutral), **P8c** (behavior changes needing work-PC acceptance). | P8a/b/c |
| R1-R09 | Accepted | Specify JS loading: **classic `<script>` ordering** (no ES modules; pywebview/file/frozen parity), `mock.js` after `app.js`, only when `#mock`. Add a deterministic boot check for production + `#mock` (no missing globals/404s). Renderer merge **not** in P9. | P9 |
| R1-R10 | Accepted | **Clean build-env policy**: `build.ps1` recreates `build/.venv` (or fails on unexpected packages); generate Windows/3.11 hashes via `pip-compile --generate-hashes`; document platform markers. | P10 |
| R1-R11 | Accepted | Replace all "byte-identical" with **"semantically identical"**, gated by the existing method (openpyxl cell/formula/style/defined-name + count canaries + COM F9). XLSX are ZIPs; no raw byte comparator exists. | P2/P5/P10 |
| R1-R12 | Accepted-w/-mod | **`compare_core` stays untouched, period.** `make_notes_sheet` goes in a new helper module (not `compare_core`); the `run_compare`-returns-counts change is **dropped** from v0.18.0 (the matrix re-read is acceptable). Protected statement is now consistent. | P5/P10 |
| R1-R13 | Accepted | Classify each fixture: UI display metadata may be generated; **report order, stable IDs, site labels, comparison layouts, approved counts stay independent approved snapshots.** CT-13 compares **independently captured** backend snapshots to frontend expectations. | P4/P9 |
| R1-R14 | Accepted | CT-10 becomes per-worker **lifecycle** tests (success/cancel/expected-error/unexpected-error/duplicate-late), asserting gate release + queue advancement — not name membership. | P0/P7a |
| R1-R15 | Accepted | **One versioned cache envelope** `{schema_version, output_identity, input_fingerprint, counts…}` defined in P1, extended (fingerprint) in P2; **one** forward rebuild; old dicts read as stale, never deleted until a successful recompute. | P1/P2 |

### A.3 Recommended
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-A01 | Accepted | Objective perf harness (env, data shape, cold/warm, repeats, percentile, no-regression threshold) defined **before** any optimization; perf work is **optional** and dropped if no material gain. | P10 |
| R1-A02 | Accepted | **Remove** the bounded worker queue (no measured growth; risks deadlock on terminal delivery). | — (dropped) |
| R1-A03 | Accepted | **Defer** the runtime signature abstraction + crypto dep; keep only workflow signing **parity** in design until the cert/publisher policy is final. | P10/Deferred |
| R1-A04 | Accepted | DoD uses **named responsibility/ownership outcomes**, not a line threshold. `gui_worker.py` (already class-segmented) is **not** force-split. | §K |
| R1-A05 | Accepted | **Drop** the CI branch-filter optimization (avoid disturbing branch-protection required checks). | — (dropped) |

### A.4 Remove / narrow
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-N01 | Accepted | P5 narrowed to **one duplication family at a time**, keep thin compat shims (`tsn_load_*` delegate to the factory), **no line-deletion quota**, notes-sheet outside `compare_core`. P5 is **conditional/deferrable**. | P5 |
| R1-N02 | Accepted-w/-mod | P6 = **writer dedup + atomic auth write + ACL + support-bundle allowlist** (evidenced). **Drop** `_safe_join` and `full_snapshot()`; keep a settings schema-version **only** because P3's manifest needs one — settings get a version field **only if** a concrete migration exists, else omitted. | P6 |
| R1-N03 | Accepted | P9 default = **mock separation + payload parity only**; renderer merge + deeper modularization deferred unless O1 is resolved + a browser net exists. | P9 |
| R1-N04 | Accepted | **Disk-full induction removed** from work-PC verification; rename/write failures stay in **offline** fault-injection; work-PC limited to safe lock/Defender with disposable destinations + cleanup. | P2/§20 |

### A.5 Missing areas
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-M01 | Accepted | Update `4. consolidate (combine reports).bat` to include both Intersection consolidators; add a **menu↔registry parity check**. | P4 |
| R1-M02 | Accepted | Add a **source-ZIP console smoke** (import + menu→module dispatch + a consolidation selection) distinct from the EXE gates. | PA/P10 |
| R1-M03 | Deferred (reason→roadmap/P11) | **Destination ownership marker deferred** with rationale: keep the current scoped-delete + preview protections; `_safe_join` removed (R1-N02) so it doesn't pretend to solve ownership. Recorded as future work. | P11 |
| R1-M04 | Accepted | Add a **per-item updater disposition table** (§J) with symbols + checks; completion criteria reference it. | P10 |
| R1-M05 | Accepted | Every open audit item gets an **individual disposition + phase or deferral rationale** (**§J2**); "where cheap" removed. | §J2 |

### A.6 Sequencing
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-S01 | Accepted | **P2 depends on P1** (artifact disposition uses the P1 promotion-result). | graph §H |
| R1-S02 | Accepted | **PA (exact-artifact gate) precedes** P4/P7/P8/P9 broad extraction. | graph §H |
| R1-S03 | Accepted | One cache migration via the R1-R15 envelope; one rebuild after P1+P2 semantics land. | P1/P2 |
| R1-S04 | Accepted | Keep thin old-name `tsn_load_*` modules (the `"module:function"` builder strings + spec entries + imports keep working); no module removed without a shim. | P5 |

### A.7 Missing tests
| ID | Disposition | Resolution | Phase |
|---|---|---|---|
| R1-T01 | Accepted | Seed every intermediate on-disk state (as if the process died) and run **startup recovery**; assert canonical live + backup retention + safe cleanup. | P2/CT-4,CT-5 |
| R1-T02 | Accepted | Inject failure on the 1st and 2nd workbook save + during promotion; assert the values-canonical/formulas-best-effort policy and **no temp names** in results. | P2/CT-8b |
| R1-T03 | Accepted | Backend payload + mock scenarios for complete/valid-empty/user-skipped/failed/cancel/consolidation-partial/consolidation-error-with-stale-prior/promotion-failure. | P1/CT-3 |
| R1-T04 | Accepted | Fake-site fixture with exact/prefix/suffix/disabled label variants **before** changing the selector; assert exact match + clear error on 0/multiple. | P8c/CT |
| R1-T05 | Accepted | Independent checks: stable-ID uniqueness, display/order snapshot, `.bat` menu coverage, dynamic-import resolvability, runtime-module packaging completeness — not one generated object. | P3/P4/PA |
| R1-T06 | Accepted | Per-variant final-artifact acceptance (system-browser EXE, bundled-browser EXE, source ZIP); the gate **fails (not skips)** when a required capability is absent. | PA/P10 |

### A.8 Architecture disagreements
| ID | Disposition | Resolution |
|---|---|---|
| R1-D01 | Accepted | Orthogonal completion/artifact fields (= R1-B01). |
| R1-D02 | Accepted | Packaging inventory separate from report catalog (= R1-B05). |
| R1-D03 | Accepted | State ownership defined first; mixins only for endpoint grouping (= R1-R06). |
| R1-D04 | Accepted | Engine graph follows verified call direction (= R1-B03/§E). |
| R1-D05 | Accepted | Independent oracles stay independent (= R1-R13). |

### A.9 Phase scope
| ID | Disposition | Resolution |
|---|---|---|
| R1-P01 | Accepted | Phases classified **release-blocking / conditional / deferrable** (§K). P7→P7a/P7b, P8→P8a/P8b/P8c, P10→PA(early)+P10(later). DoD = release-blocking set only; work-PC acceptance is a separate gate, never silently "owed." |
| R1-P02 | Accepted | Rollback rules are now **dependency-aware** (§L); each persisted schema change states its post-rollback backward-read behavior. |

**Rejections:** none. Every Codex finding was repository-validated. (The only "no-op" items are those Codex
itself asked to **drop**: R1-R05 paths-init, R1-A02 bounded queue, R1-A05 CI trigger, the
`run_compare`-counts change.)

---

## B. Verified findings (carried forward, re-confirmed this round)

F1 (`gui_worker.py:423–429` promotes on no-exception, ignores `RunResult.failed`), F2 (`:194–219`
non-transactional swap), F3 (`matrix.py:692/795` ignores `ConsolidateResult`), **F4** (`matrix.py:874` +
`day_matrix.py:355` hardcode `read_counts(has_route=True)` vs `has_route=False` aggregate adapters → 0
diffs shown), F5 (`matrix.py:751–766` newest-mtime freshness), F6 (`APP_MODULES` omits `matrix`/
`day_matrix`/`report_library`), F7 (manifest integer indices), F8 (`_handle` no default; implicit
protocol), F9 (direct-to-final workbook writes), F10 (docs copied after the DLP scan; `build.ps1:111–112`),
F11 (`import reports` eagerly loads openpyxl+pdfplumber+PIL+playwright — runtime-probed), F13 (mock 2nd
backend), F14 (responsibility clusters). New this round: the engine DAG (§E) and O3-non-reproducible are
both repository-confirmed.

---

## C. Resolved design contracts (answers to Codex's §10 questions)

### C.1 Outcome contract (Q1–Q3) — two orthogonal axes, producer-owned
`completion ∈ {complete, partial, no_data, cancelled, failed}` · `artifact ∈ {promoted,
new_unpromoted, previous_preserved, none}`. **Never inferred from `summary_lines`.**

**Export `RunResult` → completion** (Q1):
| Condition | completion | note |
|---|---|---|
| `failed > 0` | partial | a route that *should* have data errored |
| `user_skipped > 0` (no failed) | partial | user chose to skip → incomplete coverage |
| `saved > 0`, `empty ≥ 0`, no failed/skipped/cancel | **complete** | per-route `empty` = valid no-data; its file legitimately absent (a complete refresh may correctly drop a formerly-present route file) |
| `saved = 0`, `empty > 0`, no failed/skipped | no_data | site returned nothing for all routes |
| cancelled mid-run | cancelled | |
| exception before output | failed | |
| any `exists` in a **fresh** staging dir | reject + log | staging residue anomaly (CT) |

**artifact / store promotion gating:** `complete` → promote (`promoted`); `partial`/`no_data` →
keep live, staging discarded (`previous_preserved`); `cancelled`/`failed` → `previous_preserved`.
**Downstream:** batch marks an env done **only if every selected report = complete**; matrix "ok" /
auto-compare requires export `complete`; cache records require consolidation `complete|partial`; green
UI requires `complete` (partial→amber "kept last-good", no_data→neutral, failed→red).

**Consolidate/Compare `ConsolidateResult` → completion** (Q3, R1-R02): producers
(`consolidate_xlsx_base`, the PDF/TSN consolidators) set `completion` + structured `skipped`/
`failed_inputs` counts (they already know this — today it only reaches `summary_lines`). Consumers
(console, GUI auto-consolidate, **matrix**, TSN library) honor it: `failed`/`no_data` ⇒ **do not
compare/cache**, keep any stale prior workbook, surface "not refreshed"; `partial` ⇒ compare but flag.

**Frontend (Q… / R1-B07/T03):** `run_ended` gains additive `completion`+`artifact` fields (absent ⇒
default `complete` for intra-version safety; the shipped mock sets them). `app.js renderCompletion`
branches on `completion`; matrix chaining keys on `complete`. Event **order preserved**.

### C.2 Transaction protocol (Q4–Q5, R1-B02/R1-R03/R1-T01/T02)
**Store promotion** = journaled, recoverable:
1. **Validate** staging before commit (`completion=complete` + expected files present).
2. Write the journal at **`<dest>/.promote/<token>.json`** — in the destination **parent**, never inside
   `live`/`<store>` (which is itself renamed) — naming `{target, backup, staging, token}`.
3. `rename(live → live.bak-<token>)` → `rename(staging → live)` → delete journal → drop `live.bak-<token>`.
4. **Startup recovery** (extends `updater.cleanup_leftovers`): on `.promote.journal`/`*.bak-*`/`*.staging`
   residue — if `live` absent but `bak` present → restore; if `live` present + stale residue → clean.
   This closes the "death between the two renames" window (next launch restores from `bak`).
**Atomic workbook write** = an `artifact_store.commit_workbook(final, produce_fn)` wrapper: `produce_fn`
writes to `final.tmp-<token>` via the **existing** writer; validate (openable + expected sheet) →
`os.replace(tmp, final)`; the wrapper **rewrites** `output_path`/summary so no temp name leaks. **This
keeps `compare_core` untouched** (the adapter is handed a tmp path; the wrapper finalizes). **Multi-file
policy (Q5):** the **values** workbook is the single transactional artifact (commit first); the
**formulas** sibling is independent best-effort (commit second; failure leaves values committed + logs)
— matching today's "values stays canonical." For a `mode="both"` comparator the wrapper passes **temp paths
for both** workbooks (so `compare_core` writes only to the temp paths it is given), commits the values
workbook via `os.replace` **first**, then the formulas sibling best-effort, and **rewrites both returned
`output_path`s** — `compare_core` is never modified.
**Fingerprint (R1-R03):** sorted `(relative_name, size, mtime_ns)` over the store's data files
(exclude `~$`/`.tmp`/`.staging`/dirs; unreadable ⇒ stale); content hash only if a same-metadata
replacement case is later proven. Sidecar written **after** a successful commit; missing/corrupt/
mismatch ⇒ stale. Day-level: a **missing** consolidation ⇒ not-fresh (fixes the `all(existing)` gap).

### C.3 Exact-artifact gate (Q11–Q12, R1-B04/T06)
Add `--self-test` to the **real** `gui_main` entry: before any webview creation it runs the same import/
asset/registry self-test `full_smoke` performs, then exits non-zero on failure. `build.ps1 -SelfTest`
then runs **`TSMIS Exporter.exe --self-test`** (the actual shipped exe), for **both** windowed variants,
**after** copy + prune. The **source ZIP** gets a separate clean-extract console smoke (import +
menu→module dispatch + a consolidation selection). The gate **fails, never skips**, when a required
capability is missing (a skipped hidden-webview probe is allowed only for the GUI-launch sub-check, not
the import/registry sub-check).

### C.4 Catalog scope (Q13, R1-B05/D02/D05/R13)
`report_catalog` owns **report/capability metadata + dynamic-import references only**. **Separate**
contracts: (a) a runtime-module **reachability** check (does `import <module>` resolve for every
dynamically-referenced report module?) for packaging; (b) **independent** golden fake-site fixtures and
approved snapshots (report order, stable IDs, site labels, comparison layouts, canary counts). Generated
from the catalog: UI display metadata + the mock's report list. Independent: every test oracle.

### C.5 Stable-ID taxonomy + manifest migration (Q6–Q7, R1-B06/R04/S04)
Four ID tiers (string keys, immutable):
- **report-family key** — e.g. `ramp_summary`, `ramp_detail`, `highway_sequence`, `highway_log`,
  `highway_log_pdf`, `intersection_summary`, `intersection_detail`.
- **export-op key** — one per `EXPORT_REPORTS` row (7); equals the family key here. **Persisted in
  `batch_job.json`**; travels through `start_export`/`retry`/`start_batch_export`.
- **consolidation-op key** — one per `CONSOLIDATE_REPORTS` row (8); HL splits:
  `cons:highway_log_excel`, `cons:highway_log_pdf`, `cons:tsn_highway_log`. Travels through the
  consolidate bridge methods.
- **comparison-op key** — one per `COMPARE_REPORTS` row (15); composite of (family, flavor, group),
  e.g. `cmp:ramp_summary:env`, `cmp:highway_log:tsn`, `cmp:highway_log:pdf_vs_tsn`,
  `cmp:highway_log:pdf_vs_excel`. Travels through the compare bridge methods.
- **matrix row key** — the existing `row_key`; **not renamed** (caches depend on it); mapped to the
  family key additively.
**Manifest (R1-R04):** explicit `v1` (int indices) and `v2` (export-op keys) loaders. `v1` indices map
through a **frozen `_V017_EXPORT_ORDER`** constant (never a mutable future view) → keys. Unknown/
duplicate/disabled/removed keys are **rejected with a logged error + user banner** (not silently
dropped); if no valid report resolves, the env is **not** marked done. Migration rewrites to `v2` on the
next save.

### C.6 Other answers
- **Q8** engine DAG → §E. **Q9** state owner → §F (a single `TaskCoordinator` owns `_task`/queue/
  cancellation/exactly-once). **Q10** mock loading → classic `<script>` after `app.js`, `#mock`-gated
  (R1-R09); **`mock.js` owns the mock boot** — it defines `makeMockApi` then calls `boot(makeMockApi())`, so
  `app.js` auto-boots only in production (no `#mock`) and the current immediate boot call moves into
  `mock.js` (RR2-C3). **Q14** paths init → **not changed** (R1-R05). **Q15** updater → §J. **Q16** O1/O2/O7 →
  the conditional phases (§K) are dropped from the DoD if their gate stays closed.

---

## D. Final target architecture

Same runtime shape; the additions are **explicit contracts**, not a framework:
1. **Orthogonal outcome contract** (`completion`+`artifact`), producer-owned (§C.1).
2. **Transactional artifact lifecycle** (journaled promotion + atomic-write wrapper + fingerprint
   freshness), one versioned cache envelope (§C.2).
3. **4-tier stable IDs**; index = display order only (§C.5).
4. **`report_catalog`** = report metadata SoT; packaging reachability + test oracles stay **separate** (§C.4).
5. **Declared bridge enums** (`contract.py`/`contract.js`) with logging defaults on both dispatch ends.
6. **A single task-state owner** (`TaskCoordinator`); `GuiApi` becomes a thin façade delegating to it +
   feature endpoints (§F). `common.py` → the acyclic engine modules behind a shim (§E). `compare_core`
   **untouched**.

---

## E. Final directory / module structure + verified engine DAG

```
scripts/ (flat — PyInstaller + .bat bare-name imports require it)
  outcome.py          completion+artifact fields + RunResult/ConsolidateResult predicates (P1)
  artifact_store.py   journaled promotion + commit_workbook wrapper + fingerprint + recovery (P2)
  cache_envelope.py   versioned matrix/day cache {schema_version, output_identity, fingerprint,…} (P1/P2)
  report_catalog.py   report/capability metadata SoT (P4)  — NOT packaging, NOT test oracle
  contract.py / ui/contract.js   bridge enums (task/env_access/event-kind) (P7a/P9)
  task_coordinator.py owns _task, queue, current job, cancellation, exactly-once transitions (P7a)
  # --- engine, extracted along the VERIFIED acyclic DAG (bottom→top): ---
  errors.py timeouts.py routes.py site.py            L0 leaves (P8a)
  browser_channels.py        L1 (launch_browser, channel resolve/probe) — independent of auth
  auth_nav.py                L2 (navigate_with_auth, is_logged_in, require_signed_in/site_params,
                                  auth_state, dump_auth_failure, auth-file lifecycle) — given a page
  report_nav.py              L2′ (select_report, preflight, report_error_text, wait_with_skip_option)
  edge_device.py             L3 (launch_edge_login_context, capture_*, open_edge_device_context,
                                  try_device_sso_login, storage_state_is_portable) → uses L1+L2
  session.py                 L4 (new_authed_browser) → orchestrates L1+L2+L3
  common.py                  SHIM re-exporting all of the above (preserve the 14-module import surface)
  compare_tsn_common.py      run_files_compare driver + normalize/notes/header helpers (P5)  — NOT compare_core
  ui/mock.js                 extracted #mock (classic <script>, #mock-gated) (P9)
  tsn_load_*.py              thin shims delegating to tsn_library.build_normalized (P5; preserve names)
```
Acyclicity is verified by the call graph (`open_edge_device_context:1521`/`storage_state_is_portable:1637`
→ `navigate_with_auth`; `new_authed_browser:1586`/`:1634` → `launch_browser`): `browser_channels` and
`auth_nav` are independent siblings above the leaves; `edge_device` sits above **both**; `session` above
`edge_device`. `compare_core.py`, `gui_worker.py` (already class-segmented), and the parsers stay in place.

---

## F. Dependency direction & ownership
Downward only; one owner per concept. `report_catalog` owns report metadata; `outcome` owns the terminal
vocabulary; `artifact_store` owns promotion+atomic-write+fingerprint; `cache_envelope` owns cache format;
`contract.py` owns bridge enums; `task_coordinator` owns task state/queue/cancellation/exactly-once;
`site.py` owns environment selection (behavior unchanged — no lock, R1-R07). No upward imports; the
`common` shim must not pull a driver. Packaging reachability and test oracles are **separate** from the
catalog (§C.4). `compare_core` is a sink (imported, never modified).

---

## G. Compatibility & persisted-data migration (R1-P02-aware)
| Artifact | Strategy | Post-rollback read |
|---|---|---|
| `batch_job.json` | v1↔v2 loaders; v1→keys via frozen `_V017_EXPORT_ORDER`; reject invalid; rewrite on next save (§C.5) | A v2 manifest written post-P3 is **not** readable by pre-P3 code → **rollback of P3 requires reverting dependents** and any v2 manifest (documented; v1 still accepted forward). |
| Matrix/day caches | one `cache_envelope` (P1) + fingerprint (P2); **one** rebuild; old dicts read as stale, never deleted until a successful recompute | Pre-P1 code ignores the envelope and rebuilds from scratch (safe). |
| `config.json` | writer dedup + atomic; **schema version only if a real migration exists** (R1-N02); unknown keys round-trip; corrupt moved aside | Backward-readable (additive). |
| `tsmis_auth.json` | atomic write + ACL; **DPAPI gated on O2** (would break portability) | Plaintext stays readable. |
| Output/store layout, filenames, `tsn_library`, `tsn_load_*` names | **no renames**; new keys are additive identifiers; thin shims keep `"module:function"` builder strings + spec entries working (R1-S04) | Unchanged. |

**Golden rule:** every phase leaves prior persisted data readable; format changes are versioned and
migrate forward; rollback rules are dependency-aware (§L).

---

## H. Final phase count & task graph

> **CR-001 amendment (2026-06-23):** the original 16 headings (graph below) are joined by **four new post-P9
> phases — P5b, P9b, P12, P13** — and **P7b + P8c are reclassified conditional → blocking**. Committed P0–P9
> are untouched (RM01). The amended order after committed P9 is **P5b → P7b → P7c → P8c → P9b → P10(expanded) →
> P12 → P13 → P11(last)**; deps are in the per-phase entries (§I). The original graph is retained for history.
>
> **CR-002 amendment (2026-06-25, ACCEPTED WITH REQUIRED MODIFICATIONS — §A0d):** two new blocking
> **forward-port** phases join the set after committed P12 — **P14** (Intersection Detail (PDF) report family)
> and **P15** (the Int-Detail vs-TSN comparison evolution) — and **P13 moves after them** (it must verify the
> final 8-report shape — CR002-RM5). New order after committed P12: **P14 → P15 → P13 → P11(last)**. Committed
> P0–P12 untouched/additive; `compare_core` stays protected (no `context_fill` — CR002-RM3); a deliberate
> forward-port from `origin/main` `068b697`, **not a merge** (CR002-RM7).

**16 original phase headings = 13 release-blocking + 3 conditional** (stable IDs retained; P7/P8/P10 split per
R1-P01/R1-S02). P11 depends only on the **release-blocking** phases:

```
P0 ──┬─► PA ──┬─► P4 ──┬─► P5            P0  safety net + diagnostics + doc-drift + dispatch defaults
     │        │        ├─► P9            PA  exact-artifact packaging gate (EARLY; precedes broad split)
     │        ├─► P7a ─► P7b             P1  outcome contract + F1/F3/F4 + frontend payload
     │        ├─► P8a ─► P8b ─► P8c      P2  transactional artifact lifecycle (F2/F9/F5)  [needs P1]
     │        └─► P10                    P3  stable-ID taxonomy + manifest v1/v2
     ├─► P1 ──► P2                       P4  report_catalog (narrowed) + .bat fix + parity  [needs P3, PA]
     ├─► P1 ──► P7a                      P5  report-family DRY (one family at a time)        [conditional]
     ├─► P3 ──► P4                       P6  persistence hardening (narrowed)
     └─► P6                              P7a GUI state owner + protocol + lifecycle + enums  [needs P1, PA]
release-blocking ─► P11                  P7b GUI mechanical endpoint extraction              [conditional]
                                         P8a engine leaf extraction (shim)                   [needs PA]
                                         P8b engine mechanical movement (DAG, shim)
                                         P8c engine BEHAVIOR changes                          [conditional, O7]
                                         P9  frontend mock separation (deeper split → O1)
                                         P10 packaging/deps/updater hardening                 [needs PA, P4]
                                         P11 docs + audit reconciliation
```
**Classification — original (R1-P01):** Release-blocking: P0, PA, P1, P2, P3, P4, P6, P7a, P8a, P8b, P9(mock),
P10, P11. Conditional/deferrable: P5(comparator), P7b, P8c, P9-deep-split, DPAPI(P6), perf(P10).

**Classification — amended (CR-001 + CR-002):** **v0.18.0 release-blocking (offline-provable):** the originals **plus**
**P5b, P7b, P7c, P8c(code), P9b, P12**, the **expanded P10** (the flipped updater items + optional perf), and
**P14 + P15** (the CR-002 forward-port of the v0.17.2–v0.17.8 Intersection Detail (PDF) feature + its vs-TSN
comparison evolution into the refactored architecture — §A0d).
**Still excluded (hard-deferred; need an explicit separate user decision — RM06):** DPAPI/O2,
runtime-signature/cert, `compare_core` `min-cost-pairs`, and the D16-dropped set. **v0.18.1 (a separate
acceptance gate, NOT in the v0.18.0 DoD):** all work-PC acceptance + the evidence-driven PDF/parser fixes
(§K2). The app is runnable + the full offline suite green at every v0.18.0 boundary.

---

## I. Phase-by-phase implementation

Each phase: Objective · Findings · Affected · Changes · Protected contracts · Prereqs · Tests/measure ·
Migration · Risks · Rollback · Completion.

### P0 — Safety net + diagnostics + doc-drift + dispatch defaults  [blocking]
- **Objective:** additive guards + zero-risk fixes that de-risk everything after.
- **Findings:** F8 (defaults), R1-R14 (lifecycle tests), doc-drift (gui-bridge §8 wrong, gui_worker Tkinter docstring, login.py "Phase 4", stale line numbers, build-release CI list); plus the two small **characterized** behavior fixes §J2 assigns here — `env-compare-side-label-cap-truncates-distinguisher` and `ramp-summary-combined-sheet-hardcoded-coordinates` (RR3-C2).
- **Affected:** `gui_api._handle` (+`else` log), `app.js dispatch` (+`default` warn); new `build/check_worker_lifecycle.py` (CT-10, per-worker success/cancel/error/duplicate-late), `build/check_import_direction.py`; **separately** `compare_env` side-label cap (keep the date/(A)/(B) distinguisher) + the Ramp Summary combined-sheet schema-length guard, **each its own commit + offline check**; doc text otherwise.
- **Changes:** two one-line defaults + new diagnostic checks + doc corrections; **plus two isolated, characterized behavior fixes** (side-label preservation, Ramp Summary schema guard) in **separate** commits, not mixed with the diagnostics (RR3-C2).
- **Protected:** the diagnostics + doc fixes are behavior-neutral; JS names/event order unchanged. The **only** behavior deltas are the two isolated characterized commits (side-label preservation, Ramp Summary schema guard), each gated by its own offline characterization check (RR3-C2).
- **Prereqs:** none. **Tests:** CT-10 green; import-direction green; the side-label + Ramp Summary schema-guard characterization checks green; 44/44 green. **Measure:** record cold-start + matrix-snapshot baselines (env + repeats per R1-A01).
- **Migration:** none. **Risks:** trivial. **Rollback:** revert additive files.
- **Completion:** new checks blocking-green (incl. the two characterization checks); the side-label + schema-guard fixes each landed as isolated commits; docs match code; baselines recorded.

### PA — Exact-artifact packaging safety gate (EARLY)  [blocking; precedes broad extraction]
- **Objective:** prove the **exact shipped exe** boots/imports before any module/UI split (R1-S02/B04/T06/M02).
- **Findings:** F6 (APP_MODULES), F10 (docs after scan), R1-B04/M02/T05/T06.
- **Affected:** `gui_main.py` (`--self-test` flag, pre-webview); `build.ps1` (run `TSMIS Exporter.exe --self-test` for both windowed variants **after** copy+prune; add source-ZIP console smoke); new `build/check_app_modules.py` (runtime-reachability of dynamically-imported report modules — fixes the `matrix`/`day_matrix`/`report_library` omission); `app.spec` (add the three modules; UI `datas` extension filter).
- **Changes:** real-exe self-test path; corrected build ordering; reachability check; CI wiring (label/nightly for the frozen gate).
- **Protected:** cert-store TLS; swap order; the `excludes`/prune behavior proven by `-SelfTest` (never weaken); console-free core.
- **Prereqs:** P0. **Tests:** the frozen gate fails-not-skips on missing capability; reachability check; source-ZIP smoke; `check_no_misspelling`.
- **Migration:** none. **Risks:** medium (CI infra) — isolated. **Rollback:** revert workflow/spec; the `--self-test` flag is inert otherwise.
- **Completion:** the **exact** windowed exe (both variants) + source ZIP pass their gates in CI; reachability check blocking-green.

### P1 — Completion/outcome contract + F1/F3/F4 + frontend payload  [blocking]
- **Objective:** partial work can never read as complete; aggregate counts correct; UI reflects partial.
- **Findings:** F1, F3, F4, R1-B01/B07/D01/R01/R02/T03/R15; O4.
- **Affected:** new `outcome.py`, `cache_envelope.py`; producers `consolidate_xlsx_base` + PDF/TSN consolidators (set `completion`+counts); consumers `gui_worker._run_specs`/`BatchWorker.run`/`MatrixBatchExportWorker.run`, `gui_api._on_matrix_export_done`, `matrix._consolidate_store_folder`/`consolidate_and_compare_tsn`/`build_comparison`, `day_matrix`; `read_counts` (layout from the adapter/workbook, **not** hardcoded `True`) — fix matrix + day; **verify O4** (cross-env aggregate via `_row_defs:63`→`build_cell_comparison:631`); `gui_api` `run_ended` payload (+`completion`/`artifact`), `app.js renderCompletion` + mock.
- **Changes:** the orthogonal contract end-to-end; the count-layout fix; producer-owned partial status; the cache envelope (counts).
- **Protected:** `compare_core` untouched; **the Comparison-sheet column layout becomes a documented contract**; output filenames unchanged; canaries semantically identical.
- **Prereqs:** P0 (CT-1/CT-3/CT-14 written first, TDD). **Tests:** CT-1 (every route status), CT-2 (consolidator error+stale prior), CT-3 (aggregate Ramp/Intersection Summary readback + O4 + mock scenarios for all completion states), CT-14 (read_counts layout matrix); all matrix/compare checks; **work-PC:** a real refresh with an induced failed route keeps last-good + shows "partial."
- **Migration:** cache envelope version → one rebuild (old dicts read stale). **Risks:** medium (live export/matrix flow) — mitigated by TDD CT-* + rebuild.
- **Rollback:** the layout fix + outcome gating are isolated commits; reverting reinstates the defects (and the cache stays stale-safe). **Completion:** CT-1/2/3/14 green; `#mock` shows correct Summary counts + partial state; 44/44 green.

### P2 — Transactional artifact lifecycle  [blocking; depends P1]
- **Objective:** never leave zero copies; never truncate a prior artifact; freshness tracks input identity.
- **Findings:** F2, F5, F9, R1-B02/R03/T01/T02/S03/N04/R15.
- **Affected:** new `artifact_store.py` (journaled promote + startup recovery + `commit_workbook` wrapper + fingerprint); `gui_worker._swap_store_dir` → delegate; consolidator/compare **save sites** wrapped (compare_core via the wrapper, untouched); `matrix._consolidated_stale` + comparison-freshness + `day_matrix` day-level → fingerprint; `updater.cleanup_leftovers` → recovery sweep; `cache_envelope` gains `input_fingerprint`.
- **Changes:** one transactional pattern; atomic writes with path-rewrite; fingerprint freshness; one cache rebuild (shared envelope with P1).
- **Protected:** output bytes **semantically identical** (only the write mechanism + freshness key change); values-canonical/formulas-best-effort policy; `compare_core` untouched.
- **Prereqs:** **P1** (uses the promotion-result; R1-S01). **Tests:** CT-4 (seed each dead-process on-disk state → recovery restores live; R1-T01), CT-5 (locked/stale staging not promoted), CT-6 (deleted route ⇒ stale), CT-7 (missing day consolidation ⇒ not fresh), CT-8 (write interrupt preserves prior), CT-8b (multi-file commit failure on 1st/2nd save, no temp-name leak; R1-T02); canary semantic-identity; **work-PC:** safe Defender/lock with disposable destinations (no disk-full induction — R1-N04).
- **Migration:** fingerprint sidecar new/versioned; absent ⇒ stale. The **released** `cache_envelope.schema_version` is the single final value carrying **both** the P1 fields and the P2 `input_fingerprint`; P1 and P2 ship in the same release with **no intermediate version cut**, so upgrading users see exactly **one** post-upgrade rebuild (RR3-C3). **Risks:** medium (Windows fs edges) — mitigated by seeded-state CT.
- **Rollback:** `artifact_store` additive; callers revert to old swap; recovery sweep is idempotent. **Completion:** CT-4..8b green; canaries semantically identical; 44/44 green.

### P3 — Stable-ID taxonomy + manifest migration  [blocking]
- **Objective:** selection/resume no longer depends on list position; legacy manifests fail safe.
- **Findings:** F7, R1-B06/R04/T05/S04.
- **Affected:** `reports.py` (4-tier keys §C.5), `gui_api._pick_report` + all index call sites, `app.js dataset.idx→key` (+ mock), `batch_manifest.py` (v1/v2 loaders + `_V017_EXPORT_ORDER` frozen constant + reject-invalid + version bump), `gui_worker._specs` (key lookup; no env-done on empty resolution).
- **Changes:** keys as the contract; index = display order; manifest v2.
- **Protected:** legacy `batch_job.json` resumes correctly; matrix `row_key` not renamed; registry order stays append-only for any remaining index consumer until P4.
- **Prereqs:** P0; CT-9 first. **Tests:** CT-9 (v1 valid resumes; v1 invalid/removed → explicit reject, env **not** done; reordered registry → no mis-resume), stable-ID uniqueness check (R1-T05); `check_gui_bridge`/`check_b3_batch`/`check_matrix_bridge`; **work-PC:** resume a real paused v0.17 batch.
- **Migration:** v1→v2 on next save. **Risks:** medium-low. **Rollback:** v1 still accepted; reverting P3 after a v2 write requires reverting dependents + any v2 manifest (§L).
- **Completion:** CT-9 green; a v0.17 manifest resumes correctly; 44/44 green.

### P4 — Report metadata catalog (narrowed) + .bat fix + parity  [blocking; depends P3, PA]
- **Objective:** one report-metadata SoT; close the console-menu drift; independent parity checks.
- **Findings:** F6, R1-B05/M01/D02/D05/R13/T05.
- **Affected:** new `report_catalog.py` (report/capability metadata + import refs **only**); `reports.py` views derived; `tsn_library._REPORTS`/`matrix_rows`/`_CONSOLIDATOR_BY_SUBDIR` derived-or-asserted; `4. consolidate (combine reports).bat` (add both Intersection consolidators); mock report list generated; **independent** snapshots + fake-site fixtures retained.
- **Changes:** descriptor + derivation; `.bat` parity check; packaging reachability stays separate (PA).
- **Protected:** derived EXPORT/CONSOLIDATE/COMPARE order + keys equal today's (golden-assert before/after); fake-site oracle independence.
- **Prereqs:** P3 (keys), PA (reachability gate exists). **Tests:** descriptor-equivalence check; `.bat`↔registry menu parity (R1-M01); independent display/order snapshot (R1-T05/R13); `check_report_library`/`check_matrix`/`check_intersection_gate`.
- **Migration:** none (refactor). **Risks:** low-medium (broad but assertable). **Rollback:** keep literal lists beside the descriptor until the equivalence check is trusted.
- **Completion:** equivalence + `.bat` parity green; 44/44 green.

### P5 — Report-family DRY (one family at a time)  [conditional / deferrable]
- **Objective:** collapse the parallel skeletons without lock exposure.
- **Findings:** §2.3 (Claude), R1-N01/S04/R12.
- **Affected:** `tsn_library.build_normalized` factory with thin `tsn_load_*` **shims** kept (S04); then (separately) `compare_tsn_common.py` (`run_files_compare` + normalize/notes/header helpers) with the 5 `compare_*_tsn` reduced to schema+projector; notes-sheet helper lives **outside** `compare_core`.
- **Changes:** shared substrate, **one family per reviewable diff**, no line quota.
- **Protected:** the `_SCHEMA`/rows reaching `run_compare` unchanged → canaries **semantically identical**; `compare_core` untouched; builder strings/imports preserved via shims.
- **Prereqs:** P3/P4. **Tests:** the 6 vs-TSN golden checks + COM/Route-1 harness **after each family**; canary semantic-identity.
- **Migration:** none. **Risks:** low (no lock exposure); per-family rollback. **Rollback:** revert one family's collapse; shims keep old names working.
- **Completion:** all vs-TSN canaries semantically identical; offline suite green. **(Status: family-1 `tsn_load` factory COMMITTED as `c0cfa39`. Per CR-001/RM01 the committed P5 stays historical/complete; the comparator-driver remainder is NOT reopened here — it is the new blocking phase P5b below.)**

### P5b — TSN comparison-driver DRY (comparator remainder)  [blocking; CR-001/RM01; depends P4 + committed P5]
- **Objective:** collapse the 5 `compare_*_tsn` skeletons onto one shared driver, behavior-neutral — the deferrable remainder of P5, now opted in (CR-001). The committed P5 family-1 (`c0cfa39`) is **not** reopened.
- **Findings:** §2.3 (Claude), R1-N01/S04/R12; CR-001 §8.2.
- **Affected:** new `compare_tsn_common.py` (`run_files_compare` + normalize/notes/header helpers); the 5 `compare_*_tsn` reduced to schema+projector; the notes-sheet helper lives **outside** `compare_core` (untouched).
- **Protected:** the `_SCHEMA`/rows reaching `run_compare` unchanged → vs-TSN canaries **semantically identical**; `compare_core` byte-for-byte untouched; builder strings/imports preserved.
- **Prereqs:** committed P4 + P5(family-1). **Tests (RM07):** the **five** `check_compare_*_tsn.py` offline canaries (semantic-identity) re-run after the collapse; **Route-1/COM-recalc acceptance is external/work-PC** unless a local harness is committed. **Migration:** none. **Risks:** low (no lock exposure). **Rollback:** revert the driver; the 5 modules restore independently.
- **Completion:** the five vs-TSN canaries semantically identical; offline suite green.

### P6 — Persistence hardening (narrowed)  [blocking core; DPAPI gated O2]
- **Objective:** dedup + atomicity + the evidenced security hardening.
- **Findings:** §2.3 (settings dup), AUDIT-P2-authrest, support-bundle allowlist, R1-N02.
- **Affected:** `settings.py` (route the 4 writers through `_atomic_write`); `common.save_auth_state` (atomic write **then** ACL); `gui_api.save_support_bundle` (setting **allowlist**). **Dropped:** `_safe_join`, `full_snapshot()`, `paths` init-rewrite, settings schema-version-as-ceremony (kept only if a concrete migration exists).
- **Changes:** as above; **DPAPI deferred to O2**.
- **Protected:** unknown-key round-trip; corrupt-file move-aside; existing `config.json` readable; auth-file **portability** preserved (ACL not DPAPI).
- **Prereqs:** P0. **Tests:** settings-writer + atomic-auth + allowlist checks; `check_gui_bridge` (support bundle).
- **Migration:** none (additive). **Risks:** low. **Rollback:** per-writer revert.
- **Completion:** persistence checks green; 44/44 green.

### P7a — GUI state ownership + protocol + lifecycle  [blocking; depends P1, PA]
- **Objective:** establish the state boundary **before** any endpoint moves (R1-R06/D03).
- **Findings:** F8, F14, R1-R06/R14.
- **Affected:** new `task_coordinator.py` (owns `_task`, queue, current job, cancellation events, exactly-once transitions); `gui_api` delegates to it; `_handle` → dict dispatch table; `contract.py` enum SSOT surfaced in `get_initial_state`; log the verified swallows (support-bundle/chromium-state/`_safe_close*`).
- **Changes:** state ownership + dispatch table + enum SSOT + exactly-once lifecycle; **no endpoint files split yet**.
- **Protected:** JS API names + event order unchanged; single-task-gate semantics unchanged.
- **Prereqs:** P1 (chaining keys on the outcome), PA. **Tests:** CT-10 lifecycle (per-worker success/cancel/error/duplicate-late asserting gate release + queue advance; R1-R14); `check_gui_bridge`/`matrix_bridge`/`day_matrix`/`b3`; `#mock`.
- **Migration:** none. **Risks:** medium (coordination state) — mitigated by lifecycle CT + façade identity. **Rollback:** the coordinator is introduced behind the existing façade; revert restores in-line state.
- **Completion:** CT-10 + bridge checks green; `#mock` all tabs; 44/44 green.

### P7b — GUI mechanical endpoint extraction  [blocking; CR-001; depends committed P7a]
- **Objective:** group endpoints into modules once the boundary is enforceable (reclassified conditional → blocking, CR-001).
- **Findings:** F14, §2.4 (Claude); CR-001 §8.2 / RM08.
- **Affected (P7b slice — the `gui_win32` group + compare-unify):** `gui_win32.py` (ctypes, zero coupling); `_begin_compare` helper unifying `start_compare`/`start_compare_env` (the `_begin_task`/compare-unify; a generic `_begin_task` over the heterogeneous claim sites is speculative — KISS/RM08). **The Matrix feature-endpoint grouping + matrix dispatch pairs are split to P7c below** (CR-001/P7b-R01 — "one group per diff": each cohesive group is its own behavior-neutral diff + per-group revert).
- **Protected (RM08):** **façade/pywebview API names + event order unchanged**; coordinator owns state (endpoints call it, never each other's privates); **no behavior change mixed with the mechanical move**; **no one-class-per-action sprawl** (group by responsibility, not per-action); no framework/ES-modules.
- **Prereqs:** committed **P7a**. **Tests:** the bridge golden checks (`check_gui_bridge`/`check_matrix_bridge`/`check_b3_batch`) **plus a new API-surface identity check** (`check_gui_api_surface`) asserting the 98-name façade is unchanged (RM08). **`#mock` smoke: N/A for this backend-only slice** (no `scripts/ui/` change → the frontend is byte-identical to P9's verified smoke; P7b-R02) — it is carried by **P7c**, which moves the matrix endpoints. **Migration:** none. **Risks:** medium — one group per diff. **Rollback:** per-group revert.
- **Completion:** bridge + API-surface-identity green; `gui_win32` is one named responsibility per module; offline suite green.

### P7c — GUI Matrix feature-endpoint grouping  [blocking; CR-001/P7b-R01; depends committed P7b]
- **Objective:** extract the cohesive Matrix / day-matrix / TSN-library feature endpoint + dispatch-machinery cluster (~50 methods, ~1000 lines) out of `gui_api.GuiApi` behind the existing façade, behavior-neutral — the next "one group per diff" increment Codex required be formalized (P7b-R01).
- **Findings:** F14, §2.4 (Claude); CR-001 §8.2 / RM08; P7b-R01.
- **Affected:** new `gui_matrix.py` (`GuiMatrixMixin` — the matrix / day-matrix / TSN-library endpoints + `_dispatch_*`/`_resolve_*`/queue machinery + the matrix `_on_*` handlers); the matrix dispatch pairs (`_dispatch_compare_job`/`_dispatch_day_compare_job`, `_dispatch_export_job`/`_dispatch_day_export_job`) unified where behavior-neutral; `gui_api` inherits the mixin; a small shared decorator module to break the `_api_method` import cycle if needed. `task_coordinator` stays the state owner.
- **Protected (RM08):** **every moved method keeps its pywebview name + return shape + event order**; `task_coordinator` owns task/queue state (endpoints call it, never each other's privates); **no behavior change mixed with the move**; no one-class-per-action sprawl; no framework/ES-modules.
- **Prereqs:** committed **P7b**. **Tests:** `check_gui_bridge`/`check_matrix_bridge`/`check_b3_batch`/`check_worker_lifecycle`; **`check_gui_api_surface` extended** to lock the moved Matrix method names + that they now live in `gui_matrix`; the **deterministic `#mock` all-tabs smoke** (matrix + by-day tabs render + queue, `scrollHeight===innerHeight`); offline suite. **Migration:** none. **Risks:** **high** (the largest mechanical move on the field-hardened bridge) — behavior-neutral mixin (MRO preserves the surface), shim-reversible. **Rollback:** revert the mixin extraction (the methods restore inline).
- **Completion:** bridge + extended API-surface + `#mock` all-tabs green; the Matrix cluster is one named responsibility per module; `gui_api` is materially smaller; offline suite green.

### P8a — Engine leaf extraction  [blocking]
- **Objective:** extract the pure leaves behind the shim, behavior-neutral (R1-R08).
- **Findings:** F14.
- **Affected:** `errors.py`/`timeouts.py`/`routes.py`/`site.py` (+ auth-file lifecycle) extracted; `common.py` re-export shim; **no behavior change** (no lock — R1-R07).
- **Protected:** console-free shim; 14-module import surface; `site` behavior unchanged.
- **Prereqs:** PA (packaging gate proves the new modules freeze). **Tests:** new `routes`/`timeouts` unit checks; `check_export_engine`; the PA reachability/frozen gate. **Migration:** none. **Risks:** low. **Rollback:** shim per-module revert. **Completion:** engine checks + frozen gate green.

### P8b — Engine mechanical movement (DAG)  [blocking; depends P8a]
- **Objective:** move channels/auth/edge/session along the **verified acyclic DAG** (§E), behavior-neutral.
- **Findings:** F14, R1-B03/D04/R08.
- **Affected:** `browser_channels.py`, `auth_nav.py`, `report_nav.py`, `edge_device.py`, `session.py`; `common.py` shim; **no behavior change** in this phase.
- **Protected:** Playwright thread-affinity (add assertions); the field-hardened flows are **moved, not modified**; acyclic imports (import-direction check from P0).
- **Prereqs:** P8a. **Tests:** import-direction (no cycle); thread-affinity assertions; `check_export_engine`/`check_fake_site`; frozen gate. **Migration:** none. **Risks:** medium (broad move) — behavior-neutral, shim-reversible. **Rollback:** per-module shim revert. **Completion:** DAG acyclic; engine + frozen green.

### P8c — Engine behavior changes  [blocking for v0.18.0 CODE; CR-001/RM03; work-PC acceptance → v0.18.1]
- **Objective:** the live-path correctness/security changes. CR-001 makes O7 available as a **v0.18.1 validation window**, so the **code is blocking for v0.18.0 completion**; **work-PC acceptance is NOT claimed until v0.18.1** (RM03). **No default runtime flag** — Codex rejected it (a flag would test a different config than the user runs); each change is a **revertible RC commit**.
- **Findings:** AUDIT-P2-substr, AUDIT-P2-cdp, `should_cancel`-in-recover, swallow logging, R1-T04/R08; CR-001 §8.2.
- **Affected:** `report_nav.select_report` (exact-match guard), `edge_device` CDP open-on-demand+close, `should_cancel` threaded into `_recover`/retry/portability, auth-path swallow logging.
- **Changes:** **each change is its own revertible commit** (don't move + alter in one — R1-R08).
- **Fixture-first (RM03):** **before any behavior change**, extend `build/fake_site/` to cover **exact label, prefix/suffix near-miss labels, a disabled option, a malformed `wait_js`/config-error, CDP open/close, and cancel-latency** as applicable. **No live TSMIS access, credential, or profile inspection during implementation.**
- **Protected:** don't chunk the field-hardened waits — only **add** cancel polling; Playwright thread-affinity.
- **Prereqs:** committed **P8b** + the extended fake-site fixture. **Tests (all offline):** the exact/prefix/suffix/disabled fixture; the malformed-`wait_js` config-error path; CDP open/close; cancel-latency; `check_export_engine`/`check_fake_site`. **v0.18.1 acceptance (§K2):** the real-PC select/CDP/cancel sign-off. **Migration:** none. **Risks:** **highest** (live auth/browser) — bounded by offline fixtures now + the v0.18.1 gate before GA. **Rollback:** per-change revert.
- **Completion (v0.18.0):** every behavior change offline-proven against the extended fixture, each its own revertible commit; offline suite green. **Work-PC acceptance is recorded as owed in §K2/§M and closed in v0.18.1 — NOT a v0.18.0 blocker** (RM02/RM03).

### P9 — Frontend mock separation  [blocking (mock); deeper split → O1]
- **Objective:** kill the mock-as-2nd-backend drift; do not framework-ize.
- **Findings:** F13, R1-R09/N03/R13.
- **Affected:** `ui/mock.js` (extracted, **classic `<script>` after `app.js`, `#mock`-gated**, and **owns the mock boot** — defines `makeMockApi` then calls `boot(makeMockApi())`; `app.js` auto-boots only in production — R1-R09/RR2-C3); `ui/contract.js` (enum mirror) + report fixtures generated from `report_catalog` (UI metadata only; oracles independent — R1-R13); `index.html` script ordering.
- **Changes:** extraction + payload parity; **renderer merge + deeper split deferred to O1** (R1-N03).
- **Protected:** **Lesson-10 sr-only CSS rule**; the browser-HTTP-cache reload procedure; no production-UI behavior change.
- **Prereqs:** P4 (fixtures); PA. **Tests:** CT-13 (independently-captured backend payload snapshots vs frontend expectations — R1-R13); a deterministic boot check for production + `#mock` (no missing globals/404s; reset preview + matrix tabs; `scrollHeight===innerHeight`); `full_smoke` boots `app.js` + `mock.js`.
- **Migration:** none. **Risks:** medium (no app.js unit net) — mitigated by CT-13 + boot check. **Rollback:** mock extraction reversible.
- **Completion:** CT-13 + boot check green; mock has no stale strings. **(Status: COMMITTED `decced4`; the deferred deeper split / renderer merge is now the new blocking phase P9b — CR-001. P9 is not reopened.)**

### P9b — Frontend deeper modularization (renderer merge + app.js split)  [blocking; CR-001; depends committed P9]
- **Objective:** the O1-deferred deeper split — merge duplicated render paths and break `app.js` into cohesive classic-script modules — opted in (CR-001) for a maintainable frontend, **without** framework-izing.
- **Findings:** D4 / R1-N03; CR-001 §8.3 / RM08.
- **Affected:** `ui/app.js` (split into cohesive modules), renderer-path merge; `index.html` classic `<script>` ordering preserved.
- **Protected (RM08):** **no framework, no ES modules** (unless separately justified **and** proven in pywebview/file/frozen modes); **no production-UI behavior change**; pywebview API names + event order, `#mock`, classic script ordering, and the **Lesson-10 `sr-only`** rule all preserved; the browser-HTTP-cache reload procedure honored.
- **Prereqs:** committed **P9**. **Tests:** **extend `build/check_ui_boot.js` + `build/check_ui_contract.py`** to lock the new module boundaries (no missing globals/404s, boot wiring intact); the existing Node UI checks (`check_mx_partial_render.js`, `check_compare_routing.js`); `node --check`; a **`#mock` smoke** (reset + matrix tabs, `scrollHeight===innerHeight`). **Migration:** none. **Risks:** medium (broad UI move) — behavior-neutral, boot-checked. **Rollback:** per-module revert.
- **Completion:** the extended boot/contract checks + `#mock` smoke green; no production-UI behavior change; offline suite green.

### P10 — Packaging / deps / updater hardening (later)  [blocking; depends PA, P4]
- **Objective:** reproducible builds, dependency integrity, the **enumerated** updater fixes.
- **Findings:** F11, F12, R1-R10/A01/A03/M02/M04/T06; the updater audit set (§J).
- **Affected:** `build.ps1` (recreate `build/.venv` / verify exact lock / fail on unexpected — R1-R10); `requirements*` (hash-pinned via `pip-compile --generate-hashes` for win/3.11; pin the **existing** `cryptography` transitive (pulled by `pdfminer.six`) — lock integrity, **not** a new dependency; assert `version.py`↔`requirements` Playwright); `release.yml` (enforce `.sha256` publication; with-browser signing **parity in workflow design only** — R1-A03; per-variant acceptance fails-not-skips — R1-T06); `updater.py` (the §J table **as amended by CR-001 — the three formerly "Defer (document)" items flip to *implement*: download **socket timeout + bounded retry**, `resolve_previous_release` **pagination past the 100 cap**, and **immediate-death-check hardening**; the **signature** row stays deferred, blocked on a cert — RM06**); **optional perf** (lazy `reports` imports) only with the R1-A01 harness + threshold.
- **Protected:** cert-store TLS; swap order; `excludes`/prune proven by `-SelfTest`; **no runtime signature abstraction / new crypto dep** (A03).
- **Prereqs:** PA (the gate exists), P4. **Tests:** the §J updater checks; `check_updater`; the frozen gate; before/after timings if perf is attempted.
- **Migration:** none. **Risks:** medium (CI + frozen-only classes — the PA gate is the mitigation). **Rollback:** workflow/spec isolated; lazy-import revert restores eager.
- **Completion:** reproducible-build policy in place; deps hash-pinned; the §J updater items each implemented/deferred per the amended table (the 3 CR-001-flipped items implemented; the signature row still deferred — RM06); offline suite + frozen gate green. **(Perf is optional; dropped if no material gain — A01.)**

### P12 — Residual offline audit hardening + evidence harnesses  [blocking; CR-001; depends committed P2/P3]
- **Objective:** close the offline-doable audit residue and stand up the PDF-completeness *harness* (not the real-data proof — RM04).
- **Findings:** §J2 rows (reset-junctions, consolidate-TOCTOU, destination-marker/M03, the PDF trio + row-count oracle); CR-001 §8.3 / RM04.
- **Affected (each its own commit + offline check):** `reset` path → junction/symlink guard (Windows-verified on the dev PC); the consolidate-overwrite **re-check** closing the confirm-then-appears window; the **destination-ownership marker** (M03) on app-created dest dirs; a new **independent expected-row oracle harness** + minimal/synthetic PDF fixtures + the evidence-capture contract that P13 consumes.
- **Protected:** `compare_core` untouched; the locked row-emit logic untouched; no live access.
- **PDF/parser honesty (RM04 — do NOT over-claim):**
  - `pdf-consolidator-no-row-count-verification` — v0.18.0 ships the **independent oracle harness** + the evidence-capture path; **real-PDF acceptance stays v0.18.1** unless a committed fixture truly reproduces it during implementation.
  - `pdf-stale-geometry-carryforward` — the stale-geometry **emit** is **not** claimed closed by synthetic-only coverage; closed only if a committed synthetic fixture proves the **exact** row-emission failure mode.
  - `ramp-summary-parse-failure-misattributed-to-source` + `ramp-summary-duplicate-pop-pattern-misassignment` — **v0.18.1 evidence-driven fixes** unless a safe minimal offline fixture reproduces the exact failure (then resolved in v0.18.0).
- **Prereqs:** committed P2 (atomic store) + P3. **Tests:** new `check_*` per item; extend `check_tsmis_pdf_reconcile`; the oracle harness over synthetic fixtures. **Migration:** none. **Risks:** low-medium (Windows fs + PDF edges) — bounded to offline-provable items. **Rollback:** per-item revert.
- **Completion (v0.18.0):** the junction guard / TOCTOU re-check / M03 marker landed + offline-checked; the oracle harness + capture contract committed; the real-PDF-dependent items explicitly carried to §K2/v0.18.1.

### P14 — Intersection Detail (PDF) report-family forward-port  [blocking; CR-002/CR002-RM1/RM2/RM4/RM5/RM6; depends committed P3/P4 + the HL-PDF structure]
- **Objective:** forward-port the **Intersection Detail (PDF)** report family from `origin/main` (v0.17.8) into the refactored architecture as an exact **`highway_log_pdf` parallel** — export + 36-col PDF consolidator + cross-env/PDF-vs-TSN/PDF-vs-Excel adapters + both matrices — wired through the v0.18.0 sources of truth. **Forward-port, not merge** (CR002-RM7).
- **Findings:** CR-002 §6/§8; the handoff §1–§7 (the §3 wiring map + the §4 parser).
- **Affected (port into the refactored SoT — RM1/RM2/RM6):**
  - **New modules (mirror the HL-PDF sibling):** `scripts/export_intersection_detail_pdf.py`, `scripts/intersection_detail_columns.py` (36-col header SoT), `scripts/consolidate_tsmis_intersection_detail_pdf.py` (the 2-row/zebra-shaded PDF parser — the genuinely new logic), `scripts/compare_intersection_detail_pdf.py` (PDF-vs-TSN + PDF-vs-Excel adapters).
  - **Metadata SoT (RM1):** add the report to **`scripts/report_catalog.py`** (the ONE SoT); `scripts/reports.py` stays the **derived** API (EXPORT/CONSOLIDATE/COMPARE + matrix rows derive); extend **`build/check_report_catalog.py`** so the catalog snapshot ↔ derived `reports.py` API ↔ backend bridge payload ↔ `mock.js` payload stay in parity.
  - **Engine wiring:** `scripts/exporter.py` (`save_intersection_detail_pdf`), `scripts/matrix.py` (the `_pdf_store_consolidator` PDF-report branch feeding `_consolidated_filename` + `_consolidate_store_folder` — the **v0.17.4 crash class**; `_row_modes`/`tsn_comparator_for`/generalized vs-Excel self-compare), `scripts/day_matrix.py` (`fmt="pdf"` branch), `scripts/compare_env.py` (`INTERSECTION_DETAIL_PDF` EnvCompare), `scripts/gui_worker.py` (reset/cleanup parity), `scripts/gui_api.py`/bridge payloads as needed.
  - **Frontend (RM2):** `scripts/ui/mock.js` fixtures (export/consolidate/compare/matrix mocks) + `scripts/ui/contract.js`/bridge keys — **never** `app.js` (do not reintroduce `makeMockApi`).
  - **Packaging/checks (RM6):** `build/app.spec` `APP_MODULES` += the 4 new modules; `build/check_intersection_detail_pdf.py` (NEW — locks the 36-col header + rowA/rowB→36-col mapping incl. the `Intrte` swap + merged Description + the **every-matrix-row-resolves-a-filename** regression); `build/fake_site/intersection_detail_print.html` + `build/check_fake_site.py`; reconcile `build/check_matrix.py`/`check_matrix_bridge.py`/`check_matrix_tsn.py`/`check_day_matrix.py` (row set now **8** — reconcile the "hide-N reject the (N+1)th" assertions to the refactored set), `build/check_intersection_gate.py` (registry-derived count), `build/check_source_zip_smoke.py` (**prove** `EXPORT_REPORTS` derivation, not literal menu edits — RM6), `build/check_stable_ids.py` (RM4), `.github/workflows/checks.yml`.
- **Protected:** committed P0–P12 contracts (stable IDs/manifest, outcome model, transactional store, matrix structure) — **EXTENDED, not reopened**; **`compare_core` untouched** (the new comparators reuse `compare_intersection_detail_tsn`'s schema/loaders via adapters); the **7 existing export keys keep positions 0–6** (RM4, append-only); no live TSMIS/credential/profile access.
- **Stable-ID/manifest compat gate (RM4):** `intersection_detail_pdf` appended only; `_V017_EXPORT_ORDER` preserves 0–6; `check_stable_ids` proves a pre-Int-PDF **v1 integer-index** manifest AND the new key both resolve correctly.
- **Prereqs:** committed **P3** (stable IDs) + **P4** (catalog) + the refactor's current `highway_log_pdf` structure. **Tests (the Codex P14 list — all offline):** `check_intersection_detail_pdf`, `check_report_catalog`, `check_stable_ids`, `check_fake_site`, `check_intersection_gate`, `check_matrix`/`_bridge`/`_tsn`, `check_day_matrix`, `check_gui_bridge`, `check_app_modules`, `check_import_direction`, `check_source_zip_smoke`, `check_ui_boot.js` + the UI/contract mock-parity check(s) if payloads change; full suite + byte-compile + `#mock` smoke green. **Migration:** none (append-only). **Risks:** medium-high (registry/matrix/packaging breadth) — bounded by the handoff map + golden checks. **Rollback:** the new report is behind the catalog/registry — revertible per-commit.
- **RM04 honesty:** the PDF parser's **36-col mapping is locked offline** by `check_intersection_detail_pdf`; **real-PDF/Excel/TSN correctness acceptance is v0.18.1** (the handoff's 218/218-route reconciliation ran on LOCAL ground truth, never in CI) — identical footing to the other PDF reports + the P12 oracle.
- **Completion (v0.18.0):** the Int-Detail-PDF report is registered + wired at full HL-PDF parity in the refactored tree; the new + reconciled golden checks green; packaging inventory updated; the live export/consolidate/compare acceptance carried to **§K2/v0.18.1 (P13)**.

### P15 — Intersection Detail vs-TSN comparison-behavior forward-port  [blocking; CR-002/CR002-RM3/RM5; depends P14 + committed P5b]
- **Objective:** re-apply the **localized** Intersection Detail vs-TSN comparison evolution (v0.17.5–v0.17.8) onto the refactored `compare_intersection_detail_tsn` — to its **final v0.17.8 state** (the handoff §9e supersedes §8/§9d) — plus the matching Summary fold. Independent of the §3 plumbing (the handoff confirms it forward-ports separately).
- **Findings:** CR-002 §6; the handoff §8/§9 (current source of truth = §9e).
- **Affected:**
  - **`scripts/compare_intersection_detail_tsn.py`:** the J–P→Signalized control crosswalk (`_norm_control_type`), the **compare-everything** policy (`CONTEXT_FIELDS=()`), **read-time TSN-library re-normalization** (`_normalized_row` on the `_load_tsn` path — the "Signalized ≠ P" stale-library fix), **position-aligned** date columns (`_TSN_COL`/`_TSMIS_POS`; do NOT revert to recent-date pairing), numeric-padding normalization (`_norm_num` + `NUMERIC_FIELDS`), `_SIGNALIZED_LABEL = "S"`, and the **"Report View"** replica sheet via the EXISTING `extra_sheet_writer` opt-in (+ the write-only techniques: `merged_cells.ranges.add` / `WriteOnlyCell.comment` / `freeze_panes`-before-rows).
  - **`scripts/compare_intersection_summary_tsn.py`** + **`scripts/summary_layout.py`** (only if Report-View/fold parity needs it): the §9b signal fold (`_CONTROL_SIGNAL_FOLD`; J–P→`S - SIGNALIZED`; `SummarySpec.notes`) + the read-time `_slug_for_key` library fold (summed, not overwrite).
  - **`scripts/compare_intersection_detail_pdf.py`** where it reuses the evolved detail schema/loaders.
  - **Canaries:** `build/check_compare_intersection_detail_tsn.py` (the **v0.17.8** canary — Excel **163,353** / PDF **163,361**; `CONTEXT_FIELDS=()`, position-aligned mappings, `S` crosswalk, Report-View locks), `build/check_compare_intersection_summary_tsn.py` (66 categories, 58/8/0, 54 diff cells).
- **Protected (CR002-RM3):** **`compare_core` is NOT modified — `context_fill` is NOT ported** (v0.17.8 dropped its only user; Report View uses the existing `extra_sheet_writer`); the **Route-1=969 Highway Log canary**, every OTHER vs-TSN comparator (Ramp Detail, Highway Sequence — they KEEP their context fields; this policy is Intersection-Detail-specific), and `check_compare_audit` stay byte-identical; the locked row-emit logic is untouched; no live access.
- **Prereqs:** **P14** (the PDF report exists) + committed **P5b** (the shared comparator driver). **Tests (the Codex P15 list):** the Int-Detail vs-TSN detail canary; the Int-Summary summary/fold canary; the PDF-vs-TSN + PDF-vs-Excel adapter checks; `check_compare_audit` + the Highway Log/Ramp/Int-Summary/Int-Detail comparison regression checks; **plus an explicit statement in the P15 report that `compare_core.context_fill` was NOT ported** (if false, STOP for the separate approval — Codex). **Migration:** none. **Risks:** medium (large/volatile canaries + read-time normalization) — port the canary verbatim from the shipped check; re-bless ONLY the touched report's canary, never `compare_core`'s. **Rollback:** localized to the two comparison modules — per-commit revert.
- **Completion (v0.18.0):** the final v0.17.8 Int-Detail vs-TSN behavior reproduced in the refactored tree; both canaries green; **`compare_core` proven unmodified**; the doc/CHANGELOG impact carried to **P11**.

### P13 — Work-PC validation handoff + v0.18.1 close-out plan  [blocking; CR-001/CR-002-RM5; FINAL design phase; depends P8c/P10/P12 + P14/P15 — verifies the final 8-report shape]
- **Objective:** design the method to validate everything that cannot be proven offline, and write the v0.18.1 plan that consumes the returned evidence and closes the refactor.
- **Findings:** §M; CR-001 §8.3 / RM05; the O7/live-verify set.
- **Affected:** a bundled **no-admin/no-PowerShell evidence-collection mode** (`--collect-evidence`, reusing the self-test plumbing — runs from a user folder, no admin/cmd/scheduled tasks); a **documented manual fallback** for PCs where even the mode can't run; the **per-item acceptance checklist** (§K2); the **v0.18.1 plan** doc. **CR002-RM5: the acceptance set covers the final 8-report application shape — incl. Intersection Detail (PDF)'s live export/consolidate/compare + the v0.17.8 Int-Detail vs-TSN behavior — NOT the pre-port 7-report shape** (still no private report data / credentials / profiles / internal-site source collected — RM05).
- **Privacy/credential safety (RM05 — hard requirements):** the bundle **never** collects auth state, browser profiles, cookies, DPAPI material, or credentials; **no** private report outputs or source PDFs **by default**; if real PDFs/workbooks are needed the **user explicitly places them in a documented evidence folder** and the **bundle manifest lists every included file**; sensitive paths/tokens redacted/avoided where practical.
- **Protected:** the work-PC capability model (unsigned exe from a user-writable folder; no admin/cmd/temp-scripts/scheduled-tasks); cert-store TLS; console-free core.
- **Prereqs:** P8c + expanded P10 + P12 **+ P14/P15 (CR-002)** — so the full **8-report** live-verify set (incl. Intersection Detail PDF) is known. **Tests:** the evidence-mode code path is **exercised by offline tests** and, where feasible, the existing **self-test/frozen gate without launching the GUI**; a test **proves the bundle excludes credentials/auth/profile data** (RM05). **Migration:** none. **Risks:** low (design + a bounded, well-tested collector). **Rollback:** the mode is inert unless invoked.
- **Completion (v0.18.0):** the evidence kit + manual fallback + acceptance checklist (§K2) + the v0.18.1 plan committed; the credential-exclusion test green. **Executing the acceptance on the work PC is v0.18.1, not v0.18.0.**

### P11 — Docs + audit/roadmap reconciliation  [blocking; LAST]
- **Objective:** canonical `docs/` reflect v0.18.0; every audit item dispositioned.
- **Findings:** §3.3 doc-drift; §I; R1-M03/M05; CR-001.
- **Affected:** `docs/` (architecture/gui/gui-bridge/comparison-engine/engine-and-reliability/build-and-release/roadmap), `CLAUDE.md` conventions (the new outcome/transaction/column-layout contracts), `CHANGELOG.md`; fold this planning folder + the CR-001 amendment in; record the now-**implemented** destination-ownership marker (M03, P12) and the residual **hard-deferrals** (O2/cert/`min-cost-pairs`/D16) in `docs/roadmap.md`.
- **Protected:** docs accuracy (verify each claim vs shipped code); the **two-tier release framing** (RM02 — v0.18.0 = offline-validated candidate, v0.18.1 = field-validated).
- **Prereqs:** the **amended v0.18.0 blocking set** complete (P0/PA/P1/P2/P3/P4/P5b/P6/P7a/P7b/P7c/P8a/P8b/P8c/P9/P9b/P10/P12/**P14/P15 (CR-002)**/P13); only the hard-deferrals (O2/cert/`min-cost`/D16) excluded. **Tests:** `check_no_misspelling`; manual review + link/anchor check. **CR-002 docs to absorb:** the v0.17.2–v0.17.8 doc set the handoff §6 lists (CLAUDE.md report 6b, README, `docs/reports.md`, `docs/comparison-engine.md`, `docs/tsn-parsers.md`, `docs/roadmap.md`, CHANGELOG) — reconciled to the refactored architecture, plus the deferred `non-hl-loaders-dont-collapse-tab-whitespace` item.
- **Migration:** none. **Risks:** low. **Rollback:** docs-only. **Completion:** docs match HEAD; every open audit item has an individual disposition (**§J2**), now **written into `docs/roadmap.md`**; the **v0.18.1 plan** (from P13) folded in; planning folder folded in.

---

## J. Updater audit disposition (R1-M04)
| Item | Symbol | Disposition | Check |
|---|---|---|---|
| size+checksum both skippable | `download_and_stage` `asset_size`/`.sha256` | **Implement (fail-closed)** — the runtime updater **requires a verified `.sha256`/API digest before extraction**; when absent it **aborts the install + shows the release page** (never size-only). Subsumes `asset_size==0` (the SHA covers integrity regardless of size). `release.yml` also asserts `.sha256` publication so the safe path is the normal path. | `check_updater` (no/forged checksum ⇒ refuse + keep old version) |
| ZIP member containment | `download_and_stage` `extractall` | **Implement** — explicit member-path containment before extract | `check_updater` (zip-slip fixture) |
| staged-exe not re-hashed at swap | `apply_update_and_restart` | **Implement** — store stage hash; re-verify immediately before swap | `check_updater` |
| rollback claims success on partial restore | `perform_swap` | **Implement** — message reflects actual restore outcome | `check_updater` |
| swap log unbounded | `update_helper.log` | **Implement** — rotate | `check_updater` |
| dev webview cache cleared every launch | `cleanup_leftovers` | **Implement** — move below `is_frozen()` | `check_updater` |
| 1.5 s death-check window | `apply_update_and_restart` | **Implement (CR-001/P10)** — harden the window (still fail-safe) | `check_updater` |
| download retry/timeout | `download_and_stage` | **Implement (CR-001/P10)** — socket timeout + bounded retry | `check_updater` |
| releases list cap 100 | `resolve_previous_release` | **Implement (CR-001/P10)** — paginate past the 100 cap | `check_updater` |
| no signature | trust chain | **Defer (blocked on cert; UNCHANGED by CR-001 — RM06)** — workflow signing parity only; **no runtime abstraction** (A03) without explicit user/procurement approval | — |

---

## J2. Open Phase-3 audit findings — item-by-item disposition (resolves R1-M05 + Readiness RR1-B1)

Every still-open Phase-3 finding at HEAD, each to a phase or an explicit deferral + destination. Closed
findings (the field-bug retry, 4/5 P1, `report_error_text`, stage-and-swap, the parallel-reconcile pair)
are recorded in the investigations and not repeated. **The PDF Highway Log trio is NOT closed** — v0.17.0
added reporting only (`consolidate_tsmis_highway_log_pdf.py:294` "reporting only … row-emit logic
unchanged"); it is dispositioned explicitly in the rows below (RR2-B1). "Resolved" = a v0.18.0 phase
implements + tests it; "Deferred" = out of v0.18.0 with a repository-backed reason + destination. **P11 only
*writes* these outcomes into `docs/roadmap.md`; the decisions live here.**

| Finding (slug) | Sev | Disposition | Phase / destination | Basis |
|---|---|---|---|---|
| update-trust-is-tls-plus-sibling-sha-only | P1 | Deferred | roadmap (blocked on SignPath cert); §J signature row | authenticity needs a trusted cert; not offline-closable. **Unchanged by CR-001 — RM06: runtime signature verification needs an explicit user/procurement decision.** |
| auth-file-plaintext-no-acl-dpapi | P2 | Resolved (ACL) / DPAPI **Requires-user-decision** | P6 (atomic write + ACL); DPAPI → **O2** | DPAPI breaks `storage_state_is_portable`. **Unchanged by CR-001 — RM06: optional off-by-default DPAPI in v0.18.0 needs explicit user approval (O2).** |
| edge-login-cdp-port-unauthenticated-loopback | P2 | Resolved | P8c | open CDP on-demand, close on capture (live) |
| select-report-substring-match-no-exact-guard | P2 | Resolved | P8c (+ R1-T04 fake-site fixture) | exact-match guard (live) |
| handle-no-default-branch | P2 | Resolved | P0 | `gui_api._handle:462` gains an `else` log |
| size-and-checksum-guards-both-skippable | P2 | Resolved-with-mod (fail-closed) | P10/§J | require a verified checksum before extraction; never size-only |
| immediate-death-check-narrow-window | P2 | **Resolved (P10, CR-001)** | P10/§J | hardened (flipped from document); still fail-safe |
| no-rollback-when-relaunch-launches-partial-tree | P2 | Resolved | P10/§J | rollback message reflects the actual restore outcome |
| ramp-summary-parse-failure-misattributed-to-source | P2 | **v0.18.1 evidence-driven** (P12 harness) | P12 (offline harness) → v0.18.1 acceptance | offline only if a committed fixture reproduces the **exact** failure; else real-PDF acceptance v0.18.1 (RM04) |
| ramp-summary-duplicate-pop-pattern-misassignment | P2 | **v0.18.1 evidence-driven** (P12 harness) | P12 (offline harness) → v0.18.1 acceptance | offline only if a committed fixture reproduces the **exact** failure; else real-PDF acceptance v0.18.1 (RM04) |
| pdf-page-skip-unlogged-when-no-prior-geometry | P2 | Resolved (reporting) + P1 partial | v0.17.0 (count+log) → P1 (partial) | the previously-silent skip is now counted + logged (the finding); **P1** escalates the `skipped_no_geometry` stat to a producer-owned `partial` completion so dropped-line output isn't promoted/cached as complete. Acceptance: `check_tsmis_pdf_reconcile.py` banner + a new P1 partial case. Row-emit logic unchanged. |
| pdf-stale-geometry-carryforward-silent-corruption | P2 | Mitigated (no longer silent) + **emit → P12 harness / v0.18.1** | v0.17.0 (NOTE) + P1 (partial); carry-forward **emit** elimination → P12 harness, acceptance v0.18.1 | flagged once per page, no longer silent (`:386`); **P1** marks carried-forward output `partial`. Per **RM04** the stale-geometry **emit** is **not** claimed closed by synthetic-only coverage — only if a committed synthetic fixture proves the **exact** row-emission failure mode; else real-PDF acceptance is v0.18.1. Audit geometric cross-check found **0**/756. |
| pdf-consolidator-no-row-count-verification | P2 | **P12 oracle harness (v0.18.0) + v0.18.1 acceptance** | P12 (harness + capture) → v0.18.1 | per **RM04**, P12 ships the **independent expected-row oracle harness** + the evidence-capture path; **real-PDF acceptance stays v0.18.1** unless a committed fixture reproduces it during impl. `check_tsmis_pdf_reconcile.py:78–81` checks banners only (parse_pdf stubbed); v0.17.0 `stats` + P1 `partial` remain the interim down-payment. |
| run-report-only-written-when-per-route-nonempty | P3 | Resolved | P1 | emit the run report on cancelled-at-start (run-lifecycle surface) |
| select-report-not-rearmed-between-routes-on-stale-form | P3 | Resolved | P8c | re-confirm the report dropdown each route (live) |
| unlogged-no-download-empty-on-pdf-and-misc | P3 | Resolved | P8c | marker-independent empty backstop on the PDF save path (live) |
| wait-js-fstring-interpolation-unvalidated | P3 | Resolved | P8b (the single **explicitly-permitted** narrow behavior change there) | validate `spec.wait_js` so a malformed spec raises a **config error** instead of reading as a route timeout; offline, locked by `check_export_engine` (RR2-C1) |
| gui-worker-stale-tkinter-docstring | P3 | Resolved | P0 | doc-drift |
| reset-follows-junctions-symlinks | P3 | **Resolved (P12)** | P12 (+ the M03 destination-ownership marker, now implemented) | junction/symlink guard, **dev-PC Windows-verified** (CR-001); scoped-delete + preview retained |
| support-bundle-settings-future-leak | P3 | Resolved | P6 | support-bundle setting allowlist |
| consolidate-overwrite-toctou | P3 | **Resolved (P12)** | P12 | P2 atomic replace closed the truncation half; **P12 adds the confirm-then-appears re-check** (CR-001) |
| device-ok-inferred-from-any-completed-run | P3 | Resolved | P7a | the task owner sets `device_ok` from the real sign-in path, not "any completed run" |
| login-busywait-no-cancel-check | P3 | Resolved | P8c | add the in-loop cancel check (cancellation behavior) |
| reset-token-consumed-before-task-gate | P3 | Resolved | P7a | check the gate before consuming the single-use token (coordinator-owned) |
| env-compare-side-label-cap-truncates-distinguisher | P3 | Resolved | P0 | `compare_env` label cap keeps the date/(A)/(B) distinguisher; 1-line + check (offline) |
| min-cost-pairs-greedy-not-optimal | P3 | **Deferred (repo-backed)** | roadmap (future `compare_core`-scoped effort) | inside the **regression-locked** `compare_core._min_cost_pairs`; any fix needs a locked-engine change + full cell re-proof; 8+ duplicate-key-group frequency unquantified. **Unchanged by CR-001 — RM06: a compare-core re-proof phase needs an explicit separate user decision.** |
| ramp-summary-combined-sheet-hardcoded-coordinates | P3 | Resolved | P0 | add a schema-length guard that raises on drift (offline check) |
| checks-yml-updater-gate-covers-only-pure-helpers | P3 | Resolved (partial) | P10/PA | §J adds zip-slip/rehash/rollback/rotation checks + the real-exe gate; full `apply_update_and_restart` on a real swap stays work-PC-verified |
| dl-socket-timeout-may-fail-slow-large-downloads | P3 | **Resolved (P10, CR-001)** | P10/§J | socket timeout + bounded retry (flipped from document) |
| extractall-zip-slip-relies-on-stdlib | P3 | Resolved | P10/§J | explicit member-path containment before extract |
| releases-list-capped-100-revert-blindspot | P3 | **Resolved (P10, CR-001)** | P10/§J | paginate past the 100 cap (flipped from document) |
| staged-exe-launched-from-user-writable-dir-no-recheck | P3 | Resolved | P10/§J | re-hash the staged exe immediately before swap |
| swap-log-grows-unbounded | P3 | Resolved | P10/§J | rotate `update_helper.log` |
| webview-cache-cleared-on-every-dev-launch | P3 | Resolved | P10/§J | move below the `is_frozen()` guard |

Every still-open finding is dispositioned — assigned to a phase (P0/P1/P6/P7a/P8b/P8c/P10/P12/PA) or deferred
with a repository-backed reason + destination. **None silently dropped.** **CR-001 update:** the offline-doable
residue is pulled into v0.18.0 (P10 updater items; P12 junction/TOCTOU/M03 + the PDF oracle *harness*); the
PDF/parser *correctness* items that need real PDFs are **v0.18.1 evidence-driven** (RM04). **P8c now ships its
offline-proven live-path *code* in v0.18.0** (each change a revertible RC commit, fixture-first); **its work-PC
acceptance is claimed in v0.18.1, not v0.18.0** (RM02/RM03) — superseding RR3-C1's "omit if no O7," since O7 is
now an available v0.18.1 window. The remaining **hard-deferrals each need an explicit separate user decision**
(RM06): DPAPI/O2, runtime signature/cert, and `min-cost-pairs` (protected `compare_core`).

---

## K. Measurable definition of done — v0.18.0 OFFLINE DoD (R1-P01/A04; amended CR-001/RM02)
- **Correctness:** CT-1..CT-14 green; F1–F5/F9 closed; O4 resolved; matrix shows correct aggregate
  vs-TSN counts; no partial run reports "complete." (Verified offline + in `#mock`.)
- **Contracts:** orthogonal outcome model + transactional artifact lifecycle + one cache envelope live;
  `report_catalog` is the report-metadata SoT (packaging reachability + oracles independent); `contract.py`
  bridge enums; `task_coordinator` owns task state; `compare_core` **unmodified**.
- **Structure (named outcomes, not line counts):** `common.py` is a shim over the acyclic engine modules;
  `gui_api` delegates to `task_coordinator`; the `#mock` is a separate file consuming shared fixtures; the
  report family has a shared substrate **where attempted** (P5 deferrable). `gui_worker.py` is **not**
  force-split.
- **Packaging/CI:** the **exact** windowed exe (both variants) + source ZIP pass their gates (fail-not-skip);
  runtime-module reachability + import-direction + lifecycle checks blocking; reproducible-venv policy +
  hash-pinned deps; the §J updater items dispositioned.
- **Persisted data:** every prior `config.json`/`batch_job.json`/`tsn_library`/output layout still works;
  format changes versioned + forward-migrating; rollback rules dependency-aware (§L).
- **Docs:** canonical `docs/` match HEAD; every open audit item individually dispositioned.
- **In the v0.18.0 offline DoD now (CR-001):** P5b, P7b, **P8c code** (offline-proven against the extended
  fake-site fixture), P9b, P12, and the expanded P10 (flipped updater items + optional perf) — each RED-proven
  + green offline before commit; the v0.18.0 code DoD stays **satisfiable from CI/offline alone** (R1-P01).
- **In the v0.18.0 offline DoD now (CR-002):** **P14 + P15** — **Intersection Detail (PDF)** registered + wired
  at full `highway_log_pdf` parity in the refactored tree (catalog/derived-API/mock parity, the matrix
  consolidated-filename wiring, append-only stable IDs, packaging inventory), and the **v0.17.8** Int-Detail
  vs-TSN behavior reproduced with its locked canaries (Excel **163,353** / PDF **163,361**; Summary 58/8/0) —
  all green offline; `compare_core` proven **unmodified** (no `context_fill`). **Real-PDF/Excel/TSN
  correctness acceptance is v0.18.1** (RM04). The 7 existing export keys keep positions 0–6 (RM4).
- **Excluded from the v0.18.0 DoD (→ §K2 / hard-deferred):** all **work-PC acceptance**; the **evidence-driven
  PDF/parser correctness** fixes (real-PDF; RM04); and **DPAPI/O2, runtime signature/cert, `min-cost-pairs`**
  (each needs an explicit separate user decision — RM06).

## K2. v0.18.1 work-PC acceptance DoD (separate gate; NOT part of the v0.18.0 DoD — CR-001/RM02)

v0.18.1 closes the refactor after the user runs the v0.18.0 **candidate** on the work PC and returns evidence
via the P13 kit. v0.18.1 is "done" when:
- **P8c live paths accepted:** exact `select_report`, CDP open-on-demand/close, cancel-in-recover latency — verified on the work PC against the returned logs.
- **Carried live-verify owed (§M) accepted:** P1 partial-keeps-last-good on a real refresh; P2 Defender/lock with disposable destinations; P3 real paused-batch resume; P10 a real v0.17→v0.18 update (staging-retry/checksum/swap); PA both frozen exes + source ZIP on the work PC.
- **Evidence-driven PDF/parser fixes:** the row-count oracle + ramp-summary misattribution/duplicate-pop verified against the **returned real source PDFs**; any fix landed + locked.
- **Intersection Detail (PDF) live acceptance (CR-002):** the forward-ported report's **live export → consolidate → PDF-vs-TSN / PDF-vs-Excel / cross-env** verified on the work PC against the returned real PDFs/Excel/TSN (the handoff's 218/218-route reconciliation re-confirmed there) — the same real-data acceptance footing as the other PDF reports; the v0.17.8 canaries already locked offline in P15.
- **No regressions:** the full offline suite still green; v0.18.1 code fixes are themselves offline-RED-proven.

**"Enterprise-ready" = operational sign-off is claimed only at v0.18.1**; v0.18.0 is the offline-validated
candidate (RM02).

## L. Risks & dependency-aware rollback (R1-P02)
- Each phase is isolated commits behind a shim/façade/additive module; the app is runnable + the full offline
  suite green at each boundary. **But rollback is dependency-aware:** reverting P3 after a `v2` manifest is written
  requires reverting P4 (which consumes keys) and tolerating/clearing v2 manifests (v1 stays forward-
  readable); reverting P1 after P2 requires reverting P2 (artifact disposition depends on the P1 result);
  reverting P4 requires reverting P9 fixtures + the P10 catalog-derived packaging. Persisted **v2
  manifests** and the **cache envelope** outlive a code revert — both are designed so older code reads
  them as "unknown → rebuild/ignore," never as corrupt. Per-phase rollback points are in §I.
- **CR-001 phases (additive, per-commit revertible):** P5b (revert the driver; the 5 modules restore), P7b
  (per-group revert behind the façade), **P8c (each behavior change its own revertible RC commit** — the
  v0.18.1 gate is where a real-PC failure triggers a per-change revert), P9b (per-module UI revert; the
  boot/contract checks lock the boundary), P12 (per-item revert), P13 (the evidence mode is inert unless
  invoked). **None reopen committed P0–P9** (RM01).

## M. Work-PC verification → the P13 handoff + v0.18.1 acceptance (CR-001/RM05; §K2)
This is no longer a loose "owed" list — **P13 turns it into a concrete evidence kit + acceptance checklist**,
and **v0.18.1 (§K2) executes it.** Safe, disposable-destination tests only (no disk-full induction — R1-N04):
P1 partial-keeps-last-good on a real refresh; P2 Defender/lock behavior with cleanup; P3 real paused-batch
resume; **P8c** exact `select_report`, CDP-on-demand, cancel-in-recover latency; P10 updater
staging-retry/checksum/swap on a real v0.17→v0.18 update; PA both frozen exes + source ZIP on the work PC;
the evidence-driven PDF/parser fixes (real source PDFs); plus the carried "Done but live-verify owed" P1/P2
audit fixes. **The P13 evidence collector is privacy/credential-safe (RM05):** never auth/profiles/cookies/
DPAPI/credentials; no private outputs/PDFs by default; a user-placed evidence folder + a file-listing
manifest; a manual fallback for locked PCs. Per RM02/RM03 the **P8c code ships in v0.18.0** (offline-proven,
revertible) and its **acceptance is claimed in v0.18.1** — no longer "omit if no O7," because O7 is now the
available v0.18.1 window.

## N. Explicit exclusions (amended by CR-001 + CR-002)
**No NET-NEW features for this branch** (A3/D1/F1 stay parked). **CR-002 exception (CR002-RM5):** P14/P15
**forward-port current-`main` v0.17.2–v0.17.8 already-shipped behavior** (Intersection Detail (PDF) + its
vs-TSN comparison evolution) into the refactored architecture — this is reconciliation of shipped behavior,
**not** a speculative new feature; **unrelated** new features remain deferred. **No `compare_core` behavior/formula/label/layout/return
change** (helpers + counts stay outside it; `min-cost-pairs` stays inside the lock — RM06). No async/plugin/
**framework rewrite; no one-class-per-action; no frontend framework** (RM08); **no ES modules for the UI
unless separately justified AND proven in pywebview/file/frozen modes** (RM08). No generic-parser
unification. No rename of report subdirs, output filenames, `tsn_library` layout, `tsn_load_*` module names,
or settings keys (keys are additive). No updater TLS change; **no runtime signature abstraction / crypto dep
(A03) without an explicit user/procurement decision** (RM06); no signing-on-by-default. **No DPAPI until O2**
(an explicit user decision; optional off-by-default if approved — RM06). No `_safe_join`/`full_snapshot`/
`paths`-init rewrite (R1-N02/R05); no bounded worker queue (A02); no CI trigger change (A05). No
`run_compare`-returns-counts. No conversion of the `check_*.py` suite to a new runner. No disk-full induction
on the work PC. No live-TSMIS / credential / profile / internal-site access in dev (reaffirmed for P8c/P13 —
RM03/RM05). No staging, committing, pushing, tagging, releasing, or AI attribution. **Note (RM01):** the
**destination-ownership marker is no longer excluded** — CR-001 implements it in P12. **Two-tier framing
(RM02):** v0.18.0 is the **offline-validated candidate**; **field/operational sign-off is v0.18.1 only.**

---

*Claude Final v0.18.0 Plan — Ready for User Approval (Codex readiness round 3: READY, no blockers). Phase
statuses in `00-coordination.md`. This is a working planning artifact, not canonical product documentation.*
