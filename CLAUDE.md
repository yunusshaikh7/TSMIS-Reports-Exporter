# CLAUDE.md — TSMIS Reports Exporter

## Project Purpose

A unified Windows desktop tool that bulk-exports TSMIS (Caltrans
Transportation System Management Information System) reports for every
California state route. The user picks which report to export from a
menu; one shared login serves every report type.

Currently supported reports:

| Choice | Report | Output format | Output folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/ramp_detail/` |

This repo combines the previously separate
`TSMIS-Reports-Export-ALL-Ramp-Summary` and
`TSMIS-Reports-Export-ALL-Ramp-Detail` projects.

## Repository Layout

```
.
├── 1. setup (one time).bat            # pip install playwright + chromium
├── 2. login (update login).bat        # captures auth session
├── 3. run_export (main script).bat    # auth check + menu + run chosen exporter
├── scripts/
│   ├── common.py                      # URL, ROUTES, auth helpers, nav helpers
│   ├── login.py                       # writes scripts/tsmis_auth.json
│   ├── export_ramp_summary.py         # PDF export loop
│   └── export_ramp_detail.py          # XLSX export loop
├── output/                            # (git-ignored)
│   ├── ramp_summary/                  # PDFs land here
│   └── ramp_detail/                   # XLSX files land here
├── .gitignore
└── CLAUDE.md
```

`scripts/tsmis_auth.json` (auth cookies) and `output/` (generated files,
potentially gigabytes) are both git-ignored.

## Technology Stack

| Component | Detail |
|---|---|
| Language | Python 3 (standard library + Playwright) |
| Browser automation | `playwright` (sync API, Chromium) |
| Target application | `https://rhansonrizing.github.io/tsmis_reports/index.html` |
| Auth mechanism | ArcGIS / Caltrans Azure AD (SSO + MFA) |
| Session persistence | Playwright `storage_state` → `scripts/tsmis_auth.json` |
| OS | Windows (`.bat` launchers); Python scripts are OS-agnostic |

## Workflow for End Users (3-Step Process)

1. **Setup (once per machine):** Double-click `1. setup (one time).bat`
   — installs Playwright and downloads Chromium.
2. **Login (once, or when the session expires):** Double-click
   `2. login (update login).bat` — opens a visible browser, the user
   completes SSO + MFA, then presses Enter to save the session into
   `scripts/tsmis_auth.json`. The same file is used by every export
   script.
3. **Export (repeatable):** Double-click
   `3. run_export (main script).bat` — checks that the auth file
   exists, shows a menu, and runs the selected exporter headlessly
   over every route.

## How the Menu Works

`3. run_export (main script).bat`:

1. Checks that `scripts\tsmis_auth.json` exists — if not, instructs
   the user to run the login BAT first and exits.
2. Shows a numbered menu:
   - `1` → `python scripts\export_ramp_summary.py`
   - `2` → `python scripts\export_ramp_detail.py`
   - `Q` → quit
3. Invalid choices loop back to the menu.

To add a new report type, add a numbered branch to the menu and a
matching `export_<name>.py` under `scripts/`.

## Shared vs. Report-Specific Code

`scripts/common.py` holds everything that is genuinely shared:

- `URL`, `AUTH` (path to `tsmis_auth.json`), `OUTPUT_ROOT`
- `ROUTES` — the canonical list of California state route strings
- `REPORT_TIMEOUT_MS`, `COUNTY_ENABLE_TIMEOUT_MS`
- `handle_bad_auth(reason)`, `require_valid_auth()`
- `navigate_with_auth(page)`, `is_logged_in(page)`
- `select_report(page, report_label)` — picks a report and sets District/County to "-- ALL --"
- `new_authed_browser(p)` — launches Chromium with saved auth

Each `export_*.py` script has its own copy of the per-route loop, the
wait condition after Generate, and the save method (`page.pdf(...)`
vs `page.expect_download` + click Export). This keeps a bug in one
report type from breaking the other.

## Configurable Constants (in `scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | `360_000` (6 min) | Hard ceiling for a single report. Some routes (e.g. Route 5 Ramp Detail) legitimately take minutes. |
| `SKIP_PROMPT_AFTER_MS` | `60_000` (1 min) | Soft timer: after this, the script prints a "still working" line and (on Windows) tells the user they can press `S` to skip the current route. |
| `COUNTY_ENABLE_TIMEOUT_MS` | `60_000` (60 s) | Max wait for the county dropdown to enable |

