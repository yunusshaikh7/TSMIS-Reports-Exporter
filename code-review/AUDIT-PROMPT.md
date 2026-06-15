You are doing a ruthless audit of this repository. Do NOT fix code. Do NOT refactor. Do NOT propose patches. Your job is to identify risks, bugs, false assumptions, brittle structure, missing verification, and places where this app could harm users, lose data, misreport data, leak sensitive information, trigger IT/security tools, or fail silently.

Operating rules (read-only audit):
- This is a READ-ONLY audit. Do not modify, fix, refactor, stage, or commit code.
- Do not run the export engine, the GUI, the login flow, or any consolidator/comparison against live data.
- Do not authenticate, sign in, or make any request to the live TSMIS site or portal.
- Do not open, print, quote, or paste the contents of scripts/tsmis_auth.json, the Edge/WebView2 profiles, captured cookies, downloaded tokens, or report output files. You may reference their existence, shape, and handling — never their values. (An audit about credential leakage must not itself leak credentials.)
- Do not install packages or mutate the environment. The only expected network calls are `git fetch` and (optionally) pip-audit against PyPI; if the sandbox blocks network, say so and continue.

Effort & evidence posture:
- Depth over breadth. ~15–30 well-evidenced findings is a healthy target. Do not manufacture P3s to fill sections.
- An unverified claim asserted as a confirmed bug is itself a defect in this audit. When in doubt, demote to "Unproven But Worth Investigating."

Parallelism / subagents (use them if your harness supports parallel tasks):
This audit is large and decomposes cleanly. If you can spawn subagents/parallel tasks, fan out the READING + EVIDENCE-GATHERING phase across independent risk domains, then synthesize in ONE context. Suggested split — one subagent each:
  - Auth / Browser / Environment + website-automation contract (lenses 2, 3): common.py, login.py, exporter.py, exporter_parallel.py, gui_worker.py auth paths
  - GUI bridge + injection (lens 5): gui_api.py, gui_worker.py, ui/app.js, ui/index.html
  - Updater + supply chain (lens 8): updater.py, gui_main.py swap path, .github/workflows/release.yml
  - IT / DLP / endpoint + packaging (lens 7): build/build.ps1, build/prune_bundle.ps1, build/app.spec, build/app.manifest, *.bat
  - Filesystem / data-loss + logging (lenses 6, 9): paths.py, settings.py, logging_setup.py, gui_worker.py reset/support-bundle paths
  - Spreadsheet / PDF correctness (lens 10): compare_core.py, compare_env.py, compare_highway_log.py, consolidate_*.py
  - Product / report-correctness + new reports (lenses 1, 4): reports.py, exporter.py, export_intersection_*.py

Rules for fan-out:
  - Each subagent returns CANDIDATE findings only — every one carrying file > symbol + a verbatim code snippet + proposed severity + confidence. No quoted code => it goes in that subagent's "unproven" list, never in findings.
  - The LEAD agent does all synthesis in one head: independently RE-VERIFY that each candidate's snippet actually says what the subagent claims (subagents hallucinate — do not rubber-stamp), assign FINAL severity uniformly via the rubric, dedup by slug ID across overlapping domains, and write the single report.
  - Do NOT fan out severity calibration, deduplication, the Executive Risk Map, or the Cross-Agent Handoff Pack — those need one context for consistency.
  - Subagents are an internal tactic. The deliverable is still ONE report file in the format below; their use must not change the output structure, and reconciliation is still by stable slug ID.

Parallel review context:
This audit may be performed by both Codex and Claude at the same time. Treat yourself as one independent audit agent in a two-agent review. Do not assume the other agent is correct, and do not defer hard analysis to them. Produce findings in a form that can be shared with the other agent later.

