# TSMIS Exporter — IT / Security review notes

What this doc covers: the plain-language IT/endpoint-security/DLP reference (network
connections, files, browser flags, MOTW, the updater, known gaps, the code-signing
path) **plus** the security threat model — the managed-work-PC capability model the
whole app design is constrained by, the read-only audit's headline findings, the
"don't re-flag, they're good" designs, and the open security gaps.

Audience: the person approving the unsigned `.exe` on a managed Caltrans PC, and any
future agent reasoning about what the app is *allowed* to do on that PC.

Related docs: full updater swap-mode / MOTW / SHA-256 / revert mechanics live in
[build-and-release.md](build-and-release.md); auth-file handling and the sign-in
flow live in [auth-and-signin.md](auth-and-signin.md); the audit prompt / review
methodology lives in [code-review-prompt.md](code-review-prompt.md).

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
(`ssl.create_default_context()` in `scripts/updater.py`), so corporate TLS
inspection and the system proxy work without any bundled CA list. Do **not** switch
this to `requests`/`certifi` — a bundled CA list would reject a TLS-inspection
re-signed certificate and break the updater on exactly the managed PCs that need it.

## 2. Files it reads and writes

Everything lives **next to the `.exe`** (or `%LOCALAPPDATA%\TSMIS Exporter` if that
folder is read-only — see `scripts/paths.py`, `_resolve_data_root` → `DATA_ROOT`).
It never writes to system locations, the registry, or other users' profiles.

- `output\…` — the exported PDF/XLSX reports and run-report CSVs (`OUTPUT_ROOT`).
- `input\tsn_highway_log\…` — TSN PDFs the user drops in (consolidate feature;
  `INPUT_ROOT`).
- `data\` (the app-private `_PRIVATE` tree) — the app's own data: `logs\` (rotating
  diagnostics, `LOG_DIR`), `config.json` (settings, `CONFIG_FILE`), the WebView2
  profile (`WEBVIEW_PROFILE_DIR` = `data\webview2`), the Edge sign-in profile
  (`EDGE_LOGIN_PROFILE_DIR` = `data\edge_login_profile`), the downloaded Chromium if
  any (`DOWNLOADED_BROWSERS_DIR` = `data\ms-playwright`), and `update\`
  (`UPDATE_DIR`, staging during an update).
- `scripts\tsmis_auth.json` (dev) / `data\tsmis_auth.json` (packaged) — the saved
  sign-in session (`AUTH`). **Treat as a credential.** Plaintext Playwright
  `storage_state` (cookies); see §6.
- `data\logs\failures\` (`FAILURES_DIR`) — best-effort screenshots + page HTML when
  a route or sign-in fails, for diagnosis. May contain report data; it is **never**
  added to the shareable support bundle.

(In a frozen build `AUTH`, `LOG_DIR`, `CONFIG_FILE`, etc. all sit under
`DATA_ROOT\data`; in a dev run `_PRIVATE` is the repo root and `AUTH` is
`scripts/tsmis_auth.json`, so the `.bat` workflow is unchanged.)

## 3. Browser flags it sets (and why)

These are the only non-default low-level options, all on automated browser contexts
(defined in `scripts/common.py`):

- **Local Network Access (LNA)** — `_LNA_ARGS`:
  `--disable-features=LocalNetworkAccessChecksWarnings`,
  `--enable-features=LocalNetworkAccessChecks`, plus a pre-granted
  `local-network-access` permission (`_new_app_context`, and the headed-login and
  device-sign-in contexts via `LOGIN_BROWSER_ARGS = _LNA_ARGS`). The TSMIS page
  pulls report data from a Caltrans **intranet** host; Chromium's LNA gate would
  otherwise block that behind an "allow access to your local network?" prompt that
  nothing can click in a headless run. This grants that one permission to the app's
  own automated pages — it does not scan or expose the local network.
- **A loopback CDP debug port** (`--remote-debugging-port=<ephemeral>` on
  `127.0.0.1`, via `_free_local_port()` in `open_edge_device_context` /
  `launch_edge_login_context`): used **only** during the headed Microsoft Edge
  sign-in flow, so the app can recapture the session if managed Edge relaunches
  itself into a work profile mid-login (returned as `http://127.0.0.1:<port>` for a
  CDP re-attach). The port is a free local port, bound to loopback, and only open
  while that one sign-in window is up. No remote access.

