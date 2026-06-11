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

- **A brand-new interface (0.8.0).** The window was rebuilt from scratch:
  a cleaner two-column layout (settings on the left, live progress + activity
  log on the right), per-route progress with running counts, clearer sign-in
  status, a searchable route picker, and dark mode that follows Windows.
  Most importantly it now **fits any screen** — on small or low-resolution
  displays the layout stacks and scrolls instead of cutting off the bottom
  buttons. (Under the hood the UI is rendered by Edge WebView2, which is part
  of Windows 10/11 — nothing extra to install; all export logic is unchanged.)
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
- **Fits small screens.** The window now caps its height to the screen and can
  be shrunk — the log pane absorbs the difference instead of the bottom
  buttons being cut off.
- **Hands-free sign-in on managed Caltrans PCs** (since v0.6): after one normal
  Edge sign-in, login and exports sign themselves in automatically — no
  password, no window. Chrome stays on the manual sign-in path.
- First run: if Windows warns about an unknown publisher, choose
  "More info" → "Run anyway" (in-house unsigned tool). If downloaded as a zip,
  right-click → Properties → Unblock before extracting.
