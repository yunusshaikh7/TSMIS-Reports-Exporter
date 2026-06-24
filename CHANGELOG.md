# Changelog

All notable changes to TSMIS Reports Exporter, newest first. Each GitHub
release shows only its own section (see `build/gen_release_notes.py`).

## v0.17.7 — 2026-06-24

- **The Intersection Detail comparison vs TSN now covers every shared column, ordered to
  match the printed report.** It previously left out the five effective dates (INT type,
  control type, lighting, mainline, cross-street), the Main Line Length, and the
  intersecting-route block (route / postmile / prefix / suffix) — these are now compared
  and counted like everything else. The five effective dates are stored exactly **one day
  apart** between the two systems (TSMIS records Dec 31 where TSN records Jan 1) — a
  consistent encoding convention rather than thousands of edits — so they flag on that
  one-day offset and the **Notes sheet explains it**. The intersecting-route postmile
  suffix now reads from the correct column.
- **Two "2024" date columns are shown but greyed out and never counted.** The report carries
  a second mainline effective-date and an int-street effective-date that are a uniform
  bulk-load stamp with no matching TSN field, so they appear in the comparison **greyed for
  reference** and never count as a difference. The Notes sheet lists them, and **every
  normalization applied is still spelled out** so a match reads as "equal after the stated
  normalization," not raw equality.

## v0.17.6 — 2026-06-24

- **Fixes "Signalized ≠ P" still showing in the Intersection comparison even though they
  should match.** The app compares against a saved, normalized copy of the TSN data that
  wasn't rebuilt after the v0.17.5 crosswalk was added, so it still held the old raw signal
  codes. The crosswalk (and the other normalizations) is now re-applied whenever that saved
  copy is read — so the comparison is correct immediately, with no need to re-import or
  rebuild anything.
- **The Intersection Detail comparison vs TSN is now a complete, mechanical diff — every
  column the two systems share is compared and counted, nothing is hidden.** It previously
  left the cross-street attributes and the Date of Record out of the count; they are now
  compared like everything else. Where a whole column differs by its nature, the **Notes
  sheet explains why** instead of hiding it (the Date of Record is a TSMIS refresh date vs
  TSN's historical record date, so it differs on nearly every row; TSMIS leaves cross-street
  detail blank for ~37% of intersections). Each workbook's Notes sheet now lists **every
  normalization applied** — including the ones that make values match — so a match reads as
  "equal after the stated normalization," not raw equality.
- **The Intersection Summary now folds the TSN signal sub-types the same way the Detail
  does.** The old TSN signal codes J–P merge into one "Signalized" category, so signalized
  intersections compare directly (instead of as separate one-sided rows), and the "no data"
  categories the TSN summary reports as zero are now compared too. Roundabout stays
  one-sided — the TSN statewide summary doesn't tabulate it.

## v0.17.5 — 2026-06-24

- **Signal control types now line up between TSMIS and the older TSN data.** The old TSN
  system recorded signalized intersections under six detailed sub-types (pretimed,
  semi-/full-actuated, 2- vs multi-phase — codes J through P), which TSMIS rolls up into a
  single "Signalized" category. The Intersection Detail comparison vs TSN now applies that
  official crosswalk, so those stop being flagged as differences — **cutting the reported
  discrepancies roughly in half** (~2,600 fewer; control-type differences went from ~2,614
  to 1). It stays transparent: wherever the crosswalk merged the codes, the Control Type
  cell reads "Signalized" (instead of a raw code) so it's clear on the comparison page that
  the normalization was applied, and the Notes sheet spells out the mapping. Applies to both
  the Excel and the PDF vs-TSN comparisons, and both matrices. Geometry/intersection type
  needed no crosswalk — both systems already use the same codes.

## v0.17.4 — 2026-06-22

- **Fixes a crash opening the by-day "vs TSN" matrix.** v0.17.3 added Intersection
  Detail (PDF) as a matrix row but didn't finish wiring it into the matrix's
  consolidated-workbook bookkeeping, so opening the by-day matrix tab failed with an
  internal error (`no consolidated filename for intersection_detail_pdf`). It's now
  wired the same way Highway Log (PDF) is — consolidate, cross-environment, vs-TSN,
  and vs-Excel all work — and a regression check now covers every matrix row so this
  can't slip through again.

## v0.17.3 — 2026-06-22

- **Intersection Detail (PDF) now plugs into the rest of the app — consolidate, compare,
  and the matrices.** Just like Highway Log, the PDF and the Excel export of Intersection
  Detail can disagree on the data, and the PDF is the accurate source. So the
  "Intersection Detail (PDF)" export now also:
  - **Consolidates** — *Consolidate ▸ TSMIS Intersection Detail (PDF)* combines the route
    PDFs into one workbook in the same 36-column format as the Excel export.
  - **Compares** — three new comparisons: between environments, **TSMIS (PDF) vs TSN**, and
    **TSMIS (PDF) vs TSMIS (Excel)** (the last pinpoints exactly where the two TSMIS exports
    differ).
  - **Shows up in both matrices** — Intersection Detail (PDF) is now a full row in the
    Everything matrix and the by-day "vs TSN" matrix, with its own vs-TSN / vs-Excel modes.

  The PDF parser was reconciled against every route statewide (218 of 218) and reproduces the
  Excel data exactly, apart from harmless whitespace in the free-text Description.



- **Export Intersection Detail as a PDF.** A new **Intersection Detail (PDF)** report
  saves the same Intersection Detail data as a print-ready PDF (Letter, landscape) —
  the full report across every page, not just the page shown on screen — alongside the
  existing Excel export. Pick it on the Export tab, in **Several / all report types at
  once**, or as option 8 in the console menus. Like Highway Log (PDF), it's
  export-only: a faithful rendering of the report, with no separate consolidate/compare.

## v0.17.1 — 2026-06-21

A quick fix-up of issues found using v0.17.0 on the matrices.

