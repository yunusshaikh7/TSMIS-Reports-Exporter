# CR-001 — Maximize offline completion + design a work‑PC validation handoff (0.18.0 → 0.18.1 close‑out)

**Status:** `awaiting_codex_review` (normal phase execution **paused**)
**Author:** Claude (implementer) · **Reviewer:** Codex (must re‑accept before implementation resumes)
**Raised:** 2026‑06‑23 · **Branch:** `refactor/v0.18.0-structural-overhaul` · **HEAD:** `decced4`
**Active phase when raised:** between **P9 (committed `decced4`)** and **P10 (next eligible, `pending`)** — no phase `in_progress`/`awaiting_review`.

---

## 1. Requested change summary

The user has directed a scope change to the approved `05-claude-final-plan.md`:

1. **Opt into every deferred item that is offline‑doable** — pull it into v0.18.0 instead of leaving it conditional/deferred. "Leave nothing else on the table."
2. **Add a final phase that designs how to validate the things we *cannot* finish offline** — i.e. produce a method/direction for testing on the locked‑down Caltrans **work PC**, and the **v0.18.1 plan** that consumes the returned evidence and closes out the refactor.
3. The target outcome: **v0.18.0 = an enterprise‑ready, polished, maintainable, code‑complete build**; **v0.18.1 = the field‑validated release** after the user runs v0.18.0 on the work PC and returns "whatever is necessary — specific logs and all."
4. The user has **removed the resourcing constraint** ("spare no expense"), **granted the work‑PC evidence/acceptance window** that gate **O7** was waiting on, and authorized **as many new phases as needed**.

This is a **meaningful scope + definition‑of‑done change**, so per the workflow it is paused here for Codex re‑acceptance rather than implemented.

## 2. Reason for the change

The approved plan deliberately drew the v0.18.0 DoD at "**satisfiable from CI/offline alone**" (R1‑P01) and pushed everything needing the work PC, a cert, or a genuine product trade‑off into conditional phases, the roadmap, or standing gates O1/O2/O7 (`05` §K, §J2; `00` "Remaining user decisions"). That was the right call **while the work‑PC window and resourcing were uncertain**. The user has now removed both constraints and asked for the most complete possible build. The deferrals therefore need re‑triage: the ones that were deferred *only* because of resourcing or the work‑PC window should be pulled in; the ones deferred for a **hard reason** (a real product trade‑off, an external cert, or the `compare_core` regression‑lock) should stay deferred **with the reason restated**, not silently swept in.

The change also gives **O7 an answer** for the first time: the user will operate v0.18.0 on the work PC and return evidence. That converts P8c from "*omit from v0.18.0 entirely if no acceptance window*" (RR3‑C1) into "*implement + offline‑prove in v0.18.0; accept on the work PC in v0.18.1*."

## 3. Current implementation state

- **13 of 16 phase headings committed** on the branch, each Codex‑`PASS`ed, one focused commit per phase, planning folder never staged:
  P0 (`4bbee65` + 2 isolated), PA (`65aef98`), P1 (`e47b700`), P2 (`ca3c2af`), P3, P4, **P5 — family‑1 only** (`c0cfa39`, the `tsn_load` factory; the comparator driver was the deferrable remainder), P6 (`8d9ec2e`), P7a (`42122ff`), P8a (`bdbda4d`), P8b (`bb144d4`), P9 (`decced4`).
- **Pending (blocking):** P10 (packaging/deps/updater), P11 (docs/audit reconciliation).
- **Pending (conditional, not in DoD):** P7b (GUI endpoint extraction), P8c (engine behavior changes, O7‑gated). P5's comparator‑driver remainder is the third deferrable.
- **Offline verification:** the golden‑check suite (67 `build/check_*` files present, incl. `check_fake_site.py` + `build/fake_site/`) has been green at every committed boundary per the phase reports. App runnable + `#mock` verified at each boundary.
- **Tree:** clean except the untracked `docs/planning/` workspace. `origin/main` still `d2ee353` (nothing pushed). `version.py` = `0.17.1`.

## 4. Current branch and commit SHA

- **Branch:** `refactor/v0.18.0-structural-overhaul` (off `main` @ `d2ee353`; not pushed).
- **HEAD:** `decced443faa70ef0807c3e80c37605ca0e5e5da` (`decced4`, P9).
- **Working tree:** clean apart from untracked `docs/planning/`.

## 5. Current phase status