To make the two reports mechanically comparable:
- Record the exact commit you audited: run `git rev-parse HEAD` and put the full SHA at the top of your report. Disagreements between the two reports are only meaningful if both audited the same SHA.
- Give every finding a STABLE SLUG ID (e.g. UPDATER-SWAP-RACE, DLP-BUNDLED-DOCS, GUI-INNERHTML-XSS) so overlapping findings can be matched by ID, not by prose.
- Anchor each finding by file path + function/symbol + a short verbatim code snippet. Line numbers are optional and may drift between agents — never rely on them as the only anchor.

If another agent's review is later pasted into this thread, use it as evidence to reconcile against, not as truth. For each overlapping issue, classify it as Confirmed, Plausible but unverified, Disagreed / needs proof, Duplicate, or New issue you missed. Prioritize code evidence, file/symbol references, reproducibility, and user impact.

Severity rubric (use these definitions so both agents calibrate the same):
- P0 — Critical / ship-blocker: data loss; leakage of credentials/tokens/cookies/auth file/report contents/PII; behavior an IT or endpoint-security tool would reasonably flag as malware, persistence, or tampering; or silently reporting missing / skipped / stale / duplicated / wrong-source / wrong-environment / partial data as success.
- P1 — High: serious correctness, security, or data-integrity defect that is bounded in blast radius or needs specific conditions to trigger; or IT-friction serious enough to get the app blocked, quarantined, or rejected.
- P2 — Medium: brittle structure, a likely-to-break website-automation contract, missing verification on a genuine risk, or a confusing/leaky diagnostic.
- P3 — Low: hygiene, polish, minor inconsistency, defense-in-depth nice-to-have.

Confidence (tag every finding):
- High = you read the code and the defect is mechanically demonstrable.
- Medium = strong inference from code, not fully traced.
- Low = pattern/smell; belongs under "Unproven But Worth Investigating" unless it carries quoted code.

Important IT / work-PC context:
This app runs on managed work PCs. It must look and behave innocent to IT/security tooling. Avoiding trouble from IT is a core product requirement, not a nice-to-have.

Audit for anything that could trigger:
- Data Loss Prevention (DLP) systems.
- Defender, SmartScreen, endpoint detection, antivirus, corporate proxy/TLS inspection, download scanners, quarantine tools, or software inventory alarms.
- Suspicion from bundled binaries, browser automation, updater behavior, unsigned executables, self-modifying files, helper processes, hidden windows, script execution, PowerShell/cmd usage, downloaded Chromium, support bundles, screenshots, logs, HTML dumps, generated zips, or suspicious strings in packaged dependencies.
- Sensitive data leakage: tokens, cookies, auth files, report contents, PII, internal URLs, screenshots, HTML snapshots, file paths, user names, machine names, or state agency data.
- Corporate policy violations: admin-required behavior, writing to protected locations, bypass-looking behavior, disabling security features, unexpected network calls, hidden background activity, persistence-like behavior, self-update behavior, or excessive telemetry-like logging.

The goal is not to hide malicious behavior. The goal is for the app to be genuinely clean, explainable, minimally invasive, supportable, and easy for IT to approve. Treat "this might look sketchy to IT even if technically safe" as a real audit finding.

Also audit the testing/release process, but do not design the replacement up front. Decide what testing process is warranted only after reviewing the code, release flow, risk areas, and current verification gaps. Recommendations are allowed only as audit findings tied to concrete risks. (Recommendations are NOT patches — describing a needed test or guardrail is in scope; writing the code for it is not.)

Important context:
The source code for the TSMIS website being automated is available to the project owner, but it is NOT attached for this review. Do not assume access to it during the audit. However, when identifying future planned fixes or test strategy gaps, consider that the website source can be used later to build better selectors, fixtures, fake-site harnesses, route/report mocks, schema checks, and regression tests.

Product context:
This is TSMIS Reports Exporter, a portable Windows desktop app for non-technical users. It bulk-exports Caltrans TSMIS reports through browser automation, consolidates PDFs/XLSX files, compares spreadsheet outputs, and packages as a PyInstaller onefolder zip. Tech stack: Python 3.11, Playwright sync API, pywebview/Edge WebView2 GUI, vanilla JS/CSS/HTML, openpyxl, pdfplumber, PowerShell build scripts, GitHub Actions release workflow, batch-file console entrypoints, GitHub Releases self-updater.

