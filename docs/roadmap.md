# TSMIS Exporter — Roadmap & backlog

The single forward list — bugs to fix, features to add, and standing concerns. The **changelog**
(what already shipped, per release) is `CHANGELOG.md`; the narrative is
[history.md](history.md). This file is what's *left*.

> ### ▶ WHERE THINGS STAND (2026-08-21, after v0.41.2)
>
> **Correctness has nothing open.** All **245** comparison-audit findings are
> closed — the last, CMP-AUD-245, in v0.39.1. The 13 integrated reports consolidate
> and compare in every lane their data supports; Highway Detail's correctness
> backlog closed in v0.38.0 and its two editions now agree statewide (51,327
> locations, 0 differing cells).
>
> **The last three releases were all comparison SPEED, with the produced workbook
> held byte-identical**: v0.40.0 (a per-workbook composite-style cache + a streamed
> read of the finished package — ~39% off a statewide run), v0.40.1 (both inputs
> were being read twice — a further 16%), and v0.41.0 (**Counts only**, a
> `mode="preview"` run that skips the writers entirely — 9.1x, and by design
> certifies nothing). **That tuning is finished and measured out**: writing is 70%
> of a comparison, spread across four writers with no hot spot left, and the only
> lever beyond it changes the output. The record is
> [planning/vs-tsn-comparison-speed.md](planning/vs-tsn-comparison-speed.md).
>
> **v0.41.2 made Counts only reachable.** Its checkbox was wired to the generic
> settings endpoint, which drops keys outside `settings.DEFAULTS` — so the option
> clicked, reported success, saved nothing and snapped back, and the mode shipped
> in v0.41.0 could not be turned on at all. Same release: a counts-only run that
> re-derives a stale cell's existing workbook counts now marks it **counts
> confirmed** (an accent on the same uncertified state — it confirms the numbers,
> never the file).
>
> **What's next, in order:**
>
> 1. **B1 — the work-PC acceptance run. Owner only**; this dev box cannot reach the
>    TSMIS intranet. Seventeen releases have landed since v0.32.0 and every one of
>    them is offline-verified only. It blocks nothing, but it is the only thing
>    standing between "the checks pass" and "it works in the field."
> 2. **H — RB-6 is implemented and awaiting review.** The bounded output-audit
>    program has merged five of its six bundles; RB-5 shipped in v0.42.0 and
>    RB-6 — its last — is implemented on `hotfix/rb-6-hygiene-and-guards` and
>    now needs its two adversarial reviews. Nothing in H is unstarted.
> 3. **G1 — the CA INTERSECTIONS + CA RAMPS clean-road builds**, on the v0.29.0
>    CA HIGHWAYS pattern, with the mappings already censused in
>    [planning/cleanroad-highways.md](planning/cleanroad-highways.md). **The next
>    large build, and it needs nothing from the vendor, the site, or the owner to
>    start.**
> 4. **DA6 → DA1's residual.** Our reconstruction's row boundaries still don't line
>    up with the report's, and the census says ~63% of our extra boundaries are
>    driven by the three block effective dates — which are 79–80% right against the
>    report but only ~60% right against TSN. Chase the columns, not the boundary
>    rule.
> 5. **DA4 — the other reports rendered from the layers.** **Intersection Detail
>    has landed**, and it settled the open question: the recipe survives a
>    different report SHAPE. Highway Detail is a span report and needs the span
>    engine plus a merge rule; an intersection is a place, so that whole
>    apparatus drops out and what is left is a mapping table and three measured
>    rules. It also did NOT need the CA INTERSECTIONS clean-road build first, so
>    G1 is not a prerequisite for the remaining reports the way it looked.
>    `arcgis_reports.py` is now the registry everything derives from — the next
>    report is a table row plus its two modules. Highway Log, Highway Sequence
>    and the Ramp reports are what's left; the residual on the one just shipped
>    is DA7/DA8.
>
> **What is NOT coming, ever:** a fresher TSN pull. TSMIS replaced TSN, so the TSN
> side of every vs-TSN comparison is frozen at the 09/2025 cutover and the gap to a
> live export only grows. Read those differing-cell counts as migration drift, not
> defect (C4 / D5).
>
> *The older status banners that used to stack here (v0.17.1 → v0.38.0) have been
> removed. Per-release detail is `CHANGELOG.md` — 92 versions, one section each —
> and the narrative is [history.md](history.md).*


---

## ▣ OPEN WORK INVENTORY (current as of v0.44.0, 2026-09-02)

**This is the definitive list of what is left.** Everything below is genuinely
open; anything not here is either shipped (see `CHANGELOG.md`) or a historical
record. The long themed sections further down keep the detail and rationale — this
table is the index into them. Re-verify an item against the code before acting on
it; a stale line here is a bug in this list.

### A. Correctness — **NOTHING OPEN.** All 245 findings are closed (last: v0.39.1)

**CMP-AUD-245 (found + fixed 2026-08-19, v0.39.1)** — the Highway Detail vs ArcGIS
projection counted the HF-01 *unavailable* marker as data and reported COMPLETE over a
PARTIAL build. Where the Clean Road build cannot place a source span it writes a reserved
non-asserting token; the v0.39.0 projection inherited the tokens but not the rule.
Statewide **207,030 → 206,875** differing cells, moving exactly the four marker-bearing
columns and no others. Red→green in `check_arcgis_report`.


**CMP-AUD-244 (found + fixed 2026-08-18, v0.38.2)** — Highway Detail vs TSN was counting
the paired-roadbed **ditto** convention as data. TSN prints one roadbed concrete and the
other as width-matched `+` runs (a POINTER to the paired row); TSMIS expands them. The
engine has had `ditto_nonasserting` since the Highway Log work, but Highway Detail's
schema never switched it on, so 14,490 pointer-vs-value cells were reported as
differences. Statewide: **174,837 → 160,347** differing cells, asserted cells down by
exactly the same 14,490, **pairing completely untouched** (48,477 paired / 2,850
only-TSMIS / 11,606 only-TSN all unchanged), 20 rows became fully identical. Both vs-TSN
flavors are on; the PDF-vs-Excel self-check is explicitly OFF (both sides expand, so a
stray `+` there must still flag). Red→green in `check_highway_detail_ditto`.

A1–A5 as listed here through v0.37.0 (CMP-AUD-186 · 053 · 133 · 142 · 045-HD) were all
closed on 2026-08-18 — see the status banner above for what each became, and the
[finding ledger](planning/comparison-perfection/comparison-audit-findings.md) for the
per-finding remediation records. The project record is
[COMPLETION-PLAN.md](planning/comparison-perfection/COMPLETION-PLAN.md).

The one thing that is *not* closed is not a defect and never will be: **TSMIS
REPLACED TSN**, so the TSN side of every vs-TSN comparison is frozen at the 09/2025
cutover and the gap to a live TSMIS export only grows. Read those differing-cell
counts as migration drift, not defect — see C4 + D5.

### B. Owed by the owner (work PC only — this dev box cannot reach TSMIS)

| # | Item | Notes |
|---|---|---|
| B1 | **The work-PC acceptance run — now against v0.44.0. THE TOP PRIORITY: everything since v0.32.0 is offline-verified only.** | Comparison + evidence output intentionally differ from v0.26.2/v0.27.x: re-run both sides, never reconcile old against new. TSN libraries rebuild once; PDF-sourced workbooks re-consolidate once. Then the carried v0.30–v0.32 items in [the backlog plan §4](planning/v0.30-owner-backlog-plan.md): Retry Edge sign-in, the PDF vs Excel Matrix, a fast-mode dual-format run, a pre-v0.32 partial resume, one Excel-row evidence run. **New for v0.37.0:** a Highway Summary export → consolidate → vs-TSN run, and one Highway Detail evidence generation (its evidence lane just opened — see D1). **New for v0.38.x:** re-consolidate Highway Detail (PDF) and confirm it reports COMPLETE with a clean PDF-vs-Excel cell; let the TSN Highway Detail library rebuild once (v4) and confirm the Report View's DCR + ADT columns are populated; and run a **both-editions Highway Summary** export to confirm one render saves both files in the right order. **New for v0.38.2:** drag a day COLUMN on each by-day matrix and confirm it moves on screen (it never did before); toggle a report chip on a matrix and confirm it responds instantly; and — the one worth watching on a STOCKED TSN library — confirm the matrices repaint quickly after the first render, now that the raw manifest memoizes instead of re-hashing every raw source each time. **New for v0.40.0–v0.41.0 (all comparison-speed work, offline-verified only):** rebuild a few cells and confirm the workbooks still open and read as before (output is byte-identical by construction, so anything else is a bug); and tick **Counts only** under Comparison output, refresh a matrix, and confirm the cells show `counts only — build to certify` in grey with NO workbooks written, that a zero-difference cell reads `match*` rather than a green tick, and that building one for real replaces the preview with a normal green result. **New for v0.41.2 — and note the v0.41.0 line above was untestable until now**: the Counts only checkbox never persisted, so confirm FIRST that it stays ticked, mirrors onto the by-day matrix, and survives an app restart. Then run it over a STALE cell that already has a workbook and confirm the workbook is left on disk untouched and the cell reads **counts confirmed** with a green left edge when the numbers still agree (grey ground, still offering a build — never a green tick). **New for v0.42.2:** consolidate a statewide Highway Sequence (PDF) export and confirm it reports COMPLETE with no ⚠ unparsed-line note — a single printed row the site renders with a blank Highway Group used to be dropped and take the whole 252-route consolidation to partial with it. **New for v0.44.0:** on the DEV site, export one route of each Clean Road report and confirm a workbook lands with the full legacy header (on prod the trio may still fail fast as "currently unavailable" — expected until prod catches up); run Settings ▸ Capture website source once and confirm the folder holds `index.html` plus every module under its site name with the BUILD_DATE in the manifest; open each matrix's add-day picker and confirm every day lists the reports it holds. |

### C. Waiting on the vendor / the site

| # | Item | Unlock |
|---|---|---|
| C1 | ~~**Clean Road exports**~~ **EXPORT SHIPPED 2026-09-02** off the dev site 9.1 capture (`clean_*.js` live, the options un-greyed). Still owed by the site/owner: **a statewide work-PC export of each** (`clean_highway` / `clean_intersection` / `clean_ramp`) | Real per-route files unlock the next tiers — a consolidator, the SITE-export-vs-TSN comparison (the TSN slots + `tsn_load_clean_road` are staged) and the site-export-vs-our-ArcGIS-build comparison (all three THY-shaped), plus the `*_printAll` print editions if wanted. The 9.1 capture is DEV: prod may still grey the trio, in which case the export fails fast. |
| C2 | **Route History export flow** | Dev-site only, greyed reserved placeholder (stable id 15). |
| C3 | **Statewide Highway Summary PRINTS** | The export edition SHIPPED in v0.38.0 (`export_highway_summary_pdf`, `hs_printAll`) and is deliberately export-only: there is no real statewide print yet to verify a parser against. One work-PC run producing 252 PDFs unlocks its consolidator + PDF-vs-Excel self-check (the HSL / RD-PDF sequence). |
| C4 | ~~A same-date TSN Highway Summary print~~ **— THERE WILL NEVER BE ONE.** Not a wait; a permanent property | **TSMIS REPLACED TSN.** The site says so on every report cover page ("TASAS — TSMIS has officially replaced the TASAS — TSN database"), and every TSN source we hold is from the one final pull (HD extract REF 2025-09-08; the RD / RS / IS / HS prints all 09/15/2025). The TSN side is a FROZEN historical snapshot and will not be refreshed. See D5 for what that means for the comparisons. |
| C5 | **DEF-01 — permanent/main-site parity** | The frozen output-audit archive is a DEV-site export; equivalence is not established and must not be assumed. Needs a review-ready permanent-site export. |
| C6 | **DEF-03 — baseline Intersection Detail (2 decisions)** | Needs a prior **SSOR-prod** Intersection Detail export for a second day. |

### D. Found during the v0.37.0 work — open

| # | Item | Notes |
|---|---|---|
| D1 | ~~Highway Detail (PDF) has no ENV evidence~~ | **DONE (v0.38.3.)** `evidence_highway_detail` gained `env_fields` / `env_locate` / `env_value` / `env_box`, so the TSMIS-vs-TSMIS print lane now covers all five `_pdf` rows. The hooks reuse the vs-TSN TSMIS locator wholesale — same LOCKSTEP walk, same geometry — differing only in the KEY: `locate_tsmis` took a `key_fn`, and the env flavor keys records by the print's own glued Post Mile text (`R012.243`) where vs-TSN keys on the canonical roadbed-aware form. Shipped together with the **vs-Baseline matrix's** evidence lane, which is the same env flavor picked by DAY instead of by environment. |
| D2 | ~~The Reset cleanup misses the two Intersection Excel export folders~~ | **Done (v0.38.0)** — `gui_worker_maint._LEGACY_OUTPUT_DIRS` now lists `intersection_detail`, `intersection_summary` and `highway_summary_pdf`. |
| D3 | ~~`check_report_wiring` only asserts Reset coverage for `fmt == "pdf"` rows~~ | **Done (v0.38.0)** — `test_reset_covers_every_export` now derives from the EXPORT registry and asserts every enabled export's subdir, skipping only the app-DISABLED placeholders. It fails on all three historical omissions. |
| D4 | ~~The Highway Summary vs-TSN cell is PERMANENTLY amber~~ | **DECIDED + DONE (v0.38.2).** Owner ruling 2026-08-18: *"the TSN summary is locked — that is the file we are working with from the old database and we can't change it. If there is a blank spot we just have to disregard it and deal with it."* A MASKED value (`**********`, the figure overflowed its column) no longer makes the build partial: TSMIS replaced TSN, so the print is a frozen artifact and that gap can never close. The build now returns **complete / 0 skipped**, and the masked category is still shown ONE-SIDED with its TSMIS value (`MEDIAN BARRIER: Z- NO BARRIER`, 12,628.607) and recorded in the sidecar as `tsn_masked_categories` — disregarded, never zeroed, never hidden. **A category the print never MENTIONS still reports PARTIAL**, because that signals a parse or taxonomy drift rather than a locked source. `normalization_version` → 2 so an existing library rebuilds once. Red→green in `check_tsn_highway_summary_masked`. |
| D5 | **The TSN side is FROZEN at the 09/2025 cutover — so vs-TSN measures DRIFT, not agreement** | TSMIS replaced TSN, so there is no fresher TSN to pull (C4). Every vs-TSN comparison therefore pairs a live TSMIS export against a fixed September-2025 baseline, and the gap grows every month: at the 2026-08-17 export it is ~11 months, which is what dominates HD's 174,837 differing cells and HS's 89-of-92 differing categories. **Read those counts as migration drift, not defect.** The rows that stay diagnostic are the STRUCTURAL ones — HD's 2,850 only-TSMIS / 11,606 only-TSN (21 unconstructed TSN routes TSMIS doesn't export) and HS's 4 only-TSMIS categories. A canary IS still bindable, because the TSN half can no longer move: bind it to (frozen TSN snapshot × a NAMED TSMIS export), and re-running that exact pair detects TSMIS-side parser/consolidator regressions. It can never go to zero, and should not be expected to. |

### D-arc. Found building "Reports vs layers" (v0.39.0) — open

