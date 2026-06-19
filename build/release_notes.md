Portable Windows desktop app that bulk-exports Caltrans TSMIS reports for every
California state route — sign in once, tick the reports you want, done (see
`Start Here.txt` inside the zip).

## Pick your download

| Download | Best for | Browser it uses |
|---|---|---|
| `…-win64.zip` | Most users — smallest download | The Microsoft Edge / Google Chrome already installed on the PC |
| `…-win64-with-browser.zip` | Managed PCs where Edge sign-in misbehaves and Chrome isn't installed | Ships its own **Built-in Chromium** and uses it by default; Edge and Chrome stay in the header dropdown |
| `…-batch-source.zip` | Developers / console fallback | Requires Python 3.11 — `1. setup (one time).bat` installs the libraries **and downloads Chromium** |

Both app zips: unzip anywhere writable and double-click `TSMIS Exporter.exe`.

## Highlights

- **A "for IT" page now ships in the app folder (0.14.3).** Every download now
  includes an **`IT-README.txt`** next to `Start Here.txt` — a plain-language page
  for whoever in IT or security reviews the tool: what it connects to, what it
  reads and writes, how the saved login is handled, and why a portable,
  self-updating, unsigned in-house app is safe to run. It rides app updates, so
  the page stays current from this version on.

- **Consolidate tab cleanup (0.14.2).** The three Highway Log consolidations now
  have clear, parallel names — **TSMIS Highway Log (Excel)**, **TSMIS Highway Log
  (PDF)**, **TSN Highway Log (PDF)** — so the plain "Highway Log" can't be confused
  for the others. The **TSMIS Highway Log (PDF)** consolidation now reads the app's
  own "Highway Log (PDF)" export straight from the output folder (with the Export-day
  picker, like the Excel one) instead of a redundant drop folder — you no longer copy
  the app's own exports into an input folder. The "Export day" picker is now hidden
  for the one report it doesn't apply to (TSN, whose district PDFs come from outside
  the app).
- **A few UI labels now match what actually happens (0.14.2).** The environment
  check no longer wrongly flags **Highway Log (PDF)** as unavailable on every site
  (it shares the "Highway Log" dropdown option, so it now follows that report's
  result); the Export Everything description says it writes to your chosen
  destination folder (not "dated run folders"); the auto-consolidate note lists every
  report that has no consolidator; and **Delete all reports** now also clears the
  Highway-Log-PDF outputs and the Export Everything store, so a "fresh start" really
  is one.

- **An accurate Highway Log, sourced from the PDF (0.14.0).** The site's Highway
  Log **Excel** export is buggy — it drops rows and whole roadbed-geometry
  columns, expands the report's "same as the other roadbed" `+` markers into
  numbers, and mis-attaches descriptions. A new consolidation parses the Highway
  Log **PDF** export instead (drop the per-route PDFs into
  `input\tsmis_highway_log_pdf`), producing the same 31-column workbook **without**
  those export errors — verified row-for-row against all 252 routes.
- **Highway Log columns are correctly labeled (0.14.0).** The vendor Excel export
  mislabeled most Highway Log columns (e.g. "N/A" is really **Non-Add Mileage**;
  the cryptic roadbed codes are surface type, shoulder widths, lane counts, …; it
  even reused "RB SH" for two different columns). Every Highway Log workbook now
  uses the **report's own legend** labels, with the old label kept in `[brackets]`,
  a hover tooltip on every column, and a **Legend** sheet explaining each one. This
  is a relabel only — the data and comparison results are unchanged.
- **Highway Log comparisons in one place (0.14.1).** The Compare tab now has a
  **Highway Log** sub-tab gathering every Highway Log comparison — TSMIS vs TSN, the
  two PDF-sourced comparisons, and across environments — beside a
  **Cross-environment** sub-tab for the plain report comparisons, instead of the old
  three-way split. (v0.14.0 briefly made this a separate top-level tab; v0.14.1
  moves it to a sub-tab inside Compare.)
- **Divided-highway rows now line up correctly (0.14.0).** On a divided highway
  each segment has two rows (one per roadbed). TSMIS marks the roadbed in the
  location (`R021.466R`/`…L`); the TSN log marks it a different way. The comparison
  used to treat these as *different* locations, so the same physical roadbed row
  showed up as **"only in TSMIS" + "only in TSN"** instead of being compared —
  hiding thousands of genuine differences. It now recognizes the roadbed on both
  sides and pairs them, surfacing those differences (audited against the source
  PDFs — every pairing is the correct roadbed, none crossed).
