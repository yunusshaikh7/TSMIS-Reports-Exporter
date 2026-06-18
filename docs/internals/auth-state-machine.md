# Auth State Machine — sign-in & recapture internals

Scope: the code-level walkthrough of `navigate_with_auth`'s sign-in loop, the layered headed-login order, the three-step Edge recapture chain, the PRT/wia portability probe, device-mode browser handles, and the concurrency rules — the "how it actually works" companion to [../auth-and-signin.md](../auth-and-signin.md) (read that first for the what/why).

All anchors are `scripts/common.py` unless another file is named. Line numbers are from the read at authoring time; trust the symbol names.

---

## 0. Mental model: three state machines stacked

There are three distinct loops, and confusing them is the #1 maintainer trap:

| Loop | Owner | Drives | Terminates on |
|---|---|---|---|
| **Sign-in loop** | `navigate_with_auth` | the OAuth/SAML round-trip *inside one browser context* | signed-in OR 60 s deadline |
| **Layered-login ladder** | `login.py:_run_login` / `gui_worker.LoginWorker.run` | which *browser/channel* to try for a HEADED capture | a portable state saved, device-mode declared, or all paths exhausted |
| **Capture chain** | `LoginWorker._try_edge_persistent_login` / `login.py:_try_edge_persistent_login` | how to *extract* a state from a managed-Edge sign-in (live → CDP → disk) | first capture that returns truthy |

`navigate_with_auth` is the innermost engine — every other path calls it (engine boot, `_recover`, device-context open, recapture-with-navigate, portability probe). Get it right and everything else is plumbing.

---

## 1. `navigate_with_auth` as an explicit state machine

`navigate_with_auth(page)` (`common.py:449`). Opens `get_url()` and drives the sign-in to completion. No return value — callers re-check with `is_logged_in`/`require_signed_in` afterward.

### 1.1 Setup / the deadline budget

```
url       = get_url()                         # honors thread-pin + custom URL override
page.goto(url)  → on ANY exception: SiteUnreachableError  (network/VPN message)
start     = time.monotonic()
deadline  = start + 60                         # HARD 60 s budget, no setting overrides it
idp_drives = 0                                 # cap counter (see 1.4)
reloaded_for_params = False                    # at-most-one corrective reload (see 1.3)
last_note = None                               # breadcrumb dedupe
```

The `goto` failure path (`common.py:466-474`) is the *only* place `SiteUnreachableError` is raised — it's a `PreflightError` subclass (`common.py:44`), so preflight surfaces it as "check your connection". Note `str(e).splitlines()[0]` truncates Playwright's multi-line error to one line for the log + message.

### 1.2 The `note()` breadcrumb helper (change-only logging)

`note(msg)` (`common.py:481`) logs `auth: +<N>s <msg>` **only when `msg != last_note`**. The loop runs ~once/second; without the dedupe the log would fill with identical "waiting at login.microsoftonline.com" lines. So every distinct state the loop passes through appears exactly once with its elapsed timestamp — the rotating log reconstructs the whole sign-in narrative. When you add a new branch, give it a *distinct* `note()` string or it'll be silently swallowed by the dedupe.

### 1.3 The main loop — branch by branch

`while time.monotonic() < deadline:` (`common.py:487`). Each iteration evaluates these in order:

**STATE A — already signed in** (`common.py:488-500`)
```
if is_logged_in(page):
    if _site_params_ok(page) or reloaded_for_params:
        note("signed in"); break                 # ← SUCCESS exit
    # signed in on WRONG src/env:
    reloaded_for_params = True
    note("signed in on wrong site params; reloading with target URL")
    page.goto(url); continue
```
The whole `is_logged_in` block is wrapped in try/except (`common.py:501-502`) — a transient evaluate error just breadcrumbs `signed-in check error: <Type>` and falls through to the sign-in steps rather than crashing the loop.

