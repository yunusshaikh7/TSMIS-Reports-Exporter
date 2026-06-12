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
