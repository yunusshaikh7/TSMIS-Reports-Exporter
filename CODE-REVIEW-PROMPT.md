# CODE-REVIEW-PROMPT.md — standard ruthless audit for TSMIS Reports Exporter

A reusable prompt for a deep, **read-only** code review of this repository. Paste
it to a capable agent (Claude, Codex, …). It is **project-tailored** (file lists,
tech stack, and IT context are specific to this app) but **not** tied to any one
patch — point it at the current `HEAD` or a specific diff range and go.

---

## How to use this prompt

- **Target.** By default audit the current working tree (record `git rev-parse HEAD`).
  To review a specific change, diff a range (`main..<branch>`, `<tag>..HEAD`) and
  focus findings on what changed — but read enough surrounding code to judge real
  blast radius.
- **Two-agent (optional).** For high-stakes reviews, run this on two independent
  agents and reconcile by stable slug ID, with a third neutral pass adjudicating
  one-sided P0/P1s against the working tree. Solo is fine for routine reviews.
- **Source-backed verification (recommended for any automation-contract finding).**
  The TSMIS website source is available locally as inspect-element captures (e.g.
  under `…/TSMIS/website-source/`). After the code pass, re-verify every finding
  that depends on the site's DOM, selectors, button text, empty-state strings,
  `CONFIG` shape, or `env/src` params against that source before trusting it —
  contract assumptions are the easiest thing to get wrong from the repo alone.
- **Output.** One report file at `code-review/AUDIT-<agent>-<short-sha>.md` (create
  the folder if needed; per-run reports are git-ignored — they quote code and
  internal detail). Distil durable follow-ups into the project `TODO.md`; do not
  leave them only in the report.

---

## Operating rules (read-only audit)

- This is a READ-ONLY audit. Do **not** modify, fix, refactor, stage, or commit code.
- Do **not** run the export engine, GUI, login flow, or any consolidator/comparison
  against live data. Do **not** authenticate or make any request to the live TSMIS
  site or portal.
- Do **not** open, print, quote, or paste the contents of `scripts/tsmis_auth.json`,
  the Edge/WebView2 profiles, captured cookies, downloaded tokens, or report output
  files. Reference their existence, shape, and handling — never their values. (An
  audit about credential leakage must not itself leak credentials.)
- Do **not** install packages or mutate the environment. Expected network is at most
  `git fetch` and optional `pip-audit` against PyPI; if the sandbox blocks network,
  say so and continue.

## Effort & evidence posture

- Depth over breadth. ~15–30 well-evidenced findings is a healthy target. Do not
  manufacture P3s to fill sections.
- An unverified claim asserted as a confirmed bug is itself a defect in this audit.
  When in doubt, demote to "Unproven But Worth Investigating."
- Treat AI/vibe-coded code as untrusted until proven otherwise. Do not trust
  comments, release notes, or architecture docs (including `CLAUDE.md`) unless the
  code backs them up.

## Parallelism / subagents (use if your harness supports parallel tasks)

This audit decomposes cleanly. Fan out the READING + EVIDENCE-GATHERING phase across
independent risk domains, then synthesize in ONE context. Suggested split:
- **Auth / Browser / Environment + automation contract:** `common.py`, `login.py`,
  `exporter.py`, `exporter_parallel.py`, `gui_worker.py` auth paths.
- **GUI bridge + injection:** `gui_api.py`, `gui_worker.py`, `ui/app.js`, `ui/index.html`.
- **Updater + supply chain:** `updater.py`, `gui_main.py` swap path, `.github/workflows/`.
- **IT / DLP / endpoint + packaging:** `build/build.ps1`, `build/prune_bundle.ps1`,
  `build/app.spec`, `build/app.manifest`, `*.bat`.
- **Filesystem / data-loss + logging:** `paths.py`, `settings.py`, `logging_setup.py`,
  `gui_worker.py` reset/support-bundle paths.
- **Spreadsheet / PDF correctness:** `compare_core.py`, `compare_env.py`,
  `compare_highway_log.py`, `consolidate_*.py`.
- **Product / report correctness:** `reports.py`, `exporter.py`, `export_*.py`.

Fan-out rules:
- Each subagent returns CANDIDATE findings only — every one with file > symbol + a
  verbatim code snippet + proposed severity + confidence. No quoted code ⇒ it goes
  in that subagent's "unproven" list, never in findings.
- The LEAD agent does ALL synthesis in one head: independently RE-VERIFY each
  candidate's snippet actually says what was claimed (subagents hallucinate — do not
  rubber-stamp), assign FINAL severity uniformly via the rubric, dedup by slug ID,
  and write the single report. Do not fan out severity calibration, dedup, the
  Executive Risk Map, or the Handoff Pack.

## Severity rubric (calibrate identically)

- **P0 — Critical / ship-blocker:** data loss; leakage of credentials/tokens/cookies/
  auth file/report contents/PII; behavior an IT or endpoint-security tool would
  reasonably flag as malware, persistence, or tampering; or silently reporting
  missing / skipped / stale / duplicated / wrong-source / wrong-environment / partial
  data as success.