**Why the reload is at-most-once and why it's *inside* the loop.** The app's access token lives **only in page memory** (URL hash, ~120 min TTL). `page.goto(url)` destroys it. So the corrective reload for a wrong-env sign-in cannot be a post-success recheck — it would throw away a good session. Instead: detect wrong env *while still in the loop*, set `reloaded_for_params=True`, reload, and let the loop sign in **again** from scratch (the app re-stores the target env/src through its own `sessionStorage` handoff: `login()` stashes env/src before the redirect and `config.js` lets URL params win on reload). The `or reloaded_for_params` guard means we accept whatever env we land on the *second* time — we never loop-reload forever fighting a CONFIG that won't change.

**STATE B — app's own signed-out button** (`common.py:504-510`)
Clicks `Sign In with ArcGIS` if visible (role=button, 2 s click timeout). Marked "currently unused" — the app self-redirects before showing it — but kept as a safety net. Wrapped in a bare `except: pass`.

**STATE C — portal sign-in page (the IdP drive)** (`common.py:512-532`)
```
idp = page.get_by_text("Caltrans Azure AD")
if idp.count() > 0 and idp.first.is_visible():
    if idp_drives < 3:
        idp_drives += 1
        idp_url   = idp.first.get_attribute("data-url")          # the SAML authorize URL
        state_val = page.locator("#oauth_state").input_value()   # the oauth_state token
        if idp_url and state_val:
            page.goto(f"{idp_url}?oauth_state={quote(state_val, safe='')}")
        else:
            idp.first.click(timeout=2000)                        # fallback: plain click
    else:
        note("portal sign-in page keeps returning; waiting")
```
This is the core of the silent round-trip. Rather than clicking the IdP button and hoping the portal's JS fires, the loop **reads the button's own `data-url` and the page's `#oauth_state`** and `goto`s the SAML authorize URL directly. `quote(state_val, safe='')` (from `urllib.parse`, imported `common.py:22`) URL-encodes the entire state token — `safe=''` means even `/` is encoded, because the value is an opaque token, not a path. With a live Azure session (saved cookies / Kerberos / Windows device auth) the authorize hop completes with no UI and the app comes back signed in on the next iteration (STATE A).

**`idp_drives < 3` cap.** The portal can bounce back to its sign-in page (expired interaction, MFA needed). Each genuine drive increments the counter; past 3, the loop stops re-driving and just `note`s + waits out the deadline. This bounds wasted authorize hops; it does **not** abort — a slow-but-progressing interactive sign-in still gets its remaining seconds.

**STATE D — off-site breadcrumb** (`common.py:534-539`)
If `_page_host(page)` is non-empty and `!= expected_host()`, breadcrumb `waiting at <host> (<title>)`. Pure diagnostics — this is how you see "parked at an Azure interactive password page" in the log. Uses `_page_host` (hostname parse), **not** a substring match (see §6).

**Tick** (`common.py:540-544`): `page.wait_for_timeout(1000)`. If even that throws (page/context died), `note("wait aborted: <Type>")` and `break`.

### 1.4 Post-loop epilogue (`common.py:545-551`)

One more `page.wait_for_timeout(1000)`, then a single `signed = is_logged_in(page)`, then the structured summary line:
```
auth: navigate done signed_in=<bool> idp_drives=<N> reloaded_for_params=<bool>
      elapsed=<s>s url=<page_url_for_display>
```
The `url=` field comes through `auth_state(page).get("url")` → `page_url_for_display` → **fragment stripped** (§7), so the token never lands in this line. On failure it additionally logs `auth_state(page).get("signals")` — the full per-element visibility snapshot — so one failed run is diagnosable without a repro.

### 1.5 State diagram