Normal phase execution **paused** at this CR. Last committed: **P9** (`decced4`). Next eligible before this CR: **P10** (`pending`). No phase is `in_progress` or `awaiting_review`. No phase is mid‑remediation.

## 6. Files / areas likely affected

Nothing is edited by this CR (proposal only). **If accepted**, the amendment touches these areas (all additive / behind the existing shims & façade; no committed phase is reworked):

| Area | Modules (from `05` §I targets) | New offline checks |
|---|---|---|
| P5 comparator driver | `compare_tsn_common.py` (new), 5 `compare_*_tsn` → schema+projector; notes helper **outside** `compare_core` | the 6 vs‑TSN golden checks + COM/Route‑1 harness (exist) |
| P7b endpoint extraction (full depth) | `gui_win32.py` (new, ctypes), endpoint grouping delegating to `task_coordinator`; `_begin_task`; unify compare/matrix dispatch pairs | `check_gui_bridge`/`matrix_bridge`/`b3` (exist) + `#mock` |
| P8c engine behavior (offline code) | `report_nav.select_report` (exact‑match), `edge_device` CDP on‑demand+close, `should_cancel` in `_recover`/retry/portability, auth‑path swallow logging — **each its own commit** | extend `build/fake_site/` to exact/prefix/suffix/disabled; `check_fake_site`/`check_export_engine` |
| P9b frontend deeper split | `ui/app.js` modularization + renderer merge **within classic `<script>`, no framework/ES‑modules** (§N) | extend `check_ui_boot.js`/`check_ui_contract.py`; `#mock` boot + `scrollHeight` |
| P10 (expanded) | flip §J "Defer (document)" rows → implement: `updater` download socket‑timeout+retry, `resolve_previous_release` pagination, immediate‑death‑check hardening; attempt the optional perf (R1‑A01 harness) | `check_updater` (extend) |
| New audit‑hardening phase | `reset` junction/symlink guard; consolidate‑overwrite re‑check (TOCTOU UX window); destination‑ownership marker (M03); **PDF‑completeness offline harness** (independent expected‑row oracle + ramp‑summary misattribution/duplicate‑pop fixes) | new `check_*` per item; extend `check_tsmis_pdf_reconcile` |
| New work‑PC handoff phase | a bundled **no‑admin `--collect-evidence`/diagnostics** exe mode (zips logs + fixtures the user returns) + a documented manual procedure; the **acceptance checklist**; the **v0.18.1 plan** doc | the mode is exercised by the existing self‑test gate |
| P11 (docs) | unchanged role; reconciles the larger closed set + folds in the v0.18.1 plan + records the residual deferrals | `check_no_misspelling` + link check |

## 7. Whether any already‑committed work is affected

**No committed phase is reworked or reverted.** Every opt‑in is **additive on top of a committed dependency**:
- P5 comparator driver builds on committed P5 family‑1 (`c0cfa39`).
- P7b builds on committed P7a (`42122ff`).
- P8c builds on committed P8b (`bb144d4`).
- P9b builds on committed P9 (`decced4`) — further extraction of `app.js`, not a re‑split.

The committed engine shim, GUI façade, and `#mock` boundary are the seams these phases extend. The **only** thing that changes about already‑shipped phases is **classification** (conditional → blocking) and the DoD they roll up into — not their code.

## 8. Proposed amendment to the phase plan

### 8.1 The core change — re‑triage every deferral by *why* it was deferred

