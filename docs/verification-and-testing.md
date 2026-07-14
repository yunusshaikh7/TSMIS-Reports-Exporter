# Verification & Testing

How this repo — which has **no unit-test framework** — is actually verified: the
golden `build/check_*.py` guards, the frozen `-SelfTest` gate, the comparison
verification loop against real data, the `#mock` GUI preview, and the still-owed
live-export on the work PC. This doc OWNS the golden-checks catalog and the
verification loops; it links out for the regression-lock internals
([comparison-engine.md](comparison-engine.md)) and CI mechanics
([build-and-release.md](build-and-release.md)).

## The core fact: there is no test framework

There is **no pytest / unittest suite, no coverage tooling**. "True"
verification of behavior is one of two real-world acts:

1. **A live export against TSMIS** (needs a login; exercises the engine end to
   end against the real site), or
2. **Running a consolidator / comparison over real exported files** and checking
   the output.

Everything below is the scaffolding that approximates those two acts when they
can't be run — runnable golden guards, a frozen self-test, an Excel-COM recalc,
and a browser preview of the UI. None of them replaces a live export; they catch
regressions cheaply between live runs.

## The verification ladder

Cheapest/fastest first; each rung catches what the rung below can't:

| Rung | What it proves | Needs | Where |
|---|---|---|---|
| **Byte-compile** | nothing imports-broken | python only | CI `compileall` |
| **Golden `check_*.py`** | engine / GUI-bridge / updater / compare-engine / parsers locked | `build\.venv` python; no login, no browser (except fake-site), no Excel, no network | local + CI (blocking) |
| **Fake-site selector contract** | the live-site JS/selector predicates still match real DOM | a drivable headless Chromium/Edge (skips cleanly if none) | `check_fake_site.py`, CI |
| **COM-recalc compare verification** | the formulas/values flavors agree and every SELF-CHECK reads OK after F9 | real Excel installed (dev PC) | `%TEMP%\tsmis_regress\com_verify.ps1` |
| **`#mock` GUI preview** | `scripts/ui/` renders + behaves without launching the app | preview HTTP server on port 8765 | `Claude_Preview` / browser |
| **Frozen `-SelfTest`** | the **pruned frozen bundle** still runs every code path | a build (`build.ps1 -SelfTest`) | release gate, CI release.yml |
| **Live export on the work PC** | the only proof the engine works against the real TSMIS site | the locked-down Caltrans work PC + a login | **STILL OWED** (see below) |

