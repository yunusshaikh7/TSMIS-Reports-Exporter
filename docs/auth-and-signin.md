# Auth & Sign-in

What this doc covers: how the app signs into TSMIS — the OAuth-token-in-the-hash session model, the signed-in detector, the layered sign-in strategy (silent device sign-in → Edge recapture → Chrome fallback), portability validation, device sign-in mode, Local Network Access pre-grant, the two title-bar login chips, and token-in-log redaction. This is the single hardest part of the app; every trap here was hit in the field.

Code owners: `scripts/common.py` (the auth/nav helpers), `scripts/login.py` (console headed login), `scripts/gui_worker.py` `LoginWorker` (GUI headed login), `scripts/gui_api.py` (`_login_states`, `_device_ok`).

Related docs: [build-and-release.md](build-and-release.md) (browser channels — which browser gets used and why), [lessons.md](lessons.md) (the managed-Edge field-failure narrative in full), [it-and-security.md](it-and-security.md) (work-PC constraints, support-bundle secrecy), [gui.md](gui.md) (GUI threading/queue model that `LoginWorker` posts into).

> **Code-level walkthrough:** [internals/auth-state-machine.md](internals/auth-state-machine.md) — `navigate_with_auth` as an explicit state machine, the recapture chain, device-mode browser handles, and the concurrency rules.

---

## 1. The session model (why this is hard)

The TSMIS report page is a single-page app. **It never shows a signed-out page.** With no token, `initAuth()` immediately self-redirects into the portal OAuth flow (same tab, `response_type=token`). The access token comes back **in the URL hash** and lives **only in page memory** (~120 min TTL).

Consequences that drive the whole design:

- **A `storage_state` never carries the app session.** Playwright's `storage_state` captures cookies + localStorage, but the app token is in-memory only. Every fresh navigation must re-run the silent OAuth round-trip. The saved auth file (`scripts/tsmis_auth.json`) carries the *Azure/SSO* cookies that let that silent round-trip complete without typing — not the app token itself.
- **`_recover()` re-mints expired tokens mid-run** the same way (a fresh `navigate_with_auth`). Session expiry mid-run otherwise raises `AuthError` and stops cleanly.
- **The portal keeps NO session cookie.** Each round-trip needs a full SAML IdP hop. So recovery is never cheap.
- **Reloading the page destroys the in-memory token.** This is why the wrong-env/src check runs *inside* the sign-in loop (see §3), never after success.
- **The token rides in the URL fragment** for the sub-second between the OAuth redirect committing and the SPA's `history.replaceState` stripping it. It must never reach the screen or a log line — see §8.

The auth file at rest is plaintext JSON (cookies), protected only by NTFS permissions in the user's own app folder. It is git-ignored and **never** added to the support bundle. Windows DPAPI at-rest encryption is a candidate future hardening (noted in `save_auth_state`; see [it-and-security.md](it-and-security.md)).

---

## 2. Signed-in detection (`is_logged_in`, `_SIGNED_IN_JS`)

The page ships its **whole form** (`#customReport` included) in static HTML even when signed out, so form presence proves nothing. The only trustworthy signal is the app's **post-auth UI**:

- Signed in ⟺ ANY of these is visible: `#modeSelector`, `#controlsGrid`, `#generateRow`, `#appForm`, `#versionCtrl`.
  - `setAuthUI(true)` shows `#modeSelector` — immediately for **ARS**; for **SSOR** only after the `TSMIS_HI` group check passes. The later stages show `#controlsGrid`/`#generateRow`/`#appForm`/`#versionCtrl`.
- Definitively **not** signed in ⟺ `#accessDenied` (authenticated but not in the TSMIS group) or `#loginPrompt` is visible.

`is_logged_in(page)` also first checks `_page_host(page) == expected_host()` — wrong host ⇒ not logged in.

