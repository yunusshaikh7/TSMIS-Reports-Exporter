# Self-Updater Internals

Scope: the code-level walkthrough of the GUI's one-click self-updater — `scripts/updater.py` end to end (check → download/stage → swap-mode reinstall → cleanup), the `gui_main.py` swap-mode branch, the GUI wiring in `gui_api.py`/`gui_worker.py`, and the `release.yml` publish side the updater trusts. Deepens [../build-and-release.md](../build-and-release.md) (the scannable what/why owner). Read that first for the high-level table of phases; this doc is the "how it actually works, line by line" companion you need before touching the swap.

> All anchors are `file:symbol` or `file:Lnn` against the repo at the time of writing. Every constant/identifier below is exact.

---

## 0. The actors and where state lives

| Piece | File | Role |
|---|---|---|
| `updater.py` | `scripts/updater.py` | Console-free core. Raises `UpdateError` (UI-neutral message), logs every decision to `tsmis.update`. |
| `UpdateWorker` | `gui_worker.py:1354` | Worker thread that drives `check` / `download` / `revert`. Posts `("update_status", dict)` to the GUI queue. |
| `GuiApi` update methods | `gui_api.py` | `check_updates`, `update_start`, `update_apply`, `open_release_page`, `revert_to_previous`, `_on_update_status`, `_start_update_check`. Own the `self._update` snapshot. |
| swap-mode branch | `gui_main.py:main` (L74–76) | Branches into `updater.run_swap_mode` **before any heavy init** when `--apply-update` is in argv. |
| `release.yml` | `.github/workflows/release.yml` | Publishes the 3 zips + 3 `<asset>.sha256` the updater downloads and verifies. |

**The single in-process state is `GuiApi._update`** — a plain dict whose `phase` drives the title-bar pill. Phases (from the `_on_update_status` docstring at `gui_api.py:151–154`):
`idle | checking | none | available | downloading | staged | applying | failed`.
The matching `UpdateInfo` object is held Python-side in `GuiApi._update_info` (never serialized to JS — it carries the asset URL).

**Updater logger:** `log = logging.getLogger("tsmis.update")` (`updater.py:67`). The swap process is the exception: it runs before logging is set up and writes by **direct file appends** to `update_helper.log` via `_swap_log` (see §6).

**Constants worth pinning (`updater.py:69–83, 446–449`):**

```
GITHUB_REPO   = "yunusshaikh7/TSMIS-Reports-Exporter"
RELEASES_PAGE = https://github.com/<repo>/releases/latest
_API_LATEST   = https://api.github.com/repos/<repo>/releases/latest
_API_RELEASES = https://api.github.com/repos/<repo>/releases?per_page=100
_EXE_NAME     = APP_NAME + ".exe"          # "TSMIS Exporter.exe"
_BUNDLE_ITEMS = (_EXE_NAME, "_internal", "Start Here.txt")   # the swap allowlist
_CHUNK        = 256 * 1024                  # stream read size
_API_TIMEOUT_S = 20      _DL_TIMEOUT_S = 60 # socket read timeout while streaming
SWAP_FLAG     = "--apply-update"
_SWAP_TIMEOUT_S = 120    # max wait for the old PID to exit
_RETRY_ATTEMPTS = 12     _RETRY_DELAY_S = 0.5  # Defender/slow-handle retry cadence
```

> **`GITHUB_REPO` is the single source of truth.** `GITHUB_REPO = "yunusshaikh7/TSMIS-Reports-Exporter"` (`updater.py:69`) drives both the GitHub API calls and `safe_release_url`'s host allowlist. The docs all use this same owner; if the repo ever moves, this one line is the place to change for both the API and the URL gate.

---

## 1. `update_support()` — the capability gate (every path checks it)

`updater.py:update_support()` returns `(verdict, reason)`:

| Verdict | Condition | Meaning |
|---|---|---|
| `"off"` | `not is_frozen()` | Dev/console run — no bundle to replace. |
| `"link"` | frozen **but** `DATA_ROOT != install_dir()` | App folder is read-only; `paths.py` redirected data to `%LOCALAPPDATA%`. Can only point at the release page. |
| `"ok"` | frozen **and** `DATA_ROOT == install_dir()` | Writable onefolder install — full one-click update. |

`install_dir()` = `Path(sys.executable).resolve().parent` (`updater.py:105`). `DATA_ROOT` is resolved once at `paths.py` import (`paths.py:_resolve_data_root`): frozen → exe dir if `_writable`, else `%LOCALAPPDATA%\TSMIS Exporter`. **So the entire "link" tier is decided by whether the exe folder passed `paths._writable`'s probe-file test at startup.** This is the only thing that distinguishes a normal install from a read-only one for update purposes.