| # | Item | Notes |
|---|---|---|
| DA1 | ~~The three block effective dates are the weakest columns~~ — **CLOSED 2026-08-20 (v0.39.2)** | The rule was wrong, not just weak. `_block_eff_date` took the OLDEST date among all five member layers — measured on route 001 only, and its own docstring called it a candidate. Measured against the real 2026-08-17 export over 44-46k joined rows, each block's date is its **PRIMARY layer's own**: the travel way IS the roadbed, the median layer IS the median; surface / shoulders / special features / barrier / curb are attributes hanging off it. Falls back to the NEWEST of the rest only where the primary has no covering span (2.3% / 0.1% / 0.4%). **`LB Eff` 56.7%→79.0% · `Med Eff` 55.5%→79.4% · `RB Eff` 57.4%→79.7%**; statewide differing cells **211,448 → 180,078**, fully identical rows **9,525 → 19,132**, no other column regressed, pairing moved 41 rows. Every single-layer and pairwise alternative scored lower and all three blocks ranked identically and independently — a rule, not a fit. Opt-in (`primary_eff`); see DA5. Red→green in `check_arcgis_report`. |
| DA2 | ~~`RU Eff` has no source~~ — **CLOSED 2026-08-19 (v0.39.1)**. The Clean Road build carries `THY_POPULATION_EFF_DATE` from `SHS Population.InventoryItemStartDate` as a build-only 75th column (`chc.BUILD_ONLY_COLUMNS`; `chc.HEADER` stays exactly TSN's 74 because the library loads the raw extract through it as an exact gate, and `chc.ARC_HEADER` is the strict superset the build writes). CONTEXT vs TSN, which has no counterpart; COUNTED in the report comparison. **Measured: 4,470 differing cells on 45,138 matched rows = 90.1% agreement** — 4th-best of the 35 counted columns and above the 87% `Acc-Cont Eff` precedent it was modelled on. Every printed column now has a source; the report comparison has no context columns left. Side effect, disclosed: `RU Eff` is a printed column, so a change in it is a record boundary — records went 51,197 → 51,277 against the export's 51,327 (gap 130 → 50), but only 14 of those 80 new records paired, so one-sided rows grew by 52 (0.1%). Those are places our eff date changes and the report does not split — a small follow-on question, not a regression. **Owed on the owner's machine: the `CRH-SW-E2` clean-road canary re-bless** — the built sheet gained a column, and though it is context (counted cells should be unchanged, as `check_clean_road` proves on the synthetic library) the statewide run needs the staged TSN extract, which the dev box does not have. The old entry, for reference: | The report prints the Rural/Urban effective date on **99.3%** of rows (51,327 rows, 334 blank, 1,194 distinct). The 74-column THY table — TSN's own schema, which ours mirrors — carries eff dates for four blocks (`THY_LEFT_ROAD_EFF_DATE`, `THY_MEDIAN_EFF_DATE`, `THY_RIGHT_ROAD_EFF_DATE`, `THY_ACCESS_EFF_DATE`) but for population carries only `THY_POPULATION_CODE` / `THY_POPULATION_GROUP_CODE`. No date column, so the projection has nothing to print and emits empty + CONTEXT (counting it would be ~45,000 false differences). **The data is NOT missing.** `SHS Population.InventoryItemStartDate` is populated on all 12,706 rows and its as-of distribution matches the report's `RU Eff` in the same rank order — `1964-01-01` and `2010-12-31` lead both, 1,237 distinct layer values vs 1,194 printed — i.e. it IS the printed date. **Closing it is a known pattern**: `THY_ACCESS_EFF_DATE` already carries `SHS Access Control`'s `InventoryItemStartDate` the same way, and that single-layer passthrough shape scores 87.0% (vs ~56% for the three composite dates in DA1), so `RU Eff` should land near it rather than with the weak ones. **Cost, and why it is still an owner call:** it adds a 75th THY column TSN has no counterpart for, so it must be CONTEXT in the clean-road vs-TSN comparison, and it re-shapes the Clean Road build — a canary re-bless. |
| DA3 | ~~A same-date pair has never been run~~ — **CLOSED 2026-08-19** | Run on the 2026-08-19 layer drop, rebuilt as-of 2026-08-17 to match the export. **The vintage gap was not what the differences were made of**: closing eleven months moved the differing-cell count under 2% (see the measured block below). The drift explanation is therefore RETIRED — what remains is structural, and DA1 is most of it. Vintage still has to match for a run to mean anything, so the warning stays; it just is not the answer. Note the as-of does NOT follow the layer library — `resolve_default_asof()` takes it from the staged TSN extract, so a default build off fresh layers still reconstructs 2025-09-08. Set it explicitly in the Clean Road sub-tab's as-of box. |
| DA4 | **The other reports** — Intersection Detail DONE; Highway Log / Highway Sequence / Ramp open | **Intersection Detail SHIPPED**, and it proved the recipe generalizes past the shape Highway Detail set: it is a POINT report, so no segmentation, no merge rule, and it needed NO CA INTERSECTIONS clean-road build first — `IM Intersection Detail` already holds one row per intersection. `arcgis_reports.py` is now the registry the endpoints, the picker and the checks derive from, so the next report is a table row plus its two modules. Measured same-date statewide: 15,177 paired, 8,862 differing cells, 33 of 36 columns ≤1.3%. Its three rules and the residual are [comparison-engine.md](comparison-engine.md) §9l. **Still open:** Highway Log, Highway Sequence, and the Ramp reports (the Ramp ones want the CA RAMPS mapping — group G). |
| DA7 | **The Intersection Detail residual — 3 columns carry it** | `ML Eff-Date` 11.8%, `R/U` 8.7%, `HG` 5.6%; everything else is ≤1.3%. The ML/CS Eff-Date class is mostly the export printing a legacy default (`1964-01-01`) where the layer holds a real date — a finding about the report, not a build gap, and exactly what this lane exists to separate. `R/U` and `HG` are span-layer coverage: the carry-forward rule (DA-measured, per column) took them from 84.0%/90.7% to 91.3%/94.5%, and the rest is genuine holes in the layers. Worth one census before treating any of it as a defect. |
| DA8 | **~500 intersections have no Minor approach legs** | 3.2–3.6% of paired rows have the whole CS block blank on our side where the export prints values (CS mast arm/channelization/flow/lanes + Xing Line Lgth). The Major/Minor rule is right — this is the population where the layer records no Minor leg at all. Check whether a 4-way with all-Major legs supplies the cross-street values from the second Major pair before changing the rule. Disclosed in the comparison's Notes as a known weak spot. |
| DA5 | ~~The Clean Road build still uses the OLD block-eff-date rule~~ — **CLOSED 2026-08-20 (v0.39.3)** | Measured, and the DA1 rule wins there too, so it is now the DEFAULT for both builds. The dev box was never actually blocked: the extract is not staged in `tsn_library/` but `CA HIGHWAYS 09.08.2025.xlsx` sits in the corpus. Scored on a same-dated build, 52k joined rows — `LEFT` 57.73%→59.83%, `MEDIAN` 54.37%→62.01%, `RIGHT` 58.85%→60.15%. Confirmed end to end by a same-layers A/B of the statewide comparison: **differing cells 287,193 → 281,393 (−5,800), fully identical rows 2,841 → 3,687 (+846), pairing IDENTICAL at 52,629** — the rule moves values only. **Open, and bigger than the rule:** neither rule explains ~40% on the TSN side (both cap near 60%, where the same columns reach 79–80% against the report). Something else differs between our reconstruction and TSN's table on these columns. |
| DA6 | **Row boundaries are still not aligned — partially fixed, mostly DOWNSTREAM of DA1** | Censused rather than guessed. Of the report's 6,327 one-sided postmiles: **62.3% we never cut at all**, 37.7% we cut and the merge removed. Only **2.9%** of OUR one-sided postmiles are slivers near one of theirs, so the two sets are genuinely independent, not the same boundary misplaced. **Fixed (v0.39.3):** a landmark whose text REPEATS the record before it now starts its own record — worth +85 records (the old rule let an identical description merge). **Not fixed, and the diagnosis matters:** ~63% of our extra boundaries are driven by `LB Eff` / `RB Eff` / `Med Eff` changing, and those columns are still only 79–80% accurate — so most spurious splits are CAUSED by a wrong eff date rather than by a boundary rule. On their side `Description` leads (3,394 of 6,327), pointing at landmark coverage. Chase DA1's residual before treating this as its own defect. |

**Measured 2026-08-19 — the SAME-DATE baseline.** Read off the shipped comparison's own
Summary sheet (an earlier ad-hoc script produced numbers that did not reconcile with each
other or with the export's real row count; those are withdrawn). Both sides 2026-08-17:
the 2026-08-19 layer drop rebuilt as-of the export's day.

| | |
|---|---|
| Source table (the report's OWN build) | 54,649 rows · 252 routes · 102 unplaceable spans / 172 marked anchors |
| Report records | **51,064** (3,585 merged away) |
| TSMIS export rows | **51,327** |
| Paired locations | **45,097** · 5,967 only-ArcGIS · 6,230 only-TSMIS |
| Differing cells | **180,078** on 25,965 rows · **19,132 rows fully identical** |
| Counted columns | **35** — every column the report prints (DA2 closed) |

Per-column agreement is 81–99.5% everywhere except the three block effective dates
(55–57%, DA1). **The ~11-month-gap run of the same export measured 207,030 differing
cells against 206,875 at the same date — 155 apart, under 2%** — which is what retires
the drift explanation: the disagreement is structural, not temporal.

The headline 211,448 is ABOVE that 206,875 only because `RU Eff` joined the counted
columns (DA2): it contributes 4,470 of its own, and the remaining +103 is pairing noise
from 14 rows that re-paired. Read as agreement rather than as a total, the run improved —
a column that was 100% blank now agrees 90.1% of the time.

The 155 are themselves the CMP-AUD-245 fix, not network change: the marker cells that
were being counted as differences. Post-fix, exactly four columns move (`LB #Ln` −76,
`LB Wid` −77, `RB OT-TO` −1, `RB OT-TR` −1) and the other thirty are identical.

### E. Hygiene / low priority

| # | Item | Notes |
|---|---|---|
| E1 | ~~**5 grandfathered silent-swallow baseline entries no longer match**~~ | **CLOSED - 2026-08-31.** The count had drifted to **7** (the roadmap said 5): `day_matrix._folder_newest_mtime` x2 went with the v0.40.x consolidation onto `artifact_store.newest_report_file_mtime`, plus entries in `artifact_store`, `auth_nav`, `edge_device` and `owned_dir` whose enclosing def moved. Pruned with `check_silent_swallows.py --write-baseline` while the scan reported **0 NEW** swallows, so nothing new was grandfathered: the diff is **7 removals, 0 additions**, 113 entries retained. The check now reports 0 stale. |
| E2 | ~~**33 ruff F401s in `build/check_*.py`**~~ | **CLOSED - already done (v0.38.2); the line was stale.** Verified 2026-08-31: `ruff check --select F401 build` reports **All checks passed**, and `pyproject.toml` selects F401 with per-file ignores only for `scripts/common.py`, `scripts/gui_worker.py` and `scripts/matrix.py` - none for `build/`. So the rule is live there and finds nothing. |
| E3 | **gh-pages landing-page regen** | Owed since v0.17.0; website only ([website.md](website.md)). |
| E4 | **Clean-road sliver policy** | The 0.001-mi boundary-calibration class (rows keyed 9.256 vs 9.257) pairs one-sided today; a few hundred statewide. |
| E5 | The smaller standing items | In the themed sections below: cancel-latency, narrow-mode matrix polish, console `run_cli_multi` coalescing, the shared whitespace-collapse helper, doc/comment line-ref drift. |
| E9 | ~~**`check_updater` had a wall-clock flake that could fail a RELEASE**~~ | **CLOSED - 2026-08-31, found the hard way.** The v0.42.1 `release` workflow failed on `a persistent marker denial is retried within the bounded window` while `checks` passed TWICE on the same commit, so no GitHub release or assets were published until the job was re-run. The test drove `_wait_for_helper_ready` with a 0.01s budget and asserted the bounded loop polls more than once; on a loaded runner the first `read_text` can consume the whole budget, giving exactly one read. Widened to 0.5s against the same 0.001s interval (~500x headroom, still half a second) - test-only, no product change. |
| E6 | ~~Comparison speed — the two measured leftovers~~ — **CLOSED 2026-08-20 (v0.40.1)** | **(a) DONE.** Both sides were read twice: the loader read the consolidated TSMIS and the TSN workbook, then the Report View re-opened and re-parsed the same two files for its own columns. Those columns now ride the read the comparison already performs, with the projections factored so the capture and the standalone reader share ONE expression, and a fallback re-read whenever a caller doesn't thread the dict. **Interleaved 3 paired rounds on statewide Intersection Detail: 229.2s → 191.7s, 16.4% (1.20x), package digest identical across all six runs.** The re-reads themselves measured 14.0s (ID) and 27.9s (HD). Applies to the two Excel comparators and their two PDF flavors; guarded in `check_compare_{intersection,highway}_detail_tsn` (red-tested: removing the capture fails the gate). **(b) NOT TAKEN, now measured rather than asserted.** The one available lever was swapping openpyxl's pure-Python serializer for `lxml`: it produces **different bytes** (`8bbc51f8…` vs the canonical `4590abe3…`) and is worth **~2%** — it fails the byte-identity bar and buys nothing, besides adding a compiled dependency to the frozen work-PC bundle. An undistorted phase breakdown of the current 129s ID comparison shows why there is no hot spot left: `_write_data_sheet` 31.0s (24%), `_write_snapshot_sheet` 21.9s (17%), `_write_report_view` 20.5s (16%), `_write_comparison` 16.4s (13%), input loading 12.0s (9%), everything else 27.3s (21%). Writing is **70%** of the comparison, spread across four writers each serializing content the workbook must contain. The only remaining lever is writing LESS, which changes the output — see the note below. |
| E7 | ~~**The startup Edge sign-in check never says whether it WORKED**~~ (owner, 2026-08-20) | **CLOSED - v0.42.1.** `_maybe_active_env_check` announced the check and `_on_active_env_done` closed with a bare "Background sign-in check finished.", outcome-free by design - so the pane confirmed a check ran and never whether the saved session is good, the one thing wanted at startup. It now ends on ONE line built from the fields the check already posts (`via_device` / `signed_in` / `had_file` / `reason`): device sign-in, saved sign-in still works, NOT signed in + why, or stopped early having re-checked nothing. That last case is deliberately NOT phrased as a failed sign-in. UI-neutral per the console-free rule; four outcomes locked in `check_gui_bridge`. |
| E10 | **Excel vs TSN reports ~311+ PHANTOM one-sided rows from the equate convention** (found 2026-08-31, from an owner question) | The equate relation is canonicalized ONLY in the PDF-vs-Excel self check (`compare_highway_sequence_pdf`, guarded by `if self._same_source:`). Neither vs-TSN path gets it — and Excel-vs-TSN is where it costs. The vs-TSN key GLUES the equate suffix into the postmile, and the Excel export seats the `E` on the opposite member of the pair from TSN (annotation row vs target row), labels it `PM EQUATION` where TSN says `EQUATES TO`, and fills HG/FT the other two leave blank — statewide **407 rows** each way. So BOTH rows of each such pair miss, and the comparison reports a location as present in only one system when it is in both. Measured on the 2026-08-31 statewide pull: the PDF pairs **448** keys Excel misses (Excel pairs 26 the PDF misses, net **+422**, and the one-sided counts differ by **exactly 422 on EACH side** — the symmetric signature of a pairing miss, not missing data). **311 of the 448 (69.4%) are demonstrably equate rows** (82 `EQUATES TO` annotations + 229 `E`-suffixed targets); **the remaining 137 are UNATTRIBUTED and must be censused before any fix** — do not assume they are the same class. Not a flag flip: `canonicalize_equate_pair(rows_print, rows_excel)` derives relations FROM THE PRINT, and Excel-vs-TSN has no print side — TSN would have to play that role (it uses the same convention). Changes published counts on a regression-locked comparator, so it needs the full census/oracle discipline and a canary re-bless. **PDF-vs-TSN needs nothing** — the print already agrees with TSN. Until then, prefer the PDF edition for any vs-TSN delivery, and footnote the Excel one. |
| E8 | **The support bundle refuses to build when a TSN library carries BOTH sidecar shapes** (found 2026-08-31, during RB-5) | **The one item in E with a user-visible failure, and it disables the work-PC diagnostic escape hatch.** `evidence.collect` flattens `_state/` out of the archive name (`evidence.py:211-214`: `rel_path.parent.parent / rel_path.name`), so a library holding both the current `consolidated/_state/X.outcome.json` and the LEGACY sibling `consolidated/X.outcome.json` maps both to one member. The duplicate-member guard then correctly rejects the archive — and **no bundle is written at all**, so Settings ▸ collect-support-bundle silently yields nothing exactly when the user needs it. This is not a contrived shape: `consolidation_meta.read_path` / `legacy_meta_path` exist precisely because the sibling is the pre-organization location, so any long-lived library that gets rebuilt on a current build ends up with both — **the owner's own reference library under `Downloads\TSMIS\tsn_library\highway_log\consolidated\` already has it**. Fix the member naming (don't collapse `_state/` into its parent, or de-duplicate deterministically preferring the organized file); keep the guard. Reproduced via `check_validation`, which fails only when such a library is staged and passes with it moved aside. |

> **Where comparison speed went next — SHIPPED in v0.41.0.** E6(b) closed with
> "writing is 70% and every byte of it is required", which is only true while the
> workbook is the deliverable. **Counts only** (`mode="preview"`) skips that 70%
> rather than shaving it: the comparison runs in full and returns its typed
> truth without writing anything — statewide Intersection Detail 185.9s → 20.4s
> (9.1x), counts identical to the build's including the per-column breakdown.
> The design constraint named here before it was built held: a preview commits
> no artifact, so it has no generation and cannot certify a cell, and it is kept
> that way structurally (its own store, outside `_staleness`; never `mx-match`;
> cleared by a real build). See [comparison-engine.md](comparison-engine.md) §2c.

### F. Design-first / gated — **NOTHING OPEN.** All of F is shipped (verified 2026-08-18)

F was stale: it read as an unstarted architectural project long after the work had
landed. A Step-0 code verification of all 13 owner observations (2026-08-18, at the
owner's "you can do all the F") found **every one already implemented** — most in
v0.30.0–v0.32.0, the last one fixed that day. The evidence, item by item:

| # | Item | Verified state |
|---|---|---|
| F1 | **Output-model unification** (items 9 / 10 / 11 / 13) | **DONE.** Its own spec has said "RESOLVED IN EFFECT" since 2026-07-23. Re-proved in code: all three export surfaces (`exporter`, `exporter_parallel`, `gui_worker_export`) default to `output_run_dir(src, env)/subdir` — there is no second export layout; `paths.py` owns every comparison tree (`comparisons_root` / `manual_comparisons_dir` / `arcgis_comparisons_dir`); `resolve_route_file` front-anchors the run identity on per-route files and `stamped_consolidated_filename` on consolidations. |
| F2 | ~~sol-002 — export-engine mechanics~~ | **DONE, and the Sol dispatch is moot** (owner, 2026-08-18: "that sol plan was from way before"). Its charter was item 12 + the export side of 9/13, all shipped in v0.32.0: coalescing runs on BOTH paths — `run_export_combined` (standard) and `run_export_parallel_combined` (fast mode) — guarded by `check_coalesce_editions`, with `check_route_file_naming` holding the dated-name contract. |
| F3 | The [app-consistency backlog](planning/app-consistency-backlog.md) | **DONE — 13 of 13.** 1 (`compare_timings` wired into `gui_worker_matrix` for logging + ETAs) · 2 (`pdf_excel_matrix.py`) · 3 (`check_report_wiring`) · 4 (**was a real bug — fixed v0.38.2**; the day-column drag persisted but never repainted) · 5 (`day_out_path`/`out_path` embed day + source + baseline token) · 6 (`list_output_days_for_report` behind the consolidate picker) · 7 (`manual_comparisons_dir()`) · 8 (`get_compare_folders` filters, folder-kind) · 9/10/11/13 (F1 above) · 12 (F2 above). |

Its one living descendant, **item 15** (a consolidate-style day dropdown for FILE-kind
manual comparisons), **shipped in v0.38.2** — see the Compare-tab entry below. This
whole family is now closed.

### G. The next large build

| # | Item | Notes |
|---|---|---|
| G1 | **CA INTERSECTIONS + CA RAMPS clean-road builds** (DEF-05) | On the v0.29.0 CA HIGHWAYS pattern; mappings already censused in [planning/cleanroad-highways.md](planning/cleanroad-highways.md). `tsn_load_clean_road` deliberately has no normalizer for these two slots until their builds land. |

### H. The bounded output-audit program — RB-6 IMPLEMENTED, awaiting review

**This group was missing from the inventory until 2026-08-20 and is the largest
genuinely-open block of work in the repo.** The post-comparison output program
(`planning/post-comparison-perfection-output-audit/`, entry point
[START-HERE.md](planning/post-comparison-perfection-output-audit/START-HERE.md))
ran Stages 1–3 to a jointly-approved plan and has merged five of its six bundles.
**RB-1 · RB-2 · RB-3 · RB-4 · RB-5 are merged, and RB-6 — the last — is
IMPLEMENTED and awaiting its two adversarial reviews.** RB-5 merged 2026-08-31
after two independent Codex approvals and shipped in v0.42.0; H1 and H2 below are
closed by it. RB-6 was implemented 2026-08-31 on
`hotfix/rb-6-hygiene-and-guards` from base `62bb0f3`; it is not merged and not
released.

| # | Item | Bundle | Verified state (H3–H5 re-verified 2026-08-31, during RB-6 Stage 4) |
|---|---|---|---|
| H1 | ~~**HF-06 — Highway Sequence self-check equation classification**~~ (PCOA-FINAL-011, P1) | RB-5 | **CLOSED — v0.42.0.** The self check normalizes the by-design equate relation before comparing: statewide **3,714 → 7** differing cells over the same 60,254 locations, the seven survivors being genuine one-sided `E` markers that must keep reporting. Pair-aware, so the moved suffix closes too; fires only where the print declared an equate; a duplicate postmile group it cannot resolve by content is left alone. HSL vs-TSN counts unmoved. |
| H2 | ~~**HF-09 — representation-only difference classification**~~ (PCOA-FINAL-013, P2) | RB-5 | **CLOSED — v0.42.0.** Five families gain one Summary line saying how much of the differing-cell total is punctuation/spacing/quoting/case rather than data (HL 1,243, HSL 12, ID 1, RD-PDF 3, plus Clean Road). Disclosure only — every cell keeps its `D` state and every published total is unchanged, proved base-vs-head per family. Follow-up **RB5-R2-FU-001**: the class key keeps only ASCII, so a dropped accented letter can be *labelled* presentation-only; it stays flagged and counted. |
| H3 | **HF-07 — missing-side fast fail and export coverage truth** (PCOA-FINAL-015 / -018, P2) | RB-6 | **IMPLEMENTED, awaiting review.** The preflight refuses through the empty side's OWN loader before anything is parsed: measured on the real 217-print statewide Intersection Detail export, **439.9 s → 0.49 s**. The export-only set had to be re-derived — `highway_summary` gained its comparisons in v0.37.0, so it is `ramp_summary_excel` / `intersection_summary_pdf` / `highway_summary_pdf` now, still 343 of 2,380 files (14.4%). |
| H4 | **HF-08 — TSN normalization identity determinism** (PCOA-FINAL-017, P2) | RB-6 | **IMPLEMENTED, awaiting review.** Root cause ESTABLISHED and it is **two** clocks: openpyxl stamps `docProps/core.xml` with the wall clock at save, and `zipfile` stamps every member's `date_time` at MS-DOS two-second resolution — which is why early probes looked clean by luck. Both are pinned at an opt-in save boundary used only by the TSN library. **Expect ONE full re-comparison after this merges**: the fix moves every dataset's identity token once, by design. |
| H5 | **HF-11 — source-side escalation and must-not-regress guards** (PCOA-FINAL-020 / -021 / -022) | RB-6 | **IMPLEMENTED, awaiting review.** Both prose guards are executable and fail against a deliberate regression; no `scripts/` change. Route 140 became [VEN-01](vendor-escalations.md) — and the census sharpened it: the four columns are blank on **one day only** (2026-07-23), complete two weeks earlier, complete in that day's own print, complete on the same day's route 138. |

**Read the plan against today's code before starting, not just as written.** It
froze at **v0.35.0** and the tree has moved thirteen releases since. RB-6's
implementation had to correct three stale scope statements against live code —
the export-only set, the count of supported TSN datasets, and one print family
the plan assumed had a parser — all recorded in
[RB-6/IMPLEMENTATION.md](planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-6/IMPLEMENTATION.md).
`IMPLEMENTATION-PLAN.md` remains authoritative over the per-bundle `BUNDLE.md`,
and every Stage 4 must record the exact clean `main` base before touching code.

**Weigh the process cost honestly when ranking this.** Each bundle carries two
independent adversarial review rounds, and RB-2 consumed ten of them on column
widths. Per the standing proportionality rule, match review depth to what the
change can actually break: H2 cannot move a single count by contract, and H1 is
scoped to one comparator's self check.

---

## How to maintain this file

- **Format.** Open item `- [ ]`; done `- [x] ~~…~~ **Done (vX.Y.Z / <commit>)**`. Tag features
  with a rough size `[S/M/L]`; tag code-review findings with severity `P0–P3` + a `slug`.
- **Sections (keep this order; don't reshuffle):** *Next patch* (the immediate worklist) →
  *Feature backlog* → *Standing & cross-cutting* → *Shipped (reconciled record)*. File new items
  under the matching section; start a new theme only if nothing fits. Bugs go under *Next patch*
  (or the findings record), not the feature backlog.
- **Reconcile every session / after each release** — the list rots otherwise. Compare the open
  items + the version table against `git tag` / `version.py` / `CHANGELOG.md`; check
  off what shipped (one line), update the version table to reality, and **flag anything deferred
  across multiple releases** for a keep / drop / bump decision. Record *what* shipped; the owner
  decides *where* deferred items go next.
- This is the backlog, **not** the changelog — keep "done" notes to one line; detail lives in
  `CHANGELOG.md` and the docs.

---

## Next version (v0.18.5) — what's actually owed

> **v0.18.2 / v0.18.3 / v0.18.4 shipped as field-driven hotfixes (2026-06-29)** — v0.18.2: comparison
> progress feedback, the large-report formulas-twin skip, Route Suffix in the Report View; v0.18.3: the
> intersecting-route-postmile 0-vs-blank fix + one-sided locations in the Report View; v0.18.4: the matrix
> queue-phantom (a finished compare stuck "running" in the queue panel). None completed the work-PC field
> sign-off below, so that sign-off (plus the small ride-alongs) now cuts as **v0.18.5**, and the
> "operational / enterprise-ready" claim moves with it.

> The single live worklist. Almost everything still owed collapses into ONE effort — the **work-PC
> field sign-off** (the dev PC can't reach TSMIS). The §J2 dispositions + the Phase-3 list below are
> the historical reconciliation record; *Feature backlog* / *Standing* hold the longer tail.
> v0.18.0's final review found **no offline leftover** — the only product TODO is this field gate;
> everything else is already **Shipped** (§ below) or an explicit **deferral** (the minor opportunistic
> carry-overs from the overhaul are under *Standing → Restructure leftovers*).

**1 — Work-PC field sign-off (GATES v0.18.5).** One session on the locked-down PC: run v0.18.4,
`--collect-evidence`, and confirm the live paths the dev PC can't. Full checklist + acceptance
criteria: [work-pc-validation.md](work-pc-validation.md) §3.
- [ ] The two **v0.18.1 field bugs** live — Intersection export selects on the **nested dev menu**
  (`data-value`); the matrix / by-day **queue clears** after a job drains; the flat **prod** menu still selects.
- [ ] **Carried live paths** — partial **keeps last-good**; stage-and-swap under Defender/lock; a real
  **paused-batch resume across a restart**; the **v0.17→v0.18 self-update**; both frozen exes + the source ZIP run.
- [ ] **P8c** — exact `select_report`, CDP open-on-demand / close-on-capture, cancel-in-recover latency.
- [ ] **Intersection Detail (PDF)** live — export → consolidate → PDF-vs-TSN / PDF-vs-Excel on the real files.
- [ ] **Evidence-driven parser fixes** (need the returned real PDFs) — ramp-summary parse-failure
  misattribution + duplicate-pop misassignment, via the P12 row-oracle. Land offline-RED-proven, then re-bless.

→ Cut **v0.18.5** as the operational sign-off ("enterprise-ready" is claimed here, never before).

**2 — Small & ready (ride along with the sign-off run):**
- [ ] **TSN-library auto-rebuild on a normalization-code change** [S] — `tsn_load_*.build_into` stores
  ALREADY-normalized values, so a normalization fix (e.g. v0.18.3's numeric-0 postmile) does NOT reach an
  existing library; compare-time `_normalized_row` can't recover lossy values (a 0 blanked at build time stays
  blank). Today the user must hit Settings ▸ TSN reports ▸ Rebuild, and it "looks unfixed" until they do (the
  v0.17.6 trap recurring — bit the v0.18.3 Intrte-Postmile fix). Fix: stamp the library with a normalization
  version + auto-rebuild from the stored raw when stale. *(Deferred — user "fine for now" 2026-06-29.)*
- [ ] **gh-pages landing-page regen** — owed since v0.17.0; website only ([website.md](website.md)).
- [ ] **cancel-latency** [S] — poll `should_cancel` in `preflight` / `select_report` (the ~60 s county-enable
  wait) / `_recover` (mid-batch re-login) so Stop interrupts the after-sign-in / recovery windows (same opt-in
  `should_cancel` pattern; verify live — the waits are field-hardened). *(v0.17.1 follow-up.)*
- [x] ~~**narrow-mode** [S] — (<980 CSS px, e.g. 1366×768 @150% DPI) matrix-tab polish~~ — **CLOSED
  2026-08-21, already fixed; this entry had gone stale.** Measured in the `#mock` at exactly 910×512
  (a 1366×768 work PC at 150% DPI): **the stray idle cards are gone** — preflight, completion and
  progress are all hidden on the matrix sub-tab — the grid renders with all its cells, and there is
  **zero horizontal overflow on any of the six tabs**. The rules the entry says are trapped in
  `@media (min-width:980px)` were moved out into a "matrix mode at ANY width" section, which is what
  hides the cards and tightens the cells regardless of window size.
  **The "cramped Matrix-options panel" is now a deliberate decision, not a defect.** A
  `@media (max-width: 979px)` block caps it at `46vh` (measured 235px of 561px content, scrolling
  internally) and caps the log at `22vh` and the grid wrap at `62vh`. That is the right trade and the
  CSS says why: below the breakpoint the columns STACK, so an uncapped ~530px options card would push
  the grid you opened the tab for into a sliver at the top of a very long scroll. Capping it is what
  keeps the grid worth looking at. Re-open only if the owner wants a different split, not as a bug.
- [ ] **wide-layout column split — needs ONE look in a real window** [S] — a note from the v0.38.2
  session says `body.matrix-wide .col-config { flex-grow: 3.4 }` computes to `1`, i.e. the matrix
  column never actually widens. **Unverifiable in the `#mock`**: the preview pane does not composite
  frames, so width and computed flex values there are unreliable (it reported `flex-grow: 0` and 2px
  columns at 1280px while the same page measured correctly at 800px). By inspection the CSS is right
  — only two rules match `.col-config`, `flex: 1 1 0` (grow 1) and the higher-specificity
  `body.matrix-wide` grow 3.4, both inside the same matching media block, and nothing sets 0 — so
  this is either already fine or a subtle cascade issue that only a real window will show. **Open the
  app on a normal monitor, switch to the Everything ▸ Comparison-matrix sub-tab, and see whether the
  left column visibly takes ~3.4x the right.** If it does, delete this item. Cost: ten seconds.
- [x] **Manual Compare: consolidate-style day dropdowns** [M] — **DONE (v0.38.2).** Every FILE-kind
  recipe now offers an Export-day dropdown that fills BOTH sides: the same day's other edition for a
  PDF-vs-Excel self-check, the TSN library's current dataset for a vs-TSN one. It lists only days
  already CONSOLIDATED (it resolves files, never builds one), defaults to the newest so the common
  case needs no clicks, labels a day whose TSN side is unresolved as "this side only", and drops to
  a browse sentinel the moment a file is hand-picked. `get_compare_days` resolves the two sides by
  inverting `report_catalog.MATRIX` on `tsn_key`/`self_key` (`compare_file_sides`), so a new report
  joins automatically; `check_report_wiring.test_compare_day_picker_resolves` fails if a recipe ever
  declares a comparison whose consolidator was never registered.
- [ ] **Console `run_cli_multi` coalescing** [S] — the `.bat` multi-export doesn't coalesce dual-edition
  pairs; share `_coalesce_groups` (move it off `gui_worker_export` to a neutral module) so the CLI groups
  too. (GUI standard path v0.19.2; fast mode + matrix steps v0.32.0.)

**Site-gated (not on our schedule):** **Highway Summary enablement** — export shipped app-side (v0.19.1)
but the report is still `cs-disabled` on the site; consolidate/compare integration follows the Highway
Detail recipe once a real export exists (see *Feature backlog*). Highway Detail itself is DONE (v0.20.0).

**Parked — pull in only by a separate decision:** code-signing (SignPath cert), DPAPI at-rest auth,
`compare_core` min-cost-pairs, the A3 / C1 / D1 / F1 feature backlog, and the two
upstream TSMIS-team reports (all in *Standing & cross-cutting* / *Feature backlog* below).

---

## v0.18.0 — audit reconciliation (§J2 dispositions)

v0.18.0 pulled in the offline-doable Phase-3 audit residue and dispositioned the rest. Every
still-open finding at the v0.17.1 baseline now has an individual outcome (this supersedes the open
checkboxes in the *Next patch* section below — that list is the historical worklist):

**Resolved in v0.18.0** (a phase implements + locks it):
- **P0** — `handle-no-default-branch` (the `_handle` else-log), `gui-worker-stale-tkinter-docstring`,
  `env-compare-side-label-cap-truncates-distinguisher`, `ramp-summary-combined-sheet-hardcoded-coordinates`
  (schema-length guard).
- **P1** — `run-report-only-written-when-per-route-nonempty`; `pdf-page-skip-unlogged-when-no-prior-geometry`
  + `pdf-stale-geometry-carryforward-silent-corruption` escalated to a producer-owned **partial** so dropped
  output is never promoted/cached as complete.
- **P6** — `support-bundle-settings-future-leak` (the diagnostic-settings allowlist).
- **P7a** — `device-ok-inferred-from-any-completed-run`, `reset-token-consumed-before-task-gate`.
- **P8c** (offline-proven code; **live acceptance → v0.18.1**) — `select-report-substring-match-no-exact-guard`
  (exact-match guard), `edge-login-cdp-port-unauthenticated-loopback` (open-on-demand / close-on-capture),
  `select-report-not-rearmed-between-routes-on-stale-form`, `login-busywait-no-cancel-check`,
  `unlogged-no-download-empty-on-pdf-and-misc`.
- **P10 / §J updater set** — `size-and-checksum-guards-both-skippable` → **fail-closed** checksum,
  `extractall-zip-slip-relies-on-stdlib`, `staged-exe-launched-from-user-writable-dir-no-recheck` (re-hash
  before swap), `no-rollback-when-relaunch-launches-partial-tree`, `swap-log-grows-unbounded` (rotate),
  `webview-cache-cleared-on-every-dev-launch` (frozen-only), `immediate-death-check-narrow-window` (hardened
  window), `dl-socket-timeout-may-fail-slow-large-downloads` (timeout + bounded retry),
  `releases-list-capped-100-revert-blindspot` (paginate). Plus a hash-pinned reproducible build +
  `release.yml` per-variant `.sha256` enforcement.
- **P12** — `reset-follows-junctions-symlinks` (junction/symlink guard, dev-PC verified) **and the M03
  destination-ownership marker, NOW IMPLEMENTED** (the deferred R1-M03 item); `consolidate-overwrite-toctou`
  (confirm-then-appears re-check at the final replace); the independent **PDF expected-row oracle** harness.

**v0.18.1 evidence-driven** (offline harness shipped; **real-PDF / work-PC acceptance owed** — RM04):
- `ramp-summary-parse-failure-misattributed-to-source`, `ramp-summary-duplicate-pop-pattern-misassignment`,
  `pdf-consolidator-no-row-count-verification` (the P12 row oracle), and the stale-geometry **emit**
  elimination — **RESOLVED in v0.26.2**: a carried-geometry page is now VALIDATED read-only
  (`pdf_table_lib.carried_line_crossings` — every printed token's chars must land in ONE window, the
  same char-center test `assign_columns` places by, so a 0 score certifies the assignment); a
  committed fixture reproduces the exact failure mode (a foreign/drifted layout splits tokens), and
  only a page whose text does NOT fit the carry keeps the ⚠ + PARTIAL. The blanket flag had marked
  every HL (PDF) day "inputs incomplete" (~280 normal zebra-parity band-less pages per statewide
  set — the work-PC field report of 2026-07-10); statewide census + re-verify in
  `ground-truth/All Reports 7.9/_verification-scripts/`.
- The carried live-verify set (P1 partial-keeps-last-good, P2 stage-and-swap, P3 resume-across-restart, the
  P8c live paths, the P10 v0.17→v0.18 self-update, **and the Intersection Detail (PDF) live reconciliation**).
  Full checklist: [work-pc-validation.md](work-pc-validation.md) §3.

**Discovered during P11 (docs reconciliation):**
- `wait-js-fstring-interpolation-unvalidated` (P3) — **RESOLVED in v0.18.1.** The plan's §J2 had recorded
  this Resolved in P8b, but at the v0.18.0 HEAD `exporter.py` still interpolated `spec.wait_js(route)` with
  **no config-error validation**. v0.18.1 added `exporter._build_wait_condition(spec, route)`, which
  validates the spec's `wait_js` is a non-empty JS arrow string before interpolating and otherwise raises a
  clear `PreflightError` + `log.error` (instead of a cryptic Playwright eval error / a full route timeout).
  `route` is app-controlled, so this is a config tripwire, not input sanitization. Locked by
  `check_export_engine.test_wait_condition_validation`.
- `non-hl-loaders-dont-collapse-tab-whitespace` (CR-002) — the Highway Log and Highway Sequence vs-TSN
  loaders collapse tab/whitespace at load, but **Ramp Detail and Intersection Detail do not**. A known
  normalization inconsistency; **still deferred** (low impact — the locked counts stand). Revisit if a
  tab-bearing value ever causes a spurious diff.

**Hard-deferred (each needs an explicit separate user decision — RM06):**
- **DPAPI at-rest auth** (O2 / `auth-file-plaintext-no-acl-dpapi`) — DPAPI breaks `storage_state_is_portable`;
  v0.18.0 did the ACL/atomic-write half (P6), not encryption.
- **Runtime signature / code-signing cert** (A03 / `update-trust-is-tls-plus-sibling-sha-only`) — blocked on
  the SignPath cert; workflow signing parity only, no runtime signature verification yet.
- **`compare_core` `min-cost-pairs` greedy-not-optimal** — inside the regression-locked engine; any fix needs
  a full cell-for-cell re-proof and the 8+ duplicate-key-group frequency is unquantified.

---

## Next patch — code-review fixes (Phase 3 review, 2026-06-18)

> **Reconciled by v0.18.0 — see the §J2 dispositions above.** The open `- [ ]` items below are the
> historical Phase-3 worklist; their v0.18.0 outcome (Resolved / v0.18.1 evidence-driven / hard-deferred)
> is recorded in that section. Kept here for the code anchors + the field-verify notes.

A read-only review (6 risk-domain auditors + adversarial refutation) over commit `0a4c071`
confirmed **45 findings (5 P1 · 17 P2 · 23 P3)**; 12 candidates were rejected on refutation. Full
report with code anchors + fix sketches: `code-review/AUDIT-phase3-0a4c071.md` (git-ignored). Do
the field bug + P1s first.

### Field-reported (work-PC logs — CONFIRMED in the field)
- [x] **`update-stage-rename-no-retry`** ✅ **Done (this update)** — wrapped the extract→staged
  rename (+ the follow-on cleanup rmtree) in the swap step's `_retry` (12×0.5 s) so a transient
  Defender/indexer lock retries instead of aborting the stage. Locked by `check_updater.py`
  (`test_stage_rename_retries` + `test_retry_recovers_transient_oserror`). ⚠ FIELD-VERIFY on the
  work PC that staging no longer fails (the Defender timing only reproduces there). Original
  evidence: `code-review/field-update-stage-rename.md`; note in
  [internals/updater-swap.md](internals/updater-swap.md) §3.

### P1 — product-risk / data-loss / security (do first)
- [x] **P1 `navigate-accepts-wrong-env-after-one-reload`** ✅ **Done (this update)** — added
  `common.require_site_params(page)` on the export path (after `require_signed_in`), raising
  `PreflightError` when the app is on a different env/src than selected; no-ops when undeterminable.
  Locked by `check_export_engine.py` (`test_require_site_params`). ⚠ LIVE work-PC re-test (only a
  real site returning the wrong env after OAuth truly exercises it).
- [x] **P1 `empty-routes-read-as-export-complete`** ✅ **Done (this update)** — `renderCompletion`
  shows an amber "Finished with no data" when `saved+exists===0 && empty>0`; `appendLog` no longer
  paints a `saved 0` summary green. Verified in the `#mock` preview.
- [x] **P1 `transient-export-click-failure-recorded-empty`** ✅ **Done (this update)** — a no-download
  `EmptyExport` now PROPAGATES from `_attempt_route`; `_process_route` retries it once in-loop and
  records `empty` only if it reproduces (a positive `is_empty` match stays immediate empty). Locked by
  `check_export_engine.py` (`test_attempt_route_empty` + `test_process_route_empty_retry`). ⚠ LIVE
  work-PC re-test (the true transient click flake only occurs against the real site).
- [x] **P1 `reset-deletes-unvalidated-batch-dest`** ✅ **Done (this update)** — `reset_targets` now
  scopes the Export-Everything store to its known `<src-env>/` children (never rmtree's the dest
  wholesale; foreign files untouched); `reset_preview` returns the real `str(path)`s and the confirm
  dialog shows each under its label. Locked by `check_b3_batch.py` (`test_reset_scopes_batch_dest`);
  dialog verified in the `#mock`.
- [ ] **P1 `update-trust-is-tls-plus-sibling-sha-only`** — auto-update authenticity = TLS (Windows
  store → a TLS-inspection root is trusted) + a same-release `.sha256`; **no signature**.
  Code-signing (Standing § below) is the fix; consider a pinned-in-build public key.

### P2 — bounded correctness / robustness / IT
- [x] **P2 PDF Highway Log silent-drop trio** (`pdf-stale-geometry-carryforward-silent-corruption`,
  `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-consolidator-no-row-count-verification`)
  ✅ **Done (v0.17.0 Phase 1)** — `consolidate_tsmis_highway_log_pdf.parse_pdf` now returns a `stats`
  dict (emitted / skipped_no_geometry / stale_geometry_pages); data-looking lines on a page with no
  column band are COUNTED + logged (WARNING), pages parsed with carried-forward geometry are flagged
  once each (NOTE), and `consolidate()` leads with a ⚠ INCOMPLETE / carried-forward banner. Reporting
  only — the row-emit logic is byte-identical (PDF comparisons unchanged). Locked by
  `check_tsmis_pdf_reconcile.py`. (The TSN sibling already logs per-route row counts.)
- [x] **P2 `report-error-text-blanket-swallow-hides-fatal`** / **`highway-sequence-errored-route-can-record-empty`**
  ✅ **Done (this update)** — `report_error_text` now LOGS the swallowed probe exception (no longer
  silent), and Highway Sequence's `is_empty` keys on the POSITIVE "No results found" text (hsl.js)
  instead of Export-button absence, so an error page is no longer misread as empty. Locked by
  `check_export_engine.py` (`test_report_error_text` + the Highway Sequence marker checks). ⚠ LIVE
  work-PC re-test of the error-page path.
- [x] **P2 `auto-consolidate-rmtree-out-dir-before-export`** ✅ **Done (this update)** — the Everything
  store now STAGE-AND-SWAPS: each report exports into a `.staging` sibling, swapped into place only on
  a clean finish (discarded on cancel/crash), so a failed refresh never destroys the last-good copy.
  Locked by `check_b3_batch.py` (`test_swap_store_dir`). ⚠ LIVE work-PC re-test of the end-to-end
  crash-preserves-last-good path.
- [ ] **P2 `edge-login-cdp-port-unauthenticated-loopback`** — the headed-Edge fallback opens an
  unauthenticated CDP port on `127.0.0.1` for the whole live SSO session. Open it only when CDP
  recapture is needed; close on capture.
- [ ] **P2 `auth-file-plaintext-no-acl-dpapi`** — re-confirms the auth-at-rest item (Standing §).
- [x] **P2 updater integrity** (`size-and-checksum-guards-both-skippable`,
  `immediate-death-check-narrow-window`, `no-rollback-when-relaunch-launches-partial-tree`,
  `swap-log-grows-unbounded`, `dl-socket-timeout-may-fail-slow-large-downloads`)
  ✅ **Done (sol-001, integrated 2026-07-17 @ merge `7a7f0e7`).** Checksum verification is
  fail-closed even when size is absent (proved); the 1.5 s death poll → a **nonce readiness
  handshake** (the staged helper must prove it opened the original PID handle before the old app
  closes — no arbitrary window); a partial rollback now **suppresses relaunch** (never starts a
  mixed tree) and the dialog stays truthful; the helper log rotates at 256 KiB; the download has a
  60 s socket timeout + bounded retry. Red→green in `check_updater`; backward-compatible across all
  upgrade/revert directions. Work-PC re-verify (frozen swap/relaunch + Revert) owed. See
  [docs/agent-handoffs/STATUS.md](agent-handoffs/STATUS.md) "sol-001 integration record".
- [ ] **P2 `select-report-substring-match-no-exact-guard`** — `select_report` uses `has_text` +
  `.first` (substring) while the env-scan uses exact-first; a future superstring option could
  silently mis-export. Match exactly.
- [x] **P2 `parallel-reconcile-uses-read-strict-not-lock-tolerant`** / **`parallel-crash-plus-cancel-skips-reconciliation`**
  ✅ **Done (this update)** — extracted `_reconcile_unaccounted`: it now uses the lock-tolerant
  `_can_resume` (an Excel-locked-but-complete file is trusted, not re-failed) and still reconciles on
  cancel when a worker CRASHED (so a crash's orphaned routes always reach the run report). Locked by
  the new `check_parallel_reconcile.py`. ⚠ LIVE work-PC re-test of the real crash+cancel path.
- [ ] **P2 `handle-no-default-branch`** — `gui_api._handle` silently drops an unrecognized message
  kind; add a logging `else`.
- [ ] **P2 ramp-summary parsing** (`ramp-summary-parse-failure-misattributed-to-source`,
  `ramp-summary-duplicate-pop-pattern-misassignment`) — a parser schema-miss is attributed to the
  source PDF; the Population-group pattern disambiguates two identical regexes only by document order.

### P3 — hygiene (batch where cheap; 23 items)
- [ ] Stale `gui_worker.py` Tkinter module docstring; the magic `wait_for_timeout(1000)`;
  `update_helper.log` rotation; dev WebView-cache clearing; the `_min_cost_pairs` greedy cliff at
  8+ duplicates; ramp-summary combined-sheet hard-coded coordinates; etc. — full list in the report.

---

## v0.15.0 — the Everything comparison matrix  ✅ SHIPPED (2026-06-19)

**Shipped — v0.15.0** (tag pushed, GitHub release live; updater offers it to users). Built on
`feat/everything-matrix`, merged to `main`. Carried an **app-wide UI polish + motion pass** —
the matrix controls set the bar and the rest of the app was brought up to it (motion tokens,
bordered secondary buttons, consistent title-bar-vs-card controls, reduced-motion-safe entrance
animations); see [gui.md](gui.md) "Motion layer + control polish". (Items below kept for the
work-PC live-verify list.)

- [x] **Stage-1 foundation audit** — see the closed-findings record below.
- [x] **8 groundwork code-review fixes** — the field bug + 4 P1s + 3 P2s above are checked off.
- [x] **Comparison matrix [L]** — report × environment grid on the Everything tab. Engine
  `scripts/matrix.py` orchestrates `compare_env` (compare_core untouched): per-cell export +
  comparison freshness (mtime staleness), comparisons cached per baseline under
  `<dest>/comparisons/<baseline>/` (stable dateless names) + a `_results.json` verdict/count cache,
  baseline switch = explicit full recompute. Cells show the **discrepancy count, color-coded**
  (green identical → amber/red by magnitude, stale, needs-export). Per-cell refresh-export
  (live) / refresh-comparison (offline) + refresh-all. Bridge in `gui_api` (`matrix_info`,
  `set_matrix_baseline`, `refresh_cell_export`, `refresh_cell_comparison`, `recompute_matrix`);
  workers `MatrixCompareWorker` / `MatrixExportWorker` (the latter reuses ExportWorker with NO
  manifest, so it can't clobber a paused batch). Locks: `check_matrix.py`, `check_matrix_bridge.py`.
- [x] **export-date-in-UI [S]** — per-(report,env) freshness from file mtime
  (`report_library.cell_ages`), surfaced in the matrix cells (no filename changes — the store
  overwrites in place). Lock: `check_report_library.py`.
- [x] **Intersection app-wide disable [S]** — one gate (`reports.DISABLED_EXPORT_SUBDIRS` +
  `export_reports_status`) shows Intersection **greyed/unpickable** (not hidden) in the Export tab +
  Everything report lists, excludes it from the Saved-reports library + matrix, and rejects it
  server-side; `EXPORT_REPORTS` indices stay stable. Flip back by emptying the set. Lock:
  `check_intersection_gate.py`.
- [x] **Matrix → Everything sub-tab + multi-mode + TSN [L]** (the new phase) — the matrix moved to a
  full-width **sub-tab** of Everything; Highway Log is now **two rows** (Excel + PDF); each row has a
  **comparison-mode dropdown** (cross-env / vs TSN (Excel|PDF) / TSMIS PDF-vs-Excel; greyed where no
  code) + a **TSN file picker**. A **config zone** under the slim activity log holds report +
  **environment-column** show/hide toggles and a global "set all". Refresh is per-cell / **per-row** /
  **per-column** / all, **cancellable + resumable**. TSN drops → `<dest>/_tsn_input/<subdir>/`, sheets →
  `<dest>/comparisons/tsn/`. Additive only — the manual compare code is untouched (the PDF *consolidator*
  gained an additive input_dir/out_path override). App-wide **motion layer** + slow theme cross-fade
  landed alongside. Locks: `check_matrix.py`, `check_matrix_tsn.py`, `check_matrix_bridge.py`.

**Owed on the work PC (live; can't verify on the dev PC):** the field bug's Defender-timing fix; the
wrong-env backstop; the transient-empty retry; `report_error_text`/Highway-Sequence empty;
batch stage-and-swap crash-preserves-last-good; parallel crash+cancel reconciliation; the
matrix's **live per-cell Refresh export** + a full **baseline-switch recompute over a real 6-env
store**; and the **live TSN / PDF-vs-Excel comparisons** (consolidate-store-folder → compare glue;
the compare adapters themselves are already golden-locked). Before releasing: bump `version.py` +
`build/release_notes.md`.

---

## v0.16.0 — matrix queue + fast mode + Compare-tab "TSN by-day" matrix  ✅ SHIPPED (2026-06-19)

Two undertakings, one feature release (committed in stages A → shared-engine factor → B).
Also the release that **field-tests the updater rename-retry fix** (v0.15.0 → v0.16.0).
`compare_core` stays untouched — orchestration only. Golden coverage:
`check_matrix_bridge.py` (queue) + `check_day_matrix.py` (by-day matrix).

**A — Everything-matrix upgrades (commit `a5d7d05`):**
- [x] **Row/column header buttons with distinct icons** — two buttons per header matching the
  cells: ↻ **live re-export** (one report × all envs, or all reports × one env; bulk confirms
  first) + ⟳ **rebuild-comparison** (`recompute_matrix`).
- [x] **Fast (parallel) mode for matrix exports** — toggle in the config zone, reuses the global
  `fast_workers` (`settings.get/set_matrix_fast`); routes through `MatrixBatchExportWorker`
  → `ExportWorker(workers=N)`.
- [x] **Editable, matrix-scoped job queue** — a 2nd action **queues** instead of being rejected;
  jobs run one at a time + auto-advance from `_end_task`; view / remove / reorder / clear /
  stop-all. New manifest-free `MatrixBatchExportWorker`. Gate+popleft claimed atomically (no
  queue↔gate race); an error that ends a matrix job clears the pending queue (no cascade).
  Cuts held: no per-job fast, no drag-drop, no cross-restart persistence, no whole-matrix button.

**B — Compare-tab "TSN by-day" matrix (commit `868d673`):** rows = report types, columns =
exported **days** you add, each cell = (report, day) **vs TSN**; ONE data source (default
SSOR/Prod); no cross-env, no live re-export. New Compare sub-tab; **Highway Log Excel + PDF**
supported, RS/RD/HSL **greyed**. Days from `output/<date src-env>/`; outputs to
`output/comparisons/tsn-by-day/<date src-env>/<row>_vs_tsn.xlsx`. New `day_matrix` engine +
`DayMatrixCompareWorker` + `day_matrix_*` bridge + `day_matrix_*` settings. Everything KEEPS its
vs-TSN (latest-refresh dashboard).

**Cross-cutting:**
- [x] **Shared TSN comparison engine** (commit `21ecdb5`) — `matrix.consolidate_and_compare_tsn`
  ("consolidate TSMIS store folder → `compare_highway_log[_pdf]` TSMIS_*_VS_TSN → write") used by
  BOTH matrices (differ only by source folder + output path); byte-identical to the prior
  Everything output (same consolidate-to-temp → same compare → same out_path).
- [x] **One queue serves both matrices** — a `which: env|day` discriminator on the Job routes to
  `MatrixCompareWorker` vs `DayMatrixCompareWorker`; one queue panel renders in both places.
- **Deviation from the plan's "auto-consolidate WITH prompt":** the user-facing consolidated
  artifact (the **TSN** district-PDF → workbook) already prompts (the existing
  `consolidate_matrix_tsn` flow, reused by both matrices). The TSMIS side is consolidated to a
  throwaway temp per build (internal plumbing), kept **silent** — prompting on every cell build
  would be hostile. Revisit if a per-build TSMIS-consolidation prompt is actually wanted.

**Owed work-PC live verification:** matrix queue auto-advance under real exports; fast mode (N
browsers, bounded, no `batch_job.json` clobber); a row/column live re-export; the by-day matrix
building two real days vs TSN; auth-error clearing the queue; and **the updater field test —
v0.15.0 → v0.16.0 stages with no manual redownload**.

---

## Shipped in v0.16.1 (`polish/matrix-tabs` → `main`, tag `v0.16.1`)

Released 2026-06-19. Fast-forwarded onto `main` and tagged; `release.yml` built + published.
All verified offline (34 golden checks, adversarial reviews); **live behavior is still
work-PC-only to verify** (matrix re-export pause/skip/preview, consolidated reuse over real
exports, the updater field-test v0.15.0→v0.16.1). Beyond the bullets below, v0.16.1 also: gave
the **"vs TSN Matrix"** full-width parity + its own config corner + a fast-mode **worker
picker** + independent per-matrix formulas; **restructured the Compare sub-tabs** to
Cross-environment / vs TSN / vs TSN Matrix (HL cross-env back in "env"); **generalized the
vs-TSN matrix to every report** (HL wired, the rest greyed groundwork) as staging for v0.17.0;
and fixed the dark-mode checkbox eyesore. Next: **v0.17.0** — see `docs/v0.17.0-prompt.md`.

- **Matrix review polish** — queue robustness (`_on_error` clears the queue only when a matrix job
  was running; dispatch wrapped so it can't stick the gate; taskbar flash on queue-drain), worker
  error lines name the cell, corrupt-cache logging, a11y (aria-labels + focus rings), by-day report
  toggles + Build-all, all-hidden empty state, `mx-na` legend swatch.
- **Pause/Resume + Skip + live preview on matrix re-export** — the events were already forwarded to
  `ExportWorker`; widened `pause_or_resume`/`skip_route`/`request_preview` to matrix EXPORT jobs +
  `MatrixBatchExportWorker.on_worker` + buttons.
- **Persist + reuse date/env-stamped consolidated** — both matrices persist the consolidated to the
  run/store `consolidated/` (the Consolidate-tab file) and reuse until a source is newer; `force`
  re-consolidate; per-day consolidated badge.
- **Opt-in live-formulas workbook** — `(formulas)` twin beside values (best-effort 2nd pass;
  values stays canonical). `settings.matrix_formulas` + toggle in both config zones.
- **Intersection export ENABLED + dev-site URL switch** — `DISABLED_EXPORT_SUBDIRS` emptied;
  Settings ▸ "Use development site" (`tsmis-dev.dot.ca.gov`, `gui_api.apply_site_preset`). See the
  Intersection consolidate/compare entry in the backlog below (groundwork; build when the user
  supplies exported Intersection + TSN data).
- **Short/wide-laptop layout fix** — the matrix no longer scrolls after ~2 rows: hidden page
  heading on the matrix sub-tab, cell actions as a hover overlay, inline column header, 82→50px row
  floor + tighter chrome. All 5 rows fit at 1440×720; labels readable (longest ellipses + tooltip).

---

## Feature backlog

- [ ] **Clean Road Files (Highway / Intersection / Ramp)** [L] — **EXPORT SHIPPED 2026-09-02;
  the consolidate/compare tiers wait on real files.** Staged 2026-07-22 off the dev site 7.21
  capture (a "Clean Road Files" dropdown group: `clean_highway` / `clean_intersection` /
  `clean_ramp`, all `cs-disabled`, no `clean_*.js` module) as reserved-DISABLED groundwork —
  stable ids **16/17/18**. The dev site 9.1 capture (`site-captures/TSMIS Dev Site 9.1/`,
  BUILD_DATE 2026-08-19) un-greyed the three options and ships their modules, so
  `export_clean_road.py` now carries real Excel-sibling specs and the trio left
  `reports.DISABLED_EXPORT_SUBDIRS` (Route History is the one placeholder left). Each export
  is the site's flat legacy-CSV replica with the FULL header (74 THY / 55 INX / 34 RAM columns
  — the first two are exactly the TSN extracts' headers; Ramp adds `RAM_HPMS_ID` +
  `RAM_RAMP_ROUTE_NAME` to TSN's 32), the unsourced columns present-and-blank (22 / 10 / 13).
  Verified offline by driving the shipped `select_report` + Generate over the real captured
  site JS with every ArcGIS query stubbed (docs/reports.md); live data + the download are
  work-PC only (B1).
  **The TSN side is already delivered and staged:** `report_catalog.TSN` carries three library
  slots for the owner's clean-road extracts (`CA HIGHWAYS 09.08.2025.xlsx` 60,083×74,
  `CA INTERSECTIONS 09.03.2025.xlsx` 16,626×55, `CA RAMPS 09.08.2025.xlsx` 15,410×32 —
  `THY_*`/`INX_*`/`RAM_*` database fields, i.e. the UNDERLYING tables rather than the TSAR
  projections; measured: CA HIGHWAYS holds exactly the same 60,083 records as the Highway Detail
  TSN extract but **74 columns instead of 56**). `tsn_load_clean_road` deliberately ships **no
  normalizer** — the normalized shape is decided by the comparison it feeds, and no Clean Road
  report exports from the site yet, so any projection written now would be a guess. Its builders
  return a typed error naming that state; the raw is still counted and the folders are created.
  **Unlock for the next tiers:** a statewide work-PC export of each report. Then per report:
  census the real files, write the consolidator (a `consolidate_xlsx` wrap — the site emits
  the full legacy header, so the TSN projection can stay verbatim like Highway's), bump that
  slot's `normalization_version`, add the comparator + matrix rows. For Highway two
  comparisons open up with all three sides THY-shaped — the site export vs TSN, and the site
  export vs OUR ArcGIS build. The vendor's own column→layer mapping (`clean_highway.js`) has
  been cross-checked against `clean_highway_columns.PROVENANCE` (2026-09-02, detail in
  [planning/cleanroad-highways.md](planning/cleanroad-highways.md)): it agrees layer-for-layer
  on every attribute column and on the primary-layer block eff-date rule, and it names two
  sources we mark unsourced — `THY_FUNCTIONAL_CLASS_CODE` ← layer 91 `F_System` and
  `THY_LAST_SIG_CHG_DATE` ← the newest significant-change layer date. See
  [reports.md](reports.md) footnote 7.
- [x] **ArcGIS layer processing → build our own Clean Road CA HIGHWAYS** [L] — **SHIPPED
  v0.29.0 (2026-07-22), same-day from the owner's full 40-layer per-layer drop.** The ArcGIS
  tab: library status vs the agreed 40-layer manifest (`clean_road_layers.py` — INDEX-verified,
  dialect-normalized), the CA HIGHWAYS overlay build (`consolidate_clean_highway.py` — THY-shaped
  74 columns, per-column `Provenance` sheet with FeatureServer sources, as-of the TSN extract's
  date), the live TSN normalizer (`tsn_load_clean_road.build_into_highway`, marker v1), and the
  ArcGIS-vs-TSN comparison (`compare_clean_highway_tsn.py`, both flavors, 23 context columns
  present-but-never-counted per the owner's decision, the full column→layer audit in the Notes).
  Measured build rules + the five probe rounds' findings: the SHIPPED section of
  [planning/cleanroad-highways.md](planning/cleanroad-highways.md). Pinned by
  `build/check_clean_road.py`. **Follow-ups (small, tracked):**
  - [ ] a **sliver policy** for the 0.001-mi boundary-calibration class (rows keyed 9.256 vs
    9.257 pair one-sided today; ~a few hundred statewide);
  - [x] ~~upgrade the ADT profile trio to compared~~ — **DONE v0.29.1** (owner decision: a
    wholesale column difference is exactly the signal to surface; the Notes name the two known
    model-fit classes inside the count). Fitting TSN's cross-county profile-continuation +
    overlap-vintage arithmetic exactly remains a nice-to-have REFINEMENT (it would shrink the
    ADT-family counts to pure data differences; measured on 001: THY's LA-0.0 line fits
    endpoints at ORA 32.953 → LA 1.2035);
  - [x] ~~a TASAS city-code table~~ — **DONE v0.29.1**: `scripts/city_codes.py`, DERIVED from
    statewide co-location (21,906 rows voted, 99.92%; ALHAMBRA resolved to its majority ALH);
    THY_CITY_CODE is compared, unmapped names pass through visibly. If Caltrans ever supplies an
    official table, swap it in and re-verify;
  - [ ] the **offset pair stays context** (each side's offsets are its own derived cumulative;
    ours diverges at every segmentation sliver — the sliver already counts once on END
    PM/LENGTH); a policy decision could upgrade them later;
  - [ ] the exact TSN **block effective-date composite** rule (oldest-member ≈ 70%; the residual
    shows honestly in the comparison);
  - [ ] attribute holes on multi-county spans whose ODOMETERS are blank (the chain walk needs
    them) — re-export or accept;
  - [ ] **CA INTERSECTIONS / CA RAMPS builds** on the same pattern (mappings censused in the
    planning doc; the tab shows them as staged).

- [x] **Ramp Summary vs TSN (AGGREGATE)** [M] — **DONE (v0.17.0).** The first AGGREGATE comparator
  + the shared `summary_layout.py` familiar-layout renderer. `consolidate_ramp_summary` completed to
  the full 16 ramp types (added TSN-only **P/V** "Dummy" classes); `compare_ramp_summary_tsn` sums
  the consolidated TSMIS workbook vs the statewide TSN PDF (key = category), with a "Summary by
  Category" familiar sheet via `extra_sheet_writer`. Registered in `tsn_library` (+
  `tsn_load_ramp_summary.build_into`), live in both matrices, golden `check_compare_ramp_summary_tsn.py`.
  Historical v0.17.0 canary (now superseded; implementation-history evidence only): 31 both /
  1 only-TSMIS / 27 diff / TSMIS 15215 vs TSN 15410. The accepted Stage-8 contract is maintained in
  [tsn-parsers.md](tsn-parsers.md) and the comparison-perfection dashboard.
- [ ] **Intersection consolidate + compare-vs-TSN** [M] — **IN PROGRESS (v0.17.0).** Export enabled
  (dev site, via Settings ▸ "Use development site"). **Done:** `consolidate_intersection_detail`
  (thin `consolidate_xlsx` wrapper); **`consolidate_intersection_summary`** (block-walk category summer,
  218 routes → 16,473) + **`compare_intersection_summary_tsn`** (AGGREGATE; 11-block union taxonomy;
  the diverged CONTROL/INTERSECTION-TYPE codes show one-sided via `Cat.sides`; 3-column TSN PDF parser;
  canary 72 union / 56 both / 10 only-TSMIS / 6 only-TSN; 16473 vs 16626) — live in both matrices, golden
  `check_compare_intersection_summary_tsn.py` + `check_consolidate_intersection.py`. The shared
  `summary_layout.py` (spec + block-walk + familiar sheet) backs both Summary reports.
  **`compare_intersection_detail_tsn`** (FLAT; read TSMIS by position — the planning "pair-order
  reversal" was a shifted-header misread; `Y↔1 / N↔0` boolean normalize + Notes indicator;
  cross-street attrs + Date of Record context; canary 16180 both / 5520 diff; 16473 vs 16626) +
  `tsn_load_intersection_detail` + golden check — live in both matrices. **Intersection is now COMPLETE
  (both reports consolidate + compare vs TSN).** The vs-TSN comparators flip on in BOTH matrices via
  `matrix.tsn_comparator_for`.
  Recipes: [reports.md](reports.md) / [comparison-engine.md](comparison-engine.md); schema + counts:
  [tsn-parsers.md](tsn-parsers.md); resume state: [v0.17.0-prompt.md](v0.17.0-prompt.md).
- [x] **Highway Sequence vs TSN (FLAT, route+county+PM)** [M] — **DONE (v0.17.0; the LAST report).**
  New `consolidate_tsn_highway_sequence` (word-level parse of the 12 district `Highway Locations` PDFs
  → one normalized workbook; 2-char G/RF flag split into HG+FT; equate annotation lines emitted) +
  `compare_highway_sequence_tsn` (FLAT with a **county-relative key** — CA postmiles restart per county,
  so `key_normalizer` composites `"COUNTY POSTMILE"`; TSMIS read by position with prefix+PM+suffix
  re-glued; FT + Description compared, HG/City/Distance context with a Notes indicator). Registered in
  `tsn_library` + `matrix.tsn_comparator_for`, live in both matrices, golden
  `check_compare_highway_sequence_tsn.py`. Canary: 57,070 both / 3,369 only-TSMIS / 12,688 only-TSN /
  5,538 diff (FT 699 + Description 4,839); 60,439 vs 69,758 rows; 242 routes both. **This completes
  v0.17.0's comparator goal — ALL 6 reports + HL-PDF now compare vs TSN in both matrices.** See
  [tsn-parsers.md](tsn-parsers.md).
- [x] **Phase 4 UX (ride-along)** [M] — **DONE (v0.17.0).** **4a** Settings ▸ TSN reports status panel
  (per-report raw/consolidated/current dot + Import raw… / Rebuild over `tsn_library`); **4b**
  drag-to-reorder rows + columns on both matrices (`matrix.apply_order` + persisted order lists). 4c
  (per-cell/row consolidate) + 4d (add-day pipeline) were found to already exist (Everything matrix
  re-export + recompute + refresh-consolidated; by-day per-day refresh) → not rebuilt (user decision).
  A 6-lens adversarial-review workflow over the session's change set confirmed + fixed 3 minor issues
  (incl. Intersection wrongly greyed in the by-day matrix). Verified in `#mock`; suite 42/42.
- [x] **All cross-environment comparisons complete** [S] — **DONE (v0.17.0; Phase 5 closed).** Every
  report now compares env-vs-env: `compare_env.INTERSECTION_SUMMARY` (AGGREGATE-per-route, route-keyed
  via the consolidator block-walk), `compare_env.INTERSECTION_DETAIL` (flat route+PM), and
  `compare_env.HIGHWAY_LOG_PDF` (flat, both sides parsed from the PDF export — the accurate HL source,
  via `flat_pdf_loader`). The HL-PDF matrix env cell is no longer greyed; `tsn_matrix_extra_rows()` is
  empty (all 7 reports are full matrix rows, every cell coded). Golden
  `check_compare_env_intersection.py` + `check_compare_env_highway_log_pdf.py`; all verified on real
  exports + in `#mock`. **The full comparison grid is now complete: every report × {cross-env, vs TSN},
  plus Highway Log's PDF↔Excel self-check.**
- **v0.17.0 is COMPLETE + release-prepped** (all consolidators + comparators + UX + every
  cross-env comparison; `version.py` → 0.17.0 and the `CHANGELOG.md` section are in). It also
  shipped the **login/browser overhaul** (background Edge one-click check + the export-browser
  indicator/setting) and **env-check matrix flags**. **Still owed:** push the `v0.17.0` tag to cut
  the release, and **work-PC verification** of live export/compare with real TSN data (the dev PC
  can't reach TSMIS).

From a notebook brainstorm (2026-06-16); size `[S/M/L]`. Their original version buckets are now in
the Shipped record below. **⚠ A3 and D1 were the planned v0.13 *and* v0.14 themes but got displaced
both times by interface + Highway Log work — deferred 3× and now unscheduled. Decide: bump, drop,
or accept as someday.**

- [ ] **A3 — Results tab / in-app file browser** [M] (#9) — a tab to open the latest per-route
  files, consolidated workbooks, comparison outputs, failure screenshots, and run reports without
  digging through folders. The v0.13.0 Everything-tab **Saved reports** library + env-labeled
  filenames, and now the **comparison matrix** (this-update: a per-cell view of what's been exported
  + compared, with freshness, in the Everything tab), are a partial down-payment on the
  "what's been produced, where" index this needs. **A3 stays parked** (do not revive). *(deferred 3×.)*
- [ ] **C1 — Deeper self-audit so outputs are trustworthy as deliverables** [?] (#1) — **NEEDS
  SCOPING — much may already exist.** Comparisons already have a live SELF-CHECK, a VERDICT banner,
  the v0.11.0 incompleteness contract, write-path safety, and CI COM-recalc. Identify the real gap
  first: likely extend the same self-audit to **consolidations + exports**, or surface a single
  plain-English **trust summary** to the user.
- [ ] **D1 — Adaptive fast mode** [M] (#10) — persist route durations/failures across runs in a
  durable aggregated store (keyed by route+report; survives updates), then recommend/auto-set worker
  count, push historically slow routes later, and retry chronically-slow ones serially sooner.
  Per-run CSVs exist (`run_report.py`) but aren't aggregated/persistent. *(deferred 3×.)*
- [ ] **F1 — "All routes in a district / all in a county"** [M] (#11) — the site forces
  district → county → route and won't let route be "all", so we must enumerate. Needs a
  district→routes / county→routes mapping, likely sourced live from how the site repopulates the
  route dropdown after a district/county pick. **Most research-heavy — do a small site-behavior
  spike before committing to a UX.**
- [x] **Highway Detail — FULLY INTEGRATED (v0.20.0)**: export (v0.19.1/2) + consolidators + vs-TSN /
  cross-env / PDF↔Excel comparators + `tsn_library` entry + both matrices, schema verified against the
  full statewide bundle. **Still owed:** **Highway Summary** consolidate/compare [S] — export shipped
  (v0.19.1) but the report is still `cs-disabled` on the site (no real export to verify a schema
  against); integrate via the same recipe when the site turns it on and a statewide sample exists.
  Live-export verification of the Highway reports against the site is owed (the dev PC can't reach it).
- [x] **Coalescing — fast mode + matrix steps SHIPPED (v0.32.0)** — `run_export_parallel_combined`
  generates each route once across N browsers and saves every edition off that render;
  `ExportWorker._run_specs` dispatches coalesced groups to it in fast mode, and
  `MatrixBatchExportWorker._grouped_steps` coalesces queued edition steps per environment
  (one pass fills both matrix cells). The console `run_cli_multi` residue is its own
  bullet in the active backlog above.
- [x] **Visual evidence — SHIPPED (v0.21.0)** for Highway Detail vs-TSN (both matrix toggles; see
  [comparison-engine.md](comparison-engine.md) §13). **v0.22.0 added Intersection Detail** —
  `evidence_intersection_detail` locates the TSN side on the STATEWIDE print's fixed monospace
  template (indexed once per file, cached on size+mtime — the ID half of the parse-cache
  follow-up), and `availability()` went per-report so the toggle hint names which report still
  needs its prints. **Follow-ups, none started:**
  - [x] **Highway Log evidence adapter — SHIPPED (v0.24.0)** (`evidence_highway_log`: ditto-aware
    via `compared_cell`, per-print sentinel routing, TSN prints read from the library raw/).
  - [x] **Highway Sequence evidence adapter — SHIPPED (v0.25.0)** (`evidence_highway_sequence`:
    context-field-aware via `compared_cell`, the HL per-print sentinel routing, TSN prints read
    from the library raw/).
  - [ ] **TSN district-parse cache for HIGHWAY DETAIL + HIGHWAY LOG + HIGHWAY SEQUENCE** [S] — an
    HD statewide
    evidence run still spends ~10–20 min re-extracting words from ~4,300 district-print pages
    every run, and the HL (v0.24.0) + HSL (v0.25.0) adapters' per-print routing full-scans their
    12 district prints
    likewise; give all three the mtime-keyed index cache the ID adapter shipped with in v0.22.0.
  - [ ] **PDF-vs-Excel self-check evidence** [M] — needs a synthetic render of the Excel side (no
    second PDF exists); park until someone actually asks for it. (The HL/HSL rows'
    `vs_pdf`/`vs_excel`
    self-check modes deliberately show no camera for the same reason.)
  - [ ] **Evidence on the Compare tab's direct file-pair flow** [S] — the matrix surfaces were the
    ask; the manual pick-two-files compare has no toggle (its TSMIS-PDF folder can't be inferred
    from the picked files — needs a picker or the standard-location assumption). The v0.24.0
    "What you'll get" text points users at the matrix pages meanwhile.
  - [ ] **Ramp Detail evidence adapter** [M] — blocked on the same work-PC PDFs as its print
    parser (below). The TSN side is already in hand: the Ramp Detail statewide TSN print
    (`ground-truth/Ramp Detail TSN print 9.15/` → `tsn_library/ramp_detail/pdf/` once flagged).
- [x] **Highway Sequence (PDF) integration — SHIPPED (v0.25.0)** off the first real work-PC print
  set (`ground-truth/HSL PDF + IS Bundle 7.9`, 252 routes): census-first parser
  (`consolidate_tsmis_highway_sequence_pdf` — wrapped-desc hyphen-aware rejoin, PM-less rows, the
  diagnostics-trailer hard stop; 60,493/60,493 parse-back), `compare_highway_sequence_pdf`
  (PDF↔TSN pairs BETTER than Excel↔TSN — the print shares TSN's equate convention; PDF↔Excel
  flagged a route-037 "Excel-dropped" Description — later proven a cross-bundle artifact of
  pairing a 7.8 Excel with a 7.9 print, not an Excel defect; CMP-AUD-193), both matrix rows +
  all special-case mirrors, and the evidence adapter above.
- [x] **Ramp Detail (PDF) integration — DONE (v0.26.0, unreleased).** Off the first real work-PC
  pair (`ground-truth/All Reports 7.9`, 126 routes): the census-first print parser
  (15,216/15,216 parse-back, 0 unclassified/strays), `consolidate_tsmis_ramp_detail_pdf` (the
  Excel layout + the two PRINT-ONLY columns the Excel export drops — On/Off + Ramp Type),
  `compare_ramp_detail_pdf` (PDF↔TSN GRADUATES those two columns to compared — +151 verified
  cells statewide; PDF↔Excel 15,212/15,216 identical, the 4 = `_x000d_` Excel escapes), both
  matrix rows + every special-case mirror, `evidence_ramp_detail` (the ID statewide-print
  pattern; TSN library v3 sidecar; e2e 16/8-of-8 + 12/6-of-6). See
  [reports.md](reports.md) / [tsn-parsers.md](tsn-parsers.md).
- [x] **Highway Detail 7.9/ARS print parse gap — CENSUSED + FIXED (v0.26.0).** The 254 unpaired
  lines decomposed into THREE uncensused record shapes (the 7.9 drop has NO ssor-prod HD prints,
  so the ars pair is the only same-build set): (1) sparse rows whose roadbed blocks print codes
  but **no effective dates** (the old "a line 2 always carries a TASAS date" guard dropped them),
  (2) line 2s whose date lands across a shifted window grid (the per-window date test missed it —
  now tested on raw text as the fast accept, with censused furniture tests carrying the date-less
  path), and (3) **outdented equate descriptions starting with a PM-shaped token** that `_is_line1`
  misread as new records (orphaning the real record AND minting a phantom — route 101's 190).
  Re-verified statewide: consolidation **COMPLETE, 0 orphans, 0 single-line records**; PDF↔Excel
  50,171/50,730 matched identical; one-sided fell 1,273 → **1,019 (476 PDF / 543 Excel)** — near-all
  the newly-parsed sparse attribute-only rows at REPEATED postmiles whose duplicate-row pairing
  tie-breaks differ between renders (enumerated on the Only-in sheets; 9 Excel-only carry real
  descriptions). Scripts + expected numbers → `All Reports 7.9/_verification-scripts/`. Follow-up
  [S]: census the duplicate-PM pairing classes if the vendor conversation needs them attributed.
- [x] **Day-vs-baseline comparisons — the "vs Baseline Matrix" — SHIPPED (v0.26.0, unreleased).**
  Same report + format + source, one exported day diffed against an EARLIER pull (a run-folder
  day or the Export-Everything store) — `scripts/baseline_matrix.py` orchestrating the untouched
  `compare_env.compare_folders` per row (an additive `labels=` override names the sides), a third
  Compare sub-tab with its own config corner, all 12 rows, per-baseline artifact store under
  `output/comparisons/baseline-by-day/`, two-folder fingerprint freshness, the shared job queue.
  Locked by `build/check_baseline_matrix.py` (incl. one REAL build per baseline kind); the
  UI verified on the `#mock`. See [comparison-engine.md](comparison-engine.md) §12c. **Owed on
  the work PC:** a real two-day baseline run (the dev PC has no run-folder history).
- [ ] **Shared whitespace-collapse helper** [XS] — `compare_highway_log._hl_normalize` and
  `compare_highway_sequence_tsn._v` carry the same tab/newline collapse
  (`compare_ramp_detail_pdf._collapse` joined the family in v0.26.0, flavor-local by design);
  homing one helper in `compare_tsn_common` needs a locked-comparator re-bless, so it waits for
  a release that re-blesses HL anyway (audit finding, 2026-07-08 — cosmetic, no behavior drift).
- [x] **Ramp Summary (Excel) edition — SHIPPED (v0.25.1**, same day it was backlogged**).** The
  site's `rs_exportToExcel` wired as `ramp_summary_excel` (stable id 13) — the INVERSE of the
  print editions. Shipped alongside **Intersection Summary (PDF)** (`ints_printAll`, id 14) and
  the greyed **Route History** placeholder (id 15), so every enabled on-site report exports in
  both formats the site offers (see the capability matrix in [reports.md](reports.md)). All
  three export-only; the consolidate side (RS-Excel consolidator, IS-PDF print parser) waits for
  real work-PC files, Lesson-13 style.
- [x] **Intersection Detail July-2026 format — SHIPPED (v0.22.0).** The site reshaped the report
  (35 columns; see [reports.md](reports.md) Reports 5–6 + 6b and
  [tsn-parsers.md](tsn-parsers.md) Intersection Detail): consolidators/comparators updated with a
  pre-update-workbook refusal, the comparison re-baselined (canary 163,310 → **21,675**), the TSN
  library moved to normalization v3 (new shape + District/County sidecar), evidence enabled.
- [x] **Intersection Summary July-2026 watch — CLOSED (v0.25.0).** The fresh 7.9 export showed the
  July update touched IS too, but only ONE header (`MAINLINE MASTARM` → `MASTERARM`): fixed with a
  parse-only Section alias + a section-partition layout-drift tripwire (see
  [tsn-parsers.md](tsn-parsers.md) Intersection Summary). The route-170 thread CLOSED with the
  `All Reports 7.9` drop: absent from all four intersection exports across BOTH data sources
  (matching dev) — a data-side removal, not an export glitch.

---

## Standing & cross-cutting (open)

### Security / IT
- [ ] **Code-sign the executable** — the one big remaining IT lever (removes most Defender / DLP /
  SmartScreen friction on the unsigned `.exe`, and is the real fix for the P1 auto-update-trust
  finding above). **In progress:** SignPath Foundation cert applied for; `build.ps1 -Sign`
  self-signs for local/test; `release.yml` has a gated SignPath step (inert until
  `SIGNPATH_ENABLED=true` + secrets). *Remaining:* approval → flip the gate on (add the
  with-browser pair) → enable updater signature verification. See
  [it-and-security.md](it-and-security.md) §7. The updater checksum + staged-item allowlist
  (v0.11.0) are the integrity half; the signature half waits on the trusted cert.
- [ ] **Auth file at rest** — `storage_state` is plaintext JSON (documented, not encrypted).
  Defense-in-depth; consider Windows DPAPI (`CryptProtectData`) if IT ever requires it. (Same as the
  P2 `auth-file-plaintext-no-acl-dpapi` finding.)

### Live-export verification (owed on the work PC — this dev PC can't reach TSMIS)
- [ ] **EmptyExport 60 s cap** rests on the site's "Export button present ⟺ data loaded" contract.
  Confirm live it doesn't false-positive on a slow-but-valid load.
- [ ] **Intersection empty markers** (`td.hl-empty` / `Total Intersections = 0`) — verify against the
  live site once intersections finalize (still site-side development; markers may drift).
- *(The bulk of this — plus the carried §J2 live-verify set: the wrong-env backstop, the empty-routes UX,
  the staging retry, `report_error_text`/Highway-Sequence empty — is consolidated as the **work-PC field
  sign-off** in [Next version](#next-version-v0185--whats-actually-owed) above.)*

### Upstream / external (report to the TSMIS team)
- [ ] **DEV-SITE SSOR REGRESSION (2026-07-09, build 14:41)** — the Route History "restore" line in
  `main.js`'s report-change handler re-hides the Query Method box for SSOR on every report pick
  (clobbers the `checkTsmisHiGroup()` un-hide), so NO SSOR user can export on dev; prod fine. Fix
  = restore `'block'` unconditionally. Relayed to the user with the one-line fix (see
  `site-captures/TSMIS Dev Site 7.9` in the local index); blocks route-170 IS, the HD coalesced
  pair, and all ID/IS/HD dev exports.
- [x] Site hardcodes `highway_sequence_listing.xlsx` as *Ramp Detail*'s export filename (cosmetic
  for us — we rename via `save_as`). **Fixed by the vendor in the dev 7.9 build**
  (`ramp_detail_<route>.xlsx`); prod follows whenever that build promotes.
- [ ] Ramp Summary **source-data** inconsistency on 9 routes (see the Shipped record — not our bug).

### Restructure leftovers (opportunistic — low priority, none release-blocking)
> v0.18.0's final review found the branch **offline-complete** (no product-code leftover). These are the
> only minor hygiene / conditional carry-overs from the overhaul — do them opportunistically.
- [ ] **Non-HL tab/whitespace normalization** — the Highway Log & Highway Sequence vs-TSN loaders collapse
  tab/whitespace at load; **Ramp Detail & Intersection Detail do not** (the disposition is recorded in §J2
  above). Low impact — the locked counts stand; revisit only if a tab-bearing value ever causes a spurious diff.
- [ ] **P11 doc/comment line-ref drift** — the v0.18.0 leaf-split moved code, so some `docs/internals/*`
  inline `file:line` refs + a few source comments still point at pre-split locations (the deeper per-row
  churn the P11 docs reconciliation explicitly deferred; the v0.18.1 docs pass fixed `export-engine.md` §6).
  Fix opportunistically when you next touch those files.
- [ ] **Cold-start / matrix-snapshot perf baselines** (R1-A01) — the import-cost baseline shipped
  (`build/measure_baselines.py`); the runtime cold-start / matrix-snapshot baselines were deferred to the
  first phase that touches a hot path. Measure then, not before.

### Comparison semantics — open questions (verify before changing anything)
> Observations, **not** confirmed defects. Each needs a code-verification pass FIRST; a change here
> moves comparison counts, so it rides the `compare_core` rules in `CLAUDE.md` (cell-for-cell proof
> against the independent oracle, both workbook flavors, an explained canary re-bless).
- [ ] **Ramp Detail's `-` null marker may be handled two ways** (noticed 2026-08-08 during the RB-4
  evidence inspection). vs-TSN projects `-` to blank before comparing
  (`compare_ramp_detail_pdf._NULL_MARK`), while the cross-environment comparator appears to compare
  the literal `-` as a value — an env evidence image shows Area 4 as ssor-test `'-'` vs ssor-prod
  `'Y'` with no normalization disclosure. **Both evidence images are honest about what they show, so
  this is not an evidence defect.** It may also be correct as-is: the env lane compares two prints of
  the same shape, so `-` against `Y` can be a genuine difference rather than a null. Verify which it
  is; if intended, record the reasoning in [comparison-engine.md](comparison-engine.md) so it is not
  re-litigated.

### Dormant / watch (no action unless the data changes)
- [x] **Med Wid flavor-parity gap — resolved in Phase-3 E1 (2026-07-12).** Python, values,
  formula Comparison, and independent Spot Check now share the approved narrow ASCII grammar via
  exact string canonicalization and hidden staged helpers; no Excel `VALUE()` coercion remains.
  The adversarial grammar/fuzz, formula-length, physical-width, and installed-Excel gates own the
  contract. Detail in [comparison-engine.md](comparison-engine.md) (Med Wid formula/value parity).

---

## Shipped (reconciled record)

What landed, so the open list stays honest. Full changelog: `CHANGELOG.md`.

### Version buckets — reconciled to reality (current: v0.26.0, IN PROGRESS — unreleased)

| Version | Date | What actually shipped |
|---|---|---|
| **v0.11.0–0.11.1** ✅ | Jun 16 | Audit-hardening patch (no-download fast-fail, token redaction, updater SHA-256, PM-keyed compares, incompleteness contract); TSN converter proven flawless. |
| **v0.12.0** ✅ | Jun 16 | **A1, A2, B1, B2, B3** — self-describing filenames, compare-folder filter, Pause/Resume, auto-consolidate, Export Everything. |
| **v0.13.0–0.13.1** ✅ | Jun 17 | UI/UX declutter, run lifecycle + ETA + completion summary, completion notification, accessibility, Compare sub-tabs, revert-to-previous, env-check split, Everything-store labeling/colour-coding; duplicate-key similarity pairing. |
| **v0.14.0–0.14.3** ✅ | Jun 18–19 | **Highway Log PDF** consolidator + PDF-sourced comparisons + corrected 31-column labels + roadbed-aware key + HL Compare sub-tab + consolidate-label clarity + UI-vs-logic audit + the IT-README handout. |
| **v0.15.0** ✅ | Jun 19 | The **Everything comparison matrix** (report × env, cross-env + vs-TSN, two Highway Log rows) + an app-wide UI/motion polish pass. |
| **v0.16.0–0.16.1** ✅ | Jun 19 | Matrix **queue + fast mode**; the Compare-tab **vs-TSN-by-day** matrix; pause/skip/preview, reused consolidated, opt-in formulas; Intersection **export** + dev-site switch. |
| **v0.17.0** ✅ | Jun 20 | **All-report TSN + cross-env comparison** (every report × {env, TSN} + HL PDF↔Excel); Intersection **consolidators**; **canonical TSN library** + Settings panel; one-stop **Export-today** by-day column; **login/browser overhaul** + **env-check matrix flags**; drag-reorder. |
| **v0.17.1** ✅ | Jun 21 | Matrix-tab blank-space + cramped-options fixes; Stop/Clear interrupts a stuck sign-in; TSN picker default + self-documenting TSN library; gitignore security fixes. |
| **v0.18.0** ✅ | Jun 26 | **Structural & engineering overhaul** (engine leaf split / `common.py` shim, the outcome + transactional-artifact contracts, report-catalog SoT, GUI endpoint split + front-end modularization, `compare_core` byte-identical) + **Intersection Detail (PDF)** (CR-002) + updater/packaging hardening + the work-PC evidence kit. Released as the offline-validated candidate. |
| **v0.18.1** ✅ | Jun 26 | **Field-validated close-out** — site-menu-safe selection (pick by stable `data-value` + reveal the `cs-submenu` fly-out; prod-safe), website-style report grouping, Highway Detail/Summary reserved-disabled groundwork (stable ids 8/9), the matrix queue-phantom fix, `wait_js` validation, and the Intersection Detail "Roadbed"→"Route Suffix" rename. `compare_core` untouched. |
| **v0.18.2** ✅ | Jun 29 | **Hotfix** (field-driven) — comparison **progress feedback** (the ~17k-row Intersection Detail vs-TSN build narrates its formerly-silent "Report View" stretch; `_PROGRESS_EVERY` 10k→2.5k ⇒ Stop lands sooner), **skip the live-formulas twin** for huge bulk matrix rebuilds (> `_FORMULAS_TWIN_MAX_ROWS` Comparison rows; the values copy is still complete, the skip is logged, the manual Compare tab is unaffected), and **Route Suffix surfaced in the Report View** (soft: red, not Major). `compare_core` output byte-identical. |
| **v0.18.3** ✅ | Jun 29 | **Hotfix** (field-driven) — two Intersection Detail vs-TSN comparison fixes: the **intersecting-route postmile** no longer false-flags where both sides are 0 (`_norm_num`/`_norm_bool` preserve a numeric 0 instead of blanking it via `str(v or "")`, so TSN's numeric-0 reads `0` and matches TSMIS's `'0.000'`; statewide canary **163,353→163,310**, −43, only that field), and the **Report View marks one-sided locations** "Only in TSMIS/TSN" (a side-colored band, kept out of the Major/Diffs tally) instead of an all-red row. `compare_core` untouched. |
| **v0.18.4** ✅ | Jun 29 | **Hotfix** (field-driven) — the **matrix job-queue phantom**: a finished/cancelled compare lingered in the queue panel marked "running" (BOTH matrices) until the next job replaced it. Backend was correct (the job released + state pushed); the panel is a `.mc-group` whose bare `display:flex` outranked the UA `[hidden]{display:none}`, so `group.hidden=true` never hid it, and `renderQueuePanel` didn't clear the row list on the empty path. Fix = `.mc-group[hidden]{display:none}` + clear the list every path. Frontend-only; reproduced + verified in `#mock` with the production event order (which the mock's own order masked). |
| **v0.18.5** ✅ | Jul 6 | **The audit release** — every confirmed full-repo-audit finding, no new features: TSN library **normalization-version stamp + auto-rebuild from raw** (comparisons self-heal after an update), a real `0` never reads as blank (the `str(v or "")` sites), and the offline check suite now **gates every release** (`run_checks.py` + `release.yml needs: offline-checks`). `compare_core` re-blessed (2.79M cells identical). |
| **v0.19.0** ✅ | Jul 6 | **Usability + trust + structural cleanup** — one-click **"Validate & package results"**; the same report grouping on every tab; add-today to the by-day matrix; laptop side-pane fix; + the R–V structural waves (shared comparator/PDF substrates, `gui_api`/`gui_worker`/`matrix`/`app.js` splits, ruff F821 blocking CI, `checks.yml` = one runner step, SEC-02/05/06 hardening, `compared_cell` re-blessed 2,789,732 cells identical). Work-PC sign-off received. |
| **v0.19.1** ✅ | Jul 7 | **Highway Detail/Summary EXPORT enabled** (the v0.18.1 reserved pair; export-only — consolidate/compare still owed) + **validation phantom-env fix** (`_envs_with_data` walked the store's `_tsn_input` TSN-drop folder as an environment → the Validate run now reads 18/18). |
| **v0.19.2** ✅ | Jul 7 | **Highway Detail (PDF)** print edition (stable id 10, `hd_printAll` — confirmed on the 7.7 dev capture) + **dual-edition coalescing** (selecting both editions of one report generates it once and saves both; `run_export_combined`, standard path — fast mode + CLI are follow-ups). Locked by `check_coalesce_editions`. |
| **v0.19.3** ✅ | Jul 7 | **Hotfix** (field-driven) — the per-route stale-form guard (`_ensure_report_armed`) false-"drifted" on **every** route for a grouped-menu report: it compared the visible `.cs-value` (the short leaf label "Detail") to the full `spec.label` ("Highway Detail") and re-selected each route (correct exports, but log spam + wasted work). Fix = key on the hidden `#reportSelect`'s stable `data-value` (`current_report_value`), text read only as fallback. Affects both Highway Detail editions. Regression-covered in `check_export_engine` + `check_fake_site` (new `test_current_report_value`); `compare_core` untouched. |
| **v0.20.0** ✅ | Jul 7 | **Highway Detail full integration** — consolidators (Excel `consolidate_highway_detail` + PDF-sourced `consolidate_tsmis_highway_detail_pdf` on `pdf_table_lib`), the **vs-TSN comparator** (`compare_highway_detail_tsn`: new opt-in `CompareSchema`, canonical roadbed-aware PM key, PS column, NA/zero-pad/length/WDA normalizations, ID-style **Report View** + **Notes**), the PDF flavors (PDF↔TSN + PDF↔Excel), a `tsn_library` statewide-xlsx entry, both matrices + by-day rows, catalog/`.bat`/mock parity. Schema verified against the full statewide bundle (252 routes / 51,243 rows vs the 60,083-row TSN extract; TSN PDFs cross-checked ≥99.9% vs the extract → the Excel is the library source). `compare_core` untouched (byte-identical; new behavior rides the new schema). Highway Summary stays export-only. |
| **v0.21.0** ✅ | Jul 8 | **Visual evidence** — the manual "screenshot both PDFs and circle the cell" workflow automated as a decoration of the Highway Detail vs-TSN comparisons: per differing column, N (1–10) random verified example rows rendered as highlighted snippets from BOTH PDFs (the app's (PDF) export + the TSN district prints in `tsn_library/highway_detail/pdf/`), each example parse-back-verified against the compared values before it's shown; `… (evidence).xlsx` + a two-layout image folder beside each comparison (keep-last-good). One shared toggle+count on both matrix pages (`evidence_images`/`evidence_examples`), ONE hook in `consolidate_and_compare_tsn`. TSN library v2 appends the District/County sidecar (D2 auto-rebuild). Pillow + pypdfium2 now SHIP (~20 MB; the frozen self-test proves the render path). Locked by `check_visual_evidence`. |
| **v0.21.1** ✅ | Jul 8 | **Hotfix** (field-driven) — the `tsn_library/highway_detail/pdf/` drop folder v0.21.0 pointed at but never created: `TsnEntry.evidence_pdfs` drives `ensure_layout` (folder + hint file; README refreshes when its generated text changes), and `matrix_info`/`day_matrix_info` re-push state so dropping the PDFs + re-entering a tab un-greys the evidence toggle without a restart. |
| **v0.22.0** ✅ | Jul 8 | **Intersection Detail July-2026 format + evidence** — the site's report overhaul absorbed end-to-end: 35-column SoT, the PDF parser rewritten for the reshaped print (cover pages, rowB bands + print-only intersection numbers, padded postmiles; pre-update workbooks/PDFs refused with re-export hints), the vs-TSN comparison re-baselined against the same-run 7.8 statewide bundle (parity 217/217 routes / 576k cells / 0 real diffs; canary 163,310 → **21,675**; Notes + Report-View Major classification rewritten to the data — soft = Int St/ML/CS Eff-Date + Route Suffix), `Xing Line Lgth`↔`X_CROSS_OVERRIDE` newly compared, TSN library **v3** (new shape + District/County sidecar), and **evidence images for both ID rows** via `evidence_intersection_detail` (the statewide TASAS print on a fixed monospace template, indexed once + cached; 16,584/16,584 records, 30/32 fields 100.00% parse-back). `availability()` went per-report; `compare_core` untouched. |
| **v0.22.1** ✅ | Jul 8 | **Evidence workbook: both layouts** — "… (evidence).xlsx" gains a second image tab: **Evidence (stacked)** + **Evidence (side-by-side)** (previously stacked-only; the pair files lived only in the images folder). Engine-level (`_image_sheet`), so HD + ID both get it. |
| **v0.23.0** ✅ | Jul 8 | **On-demand per-cell evidence** — a camera action on built, fresh vs-TSN cells (both matrices) generates/refreshes the evidence set for the EXISTING comparison: no re-compare, toggle-independent (`matrix.run_evidence_only` + `evidence_for_cell`/`evidence_for_day_cell`, an `evidence` queue job, endpoints `matrix_evidence_cell`/`day_matrix_evidence_cell`). The freshness gate refuses when the store/consolidated/TSN moved past the comparison ("refresh the comparison" hint) so images can't illustrate a diff set the workbook doesn't carry; `availability()` gains the `row_reports` map the JS gate reads. Verified e2e on the 7.8 mini-store (real compare → on-demand run → warm-cache re-run → staleness refusal). |
| **v0.24.0** ✅ | Jul 9 | **Highway Log evidence + two print editions + the comparison standards audit + evidence-toggle clarity** — (1) `evidence_highway_log`: both HL rows render evidence images (compared_cell-judged so dittos/Med-Wid never enumerate; per-print sentinel routing since HL's 31 columns carry no district — records carry their own `src`/dist/cnty, the engine prefers them, cross-print collisions skip via the uniqueness gate; TSN side reads the SAME district prints from `tsn_library/highway_log/raw/`, no duplicate drop). (2) **Highway Sequence (PDF)** + **Ramp Detail (PDF)** export-only print editions (stable ids 11/12; `hsl_printAll` portrait / the shared async `printAll()` dispatcher with a `showPrompt` auto-answer + `Promise.race` bound, landscape; coalescing automatic). (3) The audit: HSL re-verified statewide on the fresh 7.8 bundle (library rebuild byte-identical, counts within ~54 rows of the canary, FT-diff census: 681/698 = the by-design equate pairings — Notes updated); Ramp Detail gained a Notes sheet + stale-library re-normalization (idempotence proven on 15,410 real rows) + a width gate; Ramp Summary gained spec notes. (4) The evidence toggle spells itself out per report (✓/○/no-support lines + row-header camera badges); disabled Create-comparison explains why; (PDF) picker rows explain print editions. `check_day_matrix`/`check_matrix_tsn` made HERMETIC (sandbox `TSN_LIBRARY_ROOT` — a stocked dev library flipped their staged fixtures). |
| **v0.25.0** ✅ | Jul 9 | **Highway Sequence (PDF) fully integrated + the Intersection Summary July fix** — off the first real work-PC print set (`ground-truth/HSL PDF + IS Bundle 7.9`, delivered same day): (1) the census-first print parser (`consolidate_tsmis_highway_sequence_pdf` — header-anchored per-page windows, wrapped-desc HYPHEN-AWARE rejoin, PM-less END-OF-ROUTE/CITY-END rows, the "Unresolved Intersections" trailer hard-stop; parse-back **60,493/60,493 rows / 59,082 fully equal** vs the 7.8 Excel — residual = the equate-representation classes + 4 `_x000D_` + the route-037 Description the Excel export DROPS). (2) `compare_highway_sequence_pdf` (PDF↔TSN pairs BETTER than Excel↔TSN — both 57,505 vs 57,071, the print shares TSN's equate convention; PDF↔Excel both 59,946 / identical 59,082; per-flavor Notes sheets) + the `HIGHWAY_SEQUENCE_PDF` env adapter + BOTH matrix rows (env/tsn/vs_excel modes; every special-case mirrored: `matrix_state`, `matrix_build`, `day_matrix`, `gui_worker_maint`, the console menu, the mock). (3) `evidence_highway_sequence` — the HL per-print sentinel routing, context-fields never enumerate (`compared_cell`), TSN prints from `tsn_library/highway_sequence/raw/` (`_TSN_PDFS_IN_RAW`). (4) **Intersection Summary**: the July `MASTARM`→`MASTERARM` rename absorbed via a parse-only Section alias + the section-partition layout-drift tripwire (every block but the site-under-counted Highway Group must sum to the route total); verified on the fresh 217-route export (route 170 missing — flagged). |
| **v0.25.1** ✅ | Jul 9 | **Every edition, everywhere** — (1) **TSAR: Ramp Summary (Excel)** (stable id 13, `rs_exportToExcel` via the shared Export-button save — the site button the app never wired; the INVERSE of the print editions); (2) **Intersection Summary (PDF)** (id 14, `save_intersection_summary_pdf`: `ints_printAll` PREPENDS a cover to the inline count tables — no pagination — `window.print` overridden, `.rs-cover`+`.ints-total` verified, total re-read as the empty backstop, portrait; in `_PAGE_REBUILDING_SAVES`); both coalesce with their siblings (shared `data_value`). (3) **Route History Table** (id 15) wired as reserved-DISABLED groundwork (`DISABLED_EXPORT_SUBDIRS={"route_history"}`, greyed in the picker — the dev site's embedded-SSRS report has no export flow; the v0.18.1 Highway-pair pattern). Export-only; consolidate/compare/matrix untouched. Gate checks re-pointed (`check_intersection_gate._RESERVED`, stable-ids 13–15, catalog baseline + mock parity). |
| **v0.25.2** ✅ | Jul 9 | **Hotfix** (field-driven, same evening) — a plain (non-fast, non-store) export of a coalesced Excel+PDF pair crashed instantly: `run_export_combined` did `Path(out_dirs[i])` on the truthy `[None, None]` list `_prep_edition` passes when there is no store base → `TypeError … not NoneType` before the browser launched. Latent since v0.19.2 (fast mode never coalesces; the Everything store always passes real staging dirs) — the user's first standard-mode pair run (2026-07-09 18:30, three attempts) was the first field exercise. Fix = `_combined_output_dirs`: a None ENTRY falls back to that spec's dated run folder (run_export's `out_dir=None` semantics, per edition). Regression-locked in `check_coalesce_editions.test_combined_output_dirs`. |
| **v0.26.0** 🚧 | Jul 10 (in progress) | **Ramp Detail (PDF) fully integrated** — the LAST export-only print edition graduated off the first real work-PC pair (`All Reports 7.9`): the census-first parser (parse-back **15,216/15,216 rows**, 0 unclassified), the consolidator carrying the Excel layout **plus the two print-only columns the Excel export DROPS** (On/Off, Ramp Type), `compare_ramp_detail_pdf` (PDF↔TSN **graduates On/Off + Ramp Type to compared** — +151 verified cells statewide vs the Excel baseline; PDF↔Excel **15,212/15,216 identical, 0 one-sided** — the 4 = the Excel's `_x000d_` escapes), the `RAMP_DETAIL_PDF` env adapter + BOTH matrix rows (every special-case mirrored), `evidence_ramp_detail` (the ID statewide-print pattern — fixed template censused 400/400 vs the raw extract; TSN library **v3** District/County sidecar; e2e 16 examples across 8/8 PDF-row columns + 12 across 6/6 Excel-row columns; dual-row discipline: the Excel row never enumerates the print-only columns). **+ the "vs Baseline Matrix"** — day-vs-baseline comparisons for all 12 reports (an earlier day or the Everything store as the baseline; `baseline_matrix.py` over the untouched `compare_env.compare_folders` with an additive `labels=` override; a third Compare sub-tab + config corner; per-baseline artifacts under `comparisons/baseline-by-day/`; locked by `check_baseline_matrix`) **+ the evidence full-width-band crop fix** (`_crop_window`: a blank cell's red box / neighbor text no longer clips — the HSL complaint; verified on 99 regenerated examples) **+ the HD-PDF July-print parser fix** (the 254-orphan census: date-less sparse roadbed rows, window-split dates, outdented PM-shaped equate descriptions — all parse; single-line records kept with a blank attribute tail) **+ one-click website-source capture** (Settings; `site_capture.py`, local-only — see [it-and-security.md](it-and-security.md)) **+ mock parity fixes** (the by-day mock gained the two HD rows + the HSL/HD-PDF fmt flags it had drifted on). |

> **The planned "A3 / D1" buckets never shipped** — v0.13 became a UI/UX release and v0.14 became
> Highway Log accuracy, displacing A3 (results tab) and D1 (adaptive fast mode) each time. They're
> now in the Feature backlog above, flagged 3×-deferred.

### Closed findings & decisions (record)
- [x] **`main` reconciled to v0.18.1** (2026-06-27) — a `-s ours` supersede merge (`9514359` = `d775ca0`
  v0.18.1 + `068b697` v0.17.8) fast-forwarded `origin/main` to the v0.18.1 tree; **no force-push**, the
  forward-ported v0.17.2–v0.17.8 line preserved as ancestry, `v0.18.0`/`v0.18.1` tags intact; the merged
  `refactor/v0.18.0-structural-overhaul` branch retired (local + origin). The diverged-histories problem
  (the CR-002 forward-port) is closed.
- [x] **Stage-1 foundation audit — consolidate + cross-env compare VERIFIED on the full 6-env
  batch** (2026-06-18; HSL / Ramp Detail / Ramp Summary). 18/18 consolidations + 15/15 cross-env
  comparisons (baseline SSOR-PROD) proven cell-accurate ≥3 independent ways (independent
  from-scratch recompute · values-flavor content · Summary literals · Excel-COM F9 of the
  formulas flavor with SELF-CHECK all OK + flavor parity) + raw-source spot checks. **Zero tool
  bugs.** The Ramp Summary "Source ≠ total" 9-route quirk reproduces identically on all 6 envs
  (SOURCE quirk, correctly flagged RED — not fixed away; geometric parser cross-check = 0
  mismatches across 756 PDFs). HSL cross-env (no prior audit) now covered: an apparent diff-cell
  over-count was traced to duplicate-PM pairing — an independent OPTIMAL recompute matches the
  workbook exactly (the engine's similarity pairing is correct; ~4,474 dup groups/pair). ARS-PROD
  == SSOR-PROD for RD/RS; HSL has 2 genuine ARS-PROD diffs (real source difference, confirmed).
  The 2026-06-16 closed finding below reproduces exactly. New lock: **`build/check_compare_highway_sequence.py`**
  (HSL adapter end-to-end: PM key, "Highway Locations" sheet, "(col X)" unnamed-column labels)
  wired into `checks.yml`. Full report: `code-review/AUDIT-stage1-foundation.md` (git-ignored).
- [x] **Cross-env Ramp comparisons VERIFIED on real data** (2026-06-16, 3-env × 126 routes,
  ≥3 independent methods): v0.11.0 PM re-key correct (Ramp Detail PROD-vs-TEST true diff = 8 cells /
  4 rows + 10 TEST-only, vs the old 1,451-cell positional inflation); Ramp Summary PROD-vs-TEST = 32
  genuine diff cells / 9 routes; PROD==ARS. Regression-locked by `build/check_compare_ramp_detail.py`
  + `check_compare_ramp_summary.py`.
- [x] **Ramp Summary source-data inconsistency on 9 routes** (005/008/010/094/110/134/210/280/605):
  the source PDF's own Ramp-Types breakdown sums short of its stated Total by 1–9 ramps, identically
  across envs. **`parse_pdf` is CORRECT** (0 mismatches vs an independent geometric extraction over
  378 PDFs × 14 ramp types); `_audit_ok` flags these RED on purpose (`⚠ Source ≠ total: <section>`,
  commit `59b0be6`). **Do NOT "fix" the parser to force them green.** (Upstream report is open above.)
- [x] **`extractall` / junction-traversal safety** (2026-06-16) — verified safe: `shutil.rmtree`
  refuses a top-level junction and doesn't recurse a nested one; `reset_targets` builds its list from
  path constants only; the updater's `extractall` is sanitized by 3.11 + SHA-256-verified.
- [x] **Audit investigate-list residue** (2026-06-16) — SELF-CHECK independence (live formulas, not
  the Python mirror); `_wait_pid_exit` PID-recycle (fail-safe); `safe_release_url` URL provenance
  (FIXED, locked by `build/check_updater.py`); env-scan CONFIG bleed (fail-closed). All closed.
- [x] **E1 — env-check day-caching** — DECIDED AGAINST (2026-06-16): the `env_check_*` Settings
  toggles already cover it, and access info is advisory-only (never gates a real export).
