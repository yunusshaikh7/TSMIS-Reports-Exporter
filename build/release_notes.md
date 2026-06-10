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

- **Managed-Edge sign-in fixed.** Sign-in now opens Edge with a durable
  app-owned profile and recovers the session even when org-managed Edge
  relaunches itself into the work profile mid-SSO (live capture, then CDP
  re-attach, then on-disk profile recapture) — with a Google Chrome fallback if
  nothing was captured.
- **New "Built-in Chromium" browser option.** When a Playwright-managed
  Chromium is present (the with-browser zip, or downloaded by the `.bat`
  setup), it becomes the default for sign-in and exports — it's unmanaged, so
  org browser policy can't interfere — and Edge/Chrome remain selectable in the
  header dropdown.
- First run: if Windows warns about an unknown publisher, choose
  "More info" → "Run anyway" (in-house unsigned tool). If downloaded as a zip,
  right-click → Properties → Unblock before extracting.
