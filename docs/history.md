# HISTORY — TSMIS Reports Exporter

How a one-day console script became a portable, self-updating Windows desktop
app — told from the repository.

**By the numbers:** 191 commits · 37 pull requests · 34 tagged releases ·
7 report types · **May 20 → June 18, 2026**.

This is the narrative companion to [`CLAUDE.md`](../CLAUDE.md) (the authoritative
"how it works and why") and [`build/release_notes.md`](../build/release_notes.md)
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

---

## Three threads that run through all of it

1. **The field keeps rewriting the design.** Managed Edge killing the login
   window, Mark-of-the-Web crashing the CLR on download, PowerShell-blocked PCs
   breaking the updater — three separate "worked on my machine, then a real
   Caltrans PC ate it" failures, each now a permanent design constraint.
2. **Refactor toward one core.** One `ReportSpec` loop serves six reports; one
   `compare_core` serves two comparison families; one registry feeds both the GUI
   and the console. The shells (Tkinter → WebView2) were swappable *because* the
   engine stayed console-free.
3. **It's honest about dead ends.** The reverts aren't hidden — five Edge-login
   attempts were tried, reverted, parked as a known issue, and later beaten
   properly.

*Generated from the git history. To regenerate the raw spine:*
`git log --reverse --pretty=format:"%h|%ad|%s" --date=short`
