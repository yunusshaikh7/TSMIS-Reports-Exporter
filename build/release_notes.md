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

- **Hands-free sign-in on managed Caltrans PCs.** After one normal Edge
  sign-in (which primes the app's own Edge profile), the tool signs in
  **automatically** — no password, no browser window. The Log in button
  completes silently, and exports can even start with **no saved login at
  all**: the export reopens that Edge profile, clicks "Caltrans Azure AD"
  itself, and Windows signs it in (Edge only — Chrome stays on the manual
  sign-in path; automatic sign-in runs one browser at a time, so save a login
  to use fast mode). The local-network permission the TSMIS site needs is
  pre-granted in every automated browser.
- **Managed-Edge sign-in fixed.** Sign-in opens Edge with a durable app-owned
  profile and recovers the session even when org-managed Edge relaunches itself
  into the work profile mid-SSO (live capture, then CDP re-attach, then on-disk
  profile recapture) — with a Google Chrome fallback if nothing was captured.
- **Captured sign-ins are now verified before saving.** If Edge signed you in
  through the Windows work profile (device-bound, so the session can't be
  reused by the export engine), the tool detects it, says so, and falls back to
  another browser instead of saving a login that won't export.
- **The Browser dropdown now applies to sign-in too** — pick Google Chrome and
  the login window opens in Chrome.
- **New "Built-in Chromium" browser option.** When a Playwright-managed
  Chromium is present (the with-browser zip, or downloaded by the `.bat`
  setup), it becomes the default for sign-in and exports — it's unmanaged, so
  org browser policy can't interfere — and Edge/Chrome remain selectable in the
  header dropdown. The standard `win64` build always defaults to Edge.
- First run: if Windows warns about an unknown publisher, choose
  "More info" → "Run anyway" (in-house unsigned tool). If downloaded as a zip,
  right-click → Properties → Unblock before extracting.