- **"Same as the other roadbed" markers are handled (0.14.0).** A roadbed column
  printed as `+`/`++` means "this roadbed's value is on the paired row" — a
  pointer, not a value. Comparisons now treat it as such (it is **never** counted
  as a difference, on either source), and a comparison cell that resolved a `+`
  shows what it points to in a hover note.
- **Highway Log can now be exported as a PDF (0.13.1).** A new **Highway Log
  (PDF)** report exports each route's Highway Log as a print-formatted PDF — the
  same layout the site's Print button produces (cover page + every page) — into
  `output/…/highway_log_pdf/`, alongside the existing Excel export. Tick it on the
  Export tab like any other report.

- **Comparisons match repeated locations correctly (0.13.1).** When a TSMIS-vs-TSN
  or cross-environment comparison had two rows at the **same location** (e.g. two
  `001 R000.129` segments), it used to pair them in the order they appear —
  first-with-first, second-with-second — so a row that actually matched the other
  side's *second* listing was wrongly flagged as different. It now pairs repeated
  locations by **which rows are most alike** (the most fields matching), not by
  order. The row's identity is unchanged (same Route + location); only the pairing
  of repeats is smarter. This can only *remove* false differences, never add one —
  on a full Highway Log comparison it cleared ~3,600 phantom differing cells.

- **A clearer window, and it tells you what's happening (0.13.0).** The right
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
- **Revert to the previous version (0.13.0).** Settings now has a **Revert to
  previous version** button: if an update ever causes trouble, one click
  reinstalls the release just before this one, through the exact same verified
  download-and-swap the normal update uses (your reports, login and settings stay
  put). It only appears on installs the app can update itself.
- **Two separate "check environments automatically" switches (0.13.0).** The old
  single setting is now two: **after sign-in** (on by default) and **after the
  app starts** (off by default) — so the background environment check can run when
  you sign in without also running every single launch.
- **Compare tab is split into sub-tabs (0.13.0).** The two comparison kinds —
  **Cross-environment** and **TSMIS vs TSN** — are now on their own sub-tabs
  (cross-environment shown first), instead of sharing one long list.
- **Export Everything labels every file by environment (0.13.0).** Files in the
  always-current store are now named with their source/environment up front
  (e.g. `ssor-prod tsar_ramp_detail_route_5.xlsx`, and the combined workbook the
  same way), so a file copied out of the folder still says which environment it
  came from. The Everything tab also **colour-codes** report types and
  environments the last environment check flagged — amber for "may be limited",
  red for "would fail" — and now greys out during an environment check like the
  other tabs.

- **Export Everything — one always-current set of reports (0.12.0).** A new
  **Everything** tab exports the report types you tick across the environments you
  tick into a single folder you choose (default **All Reports (current)**). Re-run
  it any time to refresh: it overwrites that folder in place, so it always holds
  the latest of every report. A **Saved reports** list shows how old each report
  is and flags any that are lagging behind the rest, with a one-click **Refresh**
  for just that report — plus pause/resume and resume-after-restart for the long
  full runs.
- **Pause / Resume a running export (0.12.0).** A new **Pause** button holds the
  run between routes and **Resume** picks it back up — separate from Skip (one
  route) and Cancel (stop the run). Works in fast mode too.
- **Auto-consolidate when an export finishes (0.12.0).** An optional checkbox
  builds the combined workbook automatically right after the export, so the
  Consolidate step happens for you.
- **Self-describing filenames (0.12.0).** Consolidated and comparison files now
  carry the date + source/environment in the filename, so a file copied out of
  its folder still says exactly which run it came from.
- **Compare tab lists only relevant folders (0.12.0).** The cross-environment
  folder pickers now show only export runs that actually contain the report type
  you picked, instead of every run folder.
- **Buttons never cut off (0.12.0).** The Start / Pause / Cancel bar stays pinned
  and visible while the report list scrolls, and the tab row no longer crowds.