`download_and_stage` and `apply_update_and_restart` both re-assert `update_support()=="ok"` and raise `UpdateError` otherwise (`updater.py:340–342, 460–462`) — defense in depth, since the GUI already gates.

---

## 2. `check_for_update()` — is there a newer release?

Entry: `check_for_update(current_version=None, variant=None)` (`updater.py:185`). The two args exist only for tests; defaults are this build.

Flow:
1. `cur = parse_version(current_version or __version__)`. `parse_version` (`updater.py:157`) matches `v?(\d+(?:\.\d+)*)$` → tuple of ints, or `None` if unparseable.
2. `want = variant or current_variant()`. `current_variant()` (`updater.py:125`) returns `"win64-with-browser"` iff `install_dir()/_internal/ms-playwright` is a dir, else `"win64"` — **the same probe `paths.py` uses** for `BUNDLED_BROWSERS_DIR` (`paths.py:235`). This is what makes a with-browser install download the with-browser zip.
3. `_http_get(_API_LATEST, _API_TIMEOUT_S)` → `json.load`.
4. Error handling:
   - `HTTPError` **404** → `return None` ("repo exists but has no releases yet") — not an error.
   - Any other `HTTPError` → `UpdateError("...HTTP {code}")`.
   - `(OSError, ValueError)` (covers `URLError`/SSL/timeout/bad JSON) → `UpdateError("could not reach github.com…")`.
5. Parse `tag_name`; if `parse_version` returns `None`, log + `return None` (unrecognized tag, not a hard error).
6. `is_newer(remote, cur)` (`updater.py:165`) → zero-pads both tuples to equal length, compares numerically (so `0.10.10 > 0.10.4`). Not newer → `return None`.
7. `_asset_info_from_release(data, remote, tag, want)` → `UpdateInfo`.

### `_http_get` — the TLS contract (do not change)

`updater.py:_http_get` (L174):

```python
return urllib.request.urlopen(req, timeout=timeout,
                              context=ssl.create_default_context())
```

`ssl.create_default_context()` trusts the **Windows certificate store**, so corporate TLS-inspection roots keep working where a bundled CA list (certifi) would reject the handshake; `urllib` also picks up the system proxy from the registry. The `User-Agent` is `"<App-Name>/<ver> (self-update)"` and `Accept: application/vnd.github+json`. The repo is public → no token. **This is load-bearing on locked-down corporate networks — never swap it for `requests`/`certifi`.**

### `_asset_info_from_release` — pick the variant's zip + its checksum

`updater.py:223`. Shared by both the latest-update check and the revert resolver so they select assets identically.

1. `suffix = f"-{want}.zip"`; find the first asset whose `name` ends with it. **None → `UpdateError`** "version {tag} is out, but its download package isn't available yet" (the variant's zip isn't published).
2. Companion checksum: look for an asset named exactly `<zip>.sha256`; carry its `browser_download_url` into `UpdateInfo.asset_sha256_url`.
3. Returns `UpdateInfo(version, tag, asset_name, asset_url, asset_size, release_url=html_url or RELEASES_PAGE, asset_digest=asset["digest"], asset_sha256_url)`.

`UpdateInfo` (`updater.py:90`) is the contract carried through the rest of the pipeline. `asset_size` defaults to `0` if the API omits it (matters for the disk-space and completeness checks below).

---

## 3. `download_and_stage()` — the heavy step (worker thread)

`updater.py:336`. Returns the path to the staged tree (`UPDATE_DIR/staged`). `UPDATE_DIR = _PRIVATE/update` = `data\update` frozen (`paths.py:210`). `on_progress(done_bytes, total_bytes)` is called as the stream advances.

Numbered flow:

1. **Capability re-check** — `update_support()!="ok"` → `UpdateError`.
2. **Fresh staging area** — if `UPDATE_DIR` exists, `shutil.rmtree`; a failure (something has a handle open) → `UpdateError("could not clear the update folder…")`. Then `mkdir(parents=True)`. *Invariant: two versions' files never mix.*
3. **Disk-space guard** — only when `asset_size` known: `need = asset_size * 3` (zip + extracted tree + headroom); compares to `shutil.disk_usage(UPDATE_DIR).free`. Short → `UpdateError` naming the MB needed/available.
4. **Stream the zip** — open `zip_path = UPDATE_DIR/(asset_name or "update.zip")`, loop `resp.read(_CHUNK)`:
   - write chunk to disk,
   - `hasher.update(chunk)` (running SHA-256),
   - `done += len(chunk)`, fire `on_progress(done, total)` where `total = asset_size or Content-Length`.
   `OSError` mid-stream → `UpdateError("the update download failed…")`.