- **P1 — High:** serious correctness, security, or data-integrity defect that is
  bounded in blast radius or needs specific conditions to trigger; or IT-friction
  serious enough to get the app blocked, quarantined, or rejected.
- **P2 — Medium:** brittle structure, a likely-to-break automation contract, missing
  verification on a genuine risk, or a confusing/leaky diagnostic.
- **P3 — Low:** hygiene, polish, minor inconsistency, defense-in-depth nice-to-have.

**Confidence (tag every finding):** High = read the code, defect mechanically
demonstrable. Medium = strong inference, not fully traced. Low = pattern/smell;
belongs under "Unproven" unless it carries quoted code.

## Product & IT context (why this app is unusual)

TSMIS Reports Exporter is a portable Windows desktop app for **non-technical users**.
It bulk-exports Caltrans TSMIS reports via browser automation, consolidates PDFs/XLSX,
compares spreadsheet outputs, and ships as a PyInstaller onefolder zip. Stack: Python
3.11, Playwright sync API, pywebview/Edge WebView2 GUI, vanilla JS/CSS/HTML, openpyxl,
pdfplumber, PowerShell build scripts, GitHub Actions release, batch-file console
entrypoints, GitHub Releases self-updater.

It runs on **managed work PCs and must look and behave innocent to IT/security
tooling** — avoiding trouble from IT is a core product requirement, not a nice-to-have.
Audit for anything that could trigger DLP; Defender/SmartScreen/EDR/AV; corporate
proxy/TLS inspection; quarantine or software-inventory alarms — from bundled binaries,
browser automation, the updater, unsigned/self-modifying executables, helper processes,
hidden windows, PowerShell/cmd usage, downloaded Chromium, support bundles, screenshots,
logs, HTML dumps, generated zips, or suspicious strings in packaged dependencies. Treat
"this might look sketchy to IT even if technically safe" as a real finding. The goal is
an app that is genuinely clean, explainable, minimally invasive, and easy for IT to
approve. Also audit the testing/release process, but recommend a process only after
reviewing the code and gaps (recommendations are findings, not patches).

## Read these files IN FULL (don't infer from grep)

`scripts/updater.py`, `scripts/common.py`, `scripts/gui_api.py`, `scripts/gui_worker.py`,
`scripts/gui_main.py`, `scripts/login.py`, `scripts/exporter.py`,
`scripts/exporter_parallel.py`, `scripts/compare_core.py`, `scripts/compare_env.py`,
`scripts/paths.py`, `scripts/settings.py`, `scripts/ui/app.js`, `build/build.ps1`,
`build/prune_bundle.ps1`, `build/app.spec`, `.github/workflows/release.yml`,
`.github/workflows/checks.yml`. For a diff-scoped review, also read every changed file
in full.

## Orientation commands (adapt to your shell; skip network if blocked)

```
git rev-parse HEAD                       # record this SHA at the top of the report
git status --short --branch
git fetch --tags origin                  # network; skip if unavailable
git tag --sort=-creatordate              # top = latest release tag
git log --oneline --decorate -20 --all
git diff --name-status HEAD..<latest_tag>
git ls-files
```