**Visibility uses `Element.checkVisibility()`** when the browser has it, falling back to a manual `getComputedStyle(...).display === 'none'` parent walk. The old `offsetParent` trick is **wrong** for fixed-position ancestors — do not regress to it.

`expected_host()` parses the *effective* URL's hostname (honoring a Settings-tab custom URL override), NOT the built-in `TSMIS_HOST`. `_page_host(page)` parses `page.url`'s hostname — **substring checks against `page.url` are wrong**, because the portal's authorize URL carries the app host inside its `redirect_uri` parameter.

Diagnostics: `_AUTH_DIAG_JS` snapshots every signal ("visible/<display>" | "hidden/<display>" | "absent") plus `document.title` and `[CONFIG.env, CONFIG.src]`. `require_signed_in(page, message)` raises `AuthError(message)` after `dump_auth_failure` writes a screenshot + HTML to `FAILURES_DIR` (stem `auth_fail`) and logs the signal snapshot — so a failed gate is diagnosable from one run.

---

## 3. `navigate_with_auth` — the sign-in loop

`navigate_with_auth(page)` opens the page and sees the sign-in through. 60-second budget; every state change is breadcrumbed to the log (`auth: +Ns <msg>`, change-only via the `note()` helper).

Flow:

1. `page.goto(get_url())`. A failure to open at all raises **`SiteUnreachableError`** ("check the network / VPN connection") — a `PreflightError` subclass.
2. Loop until the deadline:
   - **If `is_logged_in(page)`:** if `_site_params_ok(page)` OR we already reloaded for params → `note("signed in")`, break. Otherwise (signed in on the *wrong* data source / env) → set `reloaded_for_params=True`, `page.goto(url)` again, continue. The reload destroys the in-memory token, so the loop must sign in again — the app re-stores our env/src via its own `sessionStorage` handoff (`login()` stashes env/src before the redirect; config.js lets URL params win on reload).
   - Click the app's own (currently unused) signed-out button `Sign In with ArcGIS` if visible.
   - On the **portal sign-in page**: drive the SAML authorize URL *directly* — `page.goto(f"{idp_url}?oauth_state={quote(state_val, safe='')}")` (the state value is URL-encoded via `urllib.parse.quote`) using the `Caltrans Azure AD` button's `data-url` (`idp_url`) and the page's `#oauth_state` input value — with a plain `.click()` as fallback. Capped at 3 IdP drives (`idp_drives < 3`).
   - Breadcrumb when parked off-site (host != `expected_host()`).
   - `page.wait_for_timeout(1000)` per iteration.
3. After the loop: one final `is_logged_in` + a structured log line (`signed_in`, `idp_drives`, `reloaded_for_params`, `elapsed`, redacted `url`). If not signed in, log the signal snapshot.

### The CONFIG lexical-global trap (`_CONFIG_JS`, `_site_params_ok`)

`CONFIG` is a **top-level `const`** in the app's `config.js` — a lexical global, **NOT** a `window` property. It must be read by **bare identifier inside a try/catch**:

```js
() => { try { return [CONFIG.env || null, CONFIG.src || null]; } catch (e) { return null; } }
```

Reading `window.CONFIG` always yields `undefined`. Acting on that once caused **every successful sign-in to be reloaded away** (`_site_params_ok` thought the env was wrong on every page).

`_site_params_ok(page)` returns **True on "unknown"** (CONFIG unreadable, or `got` falsy) — callers must NEVER reload on unknown, because a reload destroys the memory-only token and forces a whole new sign-in. It returns False only when CONFIG reports a concrete env/src that differs from `get_site()`'s `[want_env, want_src]`.

The wrong-env/src reload is allowed **at most once** (`reloaded_for_params`), and only inside the loop — never as a post-success recheck.

---

## 4. The layered sign-in strategy

Both the console flow (`login.py` `_run_login`) and the GUI (`gui_worker.LoginWorker.run`) follow the same order, honoring the user's Browser pick first via `get_preferred_channel()` (the GUI Browser dropdown / `TSMIS_BROWSER_CHANNEL`). See [build-and-release.md](build-and-release.md) for how channels are chosen.