The dev PC cannot reach the TSMIS intranet host, so rungs 1–6 are everything that
can run off the work PC; the top rung is owed work (see
[Live-export verification is owed](#live-export-verification-is-owed-on-the-work-pc)).

## Golden `check_*.py` catalog

Plain runnable guards (no login). **Run the whole suite with one command** (the
same globbed set CI runs; `check_ci_manifest.py` guards the workflow list against
drift, so the glob IS the canonical list):

```
build\.venv\Scripts\python.exe build/run_checks.py           # stop on first failure
build\.venv\Scripts\python.exe build/run_checks.py -j 4 -k   # parallel, keep going
```

One check at a time (e.g. while iterating on it):

```
build\.venv\Scripts\python.exe build\check_<name>.py
```

### Comparison audit Phase-1 safety checks

| Check | Safety contract |
|---|---|
| `check_compare_overwrite_consent.js` | Classic both-mode uses an exact-path, single-use server token before replacing an existing derived values twin; decline, mismatch, and replay never launch. |
| `check_artifact_store.py` | Source/output alias rejection, exclusively reserved identity-bound workbook temps, target-aware commit guards, and reparse/replacement-safe promotion journals/recovery. |
| `check_owned_dir.py` / `check_reset_safety.py` | Create-only purpose markers, exact leases, exclusive staging, linked/replaced descendant refusal, and preview-bound Reset quarantine with real Windows junction probes. |
| `check_matrix_ownership.py` | Everything Matrix comparisons/store dual-lease routing, unknown/link/replacement refusal, guarded cache/consolidation/PDF scratch/evidence; Day/Baseline stay app-private. |
| `check_evidence_literal_cells.py` | Evidence source text beginning `= + - @` or equal to any Excel error token remains byte-exact STRING data. |
| `check_visual_evidence.py` | Source-safe and lease-bound evidence workbook/image temp, fallback, swap, rollback, and cleanup transactions. |
| `check_matrix_tsn.py` / `check_day_matrix.py` / `check_persistence.py` / `check_validation.py` | Versioned explicit TSN selection identity, five PDF-to-base aliases, path-only migration blocking, and no silent canonical fallback after deletion/replacement. |
| `check_evidence_bundle.py` / `check_validation.py` | Shared credential redaction plus final all-member ZIP scanning (metadata, UTF-16, raw/nested Office bytes) with prior-good preservation on rejection. |

Phase-1 close (2026-07-11): discovery is 92 Python checks + 5 Node checks +
`compileall` = 98 runner entries; `build/run_checks.py -j 4 -k` passed 98/98.

### Comparison audit Phase-2 typed-outcome checks

| Check | Typed truth contract |
|---|---|
| `check_comparison_contract.py` | Canonical validation/round-trip invariants for `SourceIdentity`, `LoadedSide`, `ComparisonCounts`, `ComparisonOutcome`, `ArtifactGeneration`, and `AttemptState`; also locks public terminal normalization for error, cancellation, and `no_data`, including the rule that a no-artifact result has no invented generation. |
| `check_comparison_outcome.py` | `run_compare` produces exact typed counts/completion/verdict for match, diff, one-sided, partial, and structured failure inputs without parsing summary prose. |
| `check_compare_input_outcomes.py` | Direct-file adapters consume coupled producer outcomes and preserve exact complete/partial/skipped/failed coverage. The real file and folder public boundaries additionally return typed fail-closed outcome/attempt state for missing inputs, malformed-shape/preflight errors, overwrite cancellation, blocked non-comparable inputs, and artifact-commit failure, with no fabricated `ArtifactGeneration`. |
| `check_compare_env_pdf_completion.py` | All five PDF environment families carry both sides' completion and diagnostics into the comparison before publication; returned and persisted truth agree. |
| `check_comparison_sidecars.py` | Strict schema-v2/v3 single/multi-member sidecars, SHA-bound peer validation, malformed/tampered/stale rejection, crash-safe no-replace chunks, bounded fallback slots, parent-scoped local/subprocess serialization, exact-winning-generation checks, sentinels, and all-member-safe interruption recovery. |
| `check_comparison_payload_resources.py` | The 64 MiB/16-chunk/32:1 schema-v3 resource policy, pre-zlib bomb rejection, peer/workbook validation before exactly one shared decode, streamed canonicality, tamper rejection, and inline schema-v2 compatibility. |
| `check_comparison_sidecar_scale.py` | The real 41,000 exact-duplicate-trace shape crosses the legacy 16 MiB inline boundary, publishes as five schema-v3 chunks, round-trips every trace in both peer orders, and rejects reordered/duplicate descriptors. |
| `check_comparison_publication.py` | The production `commit_workbook` path publishes formulas/values/both generations and matching succeeded attempts; interrupted metadata remains untrusted. |
| `check_phase3_canary_payload_evidence.py` | The production canary requires schema v3, binds persisted truth to the returned generation, records every shared chunk exactly once, rejects orphan payloads/sentinels, and prevents case-insensitive artifact-key loss. |
| `check_consolidate_worker_publication.py` | Generic workers do not race or overwrite comparison-owned generation publication. |
| `check_classic_comparison_outcome.py` | Classic dialogs use trusted typed completion/verdict, reject returned/persisted disagreement, and title comparison failures correctly. |

The terminal contract and artifact contract are intentionally distinct. A public comparison that
returns without committing a workbook still has a `ComparisonOutcome` and terminal `AttemptState`,
but `artifact_generation is None` and `attempt_state.generation_id == ""`; no sidecar is expected.
Strict artifact consumers continue to require a real committed generation and matching persisted
member metadata. These checks do not close the deferred Phase-5 Matrix formula-twin/provenance/
attempt-overlay work or the Phase-7 exact-generation evidence transaction.

Phase-2 current gate (2026-07-11): discovery is 100 Python checks + 5 Node checks +
`compileall` = 106 runner entries; `build/run_checks.py -j 4 -k` passed 106/106.
On local Windows shells, set `$env:PYTHONUTF8='1'` before the command so diagnostic
symbols cannot be rejected by a cp1252 console.

### Comparison audit Phase-3 equality, publication, and production gate

Phase 3 closed on 2026-07-12. The complete offline runner passed 119/119 and the
comparison-specific `check_compare*` selection passed 31/31. The clean installed-Excel
production canary `CORE-ID-78-XLSX-TSN-2026-07-12-r3` then reproduced the independent
oracle exactly: 16,199 paired rows, 260/427 one-sided rows, 16,053 differing rows,
21,675 differing cells, 518,368 asserted cells, and 106 exact duplicate groups. Its
218-member raw-input manifest SHA-256 is
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`; the accepted
production result SHA-256 is
`a54448f621beb27cea4e4b7a82af1b0a65580e84c5eac6df313242959a1111b2`.

The accepted formulas and values peers carry one strict schema-v3 comparison generation,
small member envelopes, and one bounded shared compressed payload. The canary rehashed
all 15 artifacts and all 11 production source files, strict-read both peers as
trusted/current, verified installed-Excel formula/value parity, and found no publication
sentinels or owner locks. Full hashes, paths, payload/chunk identity, and Excel counts live
in [planning/comparison-perfection/comparison-canary-bindings.md](planning/comparison-perfection/comparison-canary-bindings.md). Phase 4
must treat this as the pre-change freeze, not as an oracle for known-wrong loader identity
or parser behavior.

### Comparison audit Phase-4 source progress and Stage-5 lifecycle close

Current verified boundary on 2026-07-12:

- `check_tsn_raw_source_contract.py` passes exact-one statewide admission, owner-lock
  exclusion, stale-reuse invalidation, exact RD/ID/HD headers, sole visible `Sheet 1`,
  extra visible/hidden sheet rejection, formula/error rejection, mandatory row claims,
  explicit complete outcomes, and both Summary exact-one paths. It also proves immutable
  captured parsing under transient A→B→A mutation, last-good preservation on persistent
  mutation, the final atomic commit source guard, snapshot cleanup, and exact builder
  manifest certificates.
- The same strict loaders read the authoritative workbooks as exactly 15,410 Ramp,
  16,626 Intersection, and 60,083 Highway Detail rows. A real Ramp blank `PR` corrected
  an initially over-strict fixture: blank prefix is a retained claim, not missing truth.
- `check_tsn_highway_log_isolation.py` passes custom-root containment, two interleaved
  attempts, exact generated-member manifests, cancel/fail/retry/guard-loss cleanup, and
  global/foreign sentinel survival.
- `check_tsn_district_source_contract.py` passes sole internal district identity,
  title/group consistency, optional filename agreement, exact unique D01-D12 universe,
  canonical content manifests, preserved-mtime replacement rejection, unowned-row and
  malformed-group rejection, build-time source mutation, commit cancellation, and
  no-publication behavior for missing/duplicate/extra/failed members in both Highway Log
  and Highway Sequence. Partial r3/r4 were stopped on those defects and remain rejected.
- A second witness/consumer review reopened CMP-AUD-035 before r5 completed. Its new
  permanent gates are green: raw removal/unreadability/ambiguity and legacy/foreign
  consolidated sources stop both matrices; real complete-sidecar failure cannot certify
  TSN success; post-predicate mutation cannot return success; and the freshness suite's
  stub emits the exact builder manifest.
- `check_phase4_tsn_rebaseline_runner.py` proves the real public build/sidecar/current/
  unchanged-reuse lifecycle under isolated paths, final global raw/evidence re-scan,
  code provenance recheck, exact generated workbook+sidecar universe, and atomic refusal
  of partial results. The combined 13-check compatibility sweep and `compileall` passed,
  but a third review rejected r6 on preserved-mtime normalized-workbook replacement and
  raw drift after `ensure_current`; r3-r6 remain rejected audit attempts, not witnesses.
- `check_tsn_status_coherence.py` permanently closes the status/reuse false greens. It
  injects preserved-mtime raw, normalized-workbook, and sidecar mutations after the
  initial and first revalidation reads; requires two full coherent revalidation passes;
  rejects partial/nonzero producer outcomes; proves Settings cannot show them current;
  and proves a valid rebuild heals the state without manufacturing completeness.
- `check_tsn_canonical_consumer_identity.py` permanently closes the consumer boundary.
  It covers synchronized A-to-B-to-A and persistent normalized-workbook drift, one
  identity-checked attempt-local capture shared by comparison/formulas/evidence, exact
  explicit-PARTIAL propagation through capture-local structured outcome metadata,
  identity-bound cleanup, mandatory target-lease bindings, and exact-token Everything/
  by-day caches. No temporary capture pathname is persisted in comparison metadata.
- The clean `raw-2026-07-12-r2` pre-hardening baseline built all seven normalized datasets
  with explicit `complete`, zero skipped/failed inputs, zero suspicious events, zero
  leftover Highway Log scratch directories, and zero writes to the former global
  intermediate boundary. Result SHA-256:
  `1e9e6e689589f5a30eb32899ed163abffc00e73889806a2a8775179df9fd4e25`.
  It predates Highway Log v4, Highway Sequence v3, and the final manifest/snapshot/token
  contracts, so it remains the pre-hardening semantic baseline rather than current-code
  lifecycle proof.
- The accepted current-code `raw-2026-07-12-r7` result is schema v2,
  `acceptance=complete`, 7/7 families complete with zero skipped/failed inputs, coherent
  current tokens, and certified unchanged immediate reuse. Its result SHA-256 is
  `b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa`;
  code provenance is 28 members / 867,593 bytes /
  `aee75325c5268e097c0fc389148b65a8ad97564ae314751e90e51062628dbfa7`,
  and its exact 14-workbook/sidecar universe is 20,794,592 bytes /
  `56fd098c268f14951ba5b860205ed5d9a40aad4aa809237726f5700fc951f3c4`.
- An independent read-only r2/r7 stream covered every sheet name, cell type, and all
  5,547,205 cell values in the seven workbooks and found zero differences. The hardening
  changed certification and consumption behavior without changing normalized facts.
- Stage 5 does not certify mutable live PDF reads. Stage 10 still must capture and
  manifest the exact TSMIS/TSN PDF read sets used by visual evidence so same-object and
  A-to-B-to-A content interposition cannot pass; that residual does not reopen
  CMP-AUD-035's normalized-workbook closure.
- `check_comparison_contract.py` and `check_compare_pairing_policy.py` pass the shared
  typed-identity and legacy pairing core. Family projector identity integration remains
  intentionally red and is owned by later family remediation after source conservation.
- Ramp v3 and Intersection v2 are accepted full-corpus XLSX-to-PDF permanent gates with
  exact source/script/result hashes and zero unresolved residue. Ramp proves 15,410
  records, 15,404 extracted exact plus six clip equivalents, an exact four-item
  `(cid:13)` contract, all Summary totals, and one disposition for all 18 XLSX fields.
  Intersection proves 16,626 two-line records / 598,536 assertions, directional PDF-only
  date flags, the measured exact 32-character Description boundary, one exact source
  delta, all Summary conservation, and Report View source mapping.
- Highway Detail's accepted 12-PDF / 4,123-page XLSX-to-PDF oracle binds 60,081 printed
  records to 60,083 XLSX rows, two exact XLSX-only occurrences, and an exact 443-item
  dated-delta manifest with zero unexplained residue. No source-date difference by itself
  blesses a value delta; Stage 6 independently reclassified one Length item as a current
  raw-to-r7 product defect because exact raw Decimal and the PDF agree.

Stage-6 raw-to-normalized conservation now adds a stricter family acceptance layer:

- `phase3_xlsx_stream.py` captures compressed workbook bytes privately before ZIP/XML
  parsing, requires coherent pre/capture/post identities, rejects error-typed cells while
  preserving literal error-looking text, and passes an actual same-object A-to-B-to-A
  mutation fixture in `check_phase3_xlsx_stream.py`.
- Ramp Detail's corrected 15,410-row result has SHA-256
  `3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd`; its detached
  acceptance has SHA-256
  `2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb`. They bind the final
  result, raw/r7 sources, sidecar, lifecycle witness, generator, reader, and post-write
  identities. All 14 invariants and six mutations pass, and two full replays are
  byte-identical. The exact projection residue is 15 numeric Description prefixes—nine
  same-route and six different-route. Audit is true while projection/full conservation
  remain false for the documented omitted/changed product facts.
- Intersection Detail is accepted over all 16,626 rows with 24/24 invariants and 25/25
  mutations. Result SHA-256
  `4d507661835cdd9e9267f05f7700777ba97b8a3948797ac3e436be8db8d21b88` and detached
  acceptance SHA-256
  `7077358da9ca016c12a4d1bc2cf8e09c95b20ac588272febf9b307f5856c7b43` bind the same
  lifecycle/code boundary. Numeric-PM collision facts are canonical rather than display-
  formatted; three omitted source fields keep full conservation false.
- Highway Detail is accepted over all 60,083 rows with 23/23 invariants, 22/22 mutations,
  and zero unexplained residue. Result SHA-256
  `283315b30605461e748246444ea523542f61b0a205cd70131c73e1f6b77fb20b` and detached
  acceptance SHA-256
  `d26dee5d11517478312cde6361c4567c30a4f8d534d822539bb36388c170cf03` bind the result
  plus eight post-write source/provenance/code identities. Audit is true; projection/full
  remain false for three documented product findings. CMP-AUD-141/CMP-AUD-143/
  CMP-AUD-147 are closed in the harness, not in product normalization.
- Ramp Summary is accepted from its authoritative three-page PDF through all 31 r7 rows.
  Result SHA-256 `38b500489c8a310529c4c7b76bea3fe7461374d6c786b992caaa458e0ef65421`
  and detached acceptance SHA-256
  `55c43d501960d3ca3702e5eac1202f96ac6c9b3e1df2eb915b19c593669bf74c` pass 18/18
  invariants, 13/13 mutations, exact 13-role coverage, 95 loaded parser modules, and 103
  live identity rehashes. Projection is exact/zero-residue; full conservation remains
  false only for CMP-AUD-146 printed provenance loss.
- Intersection Summary is accepted from its authoritative three-page PDF through all 58
  r7 rows. Result SHA-256
  `f3a0aa0dfb15cf2ca911ec98721c8dcc0d5d9b25c0ce3cc89184d2959aaf64de` and detached
  acceptance SHA-256
  `cdf63defdb62d2066a2cafb7229d0c1539a0c6d90f80ea1b96c07c77f609b703` pass 19/19
  invariants, 17/17 mutations, 62 source dispositions, 58/58 typed category ledgers,
  137 loaded modules, full-result JSON round-trip, and independent visual/lifecycle
  review. Projection is exact/zero-residue; raw-granularity full conservation remains
  false for CMP-AUD-144/CMP-AUD-145/CMP-AUD-146.
- Highway Sequence is accepted from all 12 authoritative PDFs / 1,540 pages through
  69,804 source records and 69,758 r7 rows. Result SHA-256
  `bdd344258ced0e138196c518be2d49ee058f5f9c0f52dea860c328fc3216d1e2` and detached
  acceptance SHA-256
  `71fe59a5f4676d3b935bcbea380374b14fdccfd77b674ea88148fa18760ffde2` reproduce
  byte-identically across two full replays and pass 22/22 invariants, 14/14 mutations,
  exact page/metadata/role claims, 47 loaded parser modules, and zero unexplained
  residue. Audit is true; projection/full remain false only for the exact
  CMP-AUD-155/156/158/159 source dispositions.

Stage-8 base comparison auditing is complete at 7/7 families. The final Highway Log
gate binds the 252-file Excel and 252-file PDF current TSMIS trees, the accepted
12-PDF/60,083-row TSN chain, an independent projection oracle, and both complete product
publication legs. Excel-vs-TSN is 48,094 paired / 3,790 Excel-only / 11,989 TSN-only /
39,466 differing rows / 140,333 differing cells; PDF-vs-TSN is 48,096 / 3,790 / 11,987 /
39,463 / 139,786. Each leg's 989 duplicate-assignment groups match the independent
oracle exactly. Two clean final-gate roots reproduce the same 9,036-byte result SHA-256
`7acf9986055750bbc49be0d4fa422329d06893f379da0cd6ded945936549860b`
and 839-byte acceptance SHA-256
`170d622d751e96e97c7f8420c0a60172e57a31838a3d1b3de090c76972dd62b6`.
This accepts only the base audit: product comparison, physical-source identity,
workbook/evidence, and end-to-end perfection remain false under the documented findings.
No product code was changed during this closeout; implementation and Stages 9–12 are
deferred to [the implementation handoff](planning/comparison-perfection/comparison-implementation-handoff.md).

`.github/workflows/checks.yml` runs them **blocking** on every push/PR (after a
`compileall` of `scripts build version.py`). CI forces `PYTHONIOENCODING=utf-8`
because the comparison checks print the ` ≠ ` diff marker, which a Windows cp1252
stdout (the runner default) would crash on. Three lint/audit steps (ruff
`E9,F63,F7,F82`; bandit `-lll -iii`; pip-audit) run **advisory** (never block).

### Engine / GUI / updater (the "og" set)

| Check | Locks |
|---|---|
| `check_export_engine.py` | WS1/WS3 audit-fix hardening: integrity helpers (XLSX `PK` / PDF `%PDF` magic), empty-marker predicates incl. Highway Sequence's positive "No results found" marker, `cs-disabled` detection in `select_report`; the Phase-3 fixes — `require_site_params` env backstop, the retry-once-then-empty path (`_process_route`), `report_error_text` logging; **v0.18.1** — `data_value`-first selection match (`test_data_value_match`), nested-`cs-submenu` disabled detection (`test_nested_disabled`), and `wait_js` config-error validation (`test_wait_condition_validation` over `_build_wait_condition`); **v0.19.3** — the per-route stale-form guard keys on the stable id (`test_ensure_report_armed`: a grouped-menu leaf whose visible label is the short "Detail" does NOT re-arm when the armed `data_value` matches, a different armed id DOES, and an unreadable id falls back to the label text). Pure Python, no browser. |
| `check_parallel_reconcile.py` | Phase-3 parallel-engine reconciliation (`_reconcile_unaccounted`): lock-tolerant `_can_resume` (not read-strict), and reconcile-on-crash-even-if-cancelled. |
| `check_intersection_gate.py` | the app-wide export-disable gate (`DISABLED_EXPORT_SUBDIRS`): **empty as of v0.19.1** — every export report enabled (Highway Detail/Summary's export went live from the v0.18.1 reserved groundwork). Locks (a) the default all-enabled state and (b) the gate MECHANISM still works: a subdir re-added to the set is SHOWN greyed (per-report `disabled` flag) rather than hidden, `enabled_export_reports`/`report_library_info`/matrix exclude it, and `start_*` reject it by its stable export-op key server-side (P3 — selection travels by key, not index). (The gate formerly held Intersection [enabled v0.16.1/v0.17.0], then the reserved Highway pair [v0.18.1], now empty.) |
| `check_report_recipe.py` | The "add a report family" recipe is executable, not just documented. Highway Detail/Summary retain stable ids 8/9 and real export specs; Highway Detail is now fully consolidated/compared while Highway Summary remains export-only. Also proves catalog derivation, a small shared TSN comparator, and the PDF-table writer. |
| `check_validation.py` | One-click validation runs on-disk samples through the real Matrix path; accepts only a strict returned/persisted generation; records explicit OK/partial/untrusted/failed/cancelled/blocked buckets; forwards worker failures; returns the actual ZIP member count; records only safe counts/outcomes/folder names; excludes phantom `_tsn_input`/`comparisons` environments; honors comparison cancellation; redacts the shared credential grammar; heals supported canonical TSN libraries; and blocks every missing explicit TSN selection instead of falling back. |
| `check_coalesce_editions.py` | **v0.19.2:** dual-edition coalescing. `_coalesce_groups` pairs same-`data_value` editions (keeps solos + order); the page-rebuilding PDF Print save is ordered LAST (`_save_rebuilds_page`); `_process_route_combined` clicks Generate ONCE then saves every edition, landing the shared outcome in each edition's result and notifying the UI once; an empty route saves nothing (both empty), a site error fails both (no partial); `run_export_combined` rejects <2 editions or a `data_value` mismatch. Faked page — no browser. |
| `check_fake_site.py` | Selector contract via a **real headless browser** over authored synthetic HTML fixtures (`build/fake_site/*`) that reconstruct only the contract-bearing DOM (the shared action bar, per-report empty states, `#rampResults` error box, `#customReport` dropdown). Catches selector drift pure Python can't — e.g. `EXPORT_READY_JS` keying on a button's *text*, not the bare `.export-btn` class shared by Print. **v0.18.1** adds `dropdown_nested.html` (the synthetic flat→nested `cs-submenu` report menu) with `test_nested_menu` + `test_env_scan_probe`, proving selection by `data-value` + the fly-out reveal on the new menu. **v0.19.3** adds `test_current_report_value` (the fixtures now carry the real hidden `<select id="reportSelect">`): the per-route re-arm guard reads the armed report's stable id from it — proven to return `intersection_detail` after selecting that grouped leaf even though the leaf's visible text is only "Detail". Fixtures are AUTHORED reconstructions, **not** copies of the Caltrans-internal source. Prints SKIPPED and exits 0 if no Chromium-based browser is drivable. |
| `check_gui_bridge.py` | `gui_api` bridge methods. Its "dialog blew up" traceback is an **intentional** test fixture — the run still reports `[OK]`. |
| `check_updater.py` | WS4 updater hardening (incl. `test_resolve_previous_release` for the v0.13.0 revert). Updater swap/SHA detail is owned by [build-and-release.md](build-and-release.md). |

### Comparison engine (correctness-locked `compare_core`)

These lock `compare_core.py` and the consolidators. The default gates are pure
openpyxl/pdfplumber — no Excel, browser, or network — with explicit optional installed-Excel
and external-corpus tiers. The correctness-lock contract (preserve correct output; explain and
re-bless every deliberate fix) is owned by [comparison-engine.md](comparison-engine.md).

| Check | Locks |
|---|---|
| `check_compare_blankkey.py` | blank-key-field self-check path |
| `check_compare_keyfield.py` | key-is-NOT-always-first-column (PM-keyed Highway Sequence / Ramp Detail vs coarse County) |
| `check_compare_skipwarn.py` | skipped-files-still-match + consolidate-xlsx partial-OK (incompleteness contract) |
| `check_compare_injection.py` | shared literal-cell guard (`= + - @` and every Excel error token stored as TEXT) on compare_core + consolidators |
| `check_compare_coercion.py` | `compare_core.normalize_value` value coercion (dates → ISO) |
| `check_compare_limits.py` | Excel row/column-limit overflow + side-name⇄sheet-name collision guards |
| `check_compare_audit.py` | audit-round hardening across compare_core + compare_env |
| `check_compare_equality_policy.py` | Phase-3 E1 authority: typed Python decisions; `E`/`D`/`N`/`U` formula/value masks; case, Boolean, ASCII-space-only TRIM, blank/zero, literal marker/error tokens, exact finite numeric text (Decimal scale/exponent + float notation), NaN/infinity fail-closed behavior, Med-Wid helpers, Summary/Spot/CF marker independence, formula length, and physical width. `--excel` performs the installed-Excel full-rebuild parity gate. |
| `check_compare_build_freshness.py` | Very-hidden E2 source/helper snapshots, row/tail sentinels, and the Summary certification wrapper. `--excel` mutates ordinary values, identity keys, opaque helpers, duplicate order, and row presence; every mutation must force `REGENERATE REQUIRED`, including a swap that creates phantom live observations. |
| `check_compare_pairing_policy.py` | Independent exhaustive rectangular oracle, lexicographic smaller-side tie rule in both orientations, retained greedy traps, strict malformed-matrix rejection, exact `1×100,000` boundary, fail-closed `317×316`/`317×317` cap behavior, full typed traces/diagnostics, and opaque delimiter-collision resistance. `--excel` recalculates the pipe-bearing identity fixture and requires every Summary self-check to remain `OK`. |
| `check_compare_cancellation.py` | Cancellation during source validation, exact cost construction, Hungarian scans, above-cap positional fallback, and typed diff counting returns cancelled/unknown with no trace or output; an approved existing output stays byte-exact. False polling is assignment/count equivalent. |
| `check_medwid_formula_prototype.py` | Independent narrow Med-Wid grammar/prototype over all printable suffixes plus fuzz; proves the staged legacy formulas stay exact and below Excel's formula limit. |
| `check_read_counts_layout.py` | Diagnostic workbook reader sums the unique numeric `Diffs` column by header and never scans rendered marker text. |
| `check_phase3_independent_oracle.py` | Standalone comparison oracle primitives that do not import production equality/key/pairing code. |
| `check_phase3_xlsx_stream.py` | Hardened stdlib XLSX reader: exact namespaces/schema, formula/error rejection, ZIP/XML limits, encoding/DTD/entity rejection, bound-file identity checks, and typed scalar policy. |
| `check_phase3_intersection_detail_oracle.py` | Independent current-schema Intersection Detail adapter/oracle: exact 35/36-column shapes, route provenance diagnostics, report numeric seam, selector manifest, and duplicate trace. The real statewide runner binds source/runtime/evidence hashes. |
| `check_phase6_ramp_detail_conservation.py` | Permanent synthetic Stage-6 Ramp gate: independent schemas/dispositions, typed order/multiset digests, impossible-date refusal, verbatim raw Description conservation, exact 15-row loss manifest, physical identity/collision census, and physical-row-contiguity acceptance. |
| `check_phase8_ramp_detail_comparison.py` | Permanent Stage-8 Ramp Detail source/comparison gate: exact D4 `(Route, County, norm_pm(PM))` identity and collision census; District/PR/PM_SFX assertions; all 15 numeric Description prefixes; duplicate occurrence pairing; strict PM/date rules; TSMIS/TSN PDF header, prefix, page, and render classes; malformed/formula XLSX rejection including physically omitted trailing blanks; raw/normalized product equivalence; package volatility; and fail-closed detached acceptance/rejection. The 1,703,996-byte result SHA `6cdf3ad5…f556` and 13,473-byte acceptance SHA `77b3af5f…bd64` reproduced byte-identically across two full five-leg runs; 36 assertions pass while CMP-AUD-045/133/135/185 remain deliberately product-red. |
| `check_phase8_intersection_detail_comparison.py` | Permanent Stage-8 Intersection Detail source/comparison gate: approved `(base Route, County, complete PP, numeric Post Mile)` identity versus weak Route+PM masking; District/County/explicit Route/physical `S` claims; exact 217+217 TSMIS member and 1,844-page PDF census; raw/normalized source-only Report View fields; PDF-vs-TSN Report View capability; all five formulas+values legs, sheet universes, snapshots, paired-cell/one-sided ledgers, per-sheet formula tags, consolidation blank serialization, per-document PDF grids, tabs, and vestigial-cell behavior. The 1,059,072-byte result SHA `7c7734aa…d86c` reproduced byte-identically across two full runs; both detached acceptances pass and differ only by result path. All 24 audit invariants and 31 permanent assertions pass while CMP-AUD-045/068/070/133 remain deliberately product-red. |
| `check_phase6_ramp_summary_conservation.py` | Permanent Stage-6 Ramp Summary gate: typed order/multiset and 31-row shape, four independent 15,410 totals, exact 13-role disposition universe, same-version loaded-parser drift, and detached acceptance/open-finding/post-write rejection semantics. |
| `check_phase8_ramp_summary_comparison.py` | Permanent Stage-8 Ramp Summary base-comparison gate: strict integer counts; exact suffixed/unique/ordered route universes; Summary PDF↔Excel and Summary↔Detail count mutations; P/V residual proof; TSN order/duplicate/type drift; the exact P/V/footnote semantic-gap set; XLSX stability that excludes only `docProps/core.xml`; formula/literal semantic drift; and fail-closed detached acceptance. Full oracle result `f05bad6e…f3ba2` passes 22 invariants and two byte-identical source-bound replays. |
| `check_phase6_intersection_summary_conservation.py` | Permanent Stage-6 Intersection Summary gate: 62→58 exact projection, six-to-one J–P→S fold, 58/58 per-category typed digests including Total, geometry/raw-only/sidecar/r7-output mutations, semantic label visibility, and ordered/multiset truth. |
| `check_phase8_intersection_summary_comparison.py` | Permanent Stage-8 Intersection Summary base-comparison gate: strict typed counts and partitions; exact 217-route suffix/drop/duplicate/order/170 behavior; Rural/Urban parent/orphan rules; distinct J–P fold versus repeated-row rejection; PDF header/band/route/provenance mutations; all 14,322 Excel/PDF paired values; TSN/TSNR drift; `core.xml`-only package volatility; formula/literal semantics; structural absence; and detached acceptance/rejection. Full oracle result `7e4aceba…a7bd` passes 12 source + 24 audit invariants and two byte-identical direct-authoritative replays. |
| `check_phase6_highway_sequence_conservation.py` | Permanent Stage-6 Highway Sequence gate: exact 12-PDF plus named-placeholder role universe, typed r7 terminal, per-owner printed pagination, exact-one page-header roles, member-specific PDF metadata/time claims including D12's unequal timestamp pair, stable detached identity, field dispositions, and semantic mutation detection. The full oracle separately binds all 1,540 pages and 69,804 source records. |
| `check_compare_ramp_detail.py` | cross-env Ramp Detail PM re-key (planted mid-list insert isolates one new row) |
| `check_compare_ramp_summary.py` | cross-env Ramp Summary route-keyed compare + route-key normalizer (unpadded `5` == zero-padded `005`) |
| `check_compare_highway_sequence.py` | cross-env Highway Sequence adapter end to end: PM key, "Highway Locations" sheet, `(col X)` unnamed-column labels (the stage-1 audit gap) |
| `check_compare_env_highway_log_pdf.py` | **cross-env Highway Log (PDF)** (v0.17.0): the adapter wiring (flat_pdf_loader + sheet_name/force_header = the corrected HL header), the matrix env mode flipped from greyed to supported (matrix_rows + _row_modes, HL-PDF kept last), and end-to-end (via a stub PDF loader) that the flat-PDF path yields a Route+Location-keyed Highway Log comparison flagging a genuine cell diff — see [comparison-engine.md](comparison-engine.md) §9c |
| `check_compare_env_intersection.py` | **cross-env Intersection Summary + Detail** (v0.17.0): both adapters' wiring (Summary AGGREGATE-per-route via side_loader/agg_header; Detail flat with key_col "Post Mile"); their promotion to full matrix rows (in COMPARE_REPORTS + matrix_rows, the TSN-only extra-rows list now empty); and end-to-end that the Summary aggregate path keys on Route (one per-route diff), and the Detail flat path keys on Route+Post Mile (a non-key cell diff flagged), each emitting the env-labelled workbook — see [comparison-engine.md](comparison-engine.md) §9c |
| `check_compare_ramp_detail_tsn.py` | **vs-TSN Ramp Detail** (v0.17.0 reference FLAT recipe): PM key + route-from-LOCATION + PM/date/desc normalization, position-based TSMIS-consolidated loader, mid-list-insert key collapse, and the `context_fields` (TSN-only cols) contributing ZERO diff cells — see [comparison-engine.md](comparison-engine.md) §9c |
| `check_compare_ramp_summary_tsn.py` | **vs-TSN Ramp Summary legacy/product-red behavior fixture, not the business oracle:** it currently locks missing-column→0, P/V as shared 0-vs-N, and the no-linework metric in *Only in TSMIS*. Stage-8 source truth supersedes those semantic expectations: 29 shared, P/V `Only in TSN`, and no-linework display-only/excluded from verdict. Update this fixture with CMP-AUD-024/025 remediation; retain its valid Category/Count, statewide aggregation, and familiar-sheet coverage. See [comparison-engine.md](comparison-engine.md) §9d. |
| `check_compare_intersection_summary_tsn.py` | **vs-TSN Intersection Summary product behavior fixture:** 65 taxonomy rows plus Total after folding raw CONTROL J–P into shared Signalized; unique keys/slugs; no TSN-only comparison rows; eight genuine TSMIS-only rows; `+ no data` buckets compared; the spec-driven block-walk mapper (incl. Rural/Urban `-O` parent disambiguation); and end-to-end **58 both / 8 only-TSMIS / 0 only-TSN**. The accepted Stage-8 source oracle now supplies the independent real count: TSMIS 16,459 vs TSN 16,626, 53 differing + 5 identical shared rows. Keep this fixture, but do not use its shared product mapper as its own oracle; see [comparison-engine.md](comparison-engine.md) §9e. |
| `check_compare_intersection_detail_tsn.py` | **vs-TSN Intersection Detail** (July-2026 shape): exact raw header order + old-format refusal, 33 shared fields ending `Xing Line Lgth`, normalization/crosswalk behavior, and typed Report View truth. Its adversarial view fixture proves complete/no-duplicate field coverage, ASCII-space equality, case sensitivity, literal marker content, blank/zero, context, hard/soft styling, and the full Diffs total on both physical rows. |
| `check_compare_highway_sequence_tsn.py` | **vs-TSN Highway Sequence** (v0.17.0 FLAT, the LAST report): the **county-relative** composite key (`key_normalizer` → "COUNTY POSTMILE"; the same postmile in two counties is NOT confused), county trailing-period strip (`LA.`→`LA`), prefix/PM/suffix re-glue, description route-prefix strip + whitespace collapse, the position-based TSMIS-consolidated loader, the TSN PDF parser's pure helpers (x-window bucketing, 2-char flag split, route/location regex), and end-to-end that FT + Description are genuine diffs while HG/City/Distance (context) contribute ZERO — see [comparison-engine.md](comparison-engine.md) §9g |
| `check_compare_highway_detail_tsn.py` | **vs-TSN Highway Detail**: roadbed-aware Post Mile identity, PS as a compared field, all report normalizations, raw/normalized idempotence, and typed Report View truth. The view gate proves complete/no-duplicate field coverage plus ASCII-space, case, literal-marker, blank/zero, context, styling, and repeated two-row count parity. |
| `check_highway_detail_pdf.py` | **Highway Detail (PDF) pipeline** (v0.20.0): the 34-column header pinned to `highway_detail_columns`, the line1(10)+line2(25)→34 mapping, the line-1 postmile classifier (accepts every real PM shape; rejects DCR group rows + page furniture), and the compare-adapter + matrix wiring (PDF↔TSN / PDF↔Excel side labels, `_pdf_self_comparator`, `_pdf_store_consolidator`, the 3-mode row) |
| `check_visual_evidence.py` | Render-free visual-evidence contract across Highway Detail, Intersection Detail, Highway Log, Highway Sequence, and Ramp Detail (Excel/PDF rows): source routing, LOCKSTEP parser pins, projections/diff enumeration, TSN sidecars, unpredictable keep-last-good workbook/image transactions, source-alias checks, and target-aware lease/rollback boundaries. The frozen self-test covers raster rendering. |
| `check_consolidate_intersection.py` | **Intersection Detail + Summary consolidators** (v0.17.0): Detail (thin `consolidate_xlsx` wrapper — subdir/sheet/filename + 2-route consolidation, leading Route column); Summary (block-walk category summer — per-route columns sum across routes, Combined statewide total) |
| `check_no_misspelling.py` | **Product-name guard** (blocking): fails the build if the "TSMIS" transposition appears anywhere in tracked source/docs — the name is always TSMIS |
| `check_matrix.py` | the 12-row comparison-matrix engine, strict sidecar truth, cache generation/output-identity/fingerprint binding, stale/retryable partial and missing-cache states, stable dateless paths, hidden row/env filters, scoped rebuilds, and real cross-environment orchestration with planted typed counts cached |
| `check_matrix_tsn.py` | the multi-mode / TSN engine: per-row mode registry (env / vs-TSN / PDF-vs-Excel; HL is two rows), TSN source detection (file > consolidated > PDFs > none), snapshot mode + greyed unsupported cells, `build_comparison` guards |
| `check_matrix_bridge.py` / `check_mx_partial_render.js` | the matrix `gui_api` bridge (stubbed workers), every method and queue invariant, plus fail-closed cell rendering: only an explicit complete, internally consistent typed match is green; partial is amber/retryable with no checkmark or `match` claim. |
| `check_compare_dupmatch.py` | duplicate-key similarity pairing (`pair_occurrences_by_similarity` — opposite file order still pairs the truly-equal rows); the exhaustive authority and cap/tie contract live in `check_compare_pairing_policy.py` |
| `check_compare_ditto.py` | ditto (`+`-run) cells are NON-ASSERTING in a Highway Log compare (the `+`/`++` domain convention is owned by [highway_log/comparison-study.md](highway_log/comparison-study.md)) |
| `check_ramp_summary_partial.py` | ramp-summary failures-OK + short-PDF-blank |
| `check_tsn_description_leak.py` | TSN Highway Log Description-leak guards (x0-gate / `*`-totals close / `_is_totals_line`) |
| `check_tsmis_pdf_parse.py` | TSMIS Highway Log (PDF) cell-rect consolidator (char-conservation, 1:1 cell mapping) — see [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) |
| `check_tsmis_pdf_reconcile.py` | TSMIS Highway Log (PDF) row-drop reconciliation: ⚠ INCOMPLETE (dropped-no-geometry lines) + the unfit-carry ⚠ escalate PARTIAL; VALIDATED carried-geometry pages get an info line and stay COMPLETE (v0.26.2) |
| `check_highway_log_columns.py` | the corrected 31-column Highway Log labels (position → canonical label) — see [highway_log/columns.md](highway_log/columns.md) |
| `check_highway_log_ditto.py` | the Highway Log ditto resolver (`is_ditto` / `fill_paired_roadbed` / `display_fills`) |
| `check_highway_log_roadbed.py` | the roadbed-aware comparison key (`roadbed_tag` / `roadbed_canonical_location` / `keys_for` opt-in; strictly refines, never merges) |

### v0.12.0+ feature checks (GUI/batch/filenames)

| Check | Locks |
|---|---|
| `check_a1_filenames.py` | A1 self-describing output filenames (`<date> <src>-<env>` stamping; env-tagged batch filenames) |
| `check_a2_compare_filter.py` | A2 — the cross-env compare dropdowns only offer run folders that contain the chosen report |
| `check_b1_pause.py` | B1 Pause/Resume (between-routes hold, works in fast mode) |
| `check_b2_autoconsolidate.py` | B2 auto-consolidate on export finish |
| `check_b3_batch.py` | B3 Export Everything batch engine |
| `check_report_library.py` | always-current destination plumbing / report-ages library |

> When adding a check, mirror CI: add it to the relevant blocking step in
> `checks.yml` and to the `APP_MODULES`/loop as appropriate. Several checks are
> grouped into `bash` loop steps with `set -e` so the first failure reds the job.

## Frozen `-SelfTest` gate (`build/full_smoke.py`)

`full_smoke.py` is the **release gate** — it exercises EVERY real code path the
app depends on, used two ways:

1. **Against the build venv**, to prove `PIL` / `pypdfium2` / `pypdfium2_raw` are
   never imported (so they stay excluded from the bundle).
2. **Frozen** (`build.ps1 -SelfTest`), as the gate that proves a **pruned**
   bundle still runs everything. `-SelfTest -BundleChromium` gates the
   bundled-Chromium path.

What it does (exit 0 = all good; nonzero/raise = something the app needs is broken):

1. **Chromium:** `launch_browser` (system Edge/Chrome) → `page.pdf()` (the Ramp
   Summary path, format `Letter`) + a real `expect_download()` round-trip;
   asserts the PDF is non-empty.
2. **pdfplumber:** exactly the calls `consolidate_ramp_summary` makes —
   `extract_text` / `extract_words` / `extract_tables`; asserts `Route 005` in
   the text and the word `1234` is found.
3. **openpyxl:** a write/read round-trip (the consolidator output path);
   asserts `C2 == 1234`.
4. Reports whether the excludable optional libs got imported (and that
   `cryptography`, a hard pdfminer import, did).
5. **GUI:** imports `webview` + `gui_api`, builds `GuiApi`, asserts
   `get_initial_state()` returns reports + routes and the UI assets exist
   (`gui_api._ui_index_path()`); then actually creates a hidden WebView2 window,
   waits up to 30 s for `window.__tsmis` to appear, reads
   `window.__tsmis.test_state()`, with a 60 s watchdog. A window that can't start
   in the environment is **tolerated as a skip** (printed), but a *started*
   window that fails its JS cycle is a hard `AssertionError`. `UpdateWorker` and
   `CheckWorker` are stubbed to `_NoWorker` so the gate is deterministic and
   offline-safe (never touches the network/GitHub).

The frozen gate runs on `windows-latest` in `.github/workflows/release.yml`;
nothing is published if any gate fails. Build/release mechanics are owned by
[build-and-release.md](build-and-release.md).

## Comparison verification loop (the real "test suite" for compares)

The user approves comparison changes by **opening real samples**; the
throwaway verifier is the only test suite this no-tests repo has for the
comparison engine.

### Real input pairs (LOCAL ONLY)

Live under `C:\Users\Yunus\Downloads\TSMIS\ground-truth\inputs` (the `Downloads\TSMIS`
folder was organized into categories on 2026-07-07 — see its `_INDEX.md`):

- **Per-route (fast):** `tsmis_highway_log_route 1.xlsx` + `tsn_highway_log_route 1.xlsx`.
- **Consolidated (50k/60k rows):** `tsmis_highway_log_consolidated 1.xlsx` +
  `tsn_highway_log_consolidated 1.xlsx`. Both-flavors generate+verify ≈ 12 min —
  **run in background**.

### The loop (established v0.9.0, 2026-06-11)

1. Run a **standalone verifier** that regenerates the workbook(s) and checks every
   asserted cell against expectations rebuilt without importing the production reader,
   adapter, equality, key, or pairing helpers. Bind the exact source-member manifest,
   source/runtime hashes, typed pairing trace, and derived evidence hashes.
2. Deliver samples to Downloads named
   `TSMIS_vs_TSN_<scope>_Comparison_vN_SAMPLE.xlsx` for the user to approve;
   **delete the superseded `vN-1`** files; **bump the `SAMPLE` version per
   iteration**.

### Route-1 approved baseline — never change silently

The per-route format is locked to the approved **Route-1** sample:

```
299 both / 18 / 69 / 221 diff rows / 969 diff cells
```

**969** is the current approved figure (was **971** before the v0.11.0 TSN
totals-block fix removed Route-1's 2 leak-caused Description false positives).
(The `comparison-verification-flow` memory claims CLAUDE.md "still says 971 and
is stale", but the current CLAUDE.md already reads 969 — the memory note is the
stale one.)

### Correctness/re-bless harness (`%TEMP%\tsmis_regress\`)

`compare_core.py` is **correctness-locked** — any formula/semantic change must be
proved cell-for-cell. Correct historical cells stay identical; every deliberate corrected
cell/count must be enumerated and independently justified before the baseline is re-blessed
(the v0.10.0 extraction was accepted because **756,892 cell positions** matched exactly across
4 workbooks). The harness scripts (`make_minis.py` /
`gen_outputs.py before|after` / `diff_outputs.py` / `test_env_compare.py` /
`com_verify.ps1`) live **outside the repo** at `%TEMP%\tsmis_regress\` (regenerate
`before/` from a pre-change checkout if the folder is gone). **The full harness
table, the regression-lock contract, and `compare_core` internals are owned by
[comparison-engine.md](comparison-engine.md) §2** — that is the canonical home; this
section is just the verification-ladder entry pointing to it.

### Excel is installed → use COM for empirical behavior

Excel is on the dev PC, so COM automation works
(`New-Object -ComObject Excel.Application`) for empirical tests — used to prove,
e.g., that whole-row `57:57` link targets don't scroll right while bounded ranges
do, and to F9-recalc the formulas flavor so every SELF-CHECK reads OK. This is
the **only** way to verify formula/HYPERLINK behavior (see gotchas below).

## Per-report flawless-audit recipe (v0.17.0 standard)

The bar for the v0.17.0 effort (a full audit + rethink + perfection of **every**
consolidator/comparator, existing and new) is **flawless, cell-for-cell, proven ≥3
independent ways**. Run this recipe for each report's consolidator + vs-TSN comparator
before it is marked done; record the result + the report's approved counts in
[tsn-parsers.md](tsn-parsers.md).

1. **Reconcile both raw files by hand FIRST.** Open the TSN and the TSMIS file and agree
   the key column(s), row identity, and normalization rules **before** writing the loader —
   the `CompareSchema` comes from the data, not a guess.
2. **Assert the wiring** in a `check_compare_<report>_tsn.py` / `check_consolidate_<report>.py`:
   the `CompareSchema` key field + side names, the `COMPARE_REPORTS` row (`group="tsn"`),
   `_CONSOLIDATOR_BY_SUBDIR`, and the `day_matrix._day_rows()` `supported` flip + `build_day_cell`
   dispatch.
3. **Synthetic key-collapse test** — plant a mid-list insert; prove the key field collapses
   the spurious diffs to the real rows (the `check_compare_ramp_detail.py` pattern).
4. **End-to-end** — drive `compare()` / `compare_folders` to a VALUES workbook in `%TEMP%`,
   read it back with openpyxl, assert the diff/one-sided counts and a known diff cell.
5. **Throwaway `%TEMP%` verifier vs RAW ground truth** — regenerate the consolidated +
   comparison from the raw files and check **every cell** against an **independent
   from-scratch recompute that does NOT import the engine** (the v0.9.0 loop).
6. **COM recalc** the live-formulas flavor (F9): every SELF-CHECK row reads OK and the
   formulas flavor equals the values flavor.
7. **Adversarial refutation** — a separate agent/method tries to **refute** the counts
   against the raw source; **verify against the actual PDF/XLSX, don't relay an agent's
   claim** (the ramp-audit gotcha below). A real source inconsistency stays flagged RED.
8. **Lock it** — record the approved counts as that report's canary in tsn-parsers.md, add
   the new `check_*.py` to the blocking loop in `.github/workflows/checks.yml`, and for any
   `compare_core` change confirm **Route-1 = 969** unless the approved policy deliberately
   changes it; in that case enumerate every changed cell and re-bind the canary evidence.

`compare_core` stays **correctness-locked** — touching formula/label/state semantics needs the
independent oracle, before/after workbook harness, and installed-Excel tier. Use an opt-in
`CompareSchema` field for report-specific behavior; fix shared defects in the shared engine.

## `#mock` GUI preview (verify `scripts/ui/` without the app)

Verify `scripts/ui/` changes without launching the real app, via a preview HTTP
server. The pywebview traps + the GUI threading model are owned by [gui.md](gui.md).

- **Mock server:** `.claude/launch.json` defines `ui-mock` (Python `http.server`
  on **port 8765** serving `scripts/ui`). Start it (`preview_start("ui-mock")`),
  then navigate to **`/index.html#mock`** — the `#mock` hash engages the built-in
  mock API (`app.js` `WANT_MOCK`). Without it the page waits for the real
  pywebview bridge and shows a fatal banner. The mock must **never auto-start**
  (a silent mock fallback inside the real app would show fake exports).
- **Bare `S`, not `window.S`:** app state is `const S` at module scope and does
  NOT attach to `window`. In `preview_eval`, reference **`S.st` / `S.init`**
  directly — `window.S` is always `undefined` (false-negative "not booted").
- **Screenshot service is flaky:** `preview_screenshot` intermittently hangs
  (30 s timeout) while `preview_eval` / `inspect` / `snapshot` keep working.
  Verify via **DOM-state evals** (classes, computed styles, geometry) — they're
  conclusive. Restarting the server sometimes recovers screenshots; don't fight it.
- **Headless freezes CSS transitions + the media query:** the preview renderer
  reports `innerWidth: 0` until you `preview_resize` to an explicit width (then the
  `≥980px` two-column layout engages), and it does **not** advance CSS transitions
  (a property with a `transition` reads its START value forever). To verify
  transitioned layout/colour (e.g. the matrix `flex-grow` widen, the theme fade),
  set the element's `transition='none'` inline and re-toggle to read the END state,
  and confirm the rule applies (`getComputedStyle(...).animationName`, computed
  values). Watch the actual motion only in the real WebView2 window.
- **Cache / stale page:** the browser caches `app.js` **and `app.css`**; a
  `?cb=`/`#mock` cache-bust on the URL only reloads `index.html`, not the linked
  stylesheet — after a CSS edit, force-refresh it too:
  `var l=document.querySelector('link[rel=stylesheet]'); l.href=l.href.split('?')[0]+'?cb='+Date.now()`.
  If the server died/restarted the page can stay on OLD `app.js` (reloads silently
  fail while down); confirm fresh code with `typeof <a-newly-added-fn> !== 'undefined'`,
  else navigate cache-busted:
  `location.replace('/index.html?v='+Math.floor(performance.now())+'#mock')`.
  `Date.now()` / `Math.random()` are fine in `preview_eval` (it's the page, not a
  Workflow script).
- **Async confirms:** clicking `#btnStartExport` shows the "No saved login"
  confirm asynchronously — click Start, then in a **separate** eval click the
  "Start anyway" button, then check `S.st.task`. A single combined eval finds no
  modal yet.

## Where the real test data + the TSMIS website-source live

**LOCAL ONLY — under `C:\Users\Yunus\Downloads\TSMIS\...` on the dev PC.** Never
commit, copy into the repo, or push any of it.

- Read `…\TSMIS\_INDEX.md` first. It is the maintained corpus map (15,890 files,
  about 5.8 GB at the 2026-07-11 inventory), including which bundle owns each locked
  canary and where older top-level names moved.
- `_INDEX.md` routes to the oracle; it is not itself identity proof. Hash/bind only the
  exact selected canary inputs and record those identities with the run. The durable
  readiness/binding ledger is
  [planning/comparison-perfection/comparison-canary-bindings.md](planning/comparison-perfection/comparison-canary-bindings.md).
- `ground-truth\inputs\` holds the direct real comparison pairs above.
  `ground-truth\All Reports 6.19\` is the locked statewide engine re-proof set;
  `ground-truth\All Reports 7.9\` is the freshest complete both-format field set.
  The dedicated Highway Detail 7.7, Intersection Detail 7.8, HSL 7.8/7.9, and Ramp
  Detail TSN-print bundles own their parser/triangle/evidence canaries.
- `report-samples\` contains curated parser spot-check sets. `comparison-outputs\`
  contains historical workbooks and may explain an old investigation, but is never the
  source for a new expected count. `_scratch\` is explicitly disposable and must never
  be treated as ground truth.
- `evidence-bundles\` contains work-PC diagnostics. It can prove field behavior but
  does not replace the owning raw source pair for a semantic re-bless.
- The **TSMIS website source** (the live page's HTML/JS) is **Caltrans-internal**
  under `site-captures\`. It is the **ground truth** for selectors, dropdown labels,
  print/export functions, and the page's `CONFIG` (env/src). When prose disagrees with
  code about a selector or label, the website source decides — but it must **never** be
  committed, copied into the repo, or pushed. The fake-site fixtures in
  `build/fake_site/` are *authored synthetic reconstructions* that carry only the
  class names / element types / marker text the predicates depend on, precisely so
  the real source never enters the repo.

## Live-export verification is owed (on the work PC)

The dev/personal PC **cannot reach the TSMIS intranet host**, so live-site
verification only happens on the locked-down Caltrans **work PC**. A live export
against TSMIS is the only proof the engine works end to end, and several releases
carry it as **owed** work (e.g. v0.10.0/0.10.1 shipped 2026-06-12 with work-PC
live checks pending).

Likewise the managed-PC security controls (Defender / DLP / corporate proxy /
managed Edge) exist on **neither** the personal dev PC nor any cloud runner, so
IT/DLP/endpoint behavior can only be **reasoned about from code, never
empirically tested** off the work PC. The work-PC constraints (no PowerShell /
cmd / admin; unsigned-exe-from-user-folder only) are owned by
[it-and-security.md](it-and-security.md).

## Diagnosing field reports — which machine?

Before diagnosing any "couldn't update" / "it failed" report:

- **It is almost always the WORK PC install, not the dev machine.** Stale copies
  of the app exist locally (e.g. an old one in Downloads); diagnosing those wastes
  a round-trip and annoys the user. **Establish which machine/install the report
  concerns first** — ask, or check whether the local evidence even matches the
  symptoms (version/dates). (Historical miss: 2026-06-12, an ancient local install
  was wrongly blamed; the real failure was the PowerShell-blocked work PC.)
- **Chat file attachments fail silently.** When the user says "I attached X" and
  nothing is visible, **say so immediately** and ask for a re-send or paste —
  don't search the filesystem for it.

## Gotchas that waste time

- **openpyxl reads HYPERLINK cells as blank.** A naive Python/openpyxl reader
  sees the `<side> Row` HYPERLINK columns (and any `=HYPERLINK(...)`-backed cell)
  as blank, because Excel caches no numeric result for `HYPERLINK`. They are
  **correct in real Excel** (COM-verified). **Do NOT flag them as broken** —
  verify in real Excel / COM.
- **Verify agent claims against ground truth — don't relay them.** In the
  2026-06-16 ramp audit, a workflow agent claimed `parse_pdf` "undercounts
  ramp-types" on 9 dense routes; a deeper check **refuted it** (cross-checked
  against an independent geometric word-position extraction across all 378 PDFs ×
  14 ramp types = 5,292 values → **0 mismatches**; exact match to raw page-2
  text). The real shortfall was a **TSMIS source-data inconsistency** (the PDF's
  own Ramp Types breakdown sums short of its stated Total), correctly flagged RED
  by `_audit_ok` — fudging it green would HIDE a real source issue. Always verify
  an agent's claim against the **actual ground-truth PDF/source**, not the agent's
  summary.
- **Verify numbers ≥3 independent ways for an audit you'll "take as fact".** The
  high-confidence method in the ramp audit: an independent from-scratch recompute
  (NOT importing the engine) + Excel COM self-check/parity recalc + v0.11.0
  regeneration + an adversarial refutation agent + the workbooks' own literals —
  all agreed.
- **Checks must be HERMETIC — sandbox every canonical root a fixture touches.**
  `tsn_source`/the matrix snapshots consult the CANONICAL TSN library as well as
  the staged dest; two checks (`check_day_matrix`, `check_matrix_tsn`) overrode
  `OUTPUT_ROOT` but not `paths.TSN_LIBRARY_ROOT`, so they passed on CI (empty
  library) and on any dev PC — until v0.24.0 staged the Highway Log district
  prints into the real `tsn_library/highway_log/raw/` (they're the HL evidence
  source) and both checks' staged "consolidated" fixtures started reading as
  "pdfs". A check that reads ANY live app root is machine-state-dependent; fix
  the CHECK (sandbox + restore in `finally`), don't unstage the data.

## Release-branch / tag pitfall

Don't name a release branch after the tag — the v0.9.0 branch+tag collided on
push. If it happens, push tags as `refs/tags/<tag>`.

## See also

- [comparison-engine.md](comparison-engine.md) — the compare_core regression-lock
  contract + engine internals the compare checks guard.
- [build-and-release.md](build-and-release.md) — CI mechanics, the release gate,
  updater swap/SHA/revert.
- [gui.md](gui.md) — the pywebview traps + GUI threading/queue model behind the
  `#mock` preview.
- [it-and-security.md](it-and-security.md) — work-PC constraints (no PowerShell /
  cmd / admin), DLP, managed Edge.
- [highway_log/columns.md](highway_log/columns.md),
  [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md),
  [highway_log/comparison-study.md](highway_log/comparison-study.md) — the
  Highway Log specifics the parser/column/ditto checks lock.