```
              goto(url)──fail──▶ SiteUnreachableError
                 │
                 ▼
        ┌───────────────────────── loop (deadline = start+60s) ─────────────────────────┐
        │                                                                                │
        │  is_logged_in? ──yes──▶ _site_params_ok OR reloaded_for_params? ──yes──▶ break │  ← SUCCESS
        │       │                          │no                                           │
        │       │no                        ▼                                             │
        │       │                  reloaded_for_params=True; goto(url); continue         │
        │       ▼                                                                        │
        │  "Sign In with ArcGIS" visible? ──▶ click                                      │
        │       ▼                                                                        │
        │  "Caltrans Azure AD" visible? ──▶ idp_drives<3 ? drive SAML authorize : wait   │
        │       ▼                                                                        │
        │  off-site? ──▶ breadcrumb                                                      │
        │       ▼                                                                        │
        │  wait_for_timeout(1000)                                                        │
        └────────────────────────────────────────────────────────────────────────────────┘
                 │ deadline hit
                 ▼
        wait 1s; signed = is_logged_in(page); log summary (+ signals if not signed)
```

---

## 2. The CONFIG lexical-global trap (`_CONFIG_JS`, `_site_params_ok`)

`_CONFIG_JS` (`common.py:425`):
```js
() => { try { return [CONFIG.env || null, CONFIG.src || null]; } catch (e) { return null; } }
```
`CONFIG` is a top-level `const` in the app's `config.js` — a **lexical global, NOT a `window` property**. `window.CONFIG` is always `undefined`. It must be read by **bare identifier inside try/catch**. The comment at `common.py:421-424` records the field consequence: reading `window.CONFIG` once made `_site_params_ok` think the env was wrong on *every* page, so **every successful sign-in got reloaded away** (an infinite-ish wrong-env reload loop, throttled only by the deadline). `_AUTH_DIAG_JS` reads CONFIG the same bare-identifier way (`common.py:606`).

`_site_params_ok(page)` (`common.py:428`):
- `evaluate` error → log "unavailable; treating as OK" → **return True**.
- `got` falsy (CONFIG returned `null`) → **return True**.
- `got != [want_env, want_src]` (note the order: CONFIG returns `[env, src]`, compared against `get_site()` unpacked as `want_src, want_env` then rebuilt as `[want_env, want_src]`) → log the mismatch → **return False**.
- else **return True**.

**Invariant: True on "unknown."** Callers must NEVER reload on unknown — a reload destroys the memory-only token. `_site_params_ok` returns False *only* when CONFIG reports a concrete env/src that concretely differs. This is why STATE A's reload is gated on a definite-False, not an unknown.

---

## 3. Signed-in detection (`_SIGNED_IN_JS`, `is_logged_in`)

