# HISTORY — TSMIS Reports Exporter

How a one-day console script became a portable, self-updating Windows desktop
app — told from the repository.

**By the numbers:** 313 commits · 39 pull requests · 51 tagged releases ·
8 report types · **May 20 → June 29, 2026**.

This is the narrative companion to [`CLAUDE.md`](../CLAUDE.md) (the authoritative
"how it works and why") and [`CHANGELOG.md`](../CHANGELOG.md)
(the user-facing changelog). Where they explain the *what*, this explains the
*journey* — including the dead ends, the reverts, and the three field failures
that rewrote the design.

## Timeline at a glance

| Version | Date | The leap |
|---|---|---|
| `v0.1.0-preview` | Jun 4 | Console scripts → packaged portable desktop app, in one day |
| `v0.2.0` | Jun 4 | Experimental parallel "fast mode" + route selection |
| `v0.3.0` | Jun 5 | Stop bundling a browser; drive the machine's Edge/Chrome — **587 MB → 148 MB** |
| `v0.4.0` | Jun 5 | Highway Log, multi-report export, a real Cancel button |
| `v0.5.0` | Jun 10 | The managed-Edge login problem, solved (recapture + Built-in Chromium) |
| `v0.6.0` | Jun 10 | Silent device sign-in — exports provision themselves, no saved file |
| `v0.7.5` | Jun 11 | Sign-in fixed for the new TSMIS site (the `CONFIG` lexical-global bug) |
| `v0.7.6` | Jun 11 | "One log upload answers it" — heavy diagnostic logging |
| `v0.8.0` | Jun 11 | GUI torn out and rebuilt on WebView2 (2,753 lines changed) |
| `v0.8.1` | Jun 11 | Mark-of-the-Web hotfix — downloaded zips were crashing the CLR |
| `v0.9.0` | Jun 11 | One-click self-updates + the Compare overhaul |
| `v0.10.0` | Jun 12 | Env-labeled run folders, live previews, Settings tab, cross-env compare |
| `v0.10.1` | Jun 12 | Self-update without PowerShell (locked-down PCs) |
| `v0.10.3` | Jun 12 | Two new Intersection reports; parallel browsers dodge managed Edge |
| `v0.10.4` | Jun 12 | Intersection labels/formats matched to the live site; dual login indicators |
| `v0.11.0` | Jun 16 | Audit-hardening: no-download fast-fail, token redaction, updater SHA-256, postmile-keyed compares |
| `v0.11.1` | Jun 16 | TSN Highway Log PDF→Excel proven flawless across all 12 districts |
| `v0.12.0` | Jun 16 | Self-describing filenames, Pause/Resume, auto-consolidate, Export Everything |
| `v0.13.0` | Jun 17 | Run lifecycle + ETA, accessibility, completion notification, revert-to-previous |
| `v0.13.1` | Jun 17 | Duplicate-key pairing by similarity (phantom-diff fix) |
| `v0.14.0` | Jun 18 | Highway Log (PDF) consolidator + PDF-sourced compares + corrected 31-column labels + roadbed-aware key |
| `v0.14.1` | Jun 18 | Highway Log comparisons regrouped onto a Compare sub-tab |
| `v0.14.2` | Jun 18 | Consolidate-label clarity + a 22-finding UI-vs-logic audit |
| `v0.14.3` | Jun 19 | An "IT-README" security handout that ships in the app folder and rides updates |
| `v0.15.0` | Jun 19 | **The Everything comparison matrix** (cross-env + vs-TSN, two Highway Log rows) + an app-wide UI polish & motion pass |
| `v0.16.0` | Jun 19 | Matrix job **queue** + **fast mode**; a Compare-tab **vs-TSN-by-day** matrix |
| `v0.16.1` | Jun 19 | Matrix polish: pause/skip/preview, reused consolidated, opt-in formulas, Intersection export + dev-site switch |
| `v0.17.0` | Jun 20 | **Every report compares vs TSN + cross-env**; Intersection consolidators; canonical TSN library; one-stop Export-today; login/browser overhaul |
| `v0.17.1` | Jun 21 | Matrix-tab hotfix — blank-space + cramped-options fixes, Stop/Clear interrupts a stuck sign-in, self-documenting TSN library |
| `v0.18.0` | Jun 26 | **The structural overhaul** — engine-leaf split, the outcome + transactional-artifact contracts, a report-catalog SoT, GUI/front-end modularization; + Intersection Detail (PDF), the 8th report; + updater/build hardening |
| `v0.18.1` | Jun 26 | **Site-menu-safe selection** (pick by stable `data-value`, reveal the fly-out) + website-style report grouping + Highway Detail/Summary groundwork + matrix-queue + Route-Suffix fixes |
| `v0.18.2` | Jun 29 | **Field-driven hotfix** — the big comparison stops looking frozen (progress through the silent "Report View" build; faster Stop), huge bulk rebuilds skip the live-formulas twin, and Route Suffix shows in the Report View |
| `v0.18.3` | Jun 29 | **Field-driven hotfix** — Intersection Detail vs-TSN: intersecting-route postmile stops false-flagging where both sides are 0 (TSN's numeric 0 was read as blank), and one-sided intersections are marked "Only in TSMIS/TSN" in the Report View instead of an all-red row |
| `v0.18.4` | Jun 29 | **Field-driven hotfix** — the matrix job-queue phantom: a finished/cancelled comparison stayed in the queue marked "running" (both matrices) until the next job; a `.mc-group`'s `display:flex` was silently overriding `[hidden]` |
| `v0.18.5` | Jul 6 | **The audit release** — every confirmed finding from the full-repo audit, no new features: comparisons self-heal after an update (TSN normalization-version stamp + auto-rebuild from raw), a real `0` never reads as blank, and the offline check suite now gates every release in CI |
| `v0.19.0` | Jul 6 | **Usability + trust + the structural cleanup** — one-click "Validate & package results"; the same report grouping on every tab; add-today to the by-day matrix; the codebase reorganized (shared comparator/PDF substrates, GUI/worker/matrix/app.js splits, a proven add-a-report recipe) with `compare_core` re-blessed cell-for-cell; safety hardening (owned-folder-only reset, pre-install digest re-verify, batch-dest validation) |
| `v0.19.1` | Jul 7 | **Highway Detail/Summary export goes live** (the v0.18.1 reserved pair, export-only for now) + a validation phantom-env fix (the store's TSN drop folder was miscounted as an export environment) |
| `v0.19.2` | Jul 7 | **Highway Detail (PDF)** print edition (the vendor shipped the report on the dev site) + **dual-edition coalescing** — selecting both editions of a report generates it once and saves both instead of twice |
| `v0.19.3` | Jul 7 | **Hotfix** — Highway Detail stopped re-selecting the report on every route (the site's grouped menu shows the short label "Detail"; the per-route stale-form check now confirms the report by its stable id, not the on-screen text) |
| `v0.20.0` | Jul 7 | **Highway Detail fully integrated** — consolidators (Excel + PDF-sourced), the vs-TSN comparison (canonical roadbed-aware key, Report View replica, Notes), the PDF↔Excel export self-check, the TSN library entry, both matrices; schema verified against the full statewide bundle + the 60k-row TSN extract (the TSN PDFs cross-checked ≥99.9% against it) |

---

## Chapter 1 — The console era (May 20)

It didn't begin as an app. The first commit — `944a487 Initial commit` — was
**9 files, 856 lines**: three `.bat` files (`setup`, `login`, `run_export`), two
exporters (Ramp Summary and Ramp Detail), and `common.py`. You drove it from a
terminal. Over that same day Highway Sequence and the consolidators were bolted
on and the per-route timeout was raised to 6 minutes — twelve commits, four tiny
PRs. Then the project went quiet **for two weeks**.

## Chapter 2 — The desktop app, in one day (June 4) · `v0.1.0` → `v0.2.0`

On June 4 the project woke up and **21 commits** landed — still the busiest day
in its history. One decision defined everything after it: *non-technical Caltrans
staff should be able to unzip a folder and double-click an exe.* The commit
`88764bb start portable desktop-app conversion (phases 0, 2, 3a)` did it in
numbered phases — importable core → a Tkinter window → a reliability layer
(`file logging, preflight, retry, failure screenshots`) → PyInstaller packaging.
Before the day was out there was also an experimental **parallel fast mode**, a
live run timer, and per-route route selection. Console script to packaged desktop
app in a single sitting.

## Chapter 3 — Slim down, add reports (June 5) · `v0.3.0` → `v0.4.1`

`v0.3.0` made a smart call: stop shipping a whole browser inside the bundle and
drive the machine's installed Edge/Chrome instead — **the download dropped from
587 MB to 148 MB**. `v0.4.0` added Highway Log, multi-report export (run several
report types in one go), and a Cancel button that stops mid-export rather than
between routes.

## Chapter 4 — The login wars (June 5 → 10)

This is the part the repo wears on its sleeve. Managed Caltrans Edge *relaunches
itself into the work profile mid-Azure-AD-login*, killing the automation
window — organizational behavior, nothing the tool did. June 5 reads like a
fistfight:

- `prevent compat-layer relaunch + debounce close`
- `Revert GUI login to the simple wait-for-button flow`
- `Sign in with Chrome; exports stay on Edge`
- `try Edge InPrivate first, fall back to Chrome`
- `Default sign-in to Chrome; document Edge sign-in as a known unresolved issue`
- `Revert "Merge pull request #13..."` — undoing the whole branch
- and finally, parked: `docs: record Edge sign-in as a known open issue to fix later`

Four of the repository's reverts cluster right here.

Then **June 10 was the comeback.** A rapid-fire branch shipped `v0.5.0` →
`v0.7.x` and solved it three ways at once: persistent-profile Edge **recapture**,
an unmanaged **Built-in Chromium** channel (org policy can't touch it), and
**silent device sign-in** so exports provision themselves with no saved session.
The "✅ RESOLVED (v0.5.0)" block still in `CLAUDE.md` is the victory lap.

## Chapter 5 — The site moved underneath them (June 10 → 11) · `v0.7.5` → `v0.7.6`

Mid-comeback, TSMIS itself changed and broke sign-in again — a second debugging
saga (`fix sign-in for new TSMIS site`, `ride the app's auto-OAuth flow`,
`harden signed-in detection`). It cracked here:

> `064f2d2` — *fix the real bug: sign-in succeeded but the site-params check
> reloaded it away (CONFIG is a lexical global, not window.CONFIG)*

Sign-in was *succeeding*; the tool's own post-login "right data source?" check
was reloading the page, which destroys the app's memory-only token and strands
the browser back at the portal. That entire class of pain is why `v0.7.6` is
`log every decision and crash; errors name the failing step` — the "one log
upload answers it" contract.

## Chapter 6 — Tearing out the GUI (June 11) · `v0.8.0` → `v0.8.1`

Tkinter could never match the approved design or fit small screens, so `v0.8.0`
**threw it out and rebuilt on WebView2** (`27259f5`, **2,753 insertions /
1,225 deletions across 19 files** — the single largest change in the repo) while
the export engine underneath stayed untouched. The next day a *downloaded*
release bit back: `v0.8.1 unblock bundled .NET assemblies at startup` — Windows'
Mark-of-the-Web was tagging every `.dll` and the CLR refused to load them. A bug
only downloaded zips could ever hit; dev runs and CI never saw it.

## Chapter 7 — The Compare era (June 11) · `v0.8.2` → `v0.9.0`

The tool grew past *exporting*. A TSN Highway Log consolidator and a **Compare
tab** arrived — diffing TSMIS against TSN through roughly **two million live
Excel formulas**, in manual-calculation mode so the workbook opens instantly and
recalculates on F9. `v0.9.0` (`a89edba`, 1,798 insertions) added one-click
self-updates plus the comparison overhaul: Only-in tabs, a Spot Check sheet,
live self-checks, and a fast plain-values output flavor alongside the auditable
live-formula one.

## Chapter 8 — v0.10.0, the big one (June 11 → 12) · `v0.10.0`

A cluster of headline features, all refactored onto shared cores:

- **Environment-labeled run folders** — `output\<date> <source>-<env>\`, so SSOR
  and ARS exports never mix (and cross-environment comparison becomes possible).
- **Live browser previews** — a status row per browser with a Preview button that
  pops a real screenshot, plus a **Verify-env** button to confirm the site loaded
  the environment you picked, without running an export.
- **A Settings tab** — timeout/worker overrides, per-env URL overrides (the
  stopgap for "the site moved before an update shipped"), a Built-in Chromium
  download manager, support-bundle export, and Delete-all-reports.
- **Cross-environment comparison** for all four reports, built by extracting the
  comparison logic into one schema-driven `compare_core`.
- **A verdict on every comparison** — "✓ EVERYTHING MATCHES" / "✗ DIFFERENCES
  FOUND" leading the dialog, the run log, and the workbook banner.

## Chapter 9 — The final sprint: hardened by the field (June 12) · `v0.10.1` → `v0.10.4`

The last stretch is the field rewriting the design one more time, and a sixth and
seventh report type:

- **`v0.10.1` — self-update without PowerShell.** Locked-down work PCs block
  PowerShell for standard users; the old updater downloaded the new version and
  then *silently failed to install it*. The staged exe now applies itself — no
  scripts, no cmd, no admin — and fails loudly (stays open on the old version)
  instead of closing into nothing.
- **`v0.10.2` — the new TSMIS address baked in.** The report site moved to
  `tsmis.dot.ca.gov`; this version points all six source/environment combinations
  there out of the box. Added a Settings **Check all environments** scan and the
  page address shown in preview/verify screenshots.
- **`v0.10.3` — Intersection Summary & Detail** (reports 5 and 6), an automatic
  background environment scan, reliable two-phase updates, and the managed-Edge
  gremlin from Chapter 4 finally dodged in fast mode too:
  *parallel browsers avoid managed Edge* — concurrent work runs in Built-in
  Chromium / Chrome, leaving Edge only for its one-click sign-in.
- **`v0.10.4` — Intersection reports matched to the live site** (no "TSAR:"
  prefix, Summary exports as XLSX), **dual login indicators** in the title bar
  (Saved login vs. Edge one-click), and the short-lived Dev update channel
  removed again.

## Chapter 10 — Trust, scale, and the Highway Log endgame (June 16 → 18) · `v0.11.0` → `v0.14.2`

The last three days turned the tool from "works" into "trustworthy as a
deliverable," then finished the Highway Log story it had been circling since
Chapter 7.

- **`v0.11.0` — the audit patch.** A ruthless read-only audit (multi-agent
  fan-out, source-backed against the live site) drove a hardening release
  implemented by **two agents in parallel** on a shared branch. It brought a
  marker-independent **no-download fast-fail** (`EmptyExport` — an empty route now
  fails in ~60 s instead of hanging ~21 min), OAuth-**token redaction** in logs, an
  updater **SHA-256 + staged-allowlist** check, a saved-file **integrity gate**, and
  the comparison **incompleteness contract** (`⚠ COULD NOT COMPARE EVERYTHING`).
  The comparisons re-keyed on the granular **postmile** — cross-env Highway Sequence
  fell from 15,797 to 5,070 diff cells once positional misalignment was removed.
- **`v0.11.1` — the TSN converter, flawless.** Audited against all 12 district PDFs
  (60,083 rows): 0 dropped characters, 0 row mismatches, 0 description leaks — with
  three structural guards so totals-footer text can never corrupt a Description.
- **`v0.12.0` — labeling, control, scale.** Self-describing output filenames,
  **Pause/Resume** (works in fast mode, unlike Skip), **auto-consolidate on finish**,
  and **Export Everything** — every report × every environment into one
  always-current store, resumable across restarts via a persistent manifest.
- **`v0.13.0`–`v0.13.1` — interface and trust.** A right-column run lifecycle
  (pre-flight summary → live ETA → completion summary + retry-failed), accessibility,
  a completion notification, **revert to the previous version**, and a subtle but
  important compare fix: **duplicate-key pairing by similarity**, so two segments at
  the same postmile no longer flag phantom differences.
- **`v0.14.0`–`v0.14.2` — the Highway Log endgame.** The vendor's Excel Highway Log
  export is *buggy* — it drops rows and whole roadbed-column blocks. So the tool now
  consolidates the report's **own PDF** (a cell-rectangle parser, verified flawless
  across all 252 routes) and ships **PDF-sourced comparisons** that expose the Excel's
  bug directly. Two deeper fixes landed with it: every Highway Log column was
  **relabeled to its true meaning** (the vendor had mislabeled most — `N/A` is really
  *Non-Add Mileage*), corrected in one source of truth; and a **roadbed-aware
  comparison key** that unifies how TSMIS and TSN encode a divided highway's two
  roadbeds, surfacing ~4,800 genuine differences the old key hid. The `.14.1`/`.14.2`
  hotfixes folded the Highway Log comparisons into a Compare sub-tab, clarified the
  Consolidate labels, and cleared a 22-finding UI-vs-logic audit.

## Chapter 11 — The comparison matrix, then every report (June 19 → 20) · `v0.15.0` → `v0.17.0`

The Compare tab had always been one-report-at-a-time. `v0.15.0` turned it into a
**grid** — the **Everything comparison matrix** (report × environment), each cell a
colour-coded discrepancy count with per-cell / per-row / per-column refresh, all over the
one schema-driven `compare_core`, left untouched. `v0.16.0` made the grid *workable* at
scale: a **job queue** so a second click lines up instead of being rejected, **fast mode**
(several browsers at once), and a second, **by-day** matrix that pits a chosen export day
against TSN. `v0.16.1` polished both and **staged** the finale — every report appeared in
the vs-TSN matrix, greyed, with the plumbing waiting.

`v0.17.0` flipped them all on. With the complete raw TSN **and** TSMIS for all six reports
in hand, every report gained a vs-TSN comparator — Ramp Summary and Intersection Summary
as statewide **category-count** roll-ups, Ramp Detail / Intersection Detail / Highway
Sequence as **postmile-keyed** flat diffs (Highway Sequence needed a brand-new district-PDF
parser and a county-relative key, since California postmiles restart per county) — and the
last cross-environment gaps (Intersection ×2, Highway Log PDF) closed, completing the grid:
**every report × {between environments, vs TSN}**, plus Highway Log's PDF-vs-Excel
self-check. A **canonical TSN library** gave each report's source data one fixed home with a
Settings panel, and the by-day matrix got a one-stop **Export today** column that exports,
consolidates and compares in a single click. The whole surface was then audited
report-by-report against the raw ground truth — each comparator proven cell-for-cell several
independent ways, with `compare_core`'s Route-1 Highway Log canary byte-identical throughout
(every new behaviour added through opt-in schema fields).

It closed with a UX cleanup the field had earned: **sign-in and the browser picker** — long
the most confusing corner — were rebuilt. Edge one-click is now proven quietly in the
background; the Browser dropdown became a read-only "what's exporting" indicator with the
real choice moved into Settings; and both matrices learned to **flag** a report the
environment check found missing, before you waste an export on it.

## Chapter 12 — The engineering close-out (June 21 → 26) · `v0.17.1` → `v0.18.1`

With the feature surface complete, the last stretch turned inward — a hotfix, then the
largest *non-feature* release in the project, then a field-driven close-out that kept the
exporter working as TSMIS itself began to move again.

**`v0.17.1` — the matrix-tab hotfix.** Using v0.17.0 in anger surfaced the usual
post-big-release rough edges: the matrix tabs scrolled into a band of blank space (the
recurring `sr-only`-containing-block bug, now Lesson 10), the Matrix-options panel was
crushed on short screens, and **Stop / Clear** wouldn't interrupt a sign-in that was
hanging. All fixed, plus a self-documenting TSN library (a ready-made folder tree that
says where each report's file goes) and two `.gitignore` tightenings.

**`v0.18.0` — the structural overhaul.** This is the one release with almost nothing for a
user to click and the most change underneath. The engine `common.py` was dissolved into an
acyclic set of single-purpose leaves (`auth_nav`, `report_nav`, `session`, `site_target`,
`routes`, `errors`, `timeouts`, `browser_channels`, `edge_device`), with `common.py` left
as a re-export shim so every `from common import X` still works while the import graph
became *guardable*. Three safety contracts were made explicit and producer-owned: an
**outcome** model where a partial / failed / cancelled run can never be promoted, cached,
or shown green (counts decide, never summary text); **transactional artifacts** that
write-then-`os.replace` and keep the last-good copy on failure, each carrying a fail-safe
completion sidecar; and a single **report-catalog** source of truth that `reports.py` now
*derives* from, so the registry can't drift. The GUI was split the same way (a
task-coordinator owning gate state, a Python⇄JS enum SSOT, endpoint groups, and `app.js`
broken into cohesive `ui-*` modules). One new report rode along — **Intersection Detail
(PDF)**, the eighth type, an exact parallel of Highway Log (PDF) — and the packaging /
updater were hardened to fail-closed (checksum-or-refuse, a staged re-hash right before the
swap, a zip-slip guard, a hash-pinned reproducible build, and a credential-safe work-PC
**evidence kit**). Through all of it `compare_core` was left **byte-for-byte unmodified** —
the regression lock held.

That eighth report arrived by an unusual route. While the refactor was underway, the
*original* line kept evolving the Intersection Detail vs-TSN comparison across
`v0.17.2`–`v0.17.8` (position-aligned dates, the signal-type crosswalk, a printed-report
"Report View"). Rather than merge that line into the refactor and risk dragging back the
structure it had just dismantled, every one of those commits was **forward-ported** —
re-implemented on the refactor branch. The two histories diverged — `main` lagged at
v0.17.8 while the refactor branch carried the real present — and stayed split until a
post-v0.18.1 supersede merge finally reconciled them (below). v0.18.0 also introduced
the project's **two-tier release model** — it is the *offline-validated candidate*
(everything provable from CI), with operational sign-off reserved for a field run on a real
locked-down work PC. That sign-off is v0.18.1.

**`v0.18.1` — the field-validated close-out, and the site moves again.** The work-PC run
surfaced a live break: TSMIS had begun migrating its report dropdown from a flat list to
grouped fly-out menus (already live on the dev site), where a leaf's visible text is just
"Detail" / "Summary" and the report's real identity lives in a stable `data-value`. The
exporter had always matched the menu by visible text, so Intersection export broke the
moment the menu changed. The fix matches by **`data-value` first** (falling back to text
for the old flat menu) and reveals the fly-out before clicking — so exports keep working on
**both** the current production menu and the new grouped one, with nothing for the user to
do when prod follows. The same migration was the cue to reorganize the app's own picker to
**mirror the website's grouping** (flat Highway Log / PDF / Sequence, then Ramp and
Intersection families) and to lay **reserved-but-disabled groundwork** for the two reports
the site is about to add — **Highway Detail** and **Highway Summary**, listed greyed as
"coming soon," with append-only stable ids, rejected server-side until the site enables
them. Two smaller things rode along: the matrix job queue no longer leaves a phantom chip
after a drained job, and a comparison column mislabeled "Roadbed" was corrected to **"Route
Suffix"** (it flags a route's letter suffix, e.g. 210U vs 210 — figures unchanged).
Released from the branch. The long-standing `main` divergence was then closed for good: a
`-s ours` **supersede merge** fast-forwarded `main` up to the v0.18.1 tree — no force-push,
the forward-ported v0.17.2–v0.17.8 commits preserved as ancestry — and the now-redundant
refactor branch was retired. `main` is the single line once more, caught up to the present
it had been chasing since the overhaul began.

**`v0.18.2` — when "working" reads as "frozen."** A work-PC log showed the Intersection
Detail vs-TSN comparison apparently failing to build its values workbook — repeatedly
started, then cancelled. Nothing was broken: it's the largest comparison the app makes
(~17,000 rows), and its final "Report View" rollup re-lays-out every record as two styled
rows with **no progress output**, so it sat silent for two-and-a-half minutes and looked
hung — so it kept getting cancelled before it could finish. The fix was honesty, not speed:
narrate the silent stretch (and tighten the progress/cancel cadence so Stop lands sooner),
**skip** the optional millions-of-formulas live-formulas twin on the giant bulk rebuilds
(the values copy already holds every value, and the skip says so), and — caught in the same
pass — surface the **Route Suffix** in the Report View, where the v0.18.1 rename had only
reached the Comparison tab. A reminder that on a locked-down PC a user can't tell "slow"
from "stuck," so the tool has to.

**`v0.18.3` — two zeros that weren't equal.** Field use of the same Intersection Detail
comparison surfaced a column — the intersecting route's postmile — that flagged a difference
at exactly the handful of intersections where the value existed. The cause was a one-character
habit: `str(v or "")`. A postmile of `0` is falsy, so `0 or "" → ""` quietly turned TSN's
numeric `0` into a blank, while TSMIS's text `"0.000"` normalized to `"0"` — two spellings of
the same zero, forced to disagree. Preserving a real `0` (`"" if v is None else str(v)`) made
the matching zeros line up and dropped 43 phantom cells from the statewide canary, touching no
other field. The same pass fixed a sibling oversight the user spotted: an intersection that
exists in only one system was being rendered in the "Report View" as an ordinary record with
every field bleeding red, instead of a calm "Only in TSMIS / TSN" band like the main sheet
already showed. Both small; both the field, again, finding what no offline test had thought to.

**`v0.18.4` — the phantom that wouldn't leave.** Another work-PC log, another frontend-only
truth: a finished or cancelled comparison kept sitting in the matrix queue marked "running" —
in *both* matrices — until the next job replaced it, and couldn't be cleared. The backend was
correct all along (the log showed a clean finish and gate release). The cause was CSS: a
`.mc-group { display:flex }` rule outranked the browser's `[hidden] { display:none }`, so
setting `hidden` never actually hid the panel — and a render path early-returned without
clearing the row list. Two durable lessons banked: a `hidden` toggle silently fails if a
class-level `display` rule outranks it, and the mock emits completion events in a *different
order* than production, so order-sensitive frontend bugs only reproduce by replaying the real
order.

**`v0.19.0` — usability, trust, and the big cleanup.** The release that turned the manual
work-PC ride-along into a button: **"Validate & package results"** runs every report already on
the PC through the real comparison pipeline and ships the outcomes, TSN freshness, and logs in
one credential-safe file — replacing the old command-line evidence step. Alongside it, three
smaller usability asks (the same report grouping on every tab; today's column available in the
by-day matrix before anything is exported; matrix side-panels that stay usable on a laptop
mid-run) and a large **structural cleanup** that changed no behavior: every comparator now rides
one shared file-comparator skeleton, the PDF parsers share one table library, the big GUI files
split into focused modules, and "add a report family" became a *proven* recipe with its own
automated check. The comparison engine was re-blessed cell-for-cell against the real statewide
data (2.79M cells identical). Safety hardening rode along: "delete all reports" now only removes
folders the app itself created, an update re-verifies its download's integrity one last time
right before installing, and the Export-Everything destination is validated when you pick it.
The **work-PC sign-off arrived the same day** — the 0.18.4→0.19.0 self-update, the TSN
auto-rebuild, and the Validate button all proven in the field — and it surfaced exactly one bug.

**`v0.19.1` — the reserved pair goes live.** The Validate button's field run had flagged a
single phantom: validation was walking *every* child folder of the export store and counting any
that held report files as an "environment" — so the store's `_tsn_input` TSN-drop folder became a
bogus environment, and its TSN workbook got fed into the comparison as if it were a TSMIS export
(the layout check then correctly rejected it). Constraining the walk to real `<src>-<env>` folder
names dropped the phantom and made the run read a clean 18-of-18. Shipping in the same release:
the **Highway Detail and Highway Summary** exports the site was adding — reserved as disabled
groundwork back in v0.18.1 — went **live**, with real specs modeled on their Excel siblings, lifted
out of the disable gate. Their consolidation and comparison are a later feature; where the site
still greys the pair, selection fails fast instead of stalling.

**`v0.19.2` — the report arrives, and stop doing the work twice.** The vendor shipped Highway
Detail on the dev site (a fresh capture confirmed `highway_detail.js` — its `hd_printAll` builds
the same print layout Highway Log uses), so the report got its **print-layout PDF edition** — the
third report, after Highway Log and Intersection Detail, to ship in both Excel and PDF. That third
pair prompted the second half: **coalescing**. Selecting both editions of a report used to load
every route twice — once for the Excel export, once for the PDF — which is wasteful and doubles the
load on the TSMIS server. Now the standard export path generates each route **once** and saves both
files off that single render, the Export-button save first and the DOM-rebuilding Print capture last
(the print layout replaces the page, so it has to go second). Each edition still keeps its own
result, staging, and consolidation. A design note the field would recognize: the win is real in the
default sequential path, but *fast mode's* parallelism is a different speed lever, so coalescing it
is left as a follow-up rather than forced to fit.

**`v0.19.3` — the guard that cried drift.** The first real run of the new Highway Detail export
came back from the field flooding the log with "report form drifted" — the per-route safety check
re-selecting the report on *every* route. It was a false alarm born of the site's own menu
migration: Highway Detail lives in the new grouped "Highway ▸ Detail" fly-out, whose selected leaf
*displays* the short label "Detail", and the guard was comparing that visible text to the full
"Highway Detail" it expected — a mismatch on every route. The exports were always correct (it
re-picked the right report by its stable id each time), but it re-opened the menu and re-fanned the
route selection ~250 times per run for nothing. The fix is the same lesson the codebase already
learned for *selecting* reports: trust the stable id, not the on-screen text. The guard now reads
the hidden `#reportSelect`'s `data-value` and only falls back to the visible label when there is no
id — so it stays silent on the happy path while still catching a genuinely reset form. A one-line
class of bug (visible text ≠ stable identity) that only surfaces once a report moves into the
grouped menu, which is exactly where the whole report catalog is headed.

**`v0.20.0` — Highway Detail joins the family.** The user delivered the promised resource drop —
a complete statewide dev bundle: all 252 TSMIS Highway Detail routes in BOTH editions, the
statewide 56-column TSN `TSAR - HIGHWAY DETAIL` extract, all 12 TSN district PDFs, and the
annotated TASAS legend. The integration was built the way the prep file demanded: *evidence
first*. A statewide reconciliation study (46,847 matched rows) decoded every convention before a
line of product code was written — TSN prints an explicit `A` where TSMIS leaves Non-Add blank
(98.7% of rows); TSMIS zero-pads what TSN doesn't; TSMIS puts the Rural/Urban layer date in the
printed slot where the legacy report (and TSN) put the ADT begin year, so that column differs on
~99% of rows *by construction*; and — the find that mattered most — TSMIS glues an `R`/`L` onto
the postmile for independent-alignment roadbed rows where TSN prints a bare postmile and says R/L
in Highway Group, which had four routes (282, 880S, 011, 260) matching ZERO rows until the
canonical roadbed-aware key unified the encodings. The equation marker turned out to be attached
to *different rows* by the two systems, so it moved out of the key into its own compared `PS`
column — a marker disagreement now flags as a one-cell diff instead of tearing the row into a
false one-sided pair. The TSN district PDFs were cross-checked against the Excel extract
(57,647 records, every shared field ≥99.9% identical) before the machine-readable Excel was
blessed as the library source. The comparison itself ships in the Intersection Detail mold —
compare-everything, nothing suppressed, a Notes sheet that names every normalization, and the
printed two-line TASAS Report View with red diffs and a Major count that ignores the structural
date columns. `compare_core` was never touched: the whole family rides a new opt-in
`CompareSchema`, and the locked canaries proved it byte-identical.

---

## Three threads that run through all of it

1. **The field keeps rewriting the design.** Managed Edge killing the login
   window, Mark-of-the-Web crashing the CLR on download, PowerShell-blocked PCs
   breaking the updater — three separate "worked on my machine, then a real
   Caltrans PC ate it" failures, each now a permanent design constraint.
2. **Refactor toward one core.** One `ReportSpec` loop serves eleven reports; one
   `compare_core` serves two comparison families; one catalog feeds both the GUI
   and the console. The shells (Tkinter → WebView2) were swappable *because* the
   engine stayed console-free — and v0.18.0 took the idea furthest, dissolving
   `common.py` into an acyclic set of guardable leaves and deriving the entire
   registry from a single source of truth, all with `compare_core` left
   byte-for-byte intact.
3. **It's honest about dead ends.** The reverts aren't hidden — five Edge-login
   attempts were tried, reverted, parked as a known issue, and later beaten
   properly.

*Generated from the git history. To regenerate the raw spine:*
`git log --reverse --pretty=format:"%h|%ad|%s" --date=short`
