# Build & Release

What this doc covers: how the portable onefolder bundle is built (`build.ps1` →
PyInstaller `app.spec` → `prune_bundle.ps1`), the three release variants and
their browser channels, the full one-click self-updater (`updater.py`: swap
mode, two-phase install, MOTW-free download, SHA-256 verify, revert), and the
CI/release workflows. This doc OWNS the updater detail and the build pipeline. For
the **code-level updater walkthrough** (the download→stage→two-phase-swap pipeline,
rollback, revert), see [internals/updater-swap.md](internals/updater-swap.md).

Related: work-PC constraints that force the updater's design → [it-and-security.md](it-and-security.md);
the golden `check_*.py` set and verification loops → [verification-and-testing.md](verification-and-testing.md);
field-failure narratives behind these design choices → [lessons.md](lessons.md).

---

## The product is a portable single-folder Windows app

- **Packaging:** PyInstaller **onefolder**, shipped as a portable zip (no
  installer, no Python on the target). Non-technical staff unzip one folder and
  double-click `TSMIS Exporter.exe`.
- **UI stack:** pywebview + **Edge WebView2** rendering vanilla HTML/CSS/JS — no
  frontend framework, no build step, no npm (static files ship in the bundle).
  `webview.start(gui="edgechromium")` is forced so a missing runtime fails loudly
  instead of degrading to MSHTML. `tkinter`/Tcl/Tk are excluded (the UI was a
  Tk window before v0.8.0). WebView2 ships with Windows 10/11 + evergreen Edge.
  Full GUI/threading detail lives in [gui.md](gui.md).
- **Data location (option A):** the packaged app writes `output/`, the auth
  token, logs, and config **next to the `.exe`**, falling back to
  `%LOCALAPPDATA%\TSMIS Exporter` if the folder is read-only (`scripts/paths.py`).
  This fallback is what makes an install "read-only" for update purposes (see
  *Read-only installs* below).
- Built/tested on **Python 3.11**. Published exe is not trust-signed yet —
  **code-signing is the only complete fix** for IT/Defender/DLP false-positives.
  A SignPath Foundation cert is applied for; `build.ps1 -Sign` self-signs for
  local/test use and `release.yml` has a gated SignPath step ready
  ([it-and-security.md §7](it-and-security.md)). The trust metadata below is the
  partial mitigation until then.

---

## `build.ps1` — one-command build

From the repo root:

```
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

Produces the windowed `dist\TSMIS Exporter\` (~148 MB; double-click
`TSMIS Exporter.exe`). Two switches:

| Switch | Effect |
|---|---|
| `-SelfTest` | Builds a **headless console** self-test exe AND runs it over the pruned bundle — the real release gate (see step 3b). |
| `-BundleChromium` | Additionally ships Playwright's own Chromium inside `_internal\ms-playwright` (the with-browser variant). |
| `-Sign` | **Self-signs** the built `.exe` (SHA-256 + timestamp) with a self-signed cert (auto-created in `Cert:\CurrentUser\My`; override `-CertSubject`). Interim/local only — other PCs won't trust it; real signing is SignPath in CI. See [it-and-security.md §7](it-and-security.md). |

Steps:

1. **Isolated build venv** — creates `build\.venv` if absent, then
   `pip install -r requirements-build.txt` into it. (End-user setup uses global
   pip; only the build uses a venv.)
2. **PyInstaller** — runs `app.spec` with `--distpath dist --workpath build\pyi-work --noconfirm`.
   `build.ps1` sets three env vars the spec reads: `TSMIS_ENTRY`
   (`scripts\gui_main.py` for the app, `build\full_smoke.py` for `-SelfTest`),
   `TSMIS_APP_NAME` (`TSMIS Exporter` / `TSMIS SelfTest`), `TSMIS_CONSOLE`
   (`0` windowed / `1` console).
2b. **Optional Chromium bundle** (`-BundleChromium`, done BEFORE the prune so its
   locale trimming applies to the browser too): sets
   `PLAYWRIGHT_BROWSERS_PATH` at `<AppDir>\_internal\ms-playwright` and runs
   `playwright install chromium --no-shell`. `--no-shell` skips the separate
   headless shell — `channel="chromium"` runs the full browser in new-headless
   mode, so one binary serves headed sign-in AND headless exports.
3. **Prune + DLP guard** — runs `prune_bundle.ps1 -Target <AppDir>` (see below);
   fails the build if DLP-blocked content remains.
3b. **Run the frozen self-test** (only with `-SelfTest`) — runs the built
   self-test exe; a nonzero exit fails the build. Building proves it *links*;
   running proves the PRUNED frozen bundle exercises every real code path
   (system browser `page.pdf()` + download, pdfplumber text/table extraction,
   openpyxl round-trip, GUI construction through the real JS bridge).
   `-SelfTest -BundleChromium` gates the bundled-Chromium path.
4. **Report** — copies `dist_readme.txt` in as `Start Here.txt` and
   `it_readme.txt` in as `IT-README.txt` (the IT/security handout), windowed
   builds only, and prints the onefolder size.

The ~148–149 MB floor is `node.exe` (~80 MB, the Playwright Node driver) +
Python + pythonnet/WebView2 assemblies + pdf/excel libs.

---

## Three release variants, one codebase

| Variant zip | Browser | Approx size | Notes |
|---|---|---|---|
| `*-win64.zip` (default build) | none bundled | ~148 MB | Drives the machine's installed **Edge** (then Chrome). |
| `*-win64-with-browser.zip` (`-BundleChromium`) | Playwright Chromium in `_internal\ms-playwright` | ~246 MB | `paths.py` points `PLAYWRIGHT_BROWSERS_PATH` there; **Built-in Chromium** is the *default* channel (Edge/Chrome stay in the dropdown). |
| `*-batch-source.zip` (`git archive`) | none | small | The `.bat` console flow; `1. setup…bat` pip-installs the libs **and** runs `playwright install chromium --no-shell`. |

(v0.10.0 published sizes: win64 64 MB / with-browser 246 MB / batch-source — the
64 MB figure predates later bundle growth; current win64 is ~148 MB.)

### Browser channels

`common.launch_browser` probes channels once per process by launching headless
and driving a page, so a too-new Edge falls through to the next channel. Order
(`common.BROWSER_CHANNELS`):

```
chromium (only when present) → msedge → chrome
```

- `chromium` appears only when a Playwright Chromium is actually present
  (`common._chromium_available()`): the bundle's own `_internal\ms-playwright`,
  an explicit `PLAYWRIGHT_BROWSERS_PATH`, or the Settings-tab download
  (`paths.DOWNLOADED_BROWSERS_DIR` = `data\ms-playwright`). The machine's global
  Playwright cache is deliberately ignored so the default build defaults to Edge
  even on a dev PC.
- **Override:** `TSMIS_BROWSER_CHANNEL` env var hard-pins a channel (for
  debugging); the GUI Browser dropdown calls `set_preferred_channel` (tried
  first, the others stay fallbacks).
- `common.launch_browser` raises `BrowserNotFoundError` only if all channels
  fail (it distinguishes "none installed" from "too new — update the tool").
- **Parallel/fast-mode workers avoid managed Edge:** `_parallel_candidates()`
  orders Built-in Chromium → Chrome → Edge-as-last-resort. See concurrency
  rationale in [engine-and-reliability.md](engine-and-reliability.md).

### `paths.py` browser-path resolution

`PLAYWRIGHT_BROWSERS_PATH` is set at import (before any `sync_playwright()`),
and an explicit env value always wins. Two locations probed in order:

1. `BUNDLED_BROWSERS_DIR` = `<exe>\_internal\ms-playwright` (with-browser
   variant; part of the read-only bundle, never user data).
2. `DOWNLOADED_BROWSERS_DIR` = `data\ms-playwright` (Settings-tab download; user
   data, survives one-click updates, deletable in Settings) — used only when
   `_has_chromium()` finds a `chromium-*` folder there.

---

## `app.spec` highlights

Entry = `TSMIS_ENTRY`; output name/console from the other env vars. Key recipe
points:

- **`collect_all('playwright')`** + Playwright's bundled PyInstaller hooks → the
  Node driver (`node.exe`) ships and is importable when frozen. **No browser
  data entry** — no `ms-playwright` is added by the spec (the with-browser
  variant adds it in build.ps1 step 2b).
- **`collect_all('webview'/'pythonnet'/'clr_loader')`** — the GUI shell. Their
  package DATA is load-bearing when frozen: `webview/lib` (WebView2 .NET
  assemblies), `pythonnet/runtime` (`Python.Runtime.dll` + netstandard facades),
  `clr_loader/ffi/dlls` (ClrLoader natives). `hiddenimports += ['clr']`
  (pythonnet's import name).
- **`scripts/ui/*` ships as data files** under `_internal/ui/`; `gui_api`
  resolves them at runtime via `sys._MEIPASS/ui/`.
- **`collect_data_files('pdfminer')`** — the pdfminer CMap data is the classic
  frozen trap (text extraction breaks without it). `collect_all('pdfplumber'/'openpyxl')`.
  `cryptography` is a hard pdfminer import and **must stay**.
- **`APP_MODULES`** lists every flat `scripts/` module as a hidden import (many
  are imported lazily inside functions). New report/consolidator/comparison
  modules MUST be added here.
- **`excludes=['PIL','pypdfium2','pypdfium2_raw','tkinter','_tkinter']`** — image
  libs the runtime paths (text/table extraction + plain workbooks) don't need,
  plus Tk/Tcl. NOTE: openpyxl imports Pillow *eagerly* at import time, so PIL
  *is* loaded in a normal install (`full_smoke.py` reports `PIL: True` against
  the venv); what makes excluding it safe is the FROZEN `-SelfTest` passing with
  it gone, not the import being absent. Trims ~20 MB.
- **Trust metadata** (reduces IT/Defender/DLP/SmartScreen false-positives on the
  unsigned exe): version-info resource from `version.py` (`version.py` is the
  single source of truth for the version), `app.ico`, `app.manifest`
  (`asInvoker` + Win10/11 compatibility), and **`upx=False`** (UPX-packed exes
  are a classic AV false-positive trigger). Code-signing remains the only
  complete fix.

---

## `prune_bundle.ps1` — bundle hygiene + DLP guard

Strips a built bundle to runtime-only files and **fails the build** if
DLP-blocked content remains. Run automatically by `build.ps1` step 3; also
re-runnable on an extracted release:

```
powershell -ExecutionPolicy Bypass -File build\prune_bundle.ps1 -Target "…\TSMIS Exporter"
```

`-GuardOnly` audits without deleting; `-Quiet` suppresses logging.

**Motivating case:** the Playwright Node driver ships docs/"agent skill" files
(e.g. `driver\package\lib\tools\cli-client\skill\references\tracing.md`) whose
examples contain a test credit-card number like `4111111111111111`. Microsoft
365 / SharePoint DLP detects "Credit Card Number" and **blocks** the file — a
released zip becomes partly inaccessible. Rather than chase one file, the script
strips ALL prose docs.

**Prune set** (verified to keep a real Chromium launch + `page.pdf()` + downloads
working):
- Driver extras: `package\lib\tools\cli-client\skill`, `…\tools\trace`,
  `…\tools\dashboard`, `…\vite`, `package\types`.
- Loose `*.d.ts` anywhere in the driver (driver-scoped); `*.md` is stripped here
  **and** bundle-wide by the later pass (see the all-prose-docs bullet below).
- Chromium locale packs: keep `en-US.pak`, drop the other ~220 locales (~42 MB).
- Safety net for the PyInstaller excludes: drop `PIL`/`Pillow`/`pypdfium2`/
  `pypdfium2_raw` package dirs + their dist-info if a hook re-bundled them.
- Generic dead weight: `tests`/`test` dirs and `*.pyi` stubs (skipping the
  `ms-playwright` tree).
- **All prose docs bundle-wide** (`*.md`/`*.markdown`/`*.rst` + stray
  `README`/`CHANGELOG`/`HISTORY`/`AUTHORS`/`CONTRIBUTING`/`NEWS`) **except
  license/notice files** (legally required for OSS redistribution, never
  DLP-flagged). The app's own `Start Here.txt` sits at the app root, not under
  `_internal`, so it is untouched.
- **dist-info/egg-info METADATA sanitized** to its RFC822 headers only (each
  embeds the package's full README as the long-description body; pdfplumber's is
  600+ lines). Drops everything after the first blank line — keeps
  `importlib.metadata.version` working.

**Guards (fail the build with `GUARD FAILED` if found):**
- Any leftover non-license doc (`*.md`/`*.markdown`/`*.rst`).
- **Credit cards** — brand IIN prefix + canonical length + **Luhn** (so random
  16-digit hashes in JS bundles aren't false positives).
- **PEM private keys** — `-----BEGIN … PRIVATE KEY-----`.
- **AWS keys** — `AKIA` + 16 base32.
- **US SSNs** — dashed, with invalid area/group/serial ranges excluded.

The text scan covers the bundled Chromium tree too — a DLP scanner won't exempt
"upstream" files, so neither does the guard. Binaries are skipped by the
text-extension filter.

---

## The one-click self-updater (`scripts/updater.py`)

GUI-only. At launch (quiet unless something is found) and on clicking the
version chip, the app asks the GitHub Releases API for the latest tag and
compares it to `version.__version__`. The only UI is the title-bar pill.
Console/`.bat` flows never update.

`GITHUB_REPO = "yunusshaikh7/TSMIS-Reports-Exporter"` (public repo, stdlib
`urllib`, no token).

### TLS — Windows cert store, never certifi

`_http_get` uses `ssl.create_default_context()`, which trusts the **Windows
certificate store** — so corporate TLS inspection roots keep working where a
bundled CA list (certifi) would reject the connection. `urllib` also picks up
the system proxy from the registry. **DO NOT switch this to requests/certifi.**

### `update_support()` — what an install can do

| Verdict | Condition | Behavior |
|---|---|---|
| `"ok"` | packaged build, app folder writable (`DATA_ROOT == install_dir()`) | full one-click update |
| `"link"` | packaged build in a read-only spot (`paths.py` redirected data to `%LOCALAPPDATA%`) | pill opens the **release page** instead of installing |
| `"off"` | dev / console run (`not is_frozen()`) | update check skipped — no bundle to replace |

### Variant matching

`current_variant()` returns `win64-with-browser` when
`install_dir()\_internal\ms-playwright` exists (same probe `paths.py` uses), else
`win64`. The updater downloads the matching `-<variant>.zip` asset.

### The download → stage → swap pipeline

1. **`check_for_update()`** — hits `/releases/latest` (never returns prereleases
   or drafts), parses `tag_name`, returns an `UpdateInfo` only if newer. HTTP 404
   = repo has no releases yet (returns None, not an error).
2. **`download_and_stage()`** (heavy; runs on a worker thread):
   - Clears `data\update`, checks free disk (needs ~3× the asset size).
   - Streams the zip into `data\update\`, computing SHA-256 as it goes.
     **Writing the bytes ourselves means NO Mark-of-the-Web is ever applied**
     (browsers add the `Zone.Identifier` stream; `zipfile`/raw writes do not), so
     the CLR-blocking MOTW field failure that motivated
     `gui_main._unblock_dotnet_assemblies()` can't happen on this path.
   - **Verifies SHA-256 against the published checksum** (`_expected_sha256`):
     prefers the companion `<asset>.sha256` file (which the release publishes and
     a user can verify by hand), then the GitHub API's own `digest`. A mismatch
     deletes the zip and **refuses to install** — guards against
     corruption/truncation/wrong-asset, NOT a forged release (that is
     code-signing's job, the planned next step). No published checksum ⇒ proceed
     on size only with a warning.
   - Extracts to `data\update\extract`, renames the inner bundle root to
     `data\update\staged`, and asserts the staged tree has the exe + `_internal`.
3. **`apply_update_and_restart(staged_dir)`** — launches the **STAGED NEW EXE**
   in swap mode (`SWAP_FLAG = "--apply-update"`, detached, `CREATE_NO_WINDOW`),
   passing the install dir, this app's PID, and the helper-log path. The caller
   then closes the app. If the swap exe dies within ~1.5 s (a policy blocked it),
   it raises `UpdateError` and the app **stays open on the old version** — the
   silent-failure mode the old PowerShell helper had.
4. **`cleanup_leftovers()`** (every GUI launch, before the CLR loads) — removes
   `data\update` staging and stale `*.old`/`*.new` bundle pieces. Deliberately
   removes a staged-but-never-applied download so stale versions are re-offered
   fresh. Also calls `_clear_webview_caches()` (see below).

### Why a swap-mode exe, not a script (work-PC constraint)

v0.9.0 ran a PowerShell helper from `%TEMP%`. On locked-down Caltrans PCs that
block PowerShell entirely for standard users, it was killed silently — the
update downloaded + staged, the app closed, and **nothing was swapped** (the
download just sat in `data\update`). v0.10.1 redesigned it: the staged new exe
applies *itself* via `--apply-update`. The one capability this needs — "exes run
from user-writable folders" — is already proven anywhere the app itself runs. No
PowerShell, cmd, temp scripts, admin, or scheduled tasks. The work PC needs ONE
manual install of ≥ 0.10.1; auto-update works from then on. Full constraint →
[it-and-security.md](it-and-security.md).

### `run_swap_mode` / `perform_swap` — two-phase install

`gui_main` branches into `run_swap_mode(argv)` **FIRST**, before
logging/paths/CLR setup: this process runs from the staged tree under the
install's `data\update\`, so `paths.py`-derived locations would aim at the WRONG
(staged) tree. Everything takes explicit paths and logs by direct appends to
`update_helper.log`.

`perform_swap`:
1. Waits up to `_SWAP_TIMEOUT_S = 120` s for the old app's PID to exit
   (`_wait_pid_exit`, ctypes `OpenProcess`/`WaitForSingleObject` — no psutil in
   the bundle; PID-recycle-safe because the handle is taken while the app is
   still alive).
2. **Phase 1 — COPY** every staged piece to `<name>.new` next to its target
   (this process can't move itself; it runs from `staged`). The big, slow,
   failure-prone work (a ~150 MB copytree under live Defender scanning) happens
   while the installed app is completely untouched — any failure here is a clean
   abort with the old version intact.
3. **Phase 2 — pure RENAMES**: `live → .old`, `.new → live` (instant on the same
   volume). A failure rolls back **with renames too** — never by deleting a
   half-copied tree.

**Why two phases (v0.10.2 field failure):** the old one-phase copy could die
mid-`_internal`, and its delete-based rollback could fail on a Defender-held
file, relaunching a MIXED tree ("says 0.10.2 but features missing").

**Staged allowlist:** the swap installs ONLY the known bundle items
`_BUNDLE_ITEMS = ("TSMIS Exporter.exe", "_internal", "Start Here.txt", "IT-README.txt")` — never
whatever else happens to sit in the staged tree, so a tampered/mis-packaged
extra top-level item can't ride into the install (unexpected items are logged
and ignored). User data (`data\`, `output\`, `input\`) is never in the staged
tree and is never touched.

A rolled-back update **announces itself** when the update is re-offered:
`last_swap_failure()` reads the tail of `update_helper.log` (only the LAST helper
run counts). The swap relaunches the app via `_relaunch()` and a last-resort
`MessageBoxW` on failure (the app is closed by then).

### Revert to the previous version (Settings ▸ Debugging)

`resolve_previous_release()` finds the newest FULL release strictly OLDER than
this build: it lists `/releases` (NOT `/latest`, which never returns older tags),
ignores drafts/prereleases, and picks by **VERSION NUMBER, not GitHub's list
order** (that ordering bug once broke the dev channel). It **variant-skips** a
release missing this variant's zip (a very old release may predate the
with-browser variant) rather than failing with the forward-update message.
Reinstalls through the SAME SHA-verified download → stage → swap pipeline
(`gui_api.revert_to_previous` → `UpdateWorker("revert")`; the pill / restart
dialog read "Reverting…" / "Restart to revert"). Gated to a writable install
(`update_support()=="ok"` — hidden on dev/read-only) and REFUSED while a forward
update is `staged` (it would clobber the staged download). Locked by
`build/check_updater.py` (`test_resolve_previous_release`).

### `_clear_webview_caches()`

Runs in `cleanup_leftovers()` on every launch. Drops the WebView2 HTTP caches
(`Cache`/`Code Cache`/`GPUCache`/`Service Worker` under `data\webview2`) but
NEVER Local Storage (the theme choice lives there). The persistent profile could
otherwise serve a cached `app.js`/`index.html` after an update — a just-updated
app showing the OLD interface under the NEW version number (v0.10.2 field
report: "says 0.10.2 but features missing"). The caches only ever hold the app's
own three UI files, so clearing every launch is cheap and kills the staleness
class (manual zip-overwrite installs included).

### `safe_release_url()`

The release page URL comes from the GitHub API's `html_url` — external data over
TLS, but a forged/MITM'd response could put an arbitrary scheme/host there, and
`webbrowser.open()` on a non-https value (`file:`, `javascript:`, a custom
handler) could launch something unexpected. `safe_release_url` returns the URL
only when it is an `https://github.com/<this repo>/…` link, else falls back to
the hardcoded releases page (which lands on the same place since updates only
target the latest release).

---

## Releasing — push a `v*` tag

Bump `version.py` first; nothing is published if any gate fails.

```
git push origin refs/tags/v0.14.2
```

> **GOTCHA — tag/branch name collision:** the working convention names release
> branches the same as the tag (e.g. branch `v0.10.0` + tag `v0.10.0`). A plain
> `git push origin v0.10.0` is ambiguous — push the tag explicitly with
> `git push origin refs/tags/v0.10.0`.

`.github/workflows/release.yml` (on `push: tags: ["v*"]`, or
`workflow_dispatch` with a `tag` input that creates the tag) on
`windows-latest`:

1. **Verify the tag matches `version.py`** — reads `__version__`, asserts
   `TAG == "v<version>"`, fails otherwise ("Bump version.py or fix the tag").
   This is the single-source-of-truth assertion.
2. **Two self-test gates** — `build.ps1 -SelfTest` (system browser) and
   `build.ps1 -SelfTest -BundleChromium` (bundled Chromium). Each builds AND runs
   the frozen smoke test over the pruned bundle; a broken bundle can't ship.
3. **Build + zip three variants** — `build.ps1` then `Compress-Archive` for
   `win64`; `build.ps1 -BundleChromium` then `Compress-Archive` for
   `win64-with-browser`; `git archive` for `batch-source`.
3b. **Code signing (SignPath, gated, inert by default)** — upload the app zip and
   submit it to SignPath, overwriting it with the signed artifact *before*
   checksums so they cover the signed file. Runs only when the repo variable
   `SIGNPATH_ENABLED=true` and `SIGNPATH_API_TOKEN`/`SIGNPATH_ORG_ID` + policy are
   set (post-approval); otherwise skipped. See [it-and-security.md §7](it-and-security.md).
4. **Publish SHA-256 checksums** — one `<asset>.sha256` per zip (sha256sum
   format `"<hash>  <name>"`, ASCII = no BOM, since a BOM would corrupt the
   hash). These are what the updater verifies against.
5. **Assemble per-version notes** — `gen_release_notes.py "$TAG" -o notes.md`
   joins the shared `build/release_notes_header.md` (download table) with the
   matching `## <tag>` section from `CHANGELOG.md`. Runs *before* the build so a
   missing CHANGELOG section fails fast; each release shows only its own version,
   not the whole history.
6. **Create the GitHub release** with all six assets (3 zips + 3 `.sha256`),
   `--target ${{ github.sha }}`, body from `notes.md`. (Backfill old releases to
   this format with `build/backfill_release_notes.ps1`.)

Uses `actions/checkout@v5` + `actions/setup-python@v6` (the older v4/v5 warned on
the June 16, 2026 GitHub-runner Node-24 switch).

---

## Website (`gh-pages`)

The marketing/landing page is a separate concern on the `gh-pages` branch, with its
own regeneration tooling (`tools/screenshots.py`). Full detail: [website.md](website.md).

---

## CI: `checks.yml` — golden regression gate

`.github/workflows/checks.yml` runs on every push/PR (separate from the release
gate). Blocking steps: byte-compile all sources (`compileall scripts build
version.py`), then the pure-Python golden guards:

- Export-engine: `check_export_engine.py`
- GUI bridge: `check_gui_bridge.py`, `check_a2_compare_filter.py`,
  `check_b1_pause.py`, `check_b2_autoconsolidate.py`, `check_b3_batch.py`,
  `check_report_library.py`
- Updater: `check_updater.py`
- Fake-site selectors: `check_fake_site.py` (drives a real headless Chromium over
  DOM fixtures; Chromium install is `continue-on-error`, falls back to system
  Edge)
- Comparison engine + consolidators: `check_compare_blankkey`, `_keyfield`,
  `_skipwarn`, `_injection`, `_coercion`, `_limits`, `_audit`, `_ramp_detail`,
  `_ramp_summary`, `_dupmatch`, `_ditto`, `check_ramp_summary_partial`,
  `check_tsn_description_leak`, `check_tsmis_pdf_parse`,
  `check_highway_log_columns`, `check_highway_log_ditto`,
  `check_highway_log_roadbed`, `check_a1_filenames`

Advisory (never block): `ruff check --select E9,F63,F7,F82`, `bandit -lll -iii`,
`pip-audit`. Full check list + how to run them locally → [verification-and-testing.md](verification-and-testing.md).

> **GOTCHA — cp1252 stdout reds CI:** the regression checks print Unicode (e.g.
> the ` ≠ ` diff marker). The Windows runner's default cp1252 stdout CRASHES on
> it. `checks.yml` sets job-level `PYTHONIOENCODING: utf-8`, AND any golden check
> that prints non-ASCII must `sys.stdout.reconfigure(encoding="utf-8")` itself —
> running locally with `PYTHONIOENCODING=utf-8` set HIDES the bug (this exact
> failure hit `check_compare_ditto.py` post-v0.14.0, fixed in `a49534f`).

The value/formula comparison flavors are additionally COM-recalc-verified on real
data outside CI (needs Excel) — see [comparison-engine.md](comparison-engine.md)
and [verification-and-testing.md](verification-and-testing.md).