Recent feature context:
- Intersection Summary/Detail exports.
- Saved login and Edge one-click sign-in indicators.
- Automatic/background all-environment checks across SSOR/ARS x Prod/Test/Dev.
- Report availability detection for greyed-out/missing report types.
- Managed Edge avoidance for fast mode and parallel environment scanning.
- Built-in Chromium download/delete and with-browser release variant.
- tsmis.dot.ca.gov default host plus custom per-environment URLs.
- Preview/Verify screenshots showing page address while stripping token fragments.
- Environment-labeled run folders.
- Cross-environment comparisons.
- TSMIS-vs-TSN comparisons with formulas/values outputs, self-checks, Only-in sheets, Spot Check sheet, and manual-calc behavior.
- One-click updater hardening against locked-down PCs, half-installs, stale WebView cache, rollback ambiguity, and removal of dev/testing update channel.
- Settings tab, support bundle, reset/delete reports, reliability knobs, verbose logging, DevTools toggle.

Treat AI/vibe-coded code as untrusted until proven otherwise. Do not trust comments, release notes, or architecture docs (including CLAUDE.md) unless code backs them up.

Audit scope:
- All tracked source/config: scripts/, scripts/ui/, build/, .github/, requirements*.txt, *.bat, README.md, CLAUDE.md, version.py.
- Ignore generated local artifacts unless tracked, behavior-affecting, or release-hygiene relevant.
- Assume Windows 10/11 users, corporate-managed browsers, SSO/MFA, sensitive session state, sensitive report contents, Excel users, locked-down IT environments, and no direct testing on real work laptops.

Read these files IN FULL (do not infer their behavior from grep alone):
scripts/updater.py, scripts/common.py, scripts/gui_api.py, scripts/gui_worker.py, scripts/gui_main.py, scripts/login.py, scripts/exporter.py, scripts/exporter_parallel.py, scripts/compare_core.py, scripts/compare_env.py, scripts/paths.py, scripts/settings.py, scripts/ui/app.js, build/build.ps1, build/prune_bundle.ps1, build/app.spec, .github/workflows/release.yml.

Start with (commands are illustrative — adapt them to your shell/OS; on Windows PowerShell `head` does not exist, use `Select-Object -First N`; substitute the real latest tag for <latest_tag>; skip network steps if the sandbox blocks them and say so):
- git rev-parse HEAD                          # record this SHA at the top of your report
- git status --short --branch
- git fetch --tags origin                     # network; skip if unavailable
- git tag --sort=-creatordate                 # top entry = <latest_tag>
- git log --oneline --decorate --max-count=20 --all
- git diff --name-status HEAD..<latest_tag>
- git ls-files
- rg --files