- **No more blank space below the matrices.** A hidden control in the Matrix-options
  panel was stretching the page so it could scroll down into a large empty area below
  the window. The panel's fast-mode / comparison-output toggles are now contained, so
  the matrix tabs stay put.
- **The Matrix-options panel is usable again.** On shorter screens it was being squeezed
  into a tiny scrolling sliver while the activity log hogged the space — now the options
  (queue, day columns, set-all modes, report toggles, fast mode) get the room and the log
  shrinks to a compact status strip.
- **Stop / Clear now work quickly when sign-in is failing or slow.** A matrix export that
  couldn't sign in used to ignore **Stop all** / **Clear queued** until its sign-in
  attempt timed out; both now interrupt the sign-in within about a second (normal and
  fast mode), so a stuck queue clears right away instead of feeling frozen.
- **The TSN "Choose…" picker opens to the TSN library.** Picking a TSN workbook on either
  matrix now starts in that report's own folder inside the TSN library, instead of the old
  per-run input location.
- **The TSN library is now self-documenting.** It starts as a ready-made folder tree —
  each report has its own `…/<report>/raw/` folder with a short note saying which file(s)
  to drop there, plus a README — so it's clear where to put your TSN reports before you
  import the first one. **Open folder** (Settings ▸ TSN reports) creates this tree on
  demand too.

## v0.17.0 — 2026-06-20

- **Every report now compares against TSN — not just Highway Log.** Ramp Summary,
  Ramp Detail, Highway Sequence, Highway Log (Excel and PDF), and Intersection
  Summary & Detail each have a TSMIS-vs-TSN comparison, live in **both** the Everything
  matrix and the by-day "vs TSN" matrix. The rows that used to be greyed "coming next
  update" are now active, and **"Set all to vs TSN"** switches every report at once.
- **And every report compares between environments.** Intersection Summary/Detail and
  Highway Log (PDF) gained their cross-environment comparison too, so the grid is now
  complete: every report × {between environments, vs TSN}, plus Highway Log's
  PDF-vs-Excel self-check.
- **Intersection Summary & Detail now consolidate** into a single workbook like every
  other report — so they can be compared and reused, not just exported.
- **A home for your TSN data.** Each report's TSN source (district PDFs or a statewide
  workbook) lives in one fixed folder, managed from a new **Settings ▸ TSN reports**
  panel: import the raw file(s) once, click **Rebuild**, and a status dot shows whether
  the comparison data is current. The panel shows the folder location with an
  **Open folder** button, and on the matrix each report has its own TSN picker.
- **One-stop "Export today" on the vs-TSN-by-day matrix.** A new **Export today →**
  button (and per-row / per-cell ↻) pulls a fresh, dated column for every report and
  automatically consolidates and compares each one against TSN — filling the column in
  one go. Only today is exportable; past days stay as the immutable record you pulled.
  Fast mode, worker count, and pause/skip all apply.
- **Sign-in and browser, made obvious.** Edge one-click sign-in is now checked quietly
  in the background (on launch and when you switch site), so the indicator lights up by
  itself. The **Log in** button now simply opens Google Chrome to save a reusable login.
  The old Browser dropdown is gone — the title bar shows a read-only **"Export via …"**
  indicator of what's actually exporting, and the one real choice (Built-in Chromium vs
  installed Chrome, Chrome by default) moved to **Settings ▸ Export browser**. Microsoft
  Edge is still used for one-click sign-in and as a fallback.
- **The matrices warn you before an export fails.** When the environment check has found
  a report greyed-out or missing on a site, both matrices now flag that report/cell amber
  — the same warning the Export tab shows — so a doomed comparison is obvious up front.
- **Drag to reorder.** Rows and columns on both matrices can be dragged into the order
  you prefer; the order is remembered.
- **Divided-roadbed routes match correctly.** Intersection rows whose TSN route carries a
  roadbed suffix (e.g. 210U vs 210) are now matched to their TSMIS counterpart, with a
  note when the suffix is the only difference.
- **Reliability + polish.** The Highway Log PDF reader now flags an incomplete parse
  instead of silently dropping rows; a thorough UI-consistency pass; and a large new set
  of automated checks across every new comparison.

## v0.16.1 — 2026-06-19

- **The TSN comparison view is now a full matrix that covers every report.** The
  Compare tab's sub-tabs are now **Cross-environment**, **vs TSN**, and **vs TSN
  Matrix**. The matrix (formerly "TSN by day") fills the screen like the Everything
  matrix and lists every report — Highway Log works today; Ramp Summary/Detail,
  Highway Sequence, and Intersection Summary/Detail appear greyed until their TSN
  comparison is added in the next update. (Highway Log's between-environments
  comparison moved back onto "Cross-environment" with the other reports.)
- **Pause, resume, and skip a matrix re-export — and watch it live.** A matrix
  re-export now shows the same per-route progress and live preview as the Export tab,
  and you can pause/resume or skip a stuck route without cancelling the whole run.
- **Pick the number of browsers for matrix Fast mode.** A browser-count picker sits
  next to the Fast mode toggle (shared with the Export tab and Settings, so it's one
  value).
- **Consolidated workbooks are saved and reused.** A comparison reuses the day's
  existing consolidated workbook instead of rebuilding it every time; a small
  indicator shows whether one exists and is current, with one click to refresh it.
- **Optional live-formulas copy of any comparison.** A toggle writes an auditable,
  recalculating workbook beside the plain values copy; each matrix remembers its own
  setting.
- **Export Intersection Summary & Detail.** These are greyed on the production TSMIS
  site but available on the development site — a new **Settings ▸ "Use development
  site"** switch points the app there (and back).
- **Fits short, wide laptop screens.** The comparison matrices no longer scroll after
  a couple of rows — the grid reclaims the surrounding space and shows all rows.
- **Polish.** The matrix-options checkboxes now match the rest of the app (no stray
  white boxes in dark mode), plus accessibility and reliability fixes across both
  matrices.

## v0.16.0 — 2026-06-19