## 4. Mark-of-the-Web (MOTW) handling

When a release zip is downloaded and extracted **without** right-click → Unblock,
Windows tags every file with an NTFS `Zone.Identifier` stream, and the .NET
Framework then refuses to load the bundled WebView2/pythonnet assemblies — the
window dies at startup. On launch the app removes that stream from **only its own
bundled .NET trees** (`_internal\pythonnet`, `_internal\clr_loader`,
`_internal\webview`), which is exactly what right-click → Properties → Unblock does,
scoped to the app's own folder. It does **not** touch user files, system files, or
anything outside the program folder, and it is best-effort (a read-only install just
shows a message explaining the manual Unblock). In-app updates write the zip bytes
directly (no browser), so they never carry MOTW in the first place. Full MOTW/CLR
narrative: [lessons.md](lessons.md); the strip routine itself is
`gui_main._unblock_dotnet_assemblies()` (see [build-and-release.md](build-and-release.md)).

## 5. The one-click updater

(Mechanics summary — full swap-mode / two-phase / revert detail is in
[build-and-release.md](build-and-release.md).)

- Checks `…/releases/latest` (full releases only — never prereleases/drafts).
- Downloads the variant-matching zip into `data\update\` and **verifies its SHA-256**
  against the published `<asset>.sha256` (and the GitHub API's asset digest) before
  extracting. A mismatch refuses the install.
- Installs by COPY-then-RENAME of **only the known bundle items** (`TSMIS
  Exporter.exe`, `_internal`, `Start Here.txt`) — an unexpected staged file is
  ignored. User data (`output\`, `input\`, `data\`) is never in the update and is
  never touched. A failed swap rolls back to the previous version.
- A read-only install can't self-update; it opens the release page instead.

## 6. Known gaps (honest disclosure)

- **The `.exe` is not code-signed yet.** This is the single biggest remaining item —
  see §7. Until then SmartScreen may warn on first run, and EDR/AV may treat the
  self-updating exe with suspicion (the audit's `IT-UNSIGNED-SELF-MODIFY-EDR`
  finding; signing calms it).
- **The saved session file is plaintext** (`storage_state` cookies, written by
  `common.save_auth_state`), protected only by NTFS file permissions in the user's
  own app folder. Windows DPAPI (`CryptProtectData`) at-rest encryption is the
  candidate hardening (the code comment at `common.save_auth_state` points back at
  this doc).
- **Build-time dependencies are not yet hash-pinned** (`--require-hashes`). CI runs
  `pip-audit` to flag known-vulnerable deps; a fully hash-locked build requirements
  file is the planned next step.

## 7. Code-signing — the recommended path

Signing the executable (and the bundled native DLLs) with an Authenticode
certificate is the highest-leverage fix: it establishes updater trust, calms EDR
heuristics about a self-replacing exe, and earns SmartScreen reputation — all at
once. Recommended approach:

1. Obtain an **OV or EV** Authenticode code-signing certificate for the publishing
   org (EV gives immediate SmartScreen reputation).
2. Add a signing step to `build.ps1` / `release.yml` that runs `signtool sign` on
   `TSMIS Exporter.exe` after the build, **gated on a CI secret** holding the cert
   (so the build still works for contributors without it).
3. Once releases are signed, enable **signature verification in the updater** (verify
   the staged exe's Authenticode signature + expected publisher before the swap, in
   addition to the SHA-256 check) and switch the requirement on.

The SHA-256 verification and staged-item allowlist already shipped (§5) are the
checksum/integrity half of this; the signature half needs the certificate.

---

## 8. Constraints & threat model

This section is the reasoning backdrop for everything above: what the work PC *can*
run, what's been independently audited as sound, and what's still open.

### 8.1 Two machines, very different capabilities

| | **Work PC** (the real users) | **Dev / personal PC** (where coding happens) |
|---|---|---|
| Who | Caltrans staff on locked-down managed PCs | The maintainer's personal Windows 11 PC |
| PowerShell | **Blocked entirely** — standard users can't even open it | Available, no limits |
| cmd | No guarantee it works | Available |
| Admin rights | None | Yes |
| TSMIS intranet | **Reachable** (live exports happen here) | **Not reachable** — cannot hit the report site at all |
| Managed-PC controls (Defender / DLP / corporate proxy / managed Edge) | Present and active | **Absent** |
| Proven capability | "Unsigned exes run from user-writable folders" (the app itself proves this) | Everything |

**Hard rule for any work-PC feature.** Anything that must run *on the work PC*
(updates, helpers, "scheduled anything") must work as a plain `.exe` invocation from
a user-writable folder — **no PowerShell, no cmd scripts, no temp script files, no
elevation, no scheduled tasks.** This is not a preference; it is the only capability
proven to exist there.

> **Why this rule exists (field failure, 2026-06-12).** The v0.9.0 updater shipped a
> PowerShell swap helper. On the work PC it **died silently** — the update downloaded
> and staged, the app closed, and nothing installed (PowerShell is blocked for
> standard users). Fixed in **v0.10.1** by making the staged exe apply itself
> (`updater.run_swap_mode`), which needs only "exes run from user folders." The full
> narrative is in [lessons.md](lessons.md).

**Why testing is asymmetric — and what that means for security work.** Live-site
verification can only happen on the work PC, because the personal dev PC can't reach
the TSMIS intranet. Crucially, the managed-PC security controls (Defender, DLP, the
corporate proxy, managed-Edge behavior) exist on **neither** the personal dev PC nor
any cloud CI runner. So **IT / DLP / endpoint behavior can only be reasoned about
from code — it can never be empirically tested off the work PC.** Treat every claim
in §1–§7 about how Defender/DLP/proxy/managed Edge will react as a code-derived
hypothesis, not a tested fact, and design conservatively. (Related context for
diagnosing field reports: a problem report almost always means the *work* PC — see
[lessons.md](lessons.md).)

The work PC's proxy/TLS-inspection setup is exactly why the updater trusts the
**Windows cert store** (§1) and the DLP scanner is exactly why `prune_bundle.ps1`
strips DLP-blocked content from the bundle (the Playwright docs once shipped a test
credit-card number that corporate DLP blocks — see
[build-and-release.md](build-and-release.md)).

### 8.2 Read-only audit, 2026-06-15 (v0.10.4 / SHA `0643fe2`)

A ruthless read-only audit (7-domain subagent fan-out + lead re-verification) was run
against v0.10.4 code (byte-identical to release tag `v0.10.4`). Full report lived at
`code-review/AUDIT-claude-0643fe2.md` (gitignored). The methodology/prompt is in
[code-review-prompt.md](code-review-prompt.md). Headline findings the maintainer
should act on (all verified against code, not just asserted):

- **P0 `AUTH-TOKEN-IN-LOG-BUNDLE`** — at audit time `common.auth_state()` logged the
  raw `page.url` (the OAuth token rides in the URL hash) to `tsmis.log` on every
  navigate, and `gui_api.save_support_bundle` zips `tsmis.log*` as "safe to share."
  `page_url_for_display` stripped the fragment for the *screen* but the *log* path
  did not. **Status in current code: addressed** — `common.auth_state` now routes the
  URL through `page_url_for_display` (which `_replace(fragment="")`), so the token can
  reach neither a log line nor a failure dump. See discrepancy note (the memory
  snapshot predates the fix).
- **P1 `AUTH-WRONG-ENV-SILENT-SUCCESS`** — `navigate_with_auth`'s
  `if _site_params_ok(page) or reloaded_for_params:` accepts a still-wrong env after
  one reload; the run folder is labeled by selection, with no post-success CONFIG
  recheck. (Auth/env mechanics: [auth-and-signin.md](auth-and-signin.md).)
- **P1 `UPDATER-NO-SIGNATURE-VERIFY`** + `RELEASE-NO-DIGEST-OR-SIGN` — the updater
  extracts and runs an unsigned exe; it trusts the Windows cert store including
  TLS-inspection roots. Code-signing is the single highest-leverage fix (also clears
  the EDR-look finding `IT-UNSIGNED-SELF-MODIFY-EDR`). The SHA-256 digest + checksum
  publishing half shipped after the audit (§5); the signature half is still open
  (§6/§7).
- **P1 `SHEET-COMPARE-SYMMETRIC-SKIP-MATCH`** — `compare_env._load_xlsx_side`
  silently drops a route unreadable on **both** sides, so a verdict could still say
  "EVERYTHING MATCHES." (The v0.11.0 incompleteness contract — `⚠ COULD NOT COMPARE
  EVERYTHING`, forced `verdict="diff"` on skipped inputs — is the intended fix; see
  [comparison-engine.md](comparison-engine.md).)

### 8.3 Notable GOOD designs (don't waste time re-flagging)

The same audit explicitly cleared these as sound — re-auditing them is wasted effort:

- **GUI is injection-safe.** The Python→JS bridge dispatches via `json.dumps`
  (`window.__tsmis.dispatch()`); `app.js` uses **no `innerHTML` / no `eval`**, so
  report data and env strings can't become markup or code. (GUI internals:
  [gui.md](gui.md).)
- **`reset_targets` (Delete-all-reports) is well-scoped.** Its docstring is explicit:
  "logs, the saved login, the Edge sign-in profile and the app's settings are NEVER
  in this list." It removes only run folders, legacy output folders, the
  TSN/TSMIS-PDF consolidated workbooks, the Export-Everything store, `FAILURES_DIR`,
  and (opt-in) the TSN input PDFs.
- **The support bundle excludes the auth file and browser profiles.**
  `gui_api.save_support_bundle` adds only the rotating logs (`tsmis.log*`,
  `crash.log`, `update_helper.log`), up to 50 recent run-report CSVs, and a
  `manifest.txt`. Its own docstring + the user-facing message say it carries "this
  PC's name in paths" so it's "safe to send to the TSMIS maintainer, not safe to post
  publicly" — and **never** the saved login, profiles, or `FAILURES_DIR` dumps.
- **Settings writes are atomic.** `config.json` (and the batch manifest,
  `batch_manifest.save` → temp file + `os.replace`) are written atomically, so a
  crash mid-write can't corrupt them.
- **The reset/extract paths can't be tricked into traversing outside their
  targets** (verified empirically on Python 3.11 + Windows, 2026-06-16).
  `shutil.rmtree` **refuses** a top-level directory junction (leaves the junction's
  target untouched) and does **not** recurse into a nested junction (removes the
  link only); `reset_targets` builds its delete list solely from path constants
  (`OUTPUT_ROOT` run folders / fixed legacy names / `FAILURES_DIR` / `INPUT_ROOT`),
  never user-supplied names. The updater's `zipfile.extractall` is likewise safe:
  3.11 sanitizes `..`/absolute/drive members and the staged zip is SHA-256-verified
  and self-produced. (Closed item; see [roadmap.md](roadmap.md).)

### 8.4 Open security gaps (the levers that remain)

In priority order:

1. **Code-signing the `.exe`** — the one big remaining lever. Fixes updater trust,
   EDR heuristics, and SmartScreen at once (§7).
2. **Auth file at rest is plaintext `storage_state`** — protected only by NTFS perms.
   Consider Windows DPAPI (`CryptProtectData`) encryption (§6; see
   [auth-and-signin.md](auth-and-signin.md) for the auth lifecycle).
3. **Build deps are not hash-pinned** — `pip-audit` flags known-vulnerable deps in
   CI, but a `--require-hashes` build requirements file is not yet in place (§6).

---

*Questions: see the rotating logs (`data\logs\tsmis.log`) and the "Save support
bundle" button, which packages logs + settings (and this PC's name in paths) for the
maintainer — never the saved login.*