- **Flawless TSN Highway Log conversion (0.11.1).** The TSN district-PDF → Excel
  converter now transcribes feature descriptions perfectly across all 12
  districts — totals-block footer text and page furniture can no longer leak into
  a segment's Description. This removes ~1,000 false-positive "differences" from
  the TSMIS-vs-TSN Highway Log comparison (what remains is all genuine data
  differences). Real descriptions that merely contain words like "UNCONST" or
  "TOTAL" are now kept correctly.
- **Ramp Summary audit cell explains itself (0.11.1).** When a route's parsed
  section sub-totals don't add up to its stated total, the consolidated workbook's
  Audit cell now names the section that's short (e.g. "⚠ Source ≠ total: Ramp
  Types") instead of a bare red result — making clear it's a quirk in the source
  PDF's own numbers on a few dense routes, not a tool error.

- **Comparisons are far more accurate (0.11.0).** Comparing the same report
  across two environments used to flag large numbers of "differences" that were
  really just rows shifting position — one missing point near the top made
  everything below it look changed. Comparisons now line rows up by their
  **postmile** (a row's real identity) instead of the coarser county, so a
  Highway Sequence comparison that used to show ~15,800 differing cells now
  shows ~5,000 genuine ones; only real differences remain.
- **A comparison never claims "everything matches" when it couldn't read a
  file (0.11.0).** If an input file is unreadable it's no longer silently
  skipped: the result says **"Comparison incomplete"** and the workbook lists
  exactly what was left out — instead of a misleading green "everything
  matches" that quietly ignored the missing data.
- **Cleaner TSN Highway Log conversion (0.11.0).** Totals-block text (running
  mileage, "CUMULATIVE", "TOTAL CONST UNCONST", …) no longer leaks into the
  Description column — which also removes the false differences it was causing
  in the TSMIS-vs-TSN comparison.
- **Empty routes no longer stall the export (0.11.0).** When a route has
  nothing to download, the tool now moves on within about a minute instead of
  waiting out the full multi-minute time limit, so a long run with many empty
  routes finishes much sooner. Empty Intersection reports are recognized
  correctly too.
- **Damaged or locked output files are handled (0.11.0).** A half-written or
  unreadable file left by an interrupted run is re-downloaded rather than
  trusted as "already done", and a file you happen to have open in Excel during
  a resume no longer breaks the run.
- **A failed report can't overwrite a good one (0.11.0).** If a Ramp Summary
  PDF fails to parse (or is a stub one-page file), the tool keeps the good
  workbook you already had instead of replacing it with a blank one.
- **Safer updates (0.11.0).** Before installing, the in-app update now verifies
  the downloaded file with a checksum and installs only the expected files —
  extra protection against a corrupted or tampered download. Sign-in tokens are
  also scrubbed from the saved session and the logs.
- **Spreadsheet safety (0.11.0).** Free-text fields that begin with `=`, `+`,
  `-` or `@` are stored as plain text so they can't run as spreadsheet formulas,
  and comparisons guard against Excel's row/column limits and duplicate sheet
  names instead of failing partway through.

- **Intersection reports fixed (0.10.4).** The two new report types now match
  the site exactly: the menu entries are **Intersection Summary** and
  **Intersection Detail** (the site doesn't use a "TSAR:" prefix for them),
  and Summary exports as an **Excel** file like Detail. The environment check
  no longer reports them missing.
- **See both sign-in paths at a glance (0.10.4).** The title bar now shows
  two small indicators: **Saved login** (the session file captured via
  Chrome / Built-in Chromium — what exports use, required for fast mode;
  age in the tooltip) and **Edge one-click** (green once the hands-free
  Windows sign-in has worked this session, amber when it's set up but not
  yet used, grey when never set up).
- **The Dev / testing update channel was removed (0.10.4).** Updates come
  only from full releases on this page. The Update channel switch is gone
  from Settings; nothing else changes.
- **Updates install reliably now (0.10.3).** The 0.10.2 update could fail
  halfway on some PCs and leave a confusing half-installed app ("says 0.10.2
  but features are missing") or quietly fall back to the old version. The
  install now prepares the whole new version next to the old one first and
  swaps it in with instant renames — it either fully installs or fully
  doesn't, a failed attempt says so the next time the update is offered, and
  the interface shown is always the one actually installed (no more stale
  screens after an update). The first launch after an update is also more
  patient: instead of a scary error while Windows checks the new files, it
  shows "Still starting…" and finishes by itself.
- **The environment check runs by itself (0.10.3).** After the app starts (or
  you sign in), it quietly verifies sign-in + report access on all six sites
  in the background — several at once when Google Chrome / the Built-in
  Chromium and a saved login are available, one at a time otherwise — and
  the title-bar chip + Settings rows fill in. Turn it off in Settings. The
  Export tab also flags any report type the current site has greyed out.
- **Two new reports: TSAR Intersection Summary & Detail (0.10.3).** Exported
  like the ramp pair (Summary → PDF, Detail → Excel) into their own folders.
  Consolidation/comparison for them comes later.
- **Fast mode no longer trips over managed Edge (0.10.3).** Parallel browsers
  (fast mode and the environment check) now run in the Built-in Chromium /
  Google Chrome; Microsoft Edge keeps the one-click sign-in and is only used
  for parallel work when nothing else is available.
- **The new TSMIS address is built in (0.10.2).** The report site moved to
  `tsmis.dot.ca.gov`; this version points there out of the box for all six
  source/environment combinations. If you had entered the new address in
  Settings as a stopgap, that custom entry keeps working — clear the box to
  fall back to the (now identical) built-in default.
- **Check sign-in + report access for every environment (0.10.2).**
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
- **Screenshots show their address (0.10.2).** The per-browser Preview and
  the Verify-environment screenshot now display the page's web address above
  the image, so which site/environment the browser is really on is readable
  in plain text (sign-in tokens never appear).
- **A Dev / testing update channel (0.10.2).** Settings ▸ Update channel —
  leave it on **Stable releases** (the default; nothing changes for you).
  Pick **Dev / testing builds** only when asked to try a fix: the title-bar
  update button then offers quick prerelease test builds, clearly labeled
  everywhere, and the next stable release returns the install to normal
  automatically.
- **The one-click update now works on locked-down PCs (0.10.1).** On machines
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
- **Comparisons answer the real question first (0.10.0).** Every comparison
  now leads with a verdict — **“✓ EVERYTHING MATCHES”** in green when the two
  sides are identical (the expected outcome between environments), or
  **“✗ DIFFERENCES FOUND — N differing cells, M one-sided rows”**. It shows
  three ways: a dialog the moment the comparison finishes, the first line of
  the run log, and a big colored banner at the top of the workbook's Summary
  (live formula in the formulas flavor, so it stays current after edits and F9).
- **Change a TSMIS address without waiting for an update (0.10.0).** Settings
  lists the page address for all six source/environment combinations; edit
  one if a site moves and it's used by the very next sign-in, export or
  Verify. Custom addresses are marked; clearing the box restores the
  built-in default.
- **Download the Built-in Chromium from Settings (0.10.0).** The standard
  (smaller) app can now fetch the same unmanaged browser the “with-browser”
  download ships (~170 MB, into the app's data folder — it survives updates)
  and remove it again later. Handy when managed-Edge sign-in misbehaves and
  installing Chrome isn't an option; restart the app after and “Built-in
  Chromium” appears in the Browser dropdown.
- **Compare environments against each other (0.10.0).** The Compare tab now
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
- **Exports are labeled by environment (0.10.0).** Runs now land in
  `output\<date> <source>-<environment>\` (e.g. `2026-06-11 ssor-prod`), so
  exports from different sites never mix or overwrite — that's what makes
  the environment comparison possible. Older bare-date folders are read as
  ssor-prod everywhere (consolidation included); run-report CSVs carry the
  same tag.
- **See what every browser is doing (0.10.0).** During an export, the
  progress card shows one live status row per browser (current route, phase,
  elapsed) — fast mode shows all of them. Each row has a **Preview** button
  that pops an actual screenshot of that browser's page, so you can see the
  sign-in state, the report being built, and the site's own **SSOR / ARS +
  environment label** with your own eyes.
- **Verify the environment without exporting (0.10.0).** A **Verify** button
  next to the environment dropdowns opens TSMIS in the background exactly
  like an export would (signed in), reads which data source / environment
  the page ACTUALLY loaded, and shows a screenshot with a clear
  matches-your-selection verdict — catch a wrong-environment setup before
  spending hours exporting.
- **A Settings tab (0.10.0).** Reliability knobs (per-route time limits,
  county wait, default fast-mode browser count — raise them when the server
  is slow), debugging tools (verbose logging, DevTools, a one-click
  **support bundle** zip with logs + run reports and **never your login**),
  quick folder shortcuts, forget-saved-login, and **Delete all reports** —
  one button clears every generated file for a fresh start after showing
  exactly what will be removed; logs, login and settings always survive.
- **Comparison: a fast values copy (0.9.0).** The Compare tab now offers two
  outputs — tick one or both. The **values workbook** holds plain computed
  results: it opens instantly with everything already filled in (no F9, no
  manual-calculation mode, about a third the size) and keeps all the
  navigation links, colors, the Spot Check sheet and the live self-checks.
  The **live-formulas workbook** stays the fully auditable version where
  every cell recalculates. With both ticked, the values copy is saved next
  to the other as "… (values).xlsx". Both are built from the same comparison
  pass, so they can never disagree.
- **Comparison: missing routes front and center + self-checks (0.9.0).** The
  TSMIS-vs-TSN workbook gains two new sheets — **Only in TSMIS** and **Only
  in TSN** — collecting every one-sided row in one place instead of leaving
  them scattered through the 50k-row Comparison sheet. Routes one system
  lacks entirely are flagged **"entire route"** and tinted, so missing-route
  coverage is impossible to overlook (filter the "Missing from …" column to
  separate whole-route gaps from single locations). The Summary also gains a
  **SELF-CHECK section**: each headline number is recomputed a second,
  independent way and shows OK/CHECK after you press F9 — proof that every
  formula still points at the right rows.
- **Comparison: built for skeptics (0.9.0).** Don't trust a red cell? The
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
- **The app updates itself (0.9.0).** When a new version is published here, a
  green **Update to vX.Y.Z** button appears in the app's title bar: one click
  downloads it (picking the right variant automatically), then **Restart to
  update** swaps it in and reopens the app — reports, login and settings stay
  exactly where they are, and a failed swap rolls back to the old version.
  The version chip next to the app name re-checks on demand. PCs where the
  app folder is read-only get a button that opens this download page instead.
  (In-app updates also skip the zip "Unblock" problem entirely.)
- **Comparison: single-side rows now show their data (0.8.2).** Rows that
  exist only in TSMIS (yellow) or only in TSN (blue) used to have blank
  field cells; they now display that system's own values, so what's missing
  from the other system is readable at a glance.
- **Fix: the downloaded app now starts without unblocking the zip (0.8.1).**
  Extracting the release zip without right-click → Unblock tags every file
  as "from the internet", and Windows then refuses to load parts of the new
  interface — v0.8.0 died on launch with "Failed to resolve
  Python.Runtime…". The app now removes that flag from its own files at
  startup, so a plain download-extract-run works. (Unblocking the zip first
  is still good practice for SmartScreen.)
- **TSN Highway Log + comparison (0.8.0).** The Consolidate tab gains **TSN
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
- **A brand-new interface (0.8.0).** The window was rebuilt from scratch:
  a cleaner two-column layout (settings on the left, live progress + activity
  log on the right), per-route progress with running counts, clearer sign-in
  status, a searchable route picker, and a **System / Light / Dark theme
  toggle**. Most importantly it now **fits any screen** — on small or
  low-resolution displays the layout stacks and scrolls instead of cutting
  off the bottom buttons. (Under the hood the UI is rendered by Edge
  WebView2, which is part of Windows 10/11 — nothing extra to install; all
  export logic is unchanged.)
- **Chrome sign-in no longer nags about local network access (0.8.0).**
  Saving a login with Google Chrome used to require clicking "Allow" on the
  "access devices on your local network?" prompt every single time — and
  missing it meant the session silently didn't save. The sign-in windows now
  pre-grant that permission, same as the exports always have.
- **The log now tells the whole story (0.7.6).** Every run writes a detailed
  trail to `data\logs\tsmis.log`: which build/PC produced it, every sign-in
  step, which browser was picked and why a fallback happened, what was clicked
  in the app, each route's outcome with timing and file size, and a full
  traceback for any crash (even ones the window can't show). Errors name the
  specific step that failed — so one log upload answers what used to take a
  back-and-forth.
- **Sign-in works on the new TSMIS site (0.7.5).** Field diagnostics finally
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