- **Queue up matrix work instead of waiting.** On the Everything tab's
  Comparison matrix, a second action no longer says "a task is already running" —
  it joins a **queue** that runs one job at a time and moves on by itself. The
  queue is shown right on the matrix, and you can reorder it, remove a job, clear
  what's waiting, or stop everything. Line up a re-export and a rebuild, or several
  cells in a row, and walk away.
- **Two clear buttons on every row and column.** Each report row and each
  environment column now has **two** buttons with distinct icons: one **re-exports**
  that report/environment live from TSMIS, the other **rebuilds its comparisons** —
  so the bulk "refresh" you want is never ambiguous. (Re-exporting a whole row or
  column asks first, since it pulls many reports from TSMIS.)
- **Fast mode for matrix re-exports.** A new **Fast mode** toggle on the matrix
  runs re-exports with several browsers at once (the same speed-up the Export tab
  has), for when you're refreshing a lot at once.
- **New: compare exports day-by-day against TSN.** A new **"TSN by day"** sub-tab
  on the Compare tab lets you pick specific exported **days** and compare each one's
  Highway Log against TSN side by side — e.g. the 17th vs TSN next to the 18th vs
  TSN. Pick a data source, add the days you want as columns, and build each cell;
  it reuses the same TSN dataset and comparison engine as the Everything matrix.
  Highway Log (Excel and PDF) works now; the other reports appear greyed until their
  TSN comparison is added.

## v0.15.0 — 2026-06-19

- **New: a comparison matrix on the Everything tab.** A new **Comparison
  matrix** sub-tab shows every report against every data source / environment at
  a glance — each cell is colour-coded by how many differences it found (green
  for identical, shading from amber to red as differences grow), alongside the
  export date and a
  one-click link to open that comparison workbook. Choose the baseline to compare
  everything against; refresh a single cell, a whole row, a whole column, or every
  stale comparison at once; and cancel a long refresh and resume it later. Your
  matrix setup — the baseline, which reports and environments are shown, and the
  comparison mode per row — is remembered between sessions.
- **Compare the Highway Log against TSN, right in the matrix.** The Highway Log
  now appears as two rows — **Excel** and **PDF** — and each can compare
  cross-environment, against **TSN**, or Excel-vs-PDF. Drop the district TSN PDFs
  into the Everything folder and the matrix offers to consolidate them for you, or
  point a row at a consolidated TSN workbook; the file in use is shown right under
  the report name. (TSN comparisons for Ramp Summary, Ramp Detail and the Highway
  Sequence Listing appear greyed for now — groundwork for a later version.)
- **Choose what's on the matrix.** Toggle which report types and which
  environments appear, so the grid stays as compact or as complete as you need.
- **Intersection reports are clearly marked as not-yet-supported.** The two
  Intersection reports now show greyed-out everywhere (they're export-only, with no
  comparison), instead of quietly behaving differently from the rest.
- **A top-to-bottom visual polish.** Cleaner, more consistent buttons, dropdowns
  and file pickers across every tab — all readable in both light and dark mode —
  plus quick, non-intrusive animations throughout: panes, lists, the activity log
  and the light/dark switch now ease in smoothly (and fully respect the system's
  "reduce motion" setting).

## v0.14.3 — 2026-06-19

- **A "for IT" page now ships in the app folder.** Every download now
  includes an **`IT-README.txt`** next to `Start Here.txt` — a plain-language page
  for whoever in IT or security reviews the tool: what it connects to, what it
  reads and writes, how the saved login is handled, and why a portable,
  self-updating, unsigned in-house app is safe to run. It rides app updates, so
  the page stays current from this version on.

## v0.14.2 — 2026-06-18

- **Consolidate tab cleanup.** The three Highway Log consolidations now
  have clear, parallel names — **TSMIS Highway Log (Excel)**, **TSMIS Highway Log
  (PDF)**, **TSN Highway Log (PDF)** — so the plain "Highway Log" can't be confused
  for the others. The **TSMIS Highway Log (PDF)** consolidation now reads the app's
  own "Highway Log (PDF)" export straight from the output folder (with the Export-day
  picker, like the Excel one) instead of a redundant drop folder — you no longer copy
  the app's own exports into an input folder. The "Export day" picker is now hidden
  for the one report it doesn't apply to (TSN, whose district PDFs come from outside
  the app).
- **A few UI labels now match what actually happens.** The environment
  check no longer wrongly flags **Highway Log (PDF)** as unavailable on every site
  (it shares the "Highway Log" dropdown option, so it now follows that report's
  result); the Export Everything description says it writes to your chosen
  destination folder (not "dated run folders"); the auto-consolidate note lists every
  report that has no consolidator; and **Delete all reports** now also clears the
  Highway-Log-PDF outputs and the Export Everything store, so a "fresh start" really
  is one.

## v0.14.1 — 2026-06-18

- **Highway Log comparisons in one place.** The Compare tab now has a
  **Highway Log** sub-tab gathering every Highway Log comparison — TSMIS vs TSN, the
  two PDF-sourced comparisons, and across environments — beside a
  **Cross-environment** sub-tab for the plain report comparisons, instead of the old
  three-way split. (v0.14.0 briefly made this a separate top-level tab; v0.14.1
  moves it to a sub-tab inside Compare.)

## v0.14.0 — 2026-06-18

- **An accurate Highway Log, sourced from the PDF.** The site's Highway
  Log **Excel** export is buggy — it drops rows and whole roadbed-geometry
  columns, expands the report's "same as the other roadbed" `+` markers into
  numbers, and mis-attaches descriptions. A new consolidation parses the Highway
  Log **PDF** export instead (drop the per-route PDFs into
  `input\tsmis_highway_log_pdf`), producing the same 31-column workbook **without**
  those export errors — verified row-for-row against all 252 routes.