| Order | Path | Code | Notes |
|---|---|---|---|
| 0 | **Explicit Chrome pick** → straight to headed Chrome | `_run_standard_login` | Silent device sign-in is an Edge/Windows integration; Chrome never gets it, so skip it. |
| 1 | **Silent device sign-in** (no window, no typing) | `try_device_sso_login` → `open_edge_device_context` | Tried first when pref is `None`/`msedge`. |
| 2 | **Built-in Chromium** headed sign-in (when present) | `p.chromium.launch(channel="chromium", …)` | Unmanaged → org policy can't relaunch it mid-SSO. |
| 3 | **Persistent-profile Edge recapture** | `_try_edge_persistent_login` → `launch_edge_login_context` + CDP/profile recapture | The original managed-Edge fix (see §5). |
| 4 | **Chrome fallback**, then any `launch_browser`-resolvable browser | `_run_standard_login` | Manual credentials. |

### Silent device sign-in (`try_device_sso_login` / `open_edge_device_context`)

Reopens the app-owned **persistent Edge sign-in profile** (`EDGE_LOGIN_PROFILE_DIR`) headless and clicks "Caltrans Azure AD" (inside `navigate_with_auth`). **The one-click Windows sign-in lives in that profile** — a fresh cookie-free Edge context does NOT get it, and Chrome never does (manual credentials).

- The profile is **primed by the headed Edge login** — first-ever use still needs one headed sign-in.
- Each known profile dir is tried in turn (`_known_edge_profile_names` — `Default` + any `Profile N`; managed Edge may have moved the session into a work profile).
- The profile can be open in **ONE browser at a time** — the classic failure here is "profile already in use." Callers must not hold two of these concurrently.
- `open_edge_device_context` returns `(ctx, page)` with the context left **OPEN**; `ctx.close()` shuts the whole persistent browser down. It raises `AuthError` (listing the profiles tried) when nothing signs in.

### Edge recapture + CDP (`launch_edge_login_context`, `capture_edge_login_state_over_cdp`, `capture_edge_login_state_from_profiles`)

When the silent path doesn't yield a portable session and the user signs in headed via Edge, the session is captured **three ways in order** (managed Edge may abandon Playwright's profile when it switches into a work profile mid-login):

1. **From the live context** — `capture_storage_state_if_logged_in(ctx)` if a still-open page is signed in.
2. **CDP re-attach** — `launch_edge_login_context` enables a `--remote-debugging-port`; if Edge preserves it across the work-profile switch, `capture_edge_login_state_over_cdp` reconnects (`connect_over_cdp`, `is_local=True`, `no_defaults=True`) and reads the state.
3. **Reopen the profile tree headless** — `capture_edge_login_state_from_profiles` relaunches each known persistent profile headless and reads the session off disk.

Full managed-Edge field story (the relaunch-into-work-profile `TargetClosedError`, what did NOT help) → [lessons.md](lessons.md).

### Portability validation — PRT/wia rejection (`storage_state_is_portable`)

**Every Edge capture is validated before saving.** The state is restored into a *fresh headless context* and must actually log in — exactly as the engine will use it.

Managed Edge work profiles can sign in via the **Windows device broker (PRT)**: `amr: ["wia"]`, an `ESTSAUTH` stub with no payload. Such cookies *look* captured but can't log in anywhere else. A capture that fails the round-trip is **rejected** with a clear message, and the flow falls back to another browser instead of saving a dud auth file. The check errs conservatively: any exception ⇒ "NOT portable."

### Chrome fallback & save-only-on-real-login

The auth file is written **only after a real login is detected** (`is_logged_in` on any open page — SSO can land the signed-in page in a popup/new tab, so all pages are checked). On any non-save outcome no file is written, so a prior valid session is preserved.

---

## 5. The managed-Caltrans-Edge resolution (v0.5.0)

