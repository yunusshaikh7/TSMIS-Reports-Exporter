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