5. **Completeness** — if `asset_size` known and `done != asset_size` → `UpdateError` "incomplete".
6. **SHA-256 verify** (see §3.1) — mismatch deletes the zip and raises; no checksum → warn + proceed on size only.
7. **Extract** — `zipfile.ZipFile(zip_path).extractall(extract_dir)`; `BadZipFile`/`OSError` → `UpdateError("not a valid app package")`. **Then `zip_path.unlink()` immediately** — frees ~150 MB before the app keeps running.
8. **Locate + rename the bundle root** — `_bundle_root(extract_dir)` (§3.2), then `root.rename(staged)` (instant — same volume). Clean up `extract_dir` if it wasn't the root itself.
9. **Sanity assert** — `staged/_EXE_NAME` is a file AND `staged/_internal` is a dir, else `UpdateError("missing expected app files")`.
10. `return staged`.

> **⚠ Known field issue — the stage rename has NO Defender retry (unlike the swap step).**
> Step 8's `root.rename(staged)` (`updater.py:416`) is a **bare** directory rename. If
> Windows Defender / the Search indexer is still scanning the freshly-extracted
> `data\update\extract\TSMIS Exporter` tree, the rename fails with
> **`PermissionError: [WinError 5] Access is denied`** and `download_and_stage` aborts →
> the GUI shows "Update problem" and `cleanup_leftovers` drops the staged download, so the
> user just **re-downloads and it works** (the scan has finished by then). This is
> **asymmetric with `perform_swap`** (§6), whose every file op is wrapped in `_retry`
> (`_RETRY_ATTEMPTS=12 × _RETRY_DELAY_S=0.5 s`, commented *"Defender / slow handle
> release"*) — the swap was hardened against held files; the stage step was not.
> **Observed twice on the work PC** (2026-06-17 ~09:20 and 2026-06-18 ~09:39, both in the
> morning; both self-healed on a re-download — every *swap* that actually started has
> always succeeded). **Fix:** wrap `root.rename(staged)` + the follow-on
> `rmtree(extract_dir)` in the same `_retry`, or `extractall` straight into `staged` and
> skip the intermediate rename. Tracked in [../roadmap.md](../roadmap.md).

### 3.1 `_expected_sha256` — where the trust comes from

`updater.py:310`. Returns lowercase-hex SHA-256 or `None`:

1. **Prefer the companion `<asset>.sha256`** (`asset_sha256_url`): fetch up to 4096 bytes over the same TLS, take the first whitespace token, accept iff it fully matches `[0-9a-f]{64}` (handles the `sha256sum` format `"<hash>  <name>"`). Unrecognized content or fetch error → warn, fall through.
2. **Fallback: GitHub API's own `digest`** (`asset_digest`, format `"sha256:HEX"`): strip the prefix, accept iff 64 hex chars.
3. Neither → `None`.

Back in `download_and_stage` (L390–402): `actual = hasher.hexdigest()`; `expected = _expected_sha256(info)`.
- `expected` present and `actual != expected` → `zip_path.unlink(missing_ok=True)` + `UpdateError("didn't match its published checksum…")`. **Refuses to extract or swap unverified bytes.**
- `expected` present and matches → log "SHA-256 verified".
- **`expected` is `None` → log a warning and proceed on size only** (the *size-only fallback*; see GOTCHAS). This is what happens if the `.sha256` companion is missing/unreadable *and* the API omits `digest`.

> **Scope of the guard (stated in the docstring):** the checksum arrives over the *same* TLS as the rest of the check, so it protects against a corrupted / truncated / wrong-asset download — **NOT a forged release**. A forged release would carry a matching forged checksum. Code-signing is the planned complete fix.

### 3.2 `_bundle_root` — the `Compress-Archive` wrapper

`updater.py:426`. `release.yml` zips with `Compress-Archive -Path "dist\TSMIS Exporter"`, which wraps the bundle in one top-level `TSMIS Exporter\` folder. So:
- if `extract_dir/_EXE_NAME` exists → root is `extract_dir` itself (defensive — handles a flat zip),
- else scan immediate children for the first dir containing `_EXE_NAME`,
- none → `UpdateError("does not contain the app")`.

### 3.3 No Mark-of-the-Web — why this path is immune to the CLR failure

The CLR-blocking MOTW field failure (`gui_main._unblock_dotnet_assemblies` exists to undo it on a manually-downloaded zip) **cannot happen on this path**: browsers add the NTFS `Zone.Identifier` stream; raw `out.write(chunk)` and `zipfile.extractall` do not. The in-app download writes raw bytes, so the extracted `.NET` assemblies are never tagged. (See `gui_main.py:_unblock_dotnet_assemblies` for the manual-install side this avoids.)

---

## 4. `apply_update_and_restart()` — launch the staged exe in swap mode

`updater.py:452`. Called from `GuiApi.update_apply` after the user clicks **Restart to update**, with the **window-close gated on no task running** (`gui_api.py:957`). Returns the swap exe path.

Flow:
1. Re-assert `update_support()=="ok"`.
2. Verify `staged/_EXE_NAME` still on disk → else `UpdateError("no longer on disk — download it again")`.
3. Build the command line:
   ```python
   [str(new_exe), SWAP_FLAG, str(install_dir()), str(os.getpid()), str(helper_log)]
   ```
   `helper_log = LOG_DIR/update_helper.log`. `new_exe` is the **staged** exe (a complete copy of the new app) — it applies itself.
4. `subprocess.Popen(..., creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP, close_fds=True, cwd=staged, stdin/out/err=DEVNULL)`. Detached, no console window. `OSError` (a policy blocks running it) → `UpdateError("the update process could not be started — install manually")`.
5. **The ~1.5 s death check** — `time.sleep(1.5); rc = proc.poll()`. If the swap process already exited, raise `UpdateError("exited before it could start — install manually")`. **This is the key fix for the old silent-failure mode:** a blocked/broken exe is caught *while the app is still open on the old version* instead of closing the app into a swap that never happens.

After this returns, `GuiApi.update_apply` spawns `_close_for_update` (`gui_api.py:979`): `sleep(1.2)` to flush the goodbye log line, then `self._window.destroy()` (returns from `webview.start()`, process exits) — falling back to `os._exit(0)` if destroy throws, so the helper can always proceed.

**The control-flow handoff:** the old app is *still running* when the swap exe launches; the swap process's very first action is to wait on the old PID. That ordering is what makes PID-recycle safety work (§6.1).

---

## 5. `gui_main.py` — the swap-mode branch (runs FIRST)

`gui_main.py:main` (L67) — the very first thing, before logging/paths/CLR:

```python
import updater
if updater.SWAP_FLAG in sys.argv:
    updater.run_swap_mode(sys.argv)   # never returns
```

**Why first, before `setup_logging`/paths/CLR (the single most important "why" in this subsystem):** this process is the **staged** exe, running from `install\data\update\staged\`. `paths.py` resolves `DATA_ROOT`/`LOG_DIR`/etc. relative to `Path(sys.executable).parent` — which here is the *staged* tree, **not the install**. If normal path setup ran, every path (logs especially) would aim at the wrong (staged) tree, which the swap is about to delete. So swap mode takes **explicit paths from argv** and logs by direct file appends. It also never creates a window, so the CLR/WebView2 must not load. The branch sits above `setup_logging`, `_unblock_dotnet_assemblies`, `cleanup_leftovers`, and the `gui_api` import — none of those run in swap mode.

`run_swap_mode(argv)` (`updater.py:500`):
1. Parse `i = argv.index(SWAP_FLAG)`; `app_dir = argv[i+1]`, `pid = int(argv[i+2])`, `log_file = argv[i+3]`. Bad argv → `os._exit(2)`.
2. `staged = Path(sys.executable).resolve().parent` (this exe's own tree).
3. `ok = perform_swap(staged, app_dir, pid, log_file)`; `os._exit(0 if ok else 1)`. **Always `os._exit`** — never a normal return, so no atexit/teardown runs in this stripped process.

---

## 6. `perform_swap()` — the two-phase install

`updater.py:576`. Signature: `perform_swap(staged, app_dir, pid, log_file, *, relaunch=True, wait_timeout_s=_SWAP_TIMEOUT_S, show_dialog=True)`. The keyword args let `check_updater.py` drive it against fake trees with `relaunch=False, show_dialog=False`. Returns `True` only when the new version is in place.

Top-level sequence:

```
1. _swap_log "waiting for pid …"
2. _wait_pid_exit(pid, wait_timeout_s)        # False on timeout -> "update NOT applied", return False
3. sleep(0.6)                                  # let handles settle
4. assert staged/_EXE_NAME exists              # else "staged update incomplete", return False
5. PHASE 1: copy each allowlisted item -> <name>.new        (old app untouched)
6. PHASE 2: rename live->.old, .new->live, per item         (rollback = renames)
7. if relaunch: _relaunch(app_dir, log_file)
8. _swap_log "swap done"/"swap failed"; return (failed is None)
```

### 6.1 `_wait_pid_exit` — PID-recycle safety

`updater.py:528`. ctypes only (no psutil in the bundle):

```python
handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
if not handle: return True                    # already gone (or recycled)
rc = kernel32.WaitForSingleObject(handle, timeout_s*1000)
return rc != WAIT_TIMEOUT
```

The safety argument (docstring L535–543): `apply_update_and_restart` launches the swap process **while the app is still alive** (it stays up ~1.5 s+ after the launch), and `OpenProcess` here is the swap's *very first* action — so the handle is taken against the *live original* process. **A held process handle keeps the kernel process object (and thus the PID) reserved until the handle is closed**, so the PID can't be recycled out from under the wait. If `OpenProcess` instead *fails*, the original already exited → returning `True` to proceed is correct. The only residual case (swap exe so slow to start that the app exits AND the PID is reused by a live process before `OpenProcess`) merely lets the wait time out → reports "not applied", old version intact, logged — **fail-safe, never a half-swap.**

### 6.2 Phase 1 — COPY to `*.new` (the slow, abortable part)

`updater.py:610–648`. The **allowlist** is enforced here:

```python
present = {p.name for p in staged.iterdir()}
extra = sorted(present - set(_BUNDLE_ITEMS))   # logged + ignored
items = [staged/name for name in _BUNDLE_ITEMS if (staged/name).exists()]
```

For each item: `_retry(_remove_tree(new))` then `copytree` (dir) / `copy2` (file) into `app_dir/(name + ".new")`, appending `(name, new)` to `news`. **On any `OSError`:** undo every `.new` already made, log "nothing was changed — the installed version is untouched; update NOT applied", optional `_message_box`, optional `_relaunch`, `return False`.

The heavy ~150 MB `copytree` of `_internal` under live Defender scanning happens **here, while the installed app is completely untouched** — so a failure is a clean abort.

> **Allowlist is a security boundary**, not just hygiene: only `_BUNDLE_ITEMS` are ever copied into the install. A tampered or mis-packaged extra top-level item in the staged tree (e.g. an injected `evil.dll`) is logged and dropped, never installed. `check_updater.py:test_staged_allowlist` plants `evil.dll` and asserts it does not appear in the install and that user `data/` is untouched.

### 6.3 Phase 2 — pure RENAMES (instant; rollback = renames)

`updater.py:650–667`. For each `(name, new)`:

```python
dest = app_dir/name;  bak = app_dir/(name + ".old")
if bak.exists(): _retry(_remove_tree(bak))
if dest.exists(): _retry(dest.rename(bak)); moved.append((dest, bak))
_retry(new.rename(dest))
```

Renames on the same volume are atomic-ish and instant. First `OSError` sets `failed` and **breaks** (stops touching anything further).

**Rollback (L669–689)** runs only if `failed`, and is renames-only:

```python
for dest, bak in reversed(moved):
    if dest.exists(): dest.rename(dest.name + ".new")   # newly-installed piece back to .new
    bak.rename(dest)                                     # .old back into place
```

If every rollback rename succeeds → "previous version restored"; if any fails → "previous version PARTIALLY restored — reinstall from the releases page". On failure `_message_box` shows the user (the app is closed by now).

**Why two phases (the v0.10.2 field failure):** the old one-phase copy wrote directly over `_internal`. A failure mid-`_internal` left a partial tree, and the delete-based rollback could fail on a Defender-held file — so the app relaunched as a NEW exe with PARTIAL/old internals ("says 0.10.2 but features missing"). Phase 2 never *deletes* a fresh tree to roll back; it only renames, so a half-state is impossible.

### 6.4 `_retry` — the Defender cadence

`updater.py:558`. Runs `fn` up to `_RETRY_ATTEMPTS` (12) times, `sleep(_RETRY_DELAY_S=0.5)` on each `OSError`, and **lets the last attempt's error surface**. Wraps every filesystem op in both phases — Defender and slow handle release can briefly hold a file right after the app exits.

### 6.5 `_relaunch` and the leftover cleanup contract

`_relaunch(app_dir, log_file)` (`updater.py:701`) `Popen`s `app_dir/_EXE_NAME` detached. Note it launches **whatever version now sits at `app_dir`** — the new exe on success, the restored old one on rollback.

**The `.old`/`.new` pieces and the staged tree are NOT cleaned up by `perform_swap`.** It can't: it is *running from* `staged`, and on success the live `_internal.old` may still be Defender-held. They're removed by `cleanup_leftovers()` at the relaunched app's next startup (§7), after this process exits and releases its own files.

### 6.6 `last_swap_failure` — surfacing a rolled-back update

`updater.py:724`. Reads the tail (last 60 lines) of `update_helper.log`, ignoring it if older than `max_age_hours=48`. Walks **backwards**: a `"swap done"` line → `return None` (a later success makes earlier failures history); a `"swap FAILED"` or `"update NOT applied"` → return that line. `GuiApi._on_update_status` calls it when an update is re-offered (`gui_api.py:745`) and, if non-None, emits a "the previous update attempt could not be applied" heads-up — closing the field-report loop where an update "applied" but the app reopened on the old version with no explanation.

---

## 7. `cleanup_leftovers()` + `_clear_webview_caches()` — every launch, before the CLR

`gui_main.py:main` calls `updater.cleanup_leftovers()` right after `_unblock_dotnet_assemblies`, before `import gui_api` (L88–90), wrapped so any exception is logged-not-fatal.

`cleanup_leftovers()` (`updater.py:780`):
1. **Always** calls `_clear_webview_caches()` first (runs even in dev).
2. If `not is_frozen()` → return (nothing else to clean in dev).
3. Targets = `[UPDATE_DIR]` + every `install_dir()/(name+suffix)` for `name in _BUNDLE_ITEMS`, `suffix in (".old", ".new")`. Removes each (rmtree dir / unlink file); failures are logged "will retry next launch" — **never raises**. Deliberately removes a **staged-but-never-applied download** so an abandoned stale version is re-offered fresh rather than silently applied later.

`_clear_webview_caches()` (`updater.py:751`): under `WEBVIEW_PROFILE_DIR` (`data\webview2`), globs and rmtrees `Cache`/`Code Cache`/`GPUCache`/`Service Worker` (plus `*/`, `*/*/` nestings) — **never Local Storage** (the theme choice lives there). Rationale: the persistent WebView2 profile could serve a *cached* `app.js`/`index.html` after the on-disk files changed, so a just-updated app would show the OLD UI under the NEW version number. The cache only ever holds the app's own three UI files, so clearing it every launch is cheap and kills the whole staleness class (manual zip-overwrite installs included). Wrapped in a bare `except Exception` — a cache-clear failure must never block startup.

---

## 8. Revert — `resolve_previous_release()`

`updater.py:253`. Powers Settings ▸ Debugging "revert to previous version". Returns an `UpdateInfo` for the **newest FULL release strictly OLDER** than this build, for the current variant; `None` when there's nothing to revert to.

Algorithm:
1. `cur = parse_version(...)`; `None` → return `None`.
2. `_http_get(_API_RELEASES)` — the **list** endpoint (`/releases?per_page=100`), *not* `/latest` (which never returns older tags). 404 → `None`; other errors → `UpdateError`. Non-list body → `None`.
3. Build `candidates`: for each release dict, **skip drafts and prereleases**, parse the tag, keep only `ver` strictly `< cur` (`is_newer(cur, ver)`).
4. `sorted(candidates, key=lambda c: c[0], reverse=True)` — **by version tuple, newest-first; NOT GitHub's list order.** (That list-order bug once broke the dev channel; selection must be by version number.)
5. For each candidate newest-first, try `_asset_info_from_release(rel, ver, tag, want)`. **Variant-skip:** if it raises `UpdateError` (this older release predates the with-browser variant and lacks that zip), log + `continue` to the next-older — *don't* fail with the forward check's "try again later" (wrong message here; that release never had the variant). First success is the revert target.
6. No candidate has the variant → `None`.

`check_updater.py:test_resolve_previous_release` proves all four behaviors: version-not-list-order selection, draft/prerelease exclusion, variant-skip to the next-older release, and `None` when nothing is older.

### Revert wiring (`gui_api.py:revert_to_previous`, L998)

- Refuse unless `update_support()=="ok"` (hidden on dev/read-only).
- Refuse while a `checking`/`downloading`/`applying` is in progress.
- **Refuse while a forward update is `staged`** — reverting would clobber the staged download.
- Otherwise set `self._update = {"phase":"downloading","revert":True}` and start `UpdateWorker(action="revert")`.

`UpdateWorker.run` for `revert` (`gui_worker.py:1393`): calls `resolve_previous_release()`; `None` → posts `phase:"none", revert:True`; else feeds the resolved `UpdateInfo` through **the exact same `download_and_stage`** path as a forward update. So the riskiest code (verify/stage/swap) is unchanged between update and revert — only the *resolution* differs. The pill/dialog text switches to "Reverting…"/"Restart to revert" off the `revert` flag.

---

## 9. `safe_release_url()` — the URL allowlist for the "link"/read-only path

`updater.py:133`. `UpdateInfo.release_url` is the API's `html_url` — external data delivered over TLS, but a forged/MITM'd response could put an arbitrary scheme/host there, and `webbrowser.open()` on a `file:`/`javascript:`/custom-handler value could launch something unexpected. The function returns `url` **only** when `urlsplit` yields `scheme=="https"` AND `hostname.lower()=="github.com"` AND `path.lstrip("/").lower()` starts with `GITHUB_REPO.lower()+"/"`; otherwise it falls back to the hardcoded `RELEASES_PAGE` (which lands on the same place, since updates only ever target the latest release). `GuiApi.open_release_page` (`gui_api.py:993`) routes through it before `webbrowser.open`. `check_updater.py:test_safe_release_url` covers look-alike hosts (`github.com.evil.test`), the `@`-userinfo trick (`github.com@evil.test`), `http://`, `file:`, `javascript:`, and empty/None.

---

## 10. End-to-end flows (who calls what, in order)

### Forward update (happy path)

```
gui_api.check_updates / _start_update_check (auto at launch or version-chip click)
  -> update_support(): "off"->skip, else continue
  -> UpdateWorker("check") -> updater.check_for_update()
       -> posts phase:"available" (+_info) | "none"
gui_api.update_start (user clicks "Update to vX")
  -> phase:"downloading"; UpdateWorker("download", info)
       -> updater.download_and_stage(info, on_progress)   # SHA-256 verify here
       -> posts phase:"downloading"(pct…) then phase:"staged"
gui_api.update_apply (user clicks "Restart to update"; gated on no task)
  -> updater.apply_update_and_restart(staged)
       -> Popen staged exe --apply-update <install> <pid> <helperlog>
       -> sleep 1.5s; poll() -> UpdateError if dead   (stay on old version)
  -> _close_for_update(): window.destroy() -> process exits
[staged exe, swap mode]
gui_main.main: SWAP_FLAG in argv -> updater.run_swap_mode(argv)   # BEFORE any init
  -> perform_swap(staged, install, pid, helperlog)
       1. _wait_pid_exit(pid)                # old app exits
       2. phase 1 copy -> *.new              # install untouched
       3. phase 2 rename live->.old, .new->live
       4. _relaunch(install)                 # new exe starts
  -> os._exit(0/1)
[relaunched new app]
gui_main.main: cleanup_leftovers()           # removes *.old/*.new + staged + webview cache
```

### Failure branches at a glance

| Where | Trigger | Result |
|---|---|---|
| `check_for_update` | network/SSL/timeout | `UpdateError` → `phase:"failed"` (logged; quiet unless manual) |
| `download_and_stage` | SHA mismatch | zip deleted, `UpdateError`, nothing staged |
| `download_and_stage` | bad zip / disk full / incomplete | `UpdateError`, nothing staged |
| `apply_update_and_restart` | swap exe blocked/dies in 1.5 s | `UpdateError`; **app stays open on old version** |
| `perform_swap` phase 1 | copy `OSError` | abort, delete `.new`, old version intact, relaunch old |
| `perform_swap` phase 2 | rename `OSError` | rename-rollback to old version; `last_swap_failure` reports it next launch |
| `_wait_pid_exit` | old PID never exits in 120 s | "update NOT applied", old version intact |

---

## 11. The publish side the updater trusts (`release.yml`)

The updater's verification only works because of what `.github/workflows/release.yml` guarantees:

1. **Tag == `version.py`** (`release.yml:47–57`) — reads `__version__`, asserts `TAG == "v<version>"`, fails otherwise. So `check_for_update`'s `tag_name` comparison against `__version__` is meaningful.
2. **Two self-test gates** before any zip is built — a broken bundle can't ship the variant the updater will hand to `perform_swap`.
3. **Three zips, exact suffixes** — `*-win64.zip`, `*-win64-with-browser.zip`, `*-batch-source.zip`. `_asset_info_from_release`'s `-{want}.zip` match and `current_variant()` depend on these exact suffixes.
4. **One `<asset>.sha256` per zip** (`release.yml:82–92`): sha256sum format `"<hash>  <name>"`, **`-Encoding ascii` (no BOM — a BOM would corrupt the hash)**. This is exactly what `_expected_sha256` parses (first whitespace token, `[0-9a-f]{64}`).
5. **`gh release create` publishes all six assets** (`release.yml:94–108`) — 3 zips + 3 `.sha256`. If a `.sha256` is ever dropped, the updater silently falls back to the GitHub API `digest`, and if that's absent too, to size-only (the §3.1 fallback chain).

> **Coupling to remember:** `Compress-Archive -Path "dist\TSMIS Exporter"` is what wraps the bundle in one top-level folder, which is exactly what `_bundle_root` unwraps. If the zip layout ever changes (e.g. a different archiver that doesn't wrap), `_bundle_root` must change with it.

---

## 12. Extension points

**Add a new top-level item to the installed bundle** (a sibling file/folder next to the exe that updates should carry, e.g. a new `Read Me.pdf` or a config template):
- Add its name to `_BUNDLE_ITEMS` (`updater.py:80`). That one tuple is the allowlist for **both** `perform_swap` (what gets copied+swapped) **and** `cleanup_leftovers` (which `.old`/`.new` it removes). An item not in the list is logged-and-ignored during a swap and never cleaned up.
- It must actually ship inside the zip's top-level folder (i.e. be in `dist\TSMIS Exporter\`). User data dirs (`data\`, `output\`, `input\`) must **never** be added — they are not in the staged tree and must stay untouched.
- `check_updater.py:_make_tree`/`test_staged_allowlist` assume the three current items; extend the fixture if you change the set.

**Change the release asset naming / variants:** the `-{want}.zip` suffix logic lives only in `_asset_info_from_release`, and the variant probe only in `current_variant()`. Keep both in lockstep with `release.yml`'s zip names.

**Add update state to the UI:** the worker→GUI protocol is a single `("update_status", dict)` message with a `phase` field; add new phases by extending `UpdateWorker.run`'s posts and `gui_api._on_update_status`'s branches. The dict is the GUI's whole update state — keep `_info` out of anything serialized to JS (it's popped in `_on_update_status`, L729).

**A different verification source:** `_expected_sha256` is the single place trust is established; its two-tier (companion `.sha256` → API `digest`) order and the size-only fallback are all here. Code-signing would slot in as a *new* check alongside (not replacing) it.

---

## 13. Gotchas a maintainer will trip on

- **Swap mode must stay the first thing in `gui_main.main`.** Anything that resolves a path via `paths.py` (logging, config, the CLR) before the `SWAP_FLAG` branch would aim at the *staged* tree, not the install. Don't move `import logging_setup`/`setup_logging` above it, and don't let any import at module top trigger `paths.py` work that the swap process shouldn't do.
- **No PowerShell / cmd / scripts / admin / scheduled tasks anywhere in the swap.** This is a hard constraint from locked-down Caltrans PCs (the v0.9.0 PowerShell helper was silently killed → nothing swapped). The design's only requirement is "exes run from user-writable folders". A change that reaches for any of those will silently fail on the work PC. See [../it-and-security.md](../it-and-security.md).
- **Size-only fallback when no checksum.** If both the `.sha256` companion and the API `digest` are absent, `download_and_stage` proceeds verifying *only* byte count (`asset_size`/`Content-Length`). That's by design but it's the weakest mode — make sure `release.yml` keeps publishing the `.sha256` assets.
- **`os._exit` in swap mode.** `run_swap_mode`/`perform_swap` finish with `os._exit` — **no** atexit handlers, no flush of the `tsmis.update` logger (which isn't even set up here). All swap-side logging is the manual `_swap_log` appends; don't expect normal logging to appear in swap mode.
- **Leftovers are cleaned by the *next* app, not the swap.** `perform_swap` cannot delete the `.old` tree (Defender may hold the just-renamed `_internal.old`) or the `staged` tree it runs from. If you add a step expecting them gone immediately, you'll be wrong — they're removed at the relaunched app's `cleanup_leftovers()`.
- **`asset_size == 0` disables two guards.** When the API omits `size`, the disk-space check (`if info.asset_size:`) and the completeness check (`if info.asset_size and done != info.asset_size`) both no-op. The download still verifies via SHA-256 (when available) and via a valid-zip extract, so it's not unguarded — but don't assume `asset_size` is always present.
- **`_clear_webview_caches` runs in dev too** (it's called unconditionally before the `is_frozen()` gate). On a dev run with a `data\webview2` profile it will clear caches — intended, but note it's not frozen-only like the rest of cleanup.
- **The 1.5 s death check is a heuristic, not a guarantee.** A swap exe that dies *after* 1.5 s (e.g. crashes during phase 1) won't be caught by `apply_update_and_restart`; that failure surfaces only via `update_helper.log` + `last_swap_failure` on the next launch. The 1.5 s window only catches *immediate* launch refusals.