One narrow "danger" pass (keep it narrow so it doesn't flood context):

```
rg -n "eval\(|exec\(|os\.system|subprocess|shell=True|os\.startfile|webbrowser\.open|rmtree|extractall|innerHTML|insertAdjacentHTML|CREATE_NO_WINDOW|storage_state|pickle|marshal|--remote-debugging|Zone\.Identifier" .
```

Then TARGETED topic greps while drilling each area (do NOT run a mega-alternation of
common words — on this codebase that matches thousands of low-signal lines):
- Secrets/auth: `rg -n "tsmis_auth|password|secret|cookie|token|Authorization|Bearer|fragment|#access_token" scripts`
- Swallowed errors: `rg -n "except Exception|except:|# noqa|^\s*pass\s*$" scripts`
- Spreadsheet/formula: `rg -n "HYPERLINK|COUNTIF|=\"|openpyxl|write_only" scripts/compare_core.py scripts/consolidate_*.py scripts/compare_env.py`
- IT/DLP: `rg -n "PowerShell|powershell|cmd\.exe|CREATE_NO_WINDOW|Defender|SmartScreen|extractall|chromium|local-network|PLAYWRIGHT_BROWSERS_PATH" scripts build .github`
- Network egress: `rg -n "urllib|urlopen|requests|http://|https://|github\.com|api\." scripts`
- File deletion/reset: `rg -n "rmtree|unlink|remove|shutil|rename|replace" scripts`

Identify current tests, fixtures, lint/type checks, dependency audits, release gates
(`build/check_*.py`, `.github/workflows/checks.yml`). If available WITHOUT changing the
repo or installing anything, run `bandit`, `pip-audit`, `ruff`, `compileall`; if
unavailable, say so — do not install them.

## Audit lenses (investigation angles, not report sections — each finding has ONE home)

1. **Product risk** — does the app ever show success when data is missing, skipped,
   stale, duplicated, wrong-source/env, partial, or from an unavailable report type?
2. **Browser/Auth/Environment** — saved login vs Edge one-click state, auth validation,
   device SSO fallback, token stripping, screenshots/HTML captures, all-environment
   checks, report-availability detection, managed-Edge avoidance, Playwright thread
   affinity, selectors, timeouts, retries, cancellation, skip, wrong-env protection.
3. **Automation contract** — hard-coded selectors/labels; assumptions about dropdown
   shape, disabled states, button text, empty states, error boxes, URL fragments,
   `CONFIG` globals, env/src params, download behavior, report-ready conditions; where
   a fix should be validated against the website source / a fake-site harness.
4. **New / changed reports** — labels, output folders, extensions, ready/empty
   detection, registry/menu/GUI/env-scan consistency, and honest handling of features
   not yet supported (e.g. export-only reports with no consolidate/compare).
5. **GUI bridge** — every pywebview public method + `app.js` caller: validation, task
   gating, races, queue ordering, Promise hangs, modal replacement, paths, screenshot
   URLs, and whether untrusted text (report data, paths, URLs, env names) can become
   executable HTML/JS.
6. **Filesystem / data loss** — paths, delete/reset, support bundle, updater
   staging/swap, WebView cache clearing, symlinks/junctions, read-only fallbacks,
   file-lock behavior, stale conversions; can user data/auth/logs be deleted or leaked?
7. **IT / DLP / endpoint security** — bundle contents, third-party docs, test data,
   fake credit-card/key/SSN strings, licenses; unsigned-exe + SmartScreen + MOTW +
   manifest + code-signing gaps; self-update/helper-process/hidden-window/process-flags/
   zip-extraction behavior resembling malware or persistence; bundled/downloaded
   Chromium, CDP/debug ports, local-network flags, proxy/TLS; whether docs make the app
   explainable to IT. (Consolidate IT material — don't triplicate it across sections.)
8. **Updater / supply chain** — GitHub Releases trust model, signatures/checksums, asset
   selection, extraction assumptions, rollback correctness, stale-UI-cache handling,
   partial-update states, unhashed dep pins, PyInstaller pruning, CI release gates.
9. **Logging / diagnostics** — enough to debug field failures? Leak tokens/cookies/
   report data/PII/internal URLs/paths/screenshots/HTML? Rotation, crash logs, update
   logs, support-bundle contents, UI log mirroring, thread labels, swallowed exceptions,
   error→user mapping.
10. **Spreadsheet / PDF correctness** — formula/CSV injection, Excel row/sheet/formula
    limits, schema drift, skipped-file accounting, route extraction, PDF parse
    heuristics, cancel mid-write, file-lock failures, self-check validity, and
    formulas-vs-values parity.
11. **Code structure** — which modules are too large / multi-responsibility, which
    boundaries would reduce risk, which splits would be harmful, what contracts a split
    must protect. (Identify — do not refactor.)
12–14. **Testing/release process, verification gaps, security baseline** — tie each
    testing recommendation to a specific finding ID; name the exact unguarded behavior
    and the test/fixture that would expose it; apply OWASP-style thinking adapted to a
    local desktop app (input validation, output encoding, auth/session, data protection,
    logging, comms, dependency/supply chain, file management, self-update).

## Deliverable format

Write to `code-review/AUDIT-<agent>-<short-sha>.md` (do not commit). Begin with: audited
HEAD SHA, branch, dirty/clean, the latest tag you diffed against, whether you used
subagents and how you split, and a summary table of ALL findings: `ID | Severity |
file > symbol | one-line | Confidence`. If the report risks running long, complete every
P0/P1 before spending budget on P2/P3.

1. **Executive Risk Map** — 8–12 bullets, highest first, each ending with its finding ID.
2. **Version/Release Delta** — what code was audited (SHA) vs latest release.
3. **Findings (P0/P1/P2/P3)** — each: stable slug ID; severity; file > symbol anchor; a
   short VERBATIM snippet; user/security/IT impact; reproduction / how-to-verify;
   confidence. No quoted code ⇒ it belongs in §10, not here.
4. **Automation-contract risks** — where website-source-backed selectors/tests would help.
5. **Structural audit** — massive modules; is decomposition warranted?
6. **Logging audit** — sufficiency, privacy, support bundle, rotation, diagnosability.
7. **IT / DLP / endpoint-security audit** — what could be flagged, why, confidence.
8. **Testing/release-process audit** — gaps + risk-based recommendations (cite finding IDs);
   separate "must-have before release" / "useful" / "overkill"; note what current gates cover.
9. **Cross-agent handoff pack** — top findings to verify (by ID); files worth a second look;
   least-confident findings; coverage & blind spots (read-in-full vs grepped vs skipped, and
   why); commands run (and which failed/were unavailable); assumptions that may be wrong.
10. **Unproven but worth investigating** — everything without quoted-code evidence.
11. **Verification gaps** — exact unguarded behavior + the test/fixture that exposes it.
12. **Questions for the maintainer.**

**No patches. No code rewrites. Serious findings first.**