| Deferred item (source) | Offline‑doable? | Proposed disposition |
|---|---|---|
| **P5 comparator driver** (`compare_tsn_common`) — `05` §I P5 | **Yes** (canary semantic‑identity, no live) | **Opt in** → finish P5 (blocking) |
| **P7b GUI endpoint extraction** — `05` §I P7b | **Yes** (behavior‑neutral, façade identity) | **Opt in** → P7b blocking |
| **P7b "depth" / deeper GUI Python split** — O1 row | **Yes** (no framework) | **Opt in** → fold full depth into P7b (O1 resolved toward "maintain now") |
| **P8c engine behavior changes** — `05` §I P8c, §J2 | **Code: yes** (fake‑site exists); **acceptance: work‑PC** | **Opt in code to 0.18.0**, offline‑proven; **work‑PC acceptance → v0.18.1** (O7 now granted) |
| **P9 deeper split** (renderer merge + `app.js` modularization) — D4/R1‑N03 | **Yes** (no framework) | **Opt in** → new **P9b** (O1 resolved) |
| **perf (P10)** — R1‑A01 | **Yes** (offline harness + threshold) | **Opt in** → attempt in P10; keep "drop if no material gain" |
| **dl‑socket‑timeout / releases‑list‑cap / immediate‑death‑check** — §J "Defer (document)" | **Yes** (updater, offline) | **Opt in** → flip to *implement* in P10 |
| **reset‑follows‑junctions‑symlinks** [P3] — §J2 | **Yes** (dev PC **is** Windows) | **Opt in** → new audit phase |
| **consolidate‑overwrite‑toctou** [P3] — §J2 | **Yes** (re‑check guard) | **Opt in** → new audit phase |
| **destination‑ownership marker (M03)** [P3] — §J2/D16 | **Yes** (marker file) | **Opt in** → new audit phase |
| **PDF‑completeness trio + row‑count oracle** [P2] — §J2 | **Partial** (offline harness yes; final proof needs real PDFs) | **Opt in offline harness + fix‑design to 0.18.0**; **real‑PDF acceptance → v0.18.1** |
| **DPAPI auth‑at‑rest (O2)** — D6/§J2 | **Has a real trade‑off** (breaks `storage_state_is_portable`, the core single‑folder‑portable tenet) | **User decision** — see 8.4; recommend an *optional, off‑by‑default* encrypt‑at‑rest toggle, not a default |
| **Updater authenticity / runtime signature (A03, update‑trust)** [P1] — §J/§J2 | **No** (needs a real code‑signing cert) | **Stays deferred** unless the user commits to a cert → then v0.18.1+; keep workflow‑signing parity in P10 |
| **min‑cost‑pairs‑greedy** [P3] — §J2 | **In principle, but inside the regression‑locked `compare_core`** | **Recommend stay deferred** (D3 + the `compare_core` lock); offer an explicit opt‑in re‑proof mini‑phase only if the user insists |
| **D16 dropped** (paths‑init rewrite, bounded worker queue, CI‑trigger change, `run_compare`‑returns‑counts, `_safe_join`/`full_snapshot`, snapshot‑once) | n/a — **rejected for cause** (ceremony/dead abstraction, KISS/YAGNI) | **Recommend keep dropped** — re‑opening contradicts the accepted D16 rationale; listed so they're consciously excluded, not forgotten |
| **All work‑PC acceptance (O7)** — §M | **No** (by definition) | **Designed** by the new handoff phase; **executed in v0.18.1** |

### 8.2 Re‑classified existing phases (conditional/deferrable → blocking)

- **P5** — finish the comparator‑driver remainder; P5 becomes fully blocking.
- **P7b** — blocking; depth‑cap lifted (O1 resolved to "no imminent full replacement; make it maintainable now," staying inside the §N no‑framework guardrail).
- **P8c** — **blocking code** in v0.18.0 (offline‑proven against the fake‑site fixture, each change its own commit); its **live acceptance is the explicit subject of the v0.18.1 gate**, not a v0.18.0 blocker.

### 8.3 New phases (proposed IDs; Codex to ratify numbering/sequence)

- **P9b — Frontend deeper modularization.** Renderer merge + `app.js` split into cohesive classic‑script modules; **no framework, no ES‑modules, no production‑UI behavior change** (§N; Lesson‑10 sr‑only rule preserved). Depends P9. Verified by the extended boot/contract checks + `#mock`.
- **P12 — Residual offline audit hardening.** `reset` junction/symlink guard; consolidate‑overwrite re‑check; destination‑ownership marker (M03); the **PDF‑completeness offline harness** (independent expected‑row oracle + ramp‑summary misattribution/duplicate‑pop fixes) driven by synthesized fixtures + the audit's geometric cross‑check, with **real‑PDF acceptance deferred to v0.18.1**. Each item its own commit + offline check.
- **P13 — Work‑PC validation handoff + v0.18.1 plan (FINAL phase).** Produces: (a) a **bundled, no‑admin/no‑PowerShell evidence‑collection mode** (`--collect-evidence`, reusing the existing self‑test plumbing) that zips the logs + fixtures the user returns, **plus** a documented manual fallback procedure that respects the work‑PC capability model (unsigned exe from a user folder, no admin/cmd/scheduled tasks); (b) the **per‑item acceptance checklist** for every O7/live item (P8c select/CDP/cancel latency, P1 partial‑keeps‑last‑good, P2 Defender/lock with disposable destinations, P3 real paused‑batch resume, P10 real v0.17→v0.18 update, PA both frozen exes + source ZIP, PDF real‑data validation); (c) the exact **fixtures to capture** (real source PDFs, a real v0.17 `batch_job.json`, a real auth‑file shape, live‑export captures); (d) the **v0.18.1 plan** that consumes the returns and closes the refactor. Depends on the full live‑verify set being known (after P8c/P10/P12).