Increase these if the TSMIS server is slow.

## Skipping a Slow Route Mid-Run

While an export is waiting on a slow route, you can press `S` in the
console window (Windows only) to skip that route and move on to the
next one. The script:

1. Waits up to `SKIP_PROMPT_AFTER_MS` silently.
2. After that, prints a status line every 30 s and watches for `S`.
3. If `S` is pressed, the route is added to a "Skipped by user" list,
   the form is reset, and the loop continues with the next route.
4. If nothing is pressed and `REPORT_TIMEOUT_MS` elapses, the route is
   added to `failed` and the loop recovers as usual.

Run the export again later and the loop will retry any routes that
don't yet have an output file.

## Resume / Idempotency

Each export loop checks `if out_path.exists(): continue` before
processing a route, so re-running after an interruption safely skips
already-downloaded files. Delete specific files from
`output/ramp_summary/` or `output/ramp_detail/` to force a
re-download.

## Auth / Session Details

- `scripts/login.py` writes `scripts/tsmis_auth.json` via
  `ctx.storage_state(path=...)`.
- Every `export_*.py` calls `require_valid_auth()` first (verifies
  the file exists and is valid JSON) and then restores the session
  via `browser.new_context(storage_state=...)`.
- If the session is missing, malformed, or expired,
  `handle_bad_auth()` deletes the stale file and instructs the user
  to re-run `2. login (update login).bat`.
- The BAT menu also gates on `scripts\tsmis_auth.json` existing
  before the menu is even shown.
- The auth file is git-ignored — treat it as a credential.

## Adding or Removing Routes

Edit the `ROUTES` list in `scripts/common.py`. The change applies to
every export script automatically. Route strings must match the exact
option values in the TSMIS "Route" `<select>` element (zero-padded
3-digit strings, with optional suffixes like `"005S"`, `"101U"`).

## Adding a New Report Type

1. Create `scripts/export_<name>.py` — copy one of the existing
   exporters and change:
   - `REPORT_LABEL` (must match the dropdown text exactly)
   - `OUT = OUTPUT_ROOT / "<name>"`
   - The wait condition after Generate, if needed
   - The save method (`page.pdf(...)` for PDFs,
     `page.expect_download` for downloads)
   - The output filename pattern
2. Add a new numbered branch to `3. run_export (main script).bat`.
3. Document it in the table at the top of this file.

## Error Handling Patterns

- **Missing/corrupted auth file:** `require_valid_auth()` →
  `handle_bad_auth()` deletes the file and prints next-step
  instructions.
- **Per-route timeout or DOM error:** Route is added to the `failed`
  list; the page is re-navigated and the form re-set so subsequent
  routes still run.
- **Session expiry mid-run:** `is_logged_in()` is checked after
  recovery navigation; triggers `handle_bad_auth()` if the session is
  gone.

## Development Conventions

- **No dependencies beyond Playwright** — keep it that way; the
  audience is non-developers using numbered `.bat` files.
- **Python 3 standard library** for everything except Playwright.
- **No virtual environment** is required or created by setup;
  Playwright is installed globally via `pip`.
- **Sync Playwright API** (not async) — simpler for a single
  sequential script.
- **No logging framework** — `print()` to stdout is intentional;
  output is visible in the `.bat` console window.
- **No tests** — the "test" is running an export against the live
  site.

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: Playwright is not installed` | Setup not run | Run `1. setup (one time).bat` |
| `NO SAVED SESSION FOUND` in BAT menu | `tsmis_auth.json` missing | Run `2. login (update login).bat` |
| `LOGIN PROBLEM — Saved session is expired` | Cookies expired | Run `2. login (update login).bat` |
| Route keeps timing out | TSMIS server slow | Increase `REPORT_TIMEOUT_MS` in `common.py` |
| County dropdown timeout | Slow network | Increase `COUNTY_ENABLE_TIMEOUT_MS` in `common.py` |
| Output looks wrong for one report only | Selector for that report changed | Edit only the affected `export_*.py` |

## Git Conventions

- **Never commit** `scripts/tsmis_auth.json` (live auth tokens) or
  anything in `output/` — both are in `.gitignore`.
- Commit messages should be short and imperative (e.g.,
  `add route 395`, `add tsar ramp inventory exporter`).