`is_logged_in(page)` (`common.py:583`):
1. `_page_host(page) != expected_host()` → **False** (wrong host can't be signed in).
2. else `bool(page.evaluate(_SIGNED_IN_JS))`.
3. any exception → **False**.

`_SIGNED_IN_JS` (`common.py:565`) logic:
- `visible(sel)`: prefers `el.checkVisibility()`; falls back to a manual `getComputedStyle(n).display === 'none'` walk up `parentElement`. The old `offsetParent` trick is **wrong for fixed-position ancestors** — do not regress.
- Definitively NOT signed in ⟺ `#accessDenied` or `#loginPrompt` visible (authenticated-but-not-in-group, or the prompt).
- Signed in ⟺ ANY of `#modeSelector`, `#controlsGrid`, `#generateRow`, `#appForm`, `#versionCtrl` visible. (`setAuthUI(true)` shows `#modeSelector` immediately for ARS; for SSOR only after the `TSMIS_HI` group check.)

The form (`#customReport`) ships in static HTML even signed out, so its presence proves nothing — that's why the detector keys on *post-auth* UI, never the form.

`require_signed_in(page, message)` (`common.py:652`): returns silently if signed in; else calls `dump_auth_failure` (screenshot + HTML to `FAILURES_DIR`, stem `auth_fail`, plus the signal snapshot logged) and raises `AuthError(message)`. This is the gate the engine uses after every `navigate_with_auth`.

---

## 4. The layered sign-in ladder (headed login)

Both `login.py:_run_login` (`login.py:71`) and `gui_worker.LoginWorker.run` (`gui_worker.py:1087`) implement the **same** ladder. They diverge only in I/O: console `print`/`input` vs. queue messages (`("log", …)`, `("login_open"/"login_saved"/"login_device_ok"/"login_failed"/"cancelled", …)`).

### 4.1 The order, and how the user's pick short-circuits it

`pref = get_preferred_channel()` (`common.py:981`) — `TSMIS_BROWSER_CHANNEL` env override first, else the UI's `set_preferred_channel` value, else `None`.

| Step | Condition | Action | Code |
|---|---|---|---|
| 0 | `pref == "chrome"` | **skip everything**, go straight to `_run_standard_login` | `login.py:80` / `gui_worker.py:1100` |
| 1 | `pref in (None, "msedge")` | `try_device_sso_login(p)` — fully silent | `login.py:90` / `gui_worker.py:1111` |
| 2 | `"chromium" in BROWSER_CHANNELS and pref in (None, "chromium")` | headed Built-in Chromium (`channel="chromium"`) | `login.py:115` / `gui_worker.py:1135` |
| 3 | (fall-through) | `_try_edge_persistent_login` → recapture chain | `login.py:129` / `gui_worker.py:1149` |
| 4 | (fall-through) | `_run_standard_login` — Chrome, then any `launch_browser` channel | `login.py:154` / `gui_worker.py:1175` |

**The Chrome short-circuit (step 0)** exists because the silent device sign-in is an Edge/Windows integration — Chrome never gets it, so trying it would just waste a profile-open. An explicit `chromium` pick skips the silent attempt too (step 1 is gated on `pref in (None, "msedge")`) but still uses the headed Chromium window at step 2.

### 4.2 Step 1 outcomes — three-way branch on `try_device_sso_login`

```
state = try_device_sso_login(p)
  state is None              → silent unavailable; continue down the ladder
  state + portable           → save file;  login_saved / "Session saved"     (DONE)
  state + NOT portable       → DEVICE MODE; login_device_ok (nothing saved)   (DONE)
```
The middle branch is the only place a silent capture is written. The third branch is **device sign-in mode** (`gui_worker.py:1128` posts `login_device_ok`; `login.py:105-112` prints the equivalent) — a successful sign-in whose cookies are device-bound, so *nothing is saved and nothing needs to be* (see §8). The GUI also checks `self.cancel.is_set()` immediately after `try_device_sso_login` (`gui_worker.py:1115`) so a cancel during the silent probe lands cleanly.

### 4.3 Steps 3–4 — Edge recapture then Chrome

After the recapture chain returns a state (`_try_edge_persistent_login`), it is **portability-validated before saving** (`login.py:136` / `gui_worker.py:1161`): portable → save; not-portable → log "device-bound, not saved" and fall to `_run_standard_login`. A `None` recapture also falls to Chrome. `_run_standard_login` (`login.py:194` / `gui_worker.py:1233`) tries `channel="chrome"` headed, and on launch failure calls `launch_browser(p, headless=False, …)` to resolve *any* drivable channel.

---

## 5. Silent device sign-in & the persistent Edge profile

### 5.1 `open_edge_device_context` (`common.py:1393`)

The workhorse. Opens the app-owned persistent Edge profile (`EDGE_LOGIN_PROFILE_DIR`) where the **one-click Windows sign-in lives**, drives `navigate_with_auth`, and returns the *open* context the moment a profile signs in.

```
for profile_name in _known_edge_profile_names():
    ctx = launch_persistent_context(EDGE_LOGIN_PROFILE_DIR,
              channel="msedge", headless=headless,
              args=_LNA_ARGS + ["--profile-directory=<name>"],
              permissions=["local-network-access"])   # retried WITHOUT permissions on failure
    page = _first_or_new_page(ctx)
    navigate_with_auth(page)
    if is_logged_in(page): return (ctx, page)          # ← context left OPEN
    else: record attempt, ctx.close(), try next profile
raise AuthError("Automatic sign-in could not complete …")
```

Key facts a maintainer needs:
- **`_known_edge_profile_names()`** (`common.py:1265`) returns `["Default"]` plus any `Profile N` subdir, de-duped. Managed Edge may have relocated the signed-in session into a work profile, so each is tried in turn.
- **The context is returned OPEN.** `open_edge_device_context` returns `(ctx, page)`; `ctx.close()` shuts the **whole persistent browser** down. There is no separate browser handle — the persistent context *is* the browser. This is the seam that makes device mode work (§8).
- **`permissions=["local-network-access"]` with a no-kwarg retry** (`common.py:1425-1434`) — the LNA pre-grant (§9), with a fallback for browsers that don't know the permission name.
- **The classic failure is "profile already in use."** Each `except` records `<profile>: <Type>: <reason>` into `attempts`, and the final `AuthError` names how many profiles were tried (`common.py:1457-1461`). One persistent profile = one open browser at a time → the concurrency cap (§10).

### 5.2 `try_device_sso_login` (`common.py:1507`)

A thin wrapper: opens the device context, returns `ctx.storage_state()`, and **always closes the context in `finally`** (`common.py:1526-1531`). On any exception (including the `AuthError` from `open_edge_device_context`) it logs and returns `None` — callers treat `None` as "silent not available" and continue the ladder. The captured state is **often device-bound**, so its docstring explicitly warns callers to run `storage_state_is_portable` before saving.

---

## 6. The three-step Edge recapture chain

`_try_edge_persistent_login` (`login.py:157` / `gui_worker.py:1182`) tries to extract a state from a *headed, interactive* managed-Edge sign-in. Managed Edge abandons Playwright's profile when it switches into a work profile mid-login, so capture is attempted three ways in order:

**Step 6.1 — live context** (`capture_storage_state_if_logged_in(ctx)`, `common.py:1188`)
After the user signals done, check every open page in the launch context; if any `is_logged_in`, return `ctx.storage_state()`. Pages that aren't signed in are logged via `auth_state` for diagnostics.

**Step 6.2 — CDP re-attach** (`capture_edge_login_state_over_cdp`, `common.py:1276`)
`launch_edge_login_context` (`common.py:1227`) launched Edge with `--remote-debugging-port=<free port>` (`_free_local_port`, `common.py:1171`). If Edge preserved that port across the work-profile switch:
```
deadline = now + 8s
loop:
    browser = connect_over_cdp(cdp_url, timeout=1500, is_local=True, no_defaults=True)
    for ctx in browser.contexts:
        state = capture_storage_state_if_logged_in(ctx, navigate=True)   # ← navigate=True!
        if state: return state
    browser.close(); sleep(0.5)
```
`navigate=True` (`capture_storage_state_if_logged_in`, `common.py:1211-1224`) means: if no open page is already signed in, open a page and run the **full `navigate_with_auth` chain** — the reopened profile's silent Azure session only helps if the "Caltrans Azure AD" click is actually driven through. `is_local=True, no_defaults=True` keep the CDP attach scoped to the local Edge with no extra contexts.

**Step 6.3 — profile tree headless** (`capture_edge_login_state_from_profiles`, `common.py:1306`)
Relaunch each known persistent profile headless (`launch_persistent_context(..., "--profile-directory=<name>")`), `capture_storage_state_if_logged_in(ctx, navigate=True)`, return `(state, profile_name)` on the first hit, else `(None, None)`. Each profile gets retries until a 20 s deadline. The live context is **closed before** this step (`login.py:189` / `gui_worker.py:1224`) — you cannot have the headed Edge and a headless reopen of the same profile open at once.

---

## 7. Portability probe — PRT/wia rejection (`storage_state_is_portable`)

`storage_state_is_portable(p, state)` (`common.py:1534`). The gate that stops a device-bound capture from being saved:
```
browser = launch_browser(p, headless=True, args=_LNA_ARGS)   # FRESH, no profile
ctx     = _new_app_context(browser, storage_state=state)     # restore the capture
page    = ctx.new_page()
navigate_with_auth(page)
return is_logged_in(page)                                    # did it ACTUALLY log in?
```
**Why:** managed Edge can satisfy Azure AD through the Windows device broker (PRT) — `amr: ["wia"]`, an `ESTSAUTH` stub with no payload. The *live* profile is signed in, but the cookie jar carries only stub tokens, so restoring it into any fresh context silently fails. Saving such a state strands the user with exports that can't sign in. The probe restores the capture **exactly the way the export engine will** (fresh headless context + `navigate_with_auth`) and only returns True if it really logs in.

**Errs conservative:** any exception → log → **return False** (`common.py:1558-1562`). A capture is portable only on a clean, positive round-trip.

---

## 8. Device sign-in mode — `new_authed_browser` & `_recover`

### 8.1 `new_authed_browser(p, parallel=False)` (`common.py:1464`)

The engine's browser factory. Returns `(browser, context, page)`. Two branches:

```
try: require_valid_auth(); state = str(AUTH)
except AuthError: state = None

if state is None:                                   # DEVICE MODE
    ctx, page = open_edge_device_context(p)         # raises AuthError if it can't sign in
    return ctx, ctx, page                           # ← browser==context (same handle!)

# SAVED-SESSION MODE
browser = launch_browser(p, headless=True, parallel=parallel, args=_LNA_ARGS)
ctx     = _new_app_context(browser, storage_state=state)
page    = ctx.new_page()
return browser, ctx, page
```

The **saved-vs-device branch** is the whole story:
- Saved-session mode honors `parallel` (passed to `launch_browser` → `_parallel_candidates`, which avoids managed Edge for concurrent workers).
- Device mode returns the persistent **context as the `browser` handle** (`return ctx, ctx, page`). The engine always calls `browser.close()` in its `finally` (`exporter.py:606-607`); for a persistent context that closes the whole browser. `parallel` is **moot** in device mode — it's single-browser by definition.

`require_valid_auth` (`common.py:353`) validates *shape* only: file exists, parses as JSON, and is a dict with `cookies` and `origins` lists. `has_valid_auth` (`common.py:377`) is the swallow-the-AuthError wrapper backing the GUI dot and the engine's "no saved session" notice (`exporter.py:526`).

### 8.2 `_recover` mid-run (`exporter.py:269`)

```
def _recover(page, spec):
    navigate_with_auth(page)
    require_signed_in(page, "Session expired partway through the batch.")
    select_report(page, spec.label)
```
When a route fails transiently or the token expires (~120 min TTL), `_recover` re-mints by re-running `navigate_with_auth` on the *same page* — the silent round-trip re-completes from the still-valid saved cookies (or the device profile). `require_signed_in` raises `AuthError` if the session truly died, which `_recover_or_stop` (`exporter.py:279`) re-raises to end the run cleanly (it swallows every *other* exception as a recoverable "recovery failed"). This is why the token being memory-only is *tolerable*: any navigation re-mints it.

---

## 9. Local Network Access pre-grant

The TSMIS page fetches report data from an intranet host; Chromium's LNA check would otherwise pop an unanswerable "allow local network access?" prompt that blocks the signed-in UI from ever appearing.

- `_LNA_ARGS` (`common.py:1358`): `--disable-features=LocalNetworkAccessChecksWarnings`, `--enable-features=LocalNetworkAccessChecks`. Passed to every launch — engine (`new_authed_browser`), device context, recapture, portability probe, **and** the headed login windows.
- `_new_app_context(browser, storage_state=None)` (`common.py:1364`): pre-grants `permissions=["local-network-access"]`, with a no-permissions fallback for browsers that reject the name.
- `LOGIN_BROWSER_ARGS = _LNA_ARGS` (`common.py:1384`) and `new_login_context(browser)` (`common.py:1387`, just `_new_app_context(browser)`) are the **public face for the headed flows**. `login.py` and `LoginWorker` pass `LOGIN_BROWSER_ARGS` on every `p.chromium.launch(headless=False, …)` and build their page context via `new_login_context`. Without this, Chrome re-prompts on *every* sign-in and the unanswered prompt blocks login detection (field bug fixed v0.8.0; managed Edge dodged it via enterprise policy, which is why only Chrome showed it).

---

## 10. Concurrency rules

1. **One persistent Edge profile = one open browser at a time.** `open_edge_device_context`, `capture_edge_login_state_from_profiles`, and `launch_edge_login_context` all open `EDGE_LOGIN_PROFILE_DIR`. Holding two concurrently → "profile already in use." The recapture chain enforces this by closing the live context *before* the headless profile reopen.
2. **Device mode caps fast mode to 1 worker.** Because device mode is a single persistent-profile browser, real parallelism needs a *saved* file. The GUI greys the Fast-mode checkbox without one. (`new_authed_browser`'s `parallel` flag is ignored in the device branch.)
3. **Per-thread site pin for parallel scanners.** A process-wide `set_site` (`common.py:103`) would race across the env-scan's parallel scanner threads. Instead `set_thread_site(src, env)` (`common.py:124`) writes a `threading.local` (`_thread_site.pair`, `common.py:121`), and `get_site()` (`common.py:134`) returns this thread's pin when set, else the global selection. **Every** site-aware helper (`get_url`, `expected_host`, `_site_params_ok`, the `is_logged_in` host check) routes through `get_site()`, so a pin retargets all of them for that thread only — the user's header selection is untouched. Engine/login threads never pin. `set_thread_site` with either arg falsy clears the pin (so a partial pin can't `None.lower()`-crash).
4. **Parallel channel order** (`_parallel_candidates`, `common.py:1001`): drops `msedge` to last and ignores a UI pick of Edge, because concurrent managed-Edge sessions restoring one storage_state timed out in the field. `TSMIS_BROWSER_CHANNEL` still hard-overrides. `resolve_parallel_channel` (`common.py:1116`) returning `"msedge"` is the scanner's signal that *only* managed Edge is usable, so it drops to one browser.

---

## 11. Token-in-log redaction (`page_url_for_display`)

`page_url_for_display(page)` (`common.py:782`): `urlsplit(page.url)._replace(fragment="").geturl()` — strips the fragment where the OAuth token rides. Every URL that could reach a log/screen goes through it:
- `auth_state(page)` (`common.py:615`) takes `info["url"]` through it → feeds both `navigate_with_auth`'s summary log and `dump_auth_failure`.
- `maybe_screenshot` (`common.py:792`) uses it for the Preview/Verify-env modal address.

The SPA `history.replaceState`s the hash away synchronously on load (off-repo, in the site's `shared.js`), so only a sub-second failure-dump race could ever capture a hash; routing every URL through this function closes even that. **Never** log raw `page.url` in auth code.

---

## 12. The "no open tabs" close-detection rule (GUI only)

`LoginWorker._run_login_in_browser` (`gui_worker.py:1244`) must tell "user finished signing in" from "user closed the window" while the SSO dance navigates, spawns popups, and replaces tabs. The loop (`gui_worker.py:1275-1293`):
```
while not self.done.wait(0.3):
    try: ctx.cookies(); blips = 0          # pump events; success resets streak
    except: blips += 1                      # transient blip OR gone — decided below
    open_pages = [pg for pg in ctx.pages if not pg.is_closed()]   # None on ctx error
    if (open_pages is not None and len(open_pages)==0) or blips >= 20:
        closed = True; break                # every tab gone, or ~6s unreachable
    if captured is None and _any_logged_in(ctx): captured = ctx.storage_state()
```
**Invariant:** the SSO flow always keeps ≥1 tab, so "zero open tabs" is the *only* reliable window-closed signal, with `blips >= 20` (~6 s of all-calls-failing) as a dead-connection backstop. A single `ctx.cookies()` error, the *original* tab closing, or a mid-redirect blip must **not** count as closed — that bug once slammed the window shut the instant a password went through and falsely reported "cancelled." `_any_logged_in` (`gui_worker.py:1324`) checks *every* page because SSO can land the signed-in page in a popup.

Outcome posting (`gui_worker.py:1312-1321`): `captured` → save + `login_saved`; else `closed` → `cancelled` (no file written, prior session preserved); else → `login_failed`. Cancel anywhere → `_safe_close` + `cancelled`, never saving.

---

## 13. The two title-bar login chips (`gui_api._login_states`)

`_login_states()` (`gui_api.py:231`) → snapshot key `logins`:
```
{"file":   {"valid": has_valid_auth(), "age_h": <hours or None>},
 "device": {"ok": self._device_ok, "primed": <profile dir non-empty>}}
```
- **Saved-login chip** = the file. `valid`/`age_h` from `has_valid_auth` + `_auth_file_age_hours` (`common.py:403`).
- **Edge one-click chip** = the device path. `ok` = `_device_ok` (set True on `login_device_ok` at `gui_api.py:444`, and when a run signs itself in via device mode at `gui_api.py:585`). `primed` = `EDGE_LOGIN_PROFILE_DIR.is_dir() and any(iterdir())`.

**Cheap stat calls only** — `_login_states` never *probes* the device path. Probing would open the persistent profile and risk the "already in use" failure; the device path is only ever proven by a real sign-in. Respect this when extending: the chips read disk state, they don't launch browsers.

---

## 14. Extension points & gotchas

### Adding a new sign-in path

Any new browser/channel sign-in path **must**:
1. Produce a state that passes **`storage_state_is_portable(p, state)`** before `save_auth_state` — never trust a "looks signed in" live context (PRT/wia stubs look fine and aren't).
2. Launch with **`_LNA_ARGS`** and build its context via **`_new_app_context`/`new_login_context`** — without the LNA pre-grant the intranet prompt blocks login detection.
3. Detect login via **`is_logged_in`/`_any_logged_in`** (post-auth UI), never form presence.
4. Slot into the ladder respecting the `pref` short-circuits (Chrome skips silent; explicit channel skips silent).
5. If it returns an OPEN persistent context as its handle (device-mode style), document that `.close()` tears down the browser.

### Adding/changing a `navigate_with_auth` branch

- Give the branch a **distinct `note()` string** (the dedupe swallows repeats).
- **Never `goto`/reload outside the `reloaded_for_params` gate** — every navigation destroys the in-memory token.
- Read CONFIG **only** via `_CONFIG_JS`'s bare-identifier pattern.
- Host comparisons use **`_page_host` + `expected_host`** (hostname parse), never `in page.url` — the authorize URL embeds the app host in its `redirect_uri` (`common.py:411-414`).

### Gotchas a maintainer will trip on

- **`window.CONFIG` is `undefined`** — the const is lexical (§2). This one bug reloaded away every good sign-in.
- **The 60 s budget is hard-coded** (`common.py:476`) — no Settings override, unlike the per-route ceilings. A genuinely slow interactive SSO can exhaust it; that's by design (the user gets a re-login prompt), but don't assume it's tunable.
- **`get_site()` returns `(src, env)` but CONFIG returns `[env, src]`** — `_site_params_ok` rebuilds the order; a naive `got == get_site()` comparison would be backwards.
- **Saving is the *only* commit point** — every failure path leaves the prior auth file untouched (`save_auth_state` is reached only on a portable capture / real login). A non-save outcome is safe by construction.
- **`_device_ok` is session-only** — it resets to `False` on restart (`gui_api.py:130`) and is only ever set True by an actual sign-in, never by probing.