### 8.4 Items that stay deferred + the three genuine user decisions

These are **not** auto‑opted, because they are blocked by something other than time:

1. **O2 — DPAPI / auth‑at‑rest.** Hard trade‑off: DPAPI binds to user+machine and **breaks the portable single‑folder app** (a core product tenet; D6). **Recommendation:** implement DPAPI as an **optional, off‑by‑default** "encrypt saved login at rest" setting — portability preserved when off, available on the work PC where it isn't needed — but only if the user wants it. **Needs the user's O2 answer.**
2. **Updater authenticity / code‑signing cert.** Runtime signature verification needs a real cert (SignPath); A03 + §N currently forbid a runtime crypto abstraction. **Recommendation:** keep workflow‑signing‑parity in P10 now; build the runtime‑verify path only if the user commits to obtaining a cert (then v0.18.1+). **Needs a user/procurement decision.**
3. **`min-cost-pairs` (greedy vs optimal) inside `compare_core`.** The fix lives inside the **regression‑locked** engine; any change needs a full cell‑for‑cell re‑proof and the 8+ duplicate‑key‑group frequency is unquantified (§J2; D3; the `compare_core` convention in `CLAUDE.md`). **Recommendation:** keep deferred even under "spare no expense," consistent with the standing regression‑lock; offer an isolated opt‑in re‑proof mini‑phase only on explicit request.

### 8.5 Version / release model