- **Highway Log columns are correctly labeled.** The vendor Excel export
  mislabeled most Highway Log columns (e.g. "N/A" is really **Non-Add Mileage**;
  the cryptic roadbed codes are surface type, shoulder widths, lane counts, …; it
  even reused "RB SH" for two different columns). Every Highway Log workbook now
  uses the **report's own legend** labels, with the old label kept in `[brackets]`,
  a hover tooltip on every column, and a **Legend** sheet explaining each one. This
  is a relabel only — the data and comparison results are unchanged.
- **Divided-highway rows now line up correctly.** On a divided highway
  each segment has two rows (one per roadbed). TSMIS marks the roadbed in the
  location (`R021.466R`/`…L`); the TSN log marks it a different way. The comparison
  used to treat these as *different* locations, so the same physical roadbed row
  showed up as **"only in TSMIS" + "only in TSN"** instead of being compared —
  hiding thousands of genuine differences. It now recognizes the roadbed on both
  sides and pairs them, surfacing those differences (audited against the source
  PDFs — every pairing is the correct roadbed, none crossed).
- **"Same as the other roadbed" markers are handled.** A roadbed column
  printed as `+`/`++` means "this roadbed's value is on the paired row" — a
  pointer, not a value. Comparisons now treat it as such (it is **never** counted
  as a difference, on either source), and a comparison cell that resolved a `+`
  shows what it points to in a hover note.

## v0.13.1 — 2026-06-17

- **Highway Log can now be exported as a PDF.** A new **Highway Log
  (PDF)** report exports each route's Highway Log as a print-formatted PDF — the
  same layout the site's Print button produces (cover page + every page) — into
  `output/…/highway_log_pdf/`, alongside the existing Excel export. Tick it on the
  Export tab like any other report.
- **Comparisons match repeated locations correctly.** When a TSMIS-vs-TSN
  or cross-environment comparison had two rows at the **same location** (e.g. two
  `001 R000.129` segments), it used to pair them in the order they appear —
  first-with-first, second-with-second — so a row that actually matched the other
  side's *second* listing was wrongly flagged as different. It now pairs repeated
  locations by **which rows are most alike** (the most fields matching), not by
  order. The row's identity is unchanged (same Route + location); only the pairing
  of repeats is smarter. This can only *remove* false differences, never add one —
  on a full Highway Log comparison it cleared ~3,600 phantom differing cells.

## v0.13.0 — 2026-06-17

