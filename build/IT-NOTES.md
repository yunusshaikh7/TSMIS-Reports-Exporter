# TSMIS Exporter — IT / Security review notes

A plain-language reference for IT, endpoint-security, and DLP reviewers: what the
app talks to, what it reads and writes, the few low-level browser flags it sets
and why, and the current code-signing status. It is intentionally boring: the app
bulk-downloads Caltrans TSMIS reports with a headless Chromium-based browser and
saves them as PDF/XLSX next to the program.

Audience: the person approving the unsigned `.exe` on a managed Caltrans PC.

---

## 1. Network connections it makes

| Destination | When | Why | Auth |
|---|---|---|---|
| `tsmis.dot.ca.gov` (or the per-env host; a Settings override is restricted to `*.ca.gov`) | Every export / sign-in / env check | Load the TSMIS report page and pull report data (the page itself fetches from a Caltrans intranet ArcGIS host) | The user's Caltrans SSO session |
| The Caltrans ArcGIS **portal / Azure AD IdP** (the page's `CONFIG.oauthAuthorizeUrl` host) | During sign-in only | Standard OAuth/SAML sign-in; the access token comes back in the URL fragment and lives only in page memory (~120 min) | Caltrans SSO / Windows device account |
| `api.github.com` + the release asset host (`objects.githubusercontent.com`) | The one-click **update check** (launch + when the version chip is clicked) and download | Read the latest release tag; download the update zip + its `.sha256` | None — public repo, read-only |
| Playwright's Chromium CDN | **Only** the `.bat` first-time setup, or the optional Settings ▸ "Download Built-in Chromium" | Fetch the bundled-browser binary | None |

It makes **no other outbound connections** — no analytics, no telemetry, no
crash-reporting service, no license server. The default `win64` build does not
download a browser at all (it drives the machine's existing Edge/Chrome).

TLS for the update check/download uses the **Windows certificate store**
(`ssl.create_default_context()`), so corporate TLS inspection and the system
proxy work without any bundled CA list.

## 2. Files it reads and writes

Everything lives **next to the `.exe`** (or `%LOCALAPPDATA%\TSMIS Exporter` if
that folder is read-only — see `scripts/paths.py`). It never writes to system
locations, the registry, or other users' profiles.

- `output\…` — the exported PDF/XLSX reports and run-report CSVs.
- `input\tsn_highway_log\…` — TSN PDFs the user drops in (consolidate feature).
- `data\` — the app's own data: `logs\` (rotating diagnostics), `config.json`
  (settings), the WebView2 profile, the Edge sign-in profile, the downloaded
  Chromium (if any), and `update\` (staging during an update).
- `scripts\tsmis_auth.json` (dev) / `data\…` (packaged) — the saved sign-in
  session. **Treat as a credential.** Plaintext Playwright `storage_state`
  (cookies); see §6.
- `data\logs\failures\` — best-effort screenshots + page HTML when a route or
  sign-in fails, for diagnosis. May contain report data; it is **never** added to
  the shareable support bundle.

## 3. Browser flags it sets (and why)

These are the only non-default low-level options, all on automated browser
contexts:

- **Local Network Access (LNA):**
  `--disable-features=LocalNetworkAccessChecksWarnings`,
  `--enable-features=LocalNetworkAccessChecks`, plus a pre-granted
  `local-network-access` permission. The TSMIS page pulls report data from a
  Caltrans **intranet** host; Chromium's LNA gate would otherwise block that
  behind an "allow access to your local network?" prompt that nothing can click
  in a headless run. This grants that one permission to the app's own automated
  pages — it does not scan or expose the local network.
- **A loopback CDP debug port** (`--remote-debugging-port=<ephemeral>` on
  `127.0.0.1`): used **only** during the headed Microsoft Edge sign-in flow, so
  the app can recapture the session if managed Edge relaunches itself into a work
  profile mid-login. The port is a free local port, bound to loopback, and only
  open while that one sign-in window is up. No remote access.

## 4. Mark-of-the-Web (MOTW) handling

When a release zip is downloaded and extracted **without** right-click → Unblock,
Windows tags every file with an NTFS `Zone.Identifier` stream, and the .NET
Framework then refuses to load the bundled WebView2/pythonnet assemblies — the
window dies at startup. On launch the app removes that stream from **only its own
bundled .NET trees** (`_internal\pythonnet`, `_internal\clr_loader`,
`_internal\webview`), which is exactly what right-click → Properties → Unblock
does, scoped to the app's own folder. It does **not** touch user files, system
files, or anything outside the program folder, and it is best-effort (a read-only
install just shows a message explaining the manual Unblock). In-app updates write
the zip bytes directly (no browser), so they never carry MOTW in the first place.

## 5. The one-click updater

- Checks `…/releases/latest` (full releases only — never prereleases/drafts).
- Downloads the variant-matching zip into `data\update\` and **verifies its
  SHA-256** against the published `<asset>.sha256` (and the GitHub API's asset
  digest) before extracting. A mismatch refuses the install.
- Installs by COPY-then-RENAME of **only the known bundle items** (`TSMIS
  Exporter.exe`, `_internal`, `Start Here.txt`) — an unexpected staged file is
  ignored. User data (`output\`, `input\`, `data\`) is never in the update and is
  never touched. A failed swap rolls back to the previous version.
- A read-only install can't self-update; it opens the release page instead.

## 6. Known gaps (honest disclosure)

- **The `.exe` is not code-signed yet.** This is the single biggest remaining
  item — see §7. Until then SmartScreen may warn on first run, and EDR/AV may
  treat the self-updating exe with suspicion.
- **The saved session file is plaintext** (`storage_state` cookies), protected
  only by NTFS file permissions in the user's own app folder. Windows DPAPI
  at-rest encryption is a candidate hardening.
- **Build-time dependencies are not yet hash-pinned** (`--require-hashes`). CI
  runs `pip-audit` to flag known-vulnerable deps; a fully hash-locked build
  requirements file is the planned next step.

## 7. Code-signing — the recommended path

Signing the executable (and the bundled native DLLs) with an Authenticode
certificate is the highest-leverage fix: it establishes updater trust, calms EDR
heuristics about a self-replacing exe, and earns SmartScreen reputation — all at
once. Recommended approach:

1. Obtain an **OV or EV** Authenticode code-signing certificate for the
   publishing org (EV gives immediate SmartScreen reputation).
2. Add a signing step to `build.ps1` / `release.yml` that runs `signtool sign`
   on `TSMIS Exporter.exe` after the build, **gated on a CI secret** holding the
   cert (so the build still works for contributors without it).
3. Once releases are signed, enable **signature verification in the updater**
   (verify the staged exe's Authenticode signature + expected publisher before
   the swap, in addition to the SHA-256 check) and switch the requirement on.

The SHA-256 verification and staged-item allowlist already shipped (§5) are the
checksum/integrity half of this; the signature half needs the certificate.

---

*Questions: see the rotating logs (`data\logs\tsmis.log`) and the "Save support
bundle" button, which packages logs + settings (and this PC's name in paths) for
the maintainer — never the saved login.*