- **v0.18.0** = code‑complete, polished, maintainable; **everything in it is still offline‑provable** (R1‑P01 invariant preserved — including P8c's live‑path *code*, proven against the fake‑site fixtures). Positioned as the **work‑PC release candidate** that the user operates to generate field evidence.
- **v0.18.1** = the **field‑validated GA**: the user returns work‑PC evidence per P13's kit; v0.18.1 applies any fixes the real logs surface and closes the refactor.
- **DoD invariant evolves cleanly:** 0.18.0 DoD = offline‑provable (live‑path code proven against fixtures); 0.18.1 DoD = work‑PC acceptance of the live paths. No v0.18.0 phase depends on the work PC to go green.

### 8.6 Proposed updated task graph (Codex to ratify)

```
committed: P0─PA─P1─P2─P3─P4─P5(fam1)─P6─P7a─P8a─P8b─P9
ready now (deps committed):  P5(comparator) · P7b(full depth) · P8c(code) · P9b
                             P10(expanded: updater items + perf)
                             P12(audit hardening; PDF harness)
near‑final:  P13 (work‑PC handoff + v0.18.1 plan)   ← needs P8c/P10/P12 to know the full live set
last:        P11 (docs; folds in the v0.18.1 plan + the residual O2/cert/min‑cost deferrals)
```

## 9. Proposed verification changes

- **Preserve** the offline‑only gate for v0.18.0: every newly opted‑in phase must be RED‑proven and green offline before commit (same discipline as P0–P9). P8c is proven against an **extended `build/fake_site/`** (exact/prefix/suffix/disabled) — no live access in dev.
- **Add** a second, explicitly‑separate **v0.18.1 acceptance gate**: the P13 checklist, executed on the work PC against returned evidence. This is **not** part of the v0.18.0 DoD (it cannot be — by design).
- **DoD text (`05` §K)** updated to two tiers: the 0.18.0 offline DoD now *includes* P5‑comparator, P7b, P8c‑code, P9b, the P12 audit items, and the expanded P10; a new **§K2 (v0.18.1 acceptance DoD)** lists the work‑PC items.
- **§J2 / §J / §M** updated so the flipped items read "Resolved (0.18.0)" or "Resolved (0.18.0 code) + accept (0.18.1)"; only O2, the cert, and `min-cost-pairs` remain "Deferred," each with its restated reason.
- **No change** to: `compare_core` regression‑lock proof, the cert‑store TLS rule, the console‑free‑core rule, the "no framework/ES‑modules" UI rule, or the "planning folder never staged" rule.

## 10. Risks & mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **P8c ships live‑path behavior in 0.18.0 before work‑PC acceptance** (reverses RR3‑C1's "omit if no O7") | **High** | 0.18.0 is the *operator‑in‑the‑loop RC*, not blind GA; each P8c change is its own revertible commit; offline fake‑site proof first; v0.18.1 is the gate before GA. **Option for Codex:** ship P8c behaviors behind a runtime flag (off by default) the work‑PC test flips on — at the cost of a temporary abstraction §N otherwise resists. |
| **Scope/DoD redefinition** changes the approved R1‑P01 "offline‑alone" invariant | Medium | The invariant is *preserved* for 0.18.0 (all code offline‑provable); a *second* tier is *added* for 0.18.1. Stated explicitly in §8.5 for Codex sign‑off. |
| **P9b deeper `app.js` split** risks a UI regression | Medium | Behavior‑neutral; extended boot/contract checks + `#mock` + the browser‑HTTP‑cache reload procedure; no framework. |
| **PDF‑completeness** can't be *fully* proven offline | Medium | Split: offline harness + fix‑design in 0.18.0; real‑PDF acceptance in v0.18.1 (P13 collects the PDFs). The audit's geometric cross‑check (0/756) bounds the residual risk. |
| **Larger change surface** before any push/CI run | Medium | Unchanged phase‑at‑a‑time discipline: one phase, one Codex `PASS`, one commit; app runnable + suite green at every boundary; nothing pushed. |
| **Re‑opening D16‑dropped or `compare_core` items** would add dead abstraction / break the lock | Low (recommend against) | Keep dropped/deferred per §8.1/§8.4; surface them so exclusion is conscious. |
| **Rollback is dependency‑aware** (§L) and the new phases extend that chain | Low | New phases are additive behind shims/façade; per‑phase revert points carried into each phase's Rollback line. |

## 11. Exact questions Codex should review

1. **DoD model:** Is the two‑tier model (0.18.0 = offline‑provable incl. live‑path *code*; 0.18.1 = work‑PC acceptance) an acceptable evolution of R1‑P01, or does it dilute "offline‑alone" in a way you object to?
2. **P8c in 0.18.0:** Does shipping P8c's offline‑proven live‑path code in 0.18.0 (with acceptance in 0.18.1) adequately replace RR3‑C1's "omit entirely if no O7"? **Do you want the runtime‑flag option (10) or the per‑commit‑revertible RC model?**
3. **Offline‑doable triage (§8.1):** Do you agree with every "opt in / stays deferred / keep dropped" call? Flag any item mis‑triaged (especially the PDF‑completeness split and the junction/TOCTOU/marker opt‑ins).
4. **P9b / P7b depth vs §N:** Does the proposed deeper modularization stay on the right side of "no framework / no ES‑modules / no one‑class‑per‑action," or is it drifting toward the rewrite §N forbids?
5. **`min-cost-pairs`:** Confirm it should stay deferred under the `compare_core` lock even given "spare no expense" — or do you want the explicit opt‑in re‑proof mini‑phase?
6. **DPAPI (O2):** Is the "optional, off‑by‑default encrypt‑at‑rest" design the right way to offer DPAPI without breaking portability — and should it be in 0.18.0 or 0.18.1?
7. **Phase IDs/sequence (§8.6):** Ratify or correct the new IDs (P9b/P12/P13), their deps, and the rule that P11 folds in the v0.18.1 plan last.
8. **P13 evidence kit:** Is a bundled `--collect-evidence` exe mode (reusing self‑test plumbing) acceptable on the work PC's capability model, or should the handoff be a pure documented‑procedure (no new code path)?
9. **Anything this CR misses** that should also be pulled in, or any opt‑in that should be pushed back to deferred.

## 12. Claude recommendation

**ACCEPT WITH MODIFICATIONS.**

The direction is sound and the workflow is preserved: every v0.18.0 addition stays offline‑provable and phase‑at‑a‑time, committed work is untouched, and the genuinely‑blocked items (O2 trade‑off, cert, `compare_core` lock) are kept deferred with restated reasons rather than forced. The **modifications** I'm asking Codex to settle before implementation: (1) confirm the two‑tier DoD; (2) choose the P8c delivery shape (runtime flag vs per‑commit RC); (3) ratify the PDF‑completeness offline/real‑data split; and (4) confirm the three standing deferrals (O2, cert, `min-cost-pairs`) plus the P13 evidence‑kit shape. On Codex's `ACCEPT`, I will amend `05-claude-final-plan.md` (§H/§I/§J/§J2/§K/§M + a new §K2), update the phase table + decision log in `00-coordination.md`, and resume phase‑at‑a‑time from the first ready phase — **not before.**

---

*CR‑001 — proposal only. No product/source files edited; nothing staged, committed, or pushed. Planning folder remains untracked.*