Managed Edge relaunches itself into the work profile mid-Azure-AD-login, killing the Playwright window (`TargetClosedError` on `storage_state`). This is Edge's org-managed behavior, zero interaction from us. **Resolved two ways:**

1. **Persistent-profile Edge recapture** (`login.py` / `LoginWorker`) — the three-step capture chain above.
2. **Built-in Chromium** (preferred when present) — unmanaged, so org policy can't touch the sign-in window at all. Ships in the `-with-browser` release variant and is downloaded by the `.bat` setup.

Historical dead-ends (do not re-try without reason): removing mid-login polling, `--edge-skip-compat-layer-relaunch`, and InPrivate did NOT help; v0.4.2's "default sign-in to Chrome" regressed Chrome too and was rolled back. Full narrative → [lessons.md](lessons.md).

---

## 6. Device sign-in mode (no saved file)

If silent sign-in **works but the captured state is device-bound** (not portable), **nothing is saved** and the app enters **device sign-in mode**:

- GUI message `login_device_ok` → `gui_api._device_ok = True`. (Also set to True when an actual run signs itself in via device mode.)
- Exports don't need an auth file — **engines no longer hard-require it.** `new_authed_browser(p)` restores the saved session when one is valid; otherwise it falls into device mode (`open_edge_device_context`), and the persistent context **doubles as the browser handle** (`.close()` shuts it down). `_recover()` re-auths the same way mid-run.
- `has_valid_auth()` logs a notice instead of raising; the `.bat` export menus print a note rather than exiting; the GUI offers to start anyway.