- **A clearer window, and it tells you what's happening.** The right
  side of the window now follows the whole run: before you start, a **summary of
  exactly what will happen** (which reports, how many routes, where it saves);
  while it runs, progress that spells out **exactly what's running** — for a
  single export the report and route, and for **Export Everything** the
  environment it's on (e.g. "Environment 2 of 6 · SSOR / Test"), the report
  within it, the route, an **estimated time remaining**, and a row of
  per-environment markers showing which are done, which is running, and which are
  still queued (so it's finally easy to see where a big run is at); and when it
  finishes, a **completion summary** with one-click **Open folder** and **Retry
  failed routes** (just the ones that failed, not the whole run). The window also
  **flashes in the taskbar when a run finishes** so you can look away and come
  back — turn that off in Settings if you'd rather it didn't. The header was
  tidied up and the report/environment checkboxes are now fully keyboard-friendly.
- **Revert to the previous version.** Settings now has a **Revert to
  previous version** button: if an update ever causes trouble, one click
  reinstalls the release just before this one, through the exact same verified
  download-and-swap the normal update uses (your reports, login and settings stay
  put). It only appears on installs the app can update itself.
- **Two separate "check environments automatically" switches.** The old
  single setting is now two: **after sign-in** (on by default) and **after the
  app starts** (off by default) — so the background environment check can run when
  you sign in without also running every single launch.
- **Compare tab is split into sub-tabs.** The two comparison kinds —
  **Cross-environment** and **TSMIS vs TSN** — are now on their own sub-tabs
  (cross-environment shown first), instead of sharing one long list.
- **Export Everything labels every file by environment.** Files in the
  always-current store are now named with their source/environment up front
  (e.g. `ssor-prod tsar_ramp_detail_route_5.xlsx`, and the combined workbook the
  same way), so a file copied out of the folder still says which environment it
  came from. The Everything tab also **colour-codes** report types and
  environments the last environment check flagged — amber for "may be limited",
  red for "would fail" — and now greys out during an environment check like the
  other tabs.

## v0.12.0 — 2026-06-17

- **Export Everything — one always-current set of reports.** A new
  **Everything** tab exports the report types you tick across the environments you
  tick into a single folder you choose (default **All Reports (current)**). Re-run
  it any time to refresh: it overwrites that folder in place, so it always holds
  the latest of every report. A **Saved reports** list shows how old each report
  is and flags any that are lagging behind the rest, with a one-click **Refresh**
  for just that report — plus pause/resume and resume-after-restart for the long
  full runs.
- **Pause / Resume a running export.** A new **Pause** button holds the
  run between routes and **Resume** picks it back up — separate from Skip (one
  route) and Cancel (stop the run). Works in fast mode too.
- **Auto-consolidate when an export finishes.** An optional checkbox
  builds the combined workbook automatically right after the export, so the
  Consolidate step happens for you.
- **Self-describing filenames.** Consolidated and comparison files now
  carry the date + source/environment in the filename, so a file copied out of
  its folder still says exactly which run it came from.
- **Compare tab lists only relevant folders.** The cross-environment
  folder pickers now show only export runs that actually contain the report type
  you picked, instead of every run folder.
- **Buttons never cut off.** The Start / Pause / Cancel bar stays pinned
  and visible while the report list scrolls, and the tab row no longer crowds.

## v0.11.1 — 2026-06-16

- **Flawless TSN Highway Log conversion.** The TSN district-PDF → Excel
  converter now transcribes feature descriptions perfectly across all 12
  districts — totals-block footer text and page furniture can no longer leak into
  a segment's Description. This removes ~1,000 false-positive "differences" from
  the TSMIS-vs-TSN Highway Log comparison (what remains is all genuine data
  differences). Real descriptions that merely contain words like "UNCONST" or
  "TOTAL" are now kept correctly.
- **Ramp Summary audit cell explains itself.** When a route's parsed
  section sub-totals don't add up to its stated total, the consolidated workbook's
  Audit cell now names the section that's short (e.g. "⚠ Source ≠ total: Ramp
  Types") instead of a bare red result — making clear it's a quirk in the source
  PDF's own numbers on a few dense routes, not a tool error.

## v0.11.0 — 2026-06-16

- **Comparisons are far more accurate.** Comparing the same report
  across two environments used to flag large numbers of "differences" that were
  really just rows shifting position — one missing point near the top made
  everything below it look changed. Comparisons now line rows up by their
  **postmile** (a row's real identity) instead of the coarser county, so a
  Highway Sequence comparison that used to show ~15,800 differing cells now
  shows ~5,000 genuine ones; only real differences remain.
- **A comparison never claims "everything matches" when it couldn't read a
  file.** If an input file is unreadable it's no longer silently
  skipped: the result says **"Comparison incomplete"** and the workbook lists
  exactly what was left out — instead of a misleading green "everything
  matches" that quietly ignored the missing data.
- **Cleaner TSN Highway Log conversion.** Totals-block text (running
  mileage, "CUMULATIVE", "TOTAL CONST UNCONST", …) no longer leaks into the
  Description column — which also removes the false differences it was causing
  in the TSMIS-vs-TSN comparison.
- **Empty routes no longer stall the export.** When a route has
  nothing to download, the tool now moves on within about a minute instead of
  waiting out the full multi-minute time limit, so a long run with many empty
  routes finishes much sooner. Empty Intersection reports are recognized
  correctly too.
- **Damaged or locked output files are handled.** A half-written or
  unreadable file left by an interrupted run is re-downloaded rather than
  trusted as "already done", and a file you happen to have open in Excel during
  a resume no longer breaks the run.
- **A failed report can't overwrite a good one.** If a Ramp Summary
  PDF fails to parse (or is a stub one-page file), the tool keeps the good
  workbook you already had instead of replacing it with a blank one.
- **Safer updates.** Before installing, the in-app update now verifies
  the downloaded file with a checksum and installs only the expected files —
  extra protection against a corrupted or tampered download. Sign-in tokens are
  also scrubbed from the saved session and the logs.
- **Spreadsheet safety.** Free-text fields that begin with `=`, `+`,
  `-` or `@` are stored as plain text so they can't run as spreadsheet formulas,
  and comparisons guard against Excel's row/column limits and duplicate sheet
  names instead of failing partway through.

## v0.10.4 — 2026-06-12

- **Intersection reports fixed.** The two new report types now match
  the site exactly: the menu entries are **Intersection Summary** and
  **Intersection Detail** (the site doesn't use a "TSAR:" prefix for them),
  and Summary exports as an **Excel** file like Detail. The environment check
  no longer reports them missing.
- **See both sign-in paths at a glance.** The title bar now shows
  two small indicators: **Saved login** (the session file captured via
  Chrome / Built-in Chromium — what exports use, required for fast mode;
  age in the tooltip) and **Edge one-click** (green once the hands-free
  Windows sign-in has worked this session, amber when it's set up but not
  yet used, grey when never set up).
- **The Dev / testing update channel was removed.** Updates come
  only from full releases on this page. The Update channel switch is gone
  from Settings; nothing else changes.

## v0.10.3 — 2026-06-12

- **Updates install reliably now.** The 0.10.2 update could fail
  halfway on some PCs and leave a confusing half-installed app ("says 0.10.2
  but features are missing") or quietly fall back to the old version. The
  install now prepares the whole new version next to the old one first and
  swaps it in with instant renames — it either fully installs or fully
  doesn't, a failed attempt says so the next time the update is offered, and
  the interface shown is always the one actually installed (no more stale
  screens after an update). The first launch after an update is also more
  patient: instead of a scary error while Windows checks the new files, it
  shows "Still starting…" and finishes by itself.
- **The environment check runs by itself.** After the app starts (or
  you sign in), it quietly verifies sign-in + report access on all six sites
  in the background — several at once when Google Chrome / the Built-in
  Chromium and a saved login are available, one at a time otherwise — and
  the title-bar chip + Settings rows fill in. Turn it off in Settings. The
  Export tab also flags any report type the current site has greyed out.
- **Two new reports: TSAR Intersection Summary & Detail.** Exported
  like the ramp pair (Summary → PDF, Detail → Excel) into their own folders.
  Consolidation/comparison for them comes later.
- **Fast mode no longer trips over managed Edge.** Parallel browsers
  (fast mode and the environment check) now run in the Built-in Chromium /
  Google Chrome; Microsoft Edge keeps the one-click sign-in and is only used
  for parallel work when nothing else is available.

## v0.10.2 — 2026-06-12

- **The new TSMIS address is built in.** The report site moved to
  `tsmis.dot.ca.gov`; this version points there out of the box for all six
  source/environment combinations. If you had entered the new address in
  Settings as a stopgap, that custom entry keeps working — clear the box to
  fall back to the (now identical) built-in default.
- **Check sign-in + report access for every environment.**
  Settings ▸ **Check all environments** opens each of the six sites
  (SSOR/ARS × Prod/Test/Dev) in the background exactly like an export and
  verifies that sign-in completes, the right site loaded, the report form
  can actually pull data, and **all four report types are offered** (the
  site sometimes greys one out). Verdicts land next to each address as they
  finish — green OK, amber "Reports limited" naming the unavailable report
  types, red for sign-in/data/site failures, full detail in the tooltip —
  and a title-bar chip ("Envs 5/6") shows the overall picture; click it to
  jump to the rows. Built for the "signs in fine but can't pull reports"
  situation, so a broken environment is a 2-minute check instead of a
  wasted export run.
- **Screenshots show their address.** The per-browser Preview and
  the Verify-environment screenshot now display the page's web address above
  the image, so which site/environment the browser is really on is readable
  in plain text (sign-in tokens never appear).
- **A Dev / testing update channel.** Settings ▸ Update channel —
  leave it on **Stable releases** (the default; nothing changes for you).
  Pick **Dev / testing builds** only when asked to try a fix: the title-bar
  update button then offers quick prerelease test builds, clearly labeled
  everywhere, and the next stable release returns the install to normal
  automatically.

## v0.10.1 — 2026-06-12

- **The one-click update now works on locked-down PCs.** On machines
  where PowerShell is blocked for standard users (common on managed work
  PCs), the previous updater downloaded the new version and then silently
  failed to install it — the app closed and the download just sat in
  `data\update`. The install step no longer uses PowerShell, cmd, scripts or
  admin rights at all: the downloaded new version installs itself. It also
  fails LOUDLY now — if the install step can't even start, the app stays
  open on the old version and says so instead of closing into nothing.
  **If an update left you stranded before:** install this version manually
  once (download the zip, replace the app's `TSMIS Exporter.exe`,
  `_internal` and `Start Here.txt` — your `data\` and `output\` stay put);
  from then on the green Update button does the whole job.

## v0.10.0 — 2026-06-12

- **Comparisons answer the real question first.** Every comparison
  now leads with a verdict — **“✓ EVERYTHING MATCHES”** in green when the two
  sides are identical (the expected outcome between environments), or
  **“✗ DIFFERENCES FOUND — N differing cells, M one-sided rows”**. It shows
  three ways: a dialog the moment the comparison finishes, the first line of
  the run log, and a big colored banner at the top of the workbook's Summary
  (live formula in the formulas flavor, so it stays current after edits and F9).
- **Change a TSMIS address without waiting for an update.** Settings
  lists the page address for all six source/environment combinations; edit
  one if a site moves and it's used by the very next sign-in, export or
  Verify. Custom addresses are marked; clearing the box restores the
  built-in default.
- **Download the Built-in Chromium from Settings.** The standard
  (smaller) app can now fetch the same unmanaged browser the “with-browser”
  download ships (~170 MB, into the app's data folder — it survives updates)
  and remove it again later. Handy when managed-Edge sign-in misbehaves and
  installing Chrome isn't an option; restart the app after and “Built-in
  Chromium” appears in the Browser dropdown.
- **Compare environments against each other.** The Compare tab now
  also compares the SAME report exported from two different places — SSOR vs
  ARS, prod vs dev/test, or today vs an older run. Pick the report type and
  two export folders (e.g. `2026-06-11 ssor-prod` vs `2026-06-11 ars-prod`);
  the per-route files are read straight from both — **no consolidation step
  needed** — and you get the same trusted discrepancy workbook as the
  TSMIS-vs-TSN comparison, with the environment names as the two sides.
  Works for all four reports: Ramp Detail, Highway Sequence and Highway Log
  compare their Excel exports; **Ramp Summary compares its PDFs** (parsed
  with the same engine the consolidator uses), one row per route. Routes
  missing from one environment are flagged "entire route", and the live
  SELF-CHECK rows prove the numbers in Excel itself.
- **Exports are labeled by environment.** Runs now land in
  `output\<date> <source>-<environment>\` (e.g. `2026-06-11 ssor-prod`), so
  exports from different sites never mix or overwrite — that's what makes
  the environment comparison possible. Older bare-date folders are read as
  ssor-prod everywhere (consolidation included); run-report CSVs carry the
  same tag.
- **See what every browser is doing.** During an export, the
  progress card shows one live status row per browser (current route, phase,
  elapsed) — fast mode shows all of them. Each row has a **Preview** button
  that pops an actual screenshot of that browser's page, so you can see the
  sign-in state, the report being built, and the site's own **SSOR / ARS +
  environment label** with your own eyes.
- **Verify the environment without exporting.** A **Verify** button
  next to the environment dropdowns opens TSMIS in the background exactly
  like an export would (signed in), reads which data source / environment
  the page ACTUALLY loaded, and shows a screenshot with a clear
  matches-your-selection verdict — catch a wrong-environment setup before
  spending hours exporting.
- **A Settings tab.** Reliability knobs (per-route time limits,
  county wait, default fast-mode browser count — raise them when the server
  is slow), debugging tools (verbose logging, DevTools, a one-click
  **support bundle** zip with logs + run reports and **never your login**),
  quick folder shortcuts, forget-saved-login, and **Delete all reports** —
  one button clears every generated file for a fresh start after showing
  exactly what will be removed; logs, login and settings always survive.

## v0.9.0 — 2026-06-12

- **Comparison: a fast values copy.** The Compare tab now offers two
  outputs — tick one or both. The **values workbook** holds plain computed
  results: it opens instantly with everything already filled in (no F9, no
  manual-calculation mode, about a third the size) and keeps all the
  navigation links, colors, the Spot Check sheet and the live self-checks.
  The **live-formulas workbook** stays the fully auditable version where
  every cell recalculates. With both ticked, the values copy is saved next
  to the other as "… (values).xlsx". Both are built from the same comparison
  pass, so they can never disagree.
- **Comparison: missing routes front and center + self-checks.** The
  TSMIS-vs-TSN workbook gains two new sheets — **Only in TSMIS** and **Only
  in TSN** — collecting every one-sided row in one place instead of leaving
  them scattered through the 50k-row Comparison sheet. Routes one system
  lacks entirely are flagged **"entire route"** and tinted, so missing-route
  coverage is impossible to overlook (filter the "Missing from …" column to
  separate whole-route gaps from single locations). The Summary also gains a
  **SELF-CHECK section**: each headline number is recomputed a second,
  independent way and shows OK/CHECK after you press F9 — proof that every
  formula still points at the right rows.
- **Comparison: built for skeptics.** Don't trust a red cell? The
  row numbers in the TSMIS Row / TSN Row columns are now **clickable** —
  they jump to the data sheet and **select the whole source row** so it
  stands out until you click elsewhere, and every data-sheet row links back
  to its Comparison row the same way. A new **Spot Check** sheet audits any
  single location end to end: type a row number (or find one by route +
  location) and every field shows the raw stored values from both systems
  next to an **independently recomputed verdict** — calculated straight from
  the data sheets, never reading the Comparison's answer — with an Agree?
  column that flags any disagreement. One-sided rows announce themselves on
  every field line (not just the status cell), difference cells are labeled
  **TSMIS first, TSN second**, and consolidated workbooks show a bold
  press-F9 reminder.
- **The app updates itself.** When a new version is published here, a
  green **Update to vX.Y.Z** button appears in the app's title bar: one click
  downloads it (picking the right variant automatically), then **Restart to
  update** swaps it in and reopens the app — reports, login and settings stay
  exactly where they are, and a failed swap rolls back to the old version.
  The version chip next to the app name re-checks on demand. PCs where the
  app folder is read-only get a button that opens this download page instead.
  (In-app updates also skip the zip "Unblock" problem entirely.)

## v0.8.2 — 2026-06-11

- **Comparison: single-side rows now show their data.** Rows that
  exist only in TSMIS (yellow) or only in TSN (blue) used to have blank
  field cells; they now display that system's own values, so what's missing
  from the other system is readable at a glance.

## v0.8.1 — 2026-06-11

- **Fix: the downloaded app now starts without unblocking the zip.**
  Extracting the release zip without right-click → Unblock tags every file
  as "from the internet", and Windows then refuses to load parts of the new
  interface — v0.8.0 died on launch with "Failed to resolve
  Python.Runtime…". The app now removes that flag from its own files at
  startup, so a plain download-extract-run works. (Unblocking the zip first
  is still good practice for SmartScreen.)

## v0.8.0 — 2026-06-11

- **TSN Highway Log + comparison.** The Consolidate tab gains **TSN
  Highway Log**: drop TSN district PDFs into `input\tsn_highway_log` and it
  converts them into TSMIS-format per-route Excel files plus one combined
  workbook. A new **Compare tab** then builds a TSMIS-vs-TSN discrepancy
  workbook from two per-route Highway Logs **or two consolidated ones (all
  routes)** — matching values shown plainly, differences highlighted in red,
  with live Excel formulas throughout (edit a value and the report
  recalculates). Consolidated comparisons add a **Routes sheet** (which
  routes each system covers, what's missing where, per-route diff counts)
  and open in **manual calculation** so the big workbook appears instantly —
  press **F9** once to calculate, then save.
- **A brand-new interface.** The window was rebuilt from scratch:
  a cleaner two-column layout (settings on the left, live progress + activity
  log on the right), per-route progress with running counts, clearer sign-in
  status, a searchable route picker, and a **System / Light / Dark theme
  toggle**. Most importantly it now **fits any screen** — on small or
  low-resolution displays the layout stacks and scrolls instead of cutting
  off the bottom buttons. (Under the hood the UI is rendered by Edge
  WebView2, which is part of Windows 10/11 — nothing extra to install; all
  export logic is unchanged.)
- **Chrome sign-in no longer nags about local network access.**
  Saving a login with Google Chrome used to require clicking "Allow" on the
  "access devices on your local network?" prompt every single time — and
  missing it meant the session silently didn't save. The sign-in windows now
  pre-grant that permission, same as the exports always have.

## v0.7.6 — 2026-06-11

- **The log now tells the whole story.** Every run writes a detailed
  trail to `data\logs\tsmis.log`: which build/PC produced it, every sign-in
  step, which browser was picked and why a fallback happened, what was clicked
  in the app, each route's outcome with timing and file size, and a full
  traceback for any crash (even ones the window can't show). Errors name the
  specific step that failed — so one log upload answers what used to take a
  back-and-forth.

## v0.7.5 — 2026-06-11

- **Sign-in works on the new TSMIS site.** Field diagnostics finally
  showed the sign-in was SUCCEEDING — and the tool's own post-sign-in
  "right data source?" check was then reloading the page, which destroys the
  app's memory-only session and strands the browser at the portal sign-in
  page. That check misread the app's config (it's not a `window` property)
  so it reloaded every time. Fixed: the config is read correctly, a reload
  happens only on a real env/src mismatch and is followed by a fresh sign-in
  pass, the IdP hop is driven directly via the portal's own SAML URL, and the
  log breadcrumbs every step of each sign-in attempt.
- **Pick the data source and environment.** Two new header dropdowns choose
  **SSOR or ARS** and **Prod / Test / Dev** (defaults: SSOR + Prod) — the tool
  now drives the new TSMIS site, one page for every combination. Console flow:
  set `TSMIS_SRC` / `TSMIS_ENV`.
- **Each day's exports get their own folder.** Files now land in
  `output\<YYYY-MM-DD>\<report>\`, so tomorrow's run starts fresh instead of
  skipping over today's files. The Consolidate tab gained an **Export day**
  picker (newest first, newest by default; console prompts, Enter = newest),
  and the combined workbook is saved in that day's `consolidated\` folder.
  Exports made with older versions are still found when no dated folders exist.
- **Fast mode is greyed out without a saved login**, with an explanation:
  automatic Edge sign-in runs one browser at a time (the sign-in profile can't
  be shared), so parallel runs need a saved session (e.g. sign in with Chrome).
- **Hands-free sign-in on managed Caltrans PCs** (since v0.6): after one normal
  Edge sign-in, login and exports sign themselves in automatically — no
  password, no window. Chrome stays on the manual sign-in path.
- First run: if Windows warns about an unknown publisher, choose
  "More info" → "Run anyway" (in-house unsigned tool). If downloaded as a zip,
  right-click → Properties → Unblock before extracting.

## v0.7.4 — 2026-06-11

- **Sign-in works on the new TSMIS site.** The portal showed its "Caltrans Azure
  AD" button before the button's click handler was wired up, so the tool's early
  click landed dead. It now keeps clicking each second until the page actually
  moves, and after several dead clicks drives the sign-in hop directly via the
  portal's own SAML URL. The Edge sign-in window also pre-grants the
  local-network permission.
- **Fits small screens.** The window caps its height to the screen and can be
  shrunk — the log pane absorbs the difference instead of the bottom buttons
  being cut off.

## v0.7.3 — 2026-06-11

- **Sign-in detection hardened, plus diagnostics.** Stronger signed-in detection
  (several post-sign-in signals, robust visibility checks) and deep sign-in
  diagnostics: the log records the app version and every sign-in attempt's
  outcome, and a failed sign-in saves a screenshot + page snapshot under
  `data\failures\` so problems can be pinpointed from one run.

## v0.7.2 — 2026-06-11

- **Sign-in works on the new TSMIS site.** The new app never shows a signed-out
  page — it redirects through the portal OAuth flow on every load and keeps its
  token in page memory only. The tool now rides that flow: it polls for the app's
  real post-sign-in state and clicks "Caltrans Azure AD" the moment the portal
  renders it, so saved Chrome sessions and the hands-free Edge sign-in work again
  (0.7.0/0.7.1 raced the redirect or watched for the wrong signals).

## v0.7.1 — 2026-06-11

- **Sign-in fix for the new report page.** The new page shows its own "Sign In
  with ArcGIS" button instead of redirecting, and renders the report form even
  when signed out — both broke automatic sign-in (Edge and Chrome) in 0.7.0. The
  tool now clicks the full chain (app button → portal page → "Caltrans Azure AD",
  popup-tolerant) and detects sign-in from the app's own state.

## v0.7.0 — 2026-06-11

- **Pick the data source and environment.** Two new header dropdowns choose
  **SSOR or ARS** and **Prod / Test / Dev** (defaults: SSOR + Prod) — the tool
  now drives the new TSMIS site, one page for every combination. Console flow:
  set `TSMIS_SRC` / `TSMIS_ENV`.

## v0.6.1 — 2026-06-10

- **Hands-free sign-in, refined.** After one normal Edge sign-in (which primes
  the app's own Edge profile), the tool signs in automatically — no password, no
  window — and exports can even start with **no saved login at all**: the export
  reopens that Edge profile, clicks "Caltrans Azure AD" itself, and Windows signs
  it in. Edge only (Chrome stays on the manual path); automatic sign-in runs one
  browser at a time, so save a login to use fast mode.

## v0.6.0 — 2026-06-10

- **Hands-free sign-in on managed Caltrans PCs.** The tool signs in
  **automatically** with Microsoft Edge and your Windows account — no password,
  no browser window. Each headless browser clicks "Caltrans Azure AD" itself and
  Windows signs it in (Edge only — Chrome stays on the manual sign-in path). The
  local-network permission the TSMIS site needs is pre-granted in every automated
  browser.

## v0.5.1 — 2026-06-10

- **Managed-Edge sign-in hardened.** Recovers the session even when org-managed
  Edge relaunches itself into the work profile mid-SSO (live capture, then CDP
  re-attach, then on-disk profile recapture), with a Google Chrome fallback if
  nothing was captured.

## v0.5.0 — 2026-06-10

- **Managed-Edge sign-in fixed.** Sign-in opens Edge with a durable app-owned
  profile and recovers the session even when org-managed Edge relaunches into the
  work profile mid-SSO, with a Google Chrome fallback if nothing was captured.

## v0.4.1 — 2026-06-05

- **Edge/Chrome login fixed.** Signing in no longer cancels itself the moment
  your password/MFA goes through — the session saves reliably.
- **A broken route fails fast.** If TSMIS itself errors on a route, it's recorded
  as Failed in seconds with the site's message instead of hanging for minutes.
- **Friendlier to IT / Defender.** Proper version details, an icon, and a
  no-admin manifest; the download is stripped of third-party documentation that
  could trip data-loss-prevention scanners.

## v0.4.0 — 2026-06-05

- **New report: Highway Log.** Bulk-export the Highway Log for every route
  (XLSX), plus a matching consolidator to combine them.
- **Export several report types at once.** Tick any combination (or all) and they
  run back-to-back in one go.
- **Cancel actually cancels now.** It stops the report it's currently working on
  right away instead of waiting for that route to finish first.
- **Fast mode is sturdier.** If one browser hits a snag the others keep going,
  and any routes that get dropped are retried rather than silently skipped.

## v0.3.0 — 2026-06-05

- **Much smaller — ~587 MB → ~148 MB.** No longer bundles Chromium; it uses the
  **Microsoft Edge (or Chrome) already installed** on the machine. This also
  fixes the SharePoint/DLP "blocked file" problem from the old bundled doc files.
- **Browser picker + startup checks in the header.** Choose Edge or Chrome, with
  readiness dots for the browser, output folder, and report tools.
- **Choose which routes to export.** Leave the Routes box blank for all, or type
  a few (e.g. `5, 99, 101`).
- **Automatic retry.** Routes that fail get one more patient, one-at-a-time
  attempt at the end of the run.
- **Login fixes.** Confirms you actually signed in before saving, and closing the
  sign-in window no longer leaves the app stuck on "Waiting…".

## v0.2.0 — 2026-06-04

- **Experimental fast mode.** Run several headless browsers at once to export
  routes in parallel (default 3, up to 30; each uses ~0.5 GB RAM).
- **Live elapsed timer** beneath the progress bar during a run.
- **Clearer run summary.** Adds an "already had" count for routes saved on a
  previous run, so the numbers reconcile to the full route count.

## v0.1.0-preview — 2026-06-04

- **Initial preview build.** First portable Windows release — no install, no
  Python required. Sign in with your Caltrans `@dot.ca.gov` account + MFA, export
  a report for every route, consolidate the per-route files into one workbook, and
  save a per-route outcome CSV. Bundles its own Chromium. Preview build, pending
  live verification against TSMIS.