One high-signal "danger" pass (kept deliberately narrow so it doesn't flood context):
- rg -n "eval\(|exec\(|os\.system|subprocess|shell=True|os\.startfile|webbrowser\.open|rmtree|extractall|innerHTML|insertAdjacentHTML|CREATE_NO_WINDOW|storage_state|pickle|marshal|--remote-debugging|Zone\.Identifier" .

Then run TARGETED topic greps only while drilling into each area (do NOT run one mega-alternation of common words like open(/logging/update/download/zip/csv/xlsx/token/cookie/formula — on this codebase those match thousands of low-signal lines and waste budget):
- Secrets/auth surface:   rg -n "tsmis_auth|password|secret|cookie|token|Authorization|Bearer|fragment|#access_token" scripts
- Swallowed errors:       rg -n "except Exception|except:|# noqa|^\s*pass\s*$" scripts
- Spreadsheet/formula:    rg -n "HYPERLINK|COUNTIF|=\"|openpyxl|write_only" scripts/compare_core.py scripts/consolidate_*.py scripts/compare_env.py
- IT/DLP surface:         rg -n "PowerShell|powershell|cmd\.exe|CREATE_NO_WINDOW|Defender|SmartScreen|extractall|chromium|local-network|PLAYWRIGHT_BROWSERS_PATH" scripts build .github
- Network egress:         rg -n "urllib|urlopen|requests|http://|https://|github\.com|api\." scripts
- File deletion/reset:    rg -n "rmtree|unlink|remove|shutil|rename|replace" scripts

- Identify current tests, fixtures, lint/type checks, dependency audits, release gates.
- If available WITHOUT changing the repo or installing anything, run static tools such as bandit, pip-audit, ruff, mypy/pyright, and compileall. If unavailable, say so — do not install them.

Audit lenses:
(The lenses below are investigation angles, not report sections. Each finding has exactly ONE home in the Deliverable; reference it by ID from other sections rather than restating it. The IT/DLP material in particular recurs across the intro, lens 7, and lens 14 — consolidate it, don't triplicate it.)

1. Product Risk
Does the app ever show success when data is missing, skipped, stale, duplicated, from the wrong source/environment, partially generated, or based on an unavailable report type?

2. Browser/Auth/Environment Risk
Audit saved login vs Edge one-click state, auth validation, device SSO fallback, token stripping, screenshots/HTML captures, all-environment checks, report availability detection, managed Edge avoidance, Playwright thread affinity, selectors, timeouts, retries, cancellation, skip behavior, and wrong-environment protection.

3. Website Automation Contract Risk
The target website source is not provided for this review, but it exists and can be used later. Audit how brittle the current automation contract appears from this repo alone:
- hard-coded selectors and report labels
- assumptions about dropdown shape, disabled states, button text, empty states, error boxes, URL fragments, CONFIG globals, env/src parameters, download behavior, and report-ready conditions
- places where future fixes should be validated against the website source or a fake-site harness derived from it

4. New Report Risk
Audit Intersection Summary/Detail. Verify labels, output folders, file extensions, ready/empty detection, registry/menu/GUI/env-scan consistency, and clear handling of no consolidation/comparison support yet.

5. GUI Bridge Risk
Audit every pywebview public API method and app.js caller. Check validation, task gating, races, queue ordering, Promise hangs, modal replacement, native dialogs, paths, screenshot URLs, and whether untrusted text (report data, file paths, page URLs, env names) can become executable HTML/JS.

6. Filesystem/Data-Loss Risk
Audit paths, delete/reset, support bundle, updater staging/swap, WebView cache clearing, generated files, symlinks/junctions, read-only fallbacks, file-lock behavior, stale conversions, and whether user data/auth/logs can be deleted or leaked.

7. IT / DLP / Endpoint-Security Risk
Audit whether the app could be flagged or misunderstood by managed-PC controls. Review:
- PyInstaller bundle contents, third-party docs, test data, fake credit-card/private-key/SSN/AWS-key strings, markdown/docs in bundles, licenses/notices, and DLP scanning.
- Unsigned executable behavior, SmartScreen friction, Mark-of-the-Web handling, app manifest, icon/version metadata, code-signing gaps.
- Self-update behavior, helper processes, hidden windows, process creation flags, zip extraction, downloaded executables, and whether update behavior resembles malware/persistence.
- Bundled/downloaded Chromium, Playwright driver, browser automation, local profiles, CDP/debug ports, local network access flags, corporate proxy/TLS behavior.
- Support bundles, logs, screenshots, HTML dumps, crash files, update logs, and generated zips.
- Network calls to GitHub, TSMIS, browser downloads, and anything that might look like telemetry.
- Whether user-facing docs make the app explainable and acceptable to IT.

8. Updater/Supply Chain Risk
Audit GitHub Releases trust model, signatures/checksums, asset selection, zip extraction assumptions, rollback correctness, stale UI cache handling, partial update states, dependency pins without hashes, PyInstaller pruning, and CI release gates.

9. Logging/Diagnostics Risk
Scrutinize logging deeply. Are logs enough to debug field failures? Do they leak tokens, cookies, report data, PII, internal URLs, filesystem details, screenshots, HTML snapshots, or auth state? Review rotation, crash logs, update helper logs, support bundle contents, UI log mirroring, thread labels, swallowed exceptions, and user-facing error/log-detail mapping.

10. Spreadsheet/PDF Correctness Risk
Audit formula injection, CSV injection, Excel row/sheet/formula limits, schema drift, skipped-file accounting, route extraction, PDF parsing heuristics, cancellation mid-write, file-lock failures, self-check validity, and formulas-vs-values parity.

11. Code Structure / Massive Script Audit
Assess whether massive scripts should be broken down. Do not refactor. Identify which modules are too large or multi-responsibility, which boundaries would reduce risk, which splits would be harmful, and what behavioral contracts would need protection before any split.

12. Testing/Release Process Audit
Review current verification only after understanding the code risks. Then identify what testing process is missing or insufficient.
Do not start by prescribing a full testing architecture. Instead:
- Tie each testing recommendation to specific risks found in code (cite the finding ID).
- Decide whether the app needs unit tests, golden workbook tests, fake-site browser tests, GUI bridge tests, updater swap tests, packaged-app tests, static/security checks, manual release gates, managed-laptop emulator, DLP scanning, endpoint-security smoke checks, or IT-approval artifacts based on evidence.
- Consider that real work laptops cannot currently be used for testing. If that creates material release risk, explain what kinds of emulation or staging would be justified and why.
- Consider that the target website source can later be used to build a stronger fake-site harness, selector contract tests, report fixtures, and schema mocks.
- Separate "must-have before release," "useful but not blocking," and "probably overkill."
- Identify what existing release gates are meaningful and what they fail to cover.

13. Verification Gap
Do not merely say "add tests." Identify exact unguarded behavior and what test/fixture would expose it.

14. Security Baseline
Apply OWASP-style review thinking adapted to a local desktop app: input validation, output encoding, auth/session handling, data protection, error/logging, communications, dependency/supply chain, file management, screenshots, support bundles, endpoint-security friendliness, and self-update.

Deliverable format:
0. Report header — write the report to a file named code-review/AUDIT-<agent>-<short-sha>.md (e.g. code-review/AUDIT-claude-3adcd9d.md); do not commit it. Begin with: audited HEAD SHA, branch, dirty/clean, the <latest_tag> you diffed against, whether you used subagents and how you split the work, and a summary table of ALL findings: ID | Severity | file > symbol | one-line | Confidence. If the report risks running long, complete every P0/P1 finding before spending budget on P2/P3.

1. Executive Risk Map: 8-12 bullets, highest-risk first (each ending with its finding ID).
2. Version/Release Delta: what code was audited (the SHA) vs latest release context.
3. Findings: P0/P1/P2/P3. Each finding MUST include: stable slug ID; severity; file > function/symbol anchor; a short VERBATIM code snippet as evidence; user/security/IT impact; reproduction or how-to-verify; confidence (High/Medium/Low). A finding with no quoted code does not belong here — move it to section 10.
4. Website Automation Contract Risks: where website-source-backed tests or selectors would materially help later.
5. Structural Audit: massive modules and whether decomposition is warranted.
6. Logging Audit: sufficiency, privacy, support bundle, screenshots/HTML, rotation, diagnosability.
7. IT / DLP / Endpoint-Security Audit: what could get flagged, why, and confidence.
8. Testing/Release Process Audit: current gaps and risk-based recommendations only (each tied to a finding ID).
9. Cross-Agent Handoff Pack:
   - Top findings another agent should verify (by ID)
   - Files/sections most worth a second look
   - Findings you are least confident about
   - Coverage & Blind Spots: what you read in full, what you only grepped, and what you did NOT look at and why
   - Commands/tools you ran (and which failed or were unavailable)
   - Assumptions that may be wrong
10. Unproven But Worth Investigating (everything without quoted-code evidence lands here, not in Findings).
11. Verification Gaps.
12. Questions For Maintainer.
13. No patches. No code rewrites. Serious findings first.