**Device mode caps fast mode to 1 worker.** The Edge profile can only be open in one browser at a time, so real parallelism needs a *saved* login. The GUI greys the Fast-mode checkbox out without one and says why. (Within `new_authed_browser`, `parallel` is moot in device mode — it's single-browser by definition.)

`require_valid_auth()` still validates the file *shape* (exists, valid JSON, `cookies`/`origins` are lists) and backs `has_valid_auth()` / the GUI status dot. On `AuthError` from a run, `cli.py` clears the stale file and guides re-login; the GUI shows a re-login dialog.

---

## 7. Local Network Access pre-grant (`_LNA_ARGS`, `_new_app_context`)

The TSMIS page pulls report data from an **intranet host**. Chromium's Local Network Access checks would block that behind an "allow this site to access devices on your local network?" prompt **no one can answer headless** — and while it sits unanswered the signed-in UI never appears, so a completed login is never detected.

- Every automated context launches with `_LNA_ARGS` (`--disable-features=LocalNetworkAccessChecksWarnings`, `--enable-features=LocalNetworkAccessChecks`) and `_new_app_context` pre-grants `permissions=["local-network-access"]` (falling back without the kwarg for browsers that don't know the name). This covers engine contexts, device sign-in, and the portability probe.
- **The headed sign-in windows need it too** — `LOGIN_BROWSER_ARGS` (= `_LNA_ARGS`) + `new_login_context`, used by `login.py` and `gui_worker.LoginWorker`. Without the grant, Chrome re-prompts on **every** sign-in and the unanswered prompt blocks the signed-in UI, so the login is never detected and no session is saved (field bug, fixed v0.8.0; managed Edge avoided it via enterprise policy, which is why only Chrome showed it). The persistent-profile Edge flow has carried it since v0.5.

---

## 8. Token-in-log redaction (`page_url_for_display`)

The OAuth access token rides in the URL **fragment**. `page_url_for_display(page)` strips the fragment (`urlsplit(page.url)._replace(fragment="").geturl()`) so the token can never reach the screen, a log line, or a failure dump.

- `auth_state(page)` — the diagnostics snapshot feeding both `navigate_with_auth`'s logs and `dump_auth_failure` — takes its `url` through `page_url_for_display`. The Verify-env and Preview modals (`maybe_screenshot`) likewise display the redacted URL.
- **Origin of the fix:** the v0.10.4 audit flagged `AUTH-TOKEN-IN-LOG-BUNDLE` as a candidate P0 — `auth_state()` logged the raw `page.url` and the support bundle zips `tsmis.log*`. Source verification (2026-06-15) downgraded it to ~P2/P3: the SPA `history.replaceState`s the hash away synchronously on load (in the TSMIS site's own `shared.js`, ~line 544 at audit time — **off-repo**, not in this codebase), so success-path logs are clean and only a sub-second failure-dump race could ever leak. The fix is to route every `auth_state`/URL log through `page_url_for_display`, which the current code does. (`AUTH-WRONG-ENV-SILENT-SUCCESS` was likewise downgraded P1→P3: reload reliably lands on the right env because URL params win in config.js and `login()` stashes env/src to sessionStorage before redirect.) Full audit context → [it-and-security.md](it-and-security.md).

---

## 9. The two title-bar login chips (`_login_states`, v0.10.4)

The title bar shows the **two sign-in paths separately** so the user can tell which one is live:

| Chip | Source | States |
|---|---|---|
| **Saved login** | the auth file (`tsmis_auth.json`) | valid / missing; age (hours) in the tooltip. This is what exports *restore* and is **required for fast mode**. |
| **Edge one-click** | the persistent Edge sign-in profile | green = silent device sign-in **proven this session** (`_device_ok`); amber = the Edge sign-in profile **exists but is unproven** (`primed` — the profile dir is non-empty); grey = never set up. |

`gui_api._login_states()` → snapshot key `logins` = `{"file": {"valid", "age_h"}, "device": {"ok", "primed"}}`. **Cheap stat calls only** — the device path is only ever *proven* by an actual sign-in, never probed eagerly (probing it would open the profile and risk the "already in use" failure).

---

## 10. Key symbols quick reference

| Symbol | File | Role |
|---|---|---|
| `navigate_with_auth` | common.py | open page + drive the OAuth/SAML sign-in loop |
| `_CONFIG_JS` / `_site_params_ok` | common.py | read CONFIG by bare identifier; wrong-env detection |
| `_SIGNED_IN_JS` / `is_logged_in` | common.py | post-auth UI signal detection (`checkVisibility`) |
| `try_device_sso_login` / `open_edge_device_context` | common.py | silent device sign-in via persistent Edge profile |
| `launch_edge_login_context` / `capture_edge_login_state_over_cdp` / `capture_edge_login_state_from_profiles` | common.py | headed Edge recapture (live → CDP → disk) |
| `storage_state_is_portable` | common.py | PRT/wia device-bound capture rejection |
| `new_authed_browser` | common.py | engine browser: saved session OR device mode |
| `_LNA_ARGS` / `_new_app_context` / `LOGIN_BROWSER_ARGS` / `new_login_context` | common.py | Local Network Access pre-grant (automated + headed) |
| `page_url_for_display` / `auth_state` / `dump_auth_failure` | common.py | token redaction + failure diagnostics |
| `require_valid_auth` / `has_valid_auth` / `clear_auth` / `save_auth_state` | common.py | auth-file shape validation + lifecycle |
| `_run_login` / `_login_with_browser` | login.py | console headed login |
| `LoginWorker` (`_run_login_in_browser`, `_try_edge_persistent_login`, `_run_standard_login`, `_any_logged_in`) | gui_worker.py | GUI headed login (mirrors the layered order); "no open tabs" = window-closed signal |
| `_login_states` / `_device_ok` | gui_api.py | the two title-bar chips |

**The "no open tabs" rule (`LoginWorker`):** the reliable "user closed the window" signal is that **no tabs remain open** in the context (the SSO flow always keeps ≥1 tab), with a long all-calls-failing streak (`blips >= 20`, ~6 s) as a backstop. It does NOT treat the original page closing, a connection blip, or a single transient `ctx.cookies()` error as "closed" — that caused a false "cancelled" that slammed the window shut the instant a password went through.
